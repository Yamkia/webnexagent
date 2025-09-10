from flask import Flask, render_template, request, jsonify, session
import sys
import os
from secrets import token_hex
import threading
import time
import uuid
import ast
import re

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

def get_app_visibility():
    """
    Gets app visibility from session, initializing from config if not present.
    """
    if 'app_visibility' not in session:
        # Initialize from config file on first load for this session
        session['app_visibility'] = {
            'email': config.ENABLE_EMAIL_APP if AGENT_LOADED else False,
            'odoo': config.ENABLE_ODOO_APP if AGENT_LOADED else False,
            'social_media': config.ENABLE_SOCIAL_MEDIA_APP if AGENT_LOADED else False,
        }
    # Ensure all keys are present if new apps are added to config later
    if 'email' not in session['app_visibility']:
        session['app_visibility']['email'] = config.ENABLE_EMAIL_APP if AGENT_LOADED else False
    if 'odoo' not in session['app_visibility']:
        session['app_visibility']['odoo'] = config.ENABLE_ODOO_APP if AGENT_LOADED else False
    if 'social_media' not in session['app_visibility']:
        session['app_visibility']['social_media'] = config.ENABLE_SOCIAL_MEDIA_APP if AGENT_LOADED else False
    
    session.modified = True
    return session['app_visibility']

@app.route('/')
def index():
    """Serves the main dashboard page."""
    visibility = get_app_visibility()
    # The template name 'index.html' is kept, but now it receives the visibility dict.
    return render_template('index.html', visibility=visibility)

@app.route('/apps/email')
def email_app():
    """Serves the HTML for the Email Assistant app."""
    visibility = get_app_visibility()
    if not visibility.get('email'):
        return render_template('app_disabled.html', app_name="Email Assistant", visibility=visibility), 403

    # Initialize chat history in the session if it doesn't exist.
    if 'chat_history' not in session:
        session['chat_history'] = [] # Stored as a serializable list
    welcome_message = "Welcome! I'm your business assistant. How can I help you manage your emails today?"
    return render_template('email_app.html', welcome_message=welcome_message, visibility=visibility)

@app.route('/apps/odoo')
def odoo_app():
    """Serves the HTML for the Odoo Environments app."""
    visibility = get_app_visibility()
    if not visibility.get('odoo'):
        return render_template('app_disabled.html', app_name="Odoo Environments", visibility=visibility), 403
    return render_template('odoo_app.html', visibility=visibility)

@app.route('/apps/social_media')
def social_media_app():
    """Serves the HTML for the Social Media app."""
    visibility = get_app_visibility()
    if not visibility.get('social_media'):
        return render_template('app_disabled.html', app_name="Social Media Suite", visibility=visibility), 403
    return render_template('social_media_app.html', visibility=visibility)

def _create_real_environment(job_id, modules):
    """A background task that creates a real Odoo environment using Docker."""
    job = JOBS[job_id]
    log = job['log']

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

        log.append(f"Creating Docker network: {network_name}")
        network = client.networks.create(network_name, driver="bridge")
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

        log.append("Provisioning Odoo container (odoo:17.0)...")
        module_string = ",".join(modules)

        # Construct the command for Odoo.
        # The --database flag specifies the database to create/use.
        # The --init flag installs modules into that database.
        # This automates the setup and bypasses the manual database creation screen.
        odoo_command = f"--database={db_name}"
        if module_string:
            odoo_command += f" --init={module_string}"

        odoo_container = client.containers.run(
            "odoo:17.0",
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

    except Exception as e:
        log.append(f"❌ An unexpected error occurred: {str(e)}")
        job['status'] = 'failed'
        log.append("Attempting to clean up created resources...")
        for container_name in [odoo_container_name, db_container_name]:
            try: client.containers.get(container_name).remove(force=True); log.append(f"Removed container: {container_name}")
            except docker.errors.NotFound: pass
        try: client.networks.get(network_name).remove(); log.append(f"Removed network: {network_name}")
        except docker.errors.NotFound: pass


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

    success, agent_output = process_agent_request(prompt, [])

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

@app.route('/apps/manage')
def manage_apps():
    """Serves the page for managing app visibility."""
    visibility = get_app_visibility()
    return render_template('manage_apps.html', visibility=visibility)

@app.route('/apps/toggle', methods=['POST'])
def toggle_app_visibility():
    """Toggles the visibility of a given app in the session."""
    app_name = request.json.get('app_name')
    if not app_name:
        return jsonify({'error': 'No app name provided'}), 400
    
    visibility = get_app_visibility() # Ensures it's initialized
    
    if app_name in visibility:
        visibility[app_name] = not visibility[app_name]
        session['app_visibility'] = visibility
        session.modified = True
        return jsonify({'success': True, 'new_state': visibility})
    else:
        return jsonify({'error': f'Unknown app: {app_name}'}), 404

@app.route('/odoo/execute', methods=['POST'])
def odoo_execute():
    """Executes a plan to create an Odoo environment."""
    modules = request.json.get('modules')
    if not modules:
        return jsonify({'error': 'No modules provided for execution.'}), 400
    
    job_id = uuid.uuid4().hex
    JOBS[job_id] = {
        'status': 'pending',
        'log': ['Request to create environment received.'],
        'url': None # Initialize the URL field
    }

    # Start the background task
    thread = threading.Thread(target=_create_real_environment, args=(job_id, modules))
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

    success, agent_output = process_agent_request(prompt, [])
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
    success, agent_output = process_agent_request(prompt, [])

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

    # Deserialize history from session for the agent to use.
    chat_history = deserialize_history(session.get('chat_history', []))
    success, agent_output = process_agent_request(user_input, chat_history)

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

        return jsonify({'response': html_output})
    else:
        # The error message from process_agent_request is already formatted.
        return jsonify({'error': agent_output}), 500

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
    success, agent_output = process_agent_request(edit_prompt, [])

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
