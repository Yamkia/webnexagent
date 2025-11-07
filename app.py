from flask import Flask, render_template, request, jsonify, session
from jinja2 import TemplateNotFound
import sys
import os
from secrets import token_hex
import threading
import time
import uuid
import ast
import re
import random
import ipaddress

import markdown
# --- Setup Python Path ---
# This ensures that the script can find other modules in the project (e.g., main, config)
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# --- Define asset paths explicitly for robustness ---
template_dir = os.path.join(project_root, 'templates')
static_dir = os.path.join(project_root, 'static')

JOBS = {} # In-memory job store. For production, use Redis or a database.

# --- Import Agent Logic ---
# We wrap this in a try-except block to allow the Flask server to start and
# display a helpful error message on the frontend if configuration is missing.
try:
    from main import process_agent_request
    from langchain_core.messages import HumanMessage, AIMessage
    import config
    AGENT_LOADED = True
except (ValueError, ImportError) as e:
    # This typically happens if .env is not configured or dependencies are missing.
    AGENT_LOAD_ERROR = str(e)
    AGENT_LOADED = False
    print(f"--- AGENT FAILED TO LOAD ---", file=sys.stderr)
    print(f"Error: {AGENT_LOAD_ERROR}", file=sys.stderr)
    print("The web UI will run, but the agent will be disabled. Check your .env file and dependencies.", file=sys.stderr)
    
    # Define dummy classes/functions so the rest of the app doesn't crash
    def process_agent_request(prompt, chat_history):
        return False, f"Agent could not be loaded. Please check the server logs. Error: {AGENT_LOAD_ERROR}"
    
    class HumanMessage:
        def __init__(self, content): self.content = content
    class AIMessage:
        def __init__(self, content): self.content = content

# --- Docker Dependency Check ---
try:
    import docker
    DOCKER_LOADED = True
except ImportError:
    DOCKER_LOAD_ERROR = "The 'docker' Python package is not installed. Please run 'pip install docker' in your terminal."
    DOCKER_LOADED = False
    print("--- DOCKER SUPPORT FAILED TO LOAD ---", file=sys.stderr)
    print(f"Error: {DOCKER_LOAD_ERROR}", file=sys.stderr)
    print("The Odoo environment creation will show an error until the package is installed.", file=sys.stderr)

# --- Serialization/Deserialization for Chat History ---
# This is needed because Flask sessions require JSON-serializable data,
# and LangChain's message objects are not.
def serialize_history(history):
    """Converts LangChain message objects to a JSON-serializable list."""
    serializable = []
    for msg in history:
        if isinstance(msg, HumanMessage):
            serializable.append({"type": "human", "content": msg.content})
        elif isinstance(msg, AIMessage):
            serializable.append({"type": "ai", "content": msg.content})
    return serializable

def deserialize_history(serializable_history):
    """Converts a JSON-serializable list back to LangChain message objects."""
    history = []
    for msg_data in serializable_history:
        if msg_data.get("type") == "human":
            history.append(HumanMessage(content=msg_data.get("content")))
        elif msg_data.get("type") == "ai":
            history.append(AIMessage(content=msg_data.get("content")))
    return history

app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)
# A secret key is required to use sessions in Flask.
# In a production app, this should be a long, random, and secret string.
app.secret_key = token_hex(16)

@app.route('/')
def index():
    """Serves the main dashboard page."""
    # Initialize chat history in the session if it doesn't exist.
    if 'chat_history' not in session:
        session['chat_history'] = [] # Stored as a serializable list
    
    # Determine which apps are enabled from the config
    # This will be passed to the main template to conditionally show UI elements.
    enabled_apps = {
        'email': config.ENABLE_EMAIL_APP if AGENT_LOADED else False,
        'odoo': config.ENABLE_ODOO_APP if AGENT_LOADED else False,
        'social_media': config.ENABLE_SOCIAL_MEDIA_APP if AGENT_LOADED else False,
    }
    
    return render_template('index.html', enabled_apps=enabled_apps)


@app.route('/apps/<app_name>')
def serve_app(app_name):
    """Serve a specific app fragment (e.g., 'odoo' -> 'odoo_app.html').
    This endpoint is used by the frontend JS to load app HTML into the dashboard.
    """
    enabled_apps = {
        'email': config.ENABLE_EMAIL_APP if AGENT_LOADED else False,
        'odoo': config.ENABLE_ODOO_APP if AGENT_LOADED else False,
        'social_media': config.ENABLE_SOCIAL_MEDIA_APP if AGENT_LOADED else False,
    }
    template_file = f"{app_name}_app.html"
    try:
        return render_template(template_file, visibility=enabled_apps)
    except TemplateNotFound:
        return jsonify({'error': 'App not found'}), 404

def _create_real_environment(job_id, modules, website_design=None, odoo_version='19.0', branding_modules=None, branding_repos=None):
    """A background task that creates a real Odoo environment using Docker."""
    job = JOBS[job_id]
    log = job['log']

    # If branding_repos provided, attempt to clone them into an extra_addons dir
    extra_addons_dir = None
    if branding_repos:
        try:
            import shutil, subprocess, tempfile
            log.append(f"Preparing branding repos ({len(branding_repos)})...")
            tmp_root = os.path.join(tempfile.gettempdir(), name_prefix)
            extra_addons_dir = os.path.join(tmp_root, 'extra_addons')
            os.makedirs(extra_addons_dir, exist_ok=True)
            for repo in branding_repos:
                try:
                    repo_name = os.path.splitext(os.path.basename(repo))[0]
                    dest = os.path.join(extra_addons_dir, repo_name)
                    if os.path.exists(dest):
                        log.append(f"Branding repo already present: {repo_name}")
                        continue
                    log.append(f"Cloning branding repo: {repo}")
                    subprocess.check_call(['git', 'clone', '--depth', '1', repo, dest], cwd=extra_addons_dir)
                    log.append(f"Cloned {repo_name}")
                except Exception as cre:
                    log.append(f"Warning: failed to clone {repo}: {cre}")
        except Exception as e:
            log.append(f"Error preparing branding repos: {e}")
            extra_addons_dir = None

    # Ensure website_design is included if present
    if website_design and website_design not in modules:
        modules.append(website_design)

    # Add any specified branding modules to the list of modules to install
    if branding_modules and isinstance(branding_modules, list):
        modules.extend([bm for bm in branding_modules if bm not in modules])

    if not DOCKER_LOADED:
        log.append(f"❌ Configuration Error: {DOCKER_LOAD_ERROR}")
        job['status'] = 'failed'
        return

    try:
        client = docker.from_env()
        client.ping() # Check if Docker is running
    except Exception as e:
        log.append("❌ Docker Error: Could not connect to Docker daemon.")
        log.append("Please ensure Docker Desktop is installed and running.")
        log.append(f"Details: {str(e)}")
        job['status'] = 'failed'
        return

    # Use a truncated job_id for shorter, Docker-friendly names
    name_prefix = f"odoo-{job_id[:8]}"
    db_container_name = f"{name_prefix}-db"
    odoo_container_name = f"{name_prefix}-app"
    network_name = f"{name_prefix}-net"
    db_name = f"odoo-{job_id[:8]}-db" # Define a unique database name for Odoo
    master_password = uuid.uuid4().hex[:12]
    db_password = uuid.uuid4().hex[:12]

    try:
        log.append("Starting environment creation...")
        job['status'] = 'running'
        time.sleep(1)

        try:
            log.append(f"Creating Docker network: {network_name}")
            network = client.networks.create(network_name, driver="bridge")
        except docker.errors.APIError as e:
            if "fully subnetted" in str(e):
                log.append("⚠️ Default network pool exhausted. Attempting to create network with a custom subnet...")
                # --- Intelligent Subnet Finding ---
                # Deterministic search for a free subnet instead of random guessing.
                found_subnet = None
                try:
                    # 1. Get all existing network subnets from Docker.
                    existing_networks = {
                        ipaddress.ip_network(config['Subnet'])
                        for net in client.networks.list() if net.attrs.get('IPAM') and net.attrs['IPAM'].get('Config')
                        for config in net.attrs['IPAM']['Config'] if config.get('Subnet')
                    }
                    
                    # 2. Sequentially search a very large private IP space to guarantee finding a free subnet.
                    # We will check 172.17.x.x through 172.31.x.x.
                    for second_octet in range(17, 32):
                        search_range = ipaddress.ip_network(f'172.{second_octet}.0.0/16')
                        for candidate_subnet in search_range.subnets(new_prefix=24):
                            is_overlap = any(candidate_subnet.overlaps(net) for net in existing_networks)
                            if not is_overlap:
                                log.append(f"Found non-overlapping subnet: {str(candidate_subnet)}")
                                found_subnet = str(candidate_subnet)
                                break # Exit inner loop
                        if found_subnet:
                            break # Exit outer loop
                
                except Exception as find_err:
                    log.append(f"⚠️ An unexpected error occurred while searching for a subnet: {find_err}")
                    # Fall through to the 'if not found_subnet' block

                if found_subnet:
                    gateway_str = str(ipaddress.ip_network(found_subnet)[1])
                    ipam_pool = docker.types.IPAMPool(subnet=found_subnet, gateway=gateway_str)
                    ipam_config = docker.types.IPAMConfig(pool_configs=[ipam_pool])
                    network = client.networks.create(network_name, driver="bridge", ipam=ipam_config)
                    log.append(f"✅ Successfully created network with custom subnet ({found_subnet}).")
                else:
                    # If all retries fail, raise a more informative exception.
                    error_message = (
                        "Failed to find an available network subnet after multiple attempts. "
                        "This suggests heavy Docker network usage on your system. "
                        "Please try cleaning up unused networks with 'docker network prune' or inspect existing network configurations with 'docker network ls'."
                    )
                    raise Exception(error_message)
            else:
                raise # Re-raise the original error if it's not the one we can handle.
        time.sleep(1)

        log.append("Provisioning PostgreSQL database container (postgres:15)...")
        db_container = client.containers.run(
            "postgres:15",
            name=db_container_name,
            hostname=db_container_name,
            network=network.name,
            environment={
                'POSTGRES_USER': 'odoo',
                'POSTGRES_PASSWORD': db_password,
                'POSTGRES_DB': 'postgres',
            },
            detach=True,
        )
        log.append(f"Database container '{db_container.short_id}' started.")
        log.append(f"ℹ️ Database user: 'odoo'")
        log.append(f"ℹ️ Database password: {db_password}")
        log.append("Waiting for database to initialize...")
        time.sleep(10) # Give postgres time to initialize

        odoo_image = f"odoo:{odoo_version}"
        log.append(f"Provisioning Odoo container ({odoo_image})...")
        module_string = ",".join(modules)

        # Construct the command for Odoo.
        # The --database flag specifies the database to create/use.
        # The --init flag installs modules into that database.
        # This automates the setup and bypasses the manual database creation screen.
        odoo_command = f"--database={db_name}"
        if module_string:
            odoo_command += f" --init={module_string}"
        # If we prepared an extra_addons dir above, add it to the addons path
        if extra_addons_dir:
            odoo_command += f" --addons-path=/mnt/extra-addons,/usr/lib/python3/dist-packages/odoo/addons"

        # Prepare volume mounts
        volumes = None
        if extra_addons_dir and os.path.exists(extra_addons_dir):
            volumes = { extra_addons_dir: {'bind': '/mnt/extra-addons', 'mode': 'rw'} }

        odoo_container = client.containers.run(
            odoo_image,
            name=odoo_container_name,
            network=network.name,
            ports={'8069/tcp': None}, # Let Docker assign a random available host port
            environment={
                'HOST': db_container_name,
                'USER': 'odoo',
                'PASSWORD': db_password,
                'MASTER_PASSWORD': master_password,
            },
            command=odoo_command,
            detach=True,
            volumes=volumes
        )
        log.append(f"Odoo container '{odoo_container.short_id}' started.")
        log.append(f"ℹ️ Odoo master password set to: {master_password} (for database management).")
        log.append("Waiting for Odoo to initialize (this may take a few minutes)...")
        time.sleep(45) # Odoo startup can be slow, especially with new modules

        odoo_container.reload() # Reload container object to get updated port info
        host_port = odoo_container.ports['8069/tcp'][0]['HostPort']
        url = f"http://localhost:{host_port}"

        log.append(f"✅ Environment created successfully! Access it at: {url}")
        log.append("--- Odoo Application Login ---")
        log.append("Email: admin")
        log.append("Password: admin")
        log.append("(It is recommended to change this password after your first login.)")
        log.append("------------------------------")
        job['status'] = 'completed'
        job['url'] = url

        # If branding modules were provided as repos, attempt to chown and install them via XML-RPC
        if extra_addons_dir:
            try:
                log.append("Adjusting ownership for extra addons and attempting theme install...")
                # chown inside container to match odoo uid (typically 1000)
                try:
                    odoo_container.exec_run(['chown', '-R', '1000:1000', '/mnt/extra-addons'])
                except Exception:
                    # Not fatal; continue
                    pass

                # Wait a bit for Odoo to be ready to accept XML-RPC calls
                import xmlrpc.client, time
                common = xmlrpc.client.ServerProxy(f'http://127.0.0.1:{host_port}/xmlrpc/2/common')
                models = xmlrpc.client.ServerProxy(f'http://127.0.0.1:{host_port}/xmlrpc/2/object')
                ready = False
                for _ in range(40):
                    try:
                        common.version()
                        ready = True
                        break
                    except Exception:
                        time.sleep(2)
                if not ready:
                    log.append('Branding install: Odoo did not respond to XML-RPC in time.')
                else:
                    # login as admin (default admin password is 'admin' in this flow)
                    try:
                        uid = common.authenticate(db_name, 'admin', 'admin', {})
                        if not uid:
                            log.append('Branding install: failed to authenticate to Odoo XML-RPC (admin).')
                        else:
                            # attempt to find any new modules in the extra_addons dir and install them
                            # This will try to install any modules that match names in branding_modules
                            if branding_modules:
                                for mod in branding_modules:
                                    try:
                                        mids = models.execute_kw(db_name, uid, 'admin', 'ir.module.module', 'search', [[['name','=',mod]]])
                                        if mids:
                                            models.execute_kw(db_name, uid, 'admin', 'ir.module.module', 'button_immediate_install', [mids])
                                            log.append(f'Branding module {mod} install triggered.')
                                    except Exception as imex:
                                        log.append(f'Error installing branding module {mod}: {imex}')
                            else:
                                # Attempt to auto-detect modules inside /mnt/extra-addons and install them
                                try:
                                    # list modules by searching for manifest files
                                    # This is a simple heuristic: search for module folders with __manifest__.py
                                    for root, dirs, files in os.walk(extra_addons_dir):
                                        if '__manifest__.py' in files:
                                            module_name = os.path.basename(root)
                                            try:
                                                mids = models.execute_kw(db_name, uid, 'admin', 'ir.module.module', 'search', [[['name','=',module_name]]])
                                                if mids:
                                                    models.execute_kw(db_name, uid, 'admin', 'ir.module.module', 'button_immediate_install', [mids])
                                                    log.append(f'Auto-install triggered for branding module: {module_name}')
                                            except Exception as autoex:
                                                log.append(f'Auto-install error for {module_name}: {autoex}')
                                except Exception as walkex:
                                    log.append(f'Error scanning extra_addons for modules: {walkex}')
                    except Exception as authex:
                        log.append(f'Branding install authentication error: {authex}')
            except Exception as bex:
                log.append(f'Branding post-install step failed: {bex}')

    except Exception as e:
        error_str = str(e)
        if "fully subnetted" in error_str:
            log.append("❌ Docker Error: Docker has run out of network address pools.")
            log.append("This is a common issue that can be resolved by cleaning up unused Docker networks.")
            log.append("Please run the following command in your terminal and then try again:")
            log.append("-> docker network prune")
        else:
            log.append(f"❌ An unexpected error occurred: {error_str}")

        job['status'] = 'failed'
        log.append("Attempting to clean up created resources...")
        # Use a more robust cleanup method by finding all resources with the job's prefix.
        # This ensures that even partially created environments are fully removed.
        try:
            # Clean up containers
            for container in client.containers.list(all=True, filters={"name": f"{name_prefix}*"}):
                log.append(f"Removing container: {container.name} ({container.short_id})")
                container.remove(force=True)
            
            # Clean up networks
            for net in client.networks.list(filters={"name": f"{name_prefix}*"}):
                log.append(f"Removing network: {net.name}")
                net.remove()
            
            log.append("Cleanup complete.")
        except Exception as cleanup_error:
            log.append(f"⚠️ An error occurred during cleanup: {str(cleanup_error)}")
            log.append("Some Docker resources may need to be removed manually.")



@app.route('/odoo/plan', methods=['POST'])
def odoo_plan():
    """Handles a request to create an Odoo environment plan."""
    data = request.json
    business_need = data.get('business_need')
    plan_type = data.get('plan_type', 'community') # Default to community

    if not business_need:
        return jsonify({'error': 'No business need provided'}), 400

    if plan_type == 'community':
        prompt = f"A user wants to create an Odoo environment. Analyze the following business need and use the `plan_odoo_environment` tool to create a plan: '{business_need}'"
    elif plan_type == 'online':
        prompt = f"""
A user wants to start a free trial on Odoo Online. Based on their business need, determine the appropriate Odoo applications.
Business Need: "{business_need}"

Your task is to generate a URL to pre-select these apps on the Odoo trial page.
The base URL is `https://www.odoo.com/trial`. Apps are added with `?app_names=app1,app2,app3`.
The app names must be the technical names (e.g., `crm`, `sale_management`, `website`, `mrp`, `account_accountant`).
Also provide a short, user-friendly summary of the apps you selected.

Return a JSON object with two keys: "summary" and "url".
Example:
{{
  "summary": "For your needs, I recommend starting with the CRM, Sales, and Website apps.",
  "url": "https://www.odoo.com/trial?app_names=crm,sale_management,website"
}}
You MUST return ONLY the JSON object.
"""
    elif plan_type == 'sh':
        prompt = f"""
A user wants to deploy a project on Odoo.sh. Based on their business need, generate a step-by-step guide for them.
Business Need: "{business_need}"

The guide should be in Markdown format and include:
1.  A list of recommended technical Odoo module names (e.g., `mrp`, `quality_control`).
2.  Instructions on how to create a new GitHub repository.
3.  Instructions on how to add the module names to a `requirements.txt` or explain how to add them as submodules.
4.  A brief overview of how to deploy that repository on Odoo.sh.

Return ONLY the Markdown text for the guide.
"""
    else:
        return jsonify({'error': 'Invalid plan type'}), 400

    success, agent_output, _ = process_agent_request(prompt, [])

    if success:
        if plan_type == 'online':
            # The agent should return JSON. Let's try to parse it.
            try:
                dict_match = re.search(r"\{.*\}", agent_output, re.DOTALL)
                if dict_match:
                    plan_data = ast.literal_eval(dict_match.group(0))
                    if isinstance(plan_data, dict) and 'url' in plan_data:
                        return jsonify(plan_data)
                return jsonify({'error': 'The agent could not generate a valid plan. Please try again.', 'summary': agent_output})
            except (ValueError, SyntaxError):
                return jsonify({'error': 'The agent response was not in the expected format.', 'summary': agent_output})

        elif plan_type == 'sh':
            # For .sh, the output is markdown text. Convert it to HTML for better rendering.
            guide_html = markdown.markdown(agent_output, extensions=['fenced_code', 'tables'])
            return jsonify({'guide_html': guide_html})

        else: # Community
            dict_match = re.search(r"\{.*\}", agent_output, re.DOTALL)
            if dict_match:
                dict_str = dict_match.group(0)
                try:
                    plan_data = ast.literal_eval(dict_str)
                    if isinstance(plan_data, dict) and 'modules' in plan_data:
                        return jsonify(plan_data)
                except (ValueError, SyntaxError):
                    pass

            parsed_modules = []
            list_items = re.findall(r"^\s*(?:\d+\.|\*|-)\s+(.*)", agent_output, re.MULTILINE)

            for item in list_items:
                if ':' in item:
                    parts = item.split(':', 1)
                    header = parts[0]
                    if 'module' in header.lower() or 'select' in header.lower():
                        modules_str = parts[1]
                        potential_modules = [m.strip() for m in modules_str.split(',')]
                        for mod in potential_modules:
                            if mod:
                                mod_cleaned = re.sub(r'[\*`]', '', mod).strip()
                                technical_name = mod_cleaned.lower().replace(' ', '_')
                                if technical_name and technical_name not in parsed_modules:
                                    parsed_modules.append(technical_name)
                        continue

                module_name_candidate = re.split(r'\s*[:\-]\s+', item, 1)[0]
                module_name_candidate = re.sub(r'[\*`]', '', module_name_candidate).strip()

                if module_name_candidate and len(module_name_candidate.split()) <= 4:
                    technical_name = module_name_candidate.lower().replace(' ', '_')
                    if technical_name and technical_name not in parsed_modules:
                        parsed_modules.append(technical_name)

            return jsonify({'summary': agent_output, 'modules': list(set(parsed_modules))})
    else:
        return jsonify({'error': agent_output}), 500

@app.route('/odoo/execute', methods=['POST'])
def odoo_execute():
    """Executes a plan to create an Odoo environment."""
    modules = request.json.get('modules')
    website_design = request.json.get('website_design')
    odoo_version = request.json.get('odoo_version', '19.0') # Get Odoo version, default to 19.0
    branding_modules = request.json.get('branding_modules', []) # New: Get branding modules

    if not modules:
        return jsonify({'error': 'No modules provided for execution.'}), 400
    
    job_id = uuid.uuid4().hex
    JOBS[job_id] = {
        'status': 'pending',
        'log': ['Request to create environment received.'], 'url': None # Initialize the URL field
    }

    # Start the background task
    thread = threading.Thread(target=_create_real_environment, args=(job_id, modules, website_design, odoo_version, branding_modules))
    thread.start()

    return jsonify({'job_id': job_id})

@app.route('/odoo/job_status/<job_id>')
def odoo_job_status(job_id):
    """Gets the status of a running job."""
    job = JOBS.get(job_id)
    if not job:
        return jsonify({'status': 'not_found'}), 404
    return jsonify(job)

@app.route('/social/generate_content', methods=['POST'])
def social_generate_content():
    """Handles a request to generate social media content (post or video script)."""
    data = request.json
    content_type = data.get('content_type')
    topic = data.get('topic')

    if not all([content_type, topic]):
        return jsonify({'error': 'Missing content type or topic.'}), 400

    if content_type == 'post':
        platform = data.get('platform', 'social media')
        style = data.get('style', 'informative')
        prompt = f"Use the `create_social_media_post` tool to create a '{style}' post for '{platform}' about the topic: '{topic}'."
    elif content_type == 'video_script':
        audience = data.get('audience', 'a general audience')
        prompt = f"Use the `generate_short_form_video_script` tool to create a video script about '{topic}' for the target audience: '{audience}'."
    else:
        return jsonify({'error': 'Invalid content type specified.'}), 400

    success, agent_output, _ = process_agent_request(prompt, [])
    if success:
        return jsonify({'content': agent_output})
    else:
        return jsonify({'error': agent_output}), 500

@app.route('/social/find_leads', methods=['POST'])
def social_find_leads():
    """Handles a request to find business leads."""
    data = request.json
    business_type = data.get('business_type')
    location = data.get('location')

    if not all([business_type, location]):
        return jsonify({'error': 'Missing business type or location.'}), 400

    prompt = f"Use the `find_business_leads` tool to find leads for business type '{business_type}' in '{location}'."
    success, agent_output, _ = process_agent_request(prompt, [])

    if success:
        # The agent output might be a string representation of a list of dicts.
        # We need to parse it robustly.
        try:
            # Use regex to find the list within any conversational text.
            list_match = re.search(r"\[.*\]", agent_output, re.DOTALL)
            if list_match:
                leads_list = ast.literal_eval(list_match.group(0))
                return jsonify({'leads': leads_list})
            else: # If no list is found, return the raw text as a message.
                return jsonify({'leads': [], 'message': agent_output})
        except (ValueError, SyntaxError): # If parsing fails, return the raw text.
            return jsonify({'leads': [], 'message': agent_output})
    else:
        return jsonify({'error': agent_output}), 500

@app.route('/chat', methods=['POST'])
def chat():
    """Handles chat messages from the user."""
    user_input = request.json.get('message')
    if not user_input:
        return jsonify({'error': 'No message provided'}), 400

    try:
        # Deserialize history from session for the agent to use.
        chat_history = deserialize_history(session.get('chat_history', []))
        success, agent_output, verbose_log = process_agent_request(user_input, chat_history)

        if success:
            # Keep history from growing indefinitely in this simple example
            if len(chat_history) > 20:
                chat_history = chat_history[-20:]
                
            # Store the raw markdown output in the history for the agent's context
            chat_history.append(HumanMessage(content=user_input))
            chat_history.append(AIMessage(content=agent_output))

            # Serialize history before saving it back to the session.
            session['chat_history'] = serialize_history(chat_history)

            # Convert the agent's markdown response to HTML for rendering in the browser
            html_output = markdown.markdown(agent_output, extensions=['fenced_code', 'tables'])

            return jsonify({'response': html_output, 'verbose_log': verbose_log})
        else:
            # The error message from process_agent_request is already formatted.
            return jsonify({'error': agent_output, 'verbose_log': verbose_log}), 500

    except Exception as e:
        # This is a safety net. If any unexpected error occurs, log it and send a proper JSON error.
        print(f"--- UNHANDLED EXCEPTION IN /chat ENDPOINT ---", file=sys.stderr)
        print(f"Error: {e}", file=sys.stderr)
        return jsonify({'error': 'An unexpected server error occurred. Please check the server logs for details.'}), 500

@app.route('/edit_app', methods=['POST'])
def edit_app():
    """Handles a request to edit the UI of an app."""
    data = request.json
    user_request = data.get('user_request')
    app_html = data.get('app_html')

    if not user_request or not app_html:
        return jsonify({'error': 'Missing user request or app HTML.'}), 400

    # A specialized prompt for the UI editing task.
    edit_prompt = f"""
You are an expert front-end web developer specializing in Bootstrap 5. A user wants to modify a part of a web application.

Their request is: "{user_request}"

Here is the current HTML of the application's content area that needs to be modified:
```html
{app_html}
```

Your task is to return the complete, updated HTML for this content area that fulfills the user's request.
- You MUST return ONLY the raw, complete HTML for the content area.
- Do NOT include ```html ... ``` markers or any other text in your output.
- Ensure the resulting HTML is valid and maintains the structure of the original components.
- If the request is unclear or impossible (e.g., 'make it fly'), return the original HTML unmodified.
"""

    # We use the existing agent infrastructure but with a very specific, one-off prompt.
    # We don't need chat history for this task.
    success, agent_output, _ = process_agent_request(edit_prompt, [])

    if success:
        # The agent's output should be the raw HTML.
        return jsonify({'suggested_html': agent_output})
    else:
        return jsonify({'error': agent_output}), 500

if __name__ == '__main__':
    # Using port 5001 to avoid potential conflicts with other services.
    # The `debug=True` setting enables auto-reloading when you save changes.
    print("--- Web-Nexus Agent UI ---")
    print("Starting Flask server...")
    print("Access the UI at: http://127.0.0.1:5001")
    if not AGENT_LOADED:
        print("\nWARNING: Agent is NOT loaded due to a configuration error. The UI will show an error message.")
    app.run(debug=True, port=5001)
