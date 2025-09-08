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
    return render_template('index.html')

@app.route('/apps/email')
def email_app():
    """Serves the HTML for the Email Assistant app."""
    # Initialize chat history in the session if it doesn't exist.
    if 'chat_history' not in session:
        session['chat_history'] = [] # Stored as a serializable list
    welcome_message = "Welcome! I'm your business assistant. How can I help you manage your emails today?"
    return render_template('email_app.html', welcome_message=welcome_message)

@app.route('/apps/odoo')
def odoo_app():
    """Serves the HTML for the Odoo Environments app."""
    return render_template('odoo_app.html')

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
        log.append("Waiting for database to initialize...")
        time.sleep(10) # Give postgres time to initialize

        log.append("Provisioning Odoo container (odoo:17.0)...")
        module_string = ",".join(modules)

        odoo_container = client.containers.run(
            "odoo:17.0",
            name=odoo_container_name,
            network=network.name,
            ports={'8069/tcp': None}, # Let Docker assign a random available host port
            environment={
                'HOST': db_container_name,
                'USER': 'odoo',
                'PASSWORD': db_password,
            },
            command=f"--init={module_string}" if module_string else "",
            detach=True,
        )
        log.append(f"Odoo container '{odoo_container.short_id}' started.")
        log.append("Waiting for Odoo to initialize (this may take a few minutes)...")
        time.sleep(45) # Odoo startup can be slow, especially with new modules

        odoo_container.reload() # Reload container object to get updated port info
        host_port = odoo_container.ports['8069/tcp'][0]['HostPort']
        url = f"http://localhost:{host_port}"

        log.append(f"✅ Environment created successfully! Access it at: {url}")
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
    business_need = request.json.get('business_need')
    if not business_need:
        return jsonify({'error': 'No business need provided'}), 400

    prompt = f"A user wants to create an Odoo environment. Analyze the following business need and use the `plan_odoo_environment` tool to create a plan: '{business_need}'"
    
    success, agent_output = process_agent_request(prompt, [])

    if success:
        # The agent might wrap the dictionary output in conversational text,
        # contrary to the prompt. We'll robustly extract the dictionary.
        # The regex looks for a string that starts with { and ends with }, spanning multiple lines.
        dict_match = re.search(r"\{.*\}", agent_output, re.DOTALL)
        
        if dict_match:
            dict_str = dict_match.group(0)
            try:
                plan_data = ast.literal_eval(dict_str)
                if isinstance(plan_data, dict) and 'modules' in plan_data:
                    # If parsing is successful, return the structured data.
                    # The frontend expects 'summary' and 'modules'. The tool provides both.
                    return jsonify(plan_data)
            except (ValueError, SyntaxError):
                # If parsing the extracted string fails, we fall through and treat
                # the whole agent output as a summary.
                pass

        # If no dictionary is found or if parsing fails, return the full agent
        # output as the summary and an empty list for modules. This gracefully
        # handles cases where the agent provides a text-only answer.
        return jsonify({'summary': agent_output, 'modules': []})
    else:
        return jsonify({'error': agent_output}), 500

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
