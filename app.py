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
import json

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
DEFAULT_WEBSITE_HELPER_CSS = os.path.join('static', 'website_helper', 'generated_theme.css')
ENV_HISTORY_FILE = os.path.join(project_root, 'env_history.json')

def _resolve_project_path(relative_path: str) -> str:
    """Resolve a repo-relative path safely inside the project root."""
    normalized = os.path.normpath(os.path.join(project_root, relative_path))
    if not normalized.startswith(project_root):
        raise ValueError('Target path must stay within the project directory')
    return normalized


# (Environment control endpoints are defined below after the Flask `app` object is created.)

def _load_env_history():
    """Load recorded environments from env_history.json, newest first."""
    try:
        with open(ENV_HISTORY_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if isinstance(data, list):
                # Sort descending by created_at if present
                return sorted(data, key=lambda x: x.get('created_at', ''), reverse=True)
    except FileNotFoundError:
        return []
    except Exception as e:
        print(f"Failed to load env history: {e}", file=sys.stderr)
        return []


def _save_env_history(envs):
    """Persist environment history list to disk."""
    try:
        with open(ENV_HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(envs, f, indent=2)
    except Exception as e:
        print(f"Failed to save env history: {e}", file=sys.stderr)


def _find_env(db_name):
    """Find environment by db_name from history."""
    if not db_name:
        return None
    needle = str(db_name).lower()
    # First try exact match (case-insensitive)
    for env in _load_env_history():
        name = str(env.get('db_name') or '').lower()
        if name == needle:
            return env

    # Next try startswith or contains (useful when db_name is a prefix or different casing)
    for env in _load_env_history():
        name = str(env.get('db_name') or '').lower()
        if name.startswith(needle) or needle in name:
            return env

    # Finally try matching by URL port or other heuristics
    for env in _load_env_history():
        url = env.get('url') or ''
        if isinstance(url, str) and needle in url.lower():
            return env
    return None

# --- Import Agent Logic ---
# Import configuration first to determine whether the agent should be enabled.
import config

if not getattr(config, 'AGENT_ENABLED', False):
    # Agent explicitly disabled or no provider keys found; do not attempt to import agent libs.
    AGENT_LOADED = False
    AGENT_LOAD_ERROR = 'Agent disabled via configuration (LLM_PROVIDER is none or not set)'
    print(f"--- AGENT DISABLED ---", file=sys.stderr)
    print("Agent is disabled via configuration. The web UI will run, but agent features are disabled.", file=sys.stderr)

    # Define dummy classes/functions so the rest of the app doesn't crash
    def process_agent_request(prompt, chat_history):
        return False, "Agent is disabled by server configuration."

    class HumanMessage:
        def __init__(self, content): self.content = content
    class AIMessage:
        def __init__(self, content): self.content = content

else:
    # Agent is enabled; attempt to import agent-related modules and report failures gracefully.
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

# --- Helper to run docker compose for a specific compose file ---
def _run_compose_file(compose_file, args):
    """Run docker compose with the given compose file and args list. Returns dict {success, output, error}."""
    if not os.path.isfile(compose_file):
        return {'success': False, 'error': 'Compose file not found'}
    base = ['docker', 'compose', '-f', compose_file]
    try:
        # Try modern docker compose
        proc = subprocess.run(base + args, capture_output=True, text=True, timeout=120)
        if proc.returncode == 0:
            return {'success': True, 'output': proc.stdout}
        else:
            # Fall back to docker-compose if available
            proc2 = subprocess.run(['docker-compose', '-f', compose_file] + args, capture_output=True, text=True, timeout=120)
            if proc2.returncode == 0:
                return {'success': True, 'output': proc2.stdout}
            return {'success': False, 'output': proc.stdout + proc2.stdout, 'error': proc.stderr + proc2.stderr}
    except Exception as e:
        return {'success': False, 'error': str(e)}

# Helper to discover a PowerShell executable on PATH (powershell or pwsh)
def _find_powershell_cmd():
    """Return the path to a PowerShell executable (e.g., 'powershell' or 'pwsh'), or None if none found."""
    candidates = ['powershell', 'powershell.exe', 'pwsh', 'pwsh.exe']
    for c in candidates:
        p = shutil.which(c)
        if p:
            return p
    return None

# --- Docker helpers ---
import stat

def _docker_available():
    """Return tuple (available: bool, message: str)."""
    p = shutil.which('docker') or shutil.which('docker.exe')
    if not p:
        return False, "'docker' not found on PATH"
    try:
        proc = subprocess.run([p, 'version'], capture_output=True, text=True, timeout=5)
        if proc.returncode != 0:
            return False, proc.stderr.strip() or 'docker command returned non-zero exit code'
        return True, proc.stdout.splitlines()[0] if proc.stdout else 'docker present'
    except Exception as e:
        return False, str(e)


def _create_docker_environment(name, version='19.0', http_port=8069, pg_user='odoo', pg_password='odoo', pg_host='db', pg_port=5432, admin_password='admin'):
    """Create a Docker-based Odoo environment by writing a docker-compose file and starting it with docker compose.
    Returns a dict with keys: success (bool), message (str), url (optional).
    """
    try:
        repo_root = project_root
        env_dir = os.path.join(repo_root, 'environments', name)
        os.makedirs(env_dir, exist_ok=True)

        compose_path = os.path.join(env_dir, 'docker-compose.yml')
        compose_content = f"""version: '3.8'

services:
  odoo-{name}:
    image: odoo:{version}
    environment:
      POSTGRES_HOST: {pg_host}
      POSTGRES_USER: {pg_user}
      POSTGRES_PASSWORD: {pg_password}
    ports:
      - "{http_port}:8069"
    volumes:
      - ../../addons:/mnt/extra-addons
      - ../../deployable_brand_theme:/mnt/brand_theme
      - odoo_{name}_data:/var/lib/odoo
    depends_on:
      - db

volumes:
  odoo_{name}_data:
"""
        with open(compose_path, 'w', encoding='utf-8') as f:
            f.write(compose_content)

        # Write minimal odoo.conf
        conf_path = os.path.join(env_dir, 'odoo.conf')
        conf_content = f"""[options]
db_host = {pg_host}
db_port = {pg_port}
db_user = {pg_user}
db_password = {pg_password}
dbfilter = ^{name}$
db_name = {name}
addons_path = /mnt/extra-addons,/mnt/brand_theme
logfile = /var/log/odoo/{name}.log
http_port = {http_port}
admin_passwd = {admin_password}
"""
        with open(conf_path, 'w', encoding='utf-8') as f:
            f.write(conf_content)

        # Ensure DB service in root compose is running (if a root docker-compose exists)
        root_compose = os.path.join(repo_root, 'docker-compose.yml')
        docker_cmd = shutil.which('docker') or 'docker'

        # Try to start db in root compose if present and not running
        if os.path.exists(root_compose):
            try:
                ps = subprocess.run([docker_cmd, 'compose', '-f', root_compose, 'ps', '-q', 'db'], capture_output=True, text=True, timeout=10)
                if not ps.stdout.strip():
                    subprocess.run([docker_cmd, 'compose', '-f', root_compose, 'up', '-d', 'db'], check=True)
            except Exception:
                # Not fatal; continue
                pass

        # Start the environment compose
        try:
            subprocess.run([docker_cmd, 'compose', '-f', compose_path, 'up', '-d'], check=True)
        except subprocess.CalledProcessError as e:
            return {'success': False, 'message': f"docker compose failed: {e}", 'compose_path': compose_path}

        # Update env_history.json
        env_entry = {
            'db_name': name,
            'port': http_port,
            'odoo_version': version,
            'url': f'http://localhost:{http_port}',
            'created_at': (time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()))
        }
        envs = _load_env_history() or []
        envs = [e for e in envs if not (e.get('db_name') == env_entry['db_name'] and e.get('port') == env_entry['port'])]
        envs.insert(0, env_entry)
        _save_env_history(envs)

        return {'success': True, 'message': f"Created Docker-based Odoo environment '{name}'", 'url': env_entry['url']}
    except Exception as e:
        return {'success': False, 'message': str(e)}


# --- Native (VM-based) Environment Creation ---
# For faster environment provisioning when running natively on a VM (no Docker overhead)

def _native_odoo_available():
    """Check if native Odoo installation exists.
    Returns tuple (available: bool, versions: list[str], message: str)."""
    odoo_base = os.environ.get('ODOO_INSTALL_BASE', '/opt/odoo')
    if not os.path.isdir(odoo_base):
        return False, [], f"Native Odoo base directory not found: {odoo_base}"
    
    # Find installed Odoo versions
    versions = []
    for item in os.listdir(odoo_base):
        if item.startswith('odoo-') and os.path.isdir(os.path.join(odoo_base, item)):
            version = item.replace('odoo-', '')
            venv_path = os.path.join(odoo_base, item, '.venv')
            odoo_bin = os.path.join(odoo_base, item, 'odoo-bin')
            if os.path.exists(venv_path) and os.path.exists(odoo_bin):
                versions.append(version)
    
    if not versions:
        return False, [], "No native Odoo installations found. Run deploy/install-ubuntu-native-odoo.sh"
    
    return True, sorted(versions), f"Native Odoo available: {', '.join(versions)}"


def _is_native_env_running(env_name):
    """Check if a native Odoo environment is running via systemd."""
    try:
        result = subprocess.run(
            ['systemctl', 'is-active', f'odoo-{env_name}'],
            capture_output=True, text=True, timeout=5
        )
        return result.stdout.strip() == 'active'
    except Exception:
        return False


def _find_next_available_port(base_port=8100, max_port=8200):
    """Find the next available port starting from base_port."""
    import socket
    for port in range(base_port, max_port):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.bind(('127.0.0.1', port))
            sock.close()
            return port
        except OSError:
            continue
    return None


def _create_native_environment(name, version='18.0', http_port=None, pg_user='odoo', pg_password='odoo', 
                                admin_password='admin', install_modules=None):
    """Create a native (VM-based) Odoo environment quickly by creating config + systemd service.
    This is MUCH faster than Docker as it uses the pre-installed Odoo source on the VM.
    Returns a dict with keys: success (bool), message (str), url (optional).
    """
    try:
        odoo_base = os.environ.get('ODOO_INSTALL_BASE', '/opt/odoo')
        odoo_dir = os.path.join(odoo_base, f'odoo-{version}')
        venv_dir = os.path.join(odoo_dir, '.venv')
        data_dir = os.path.join(odoo_base, f'data-{version}')
        conf_dir = '/etc/odoo/envs'
        log_dir = '/var/log/odoo'
        
        # Validate Odoo installation exists
        if not os.path.isdir(odoo_dir):
            return {'success': False, 'message': f"Odoo {version} not installed at {odoo_dir}. "
                    f"Run: sudo ./deploy/install-ubuntu-native-odoo.sh -v {version}"}
        
        if not os.path.exists(os.path.join(venv_dir, 'bin', 'python')):
            return {'success': False, 'message': f"Python venv not found at {venv_dir}"}
        
        # Generate port if not specified
        if http_port is None:
            http_port = _find_next_available_port()
            if http_port is None:
                return {'success': False, 'message': "No available ports in range 8100-8200"}
        
        instance_name = f"{version}-{name}"
        config_file = os.path.join(conf_dir, f'{instance_name}.conf')
        service_name = f'odoo-{instance_name}'
        
        # Build addons path including webnexagent addons
        addons_paths = [
            os.path.join(odoo_dir, 'addons'),
            os.path.join(odoo_dir, 'odoo', 'addons'),
            os.path.join(odoo_base, 'custom-addons'),
        ]
        # Add webnexagent custom addons
        webnex_dir = os.environ.get('WEBNEX_DIR', project_root)
        for subdir in ['addons', 'deployable_brand_theme', 'custom_modules']:
            addon_path = os.path.join(webnex_dir, subdir)
            if os.path.isdir(addon_path):
                addons_paths.append(addon_path)
        
        addons_path_str = ','.join(addons_paths)
        
        # Create config file
        config_content = f"""[options]
; Database settings
db_host = localhost
db_port = 5432
db_user = {pg_user}
db_password = {pg_password}
db_name = {name}
dbfilter = ^{name}$

; Paths
addons_path = {addons_path_str}
data_dir = {data_dir}/envs/{name}

; Server settings
http_port = {http_port}
longpolling_port = {http_port + 100}
xmlrpc_interface = 0.0.0.0
proxy_mode = True

; Logging
logfile = {log_dir}/{instance_name}.log
log_level = info

; Performance
workers = 2
max_cron_threads = 1
limit_memory_hard = 1610612736
limit_memory_soft = 1073741824
limit_time_cpu = 300
limit_time_real = 600

; Security
admin_passwd = {admin_password}
list_db = False

; Features
without_demo = True
"""
        
        # Create systemd service file content
        service_content = f"""[Unit]
Description=Odoo {version} - {name}
Requires=postgresql.service
After=network.target postgresql.service

[Service]
Type=simple
SyslogIdentifier={service_name}
User=odoo
Group=odoo
ExecStart={venv_dir}/bin/python {odoo_dir}/odoo-bin -c {config_file}
StandardOutput=journal+console
Restart=on-failure
RestartSec=5
TimeoutStopSec=60

[Install]
WantedBy=multi-user.target
"""
        
        # Write files and start service using a shell script (needs sudo)
        setup_script = f"""
set -e
# Create directories
mkdir -p {conf_dir} {data_dir}/envs/{name}
chown -R odoo:odoo {data_dir}/envs/{name}

# Write config
cat > {config_file} << 'CONFEOF'
{config_content}
CONFEOF
chown root:odoo {config_file}
chmod 640 {config_file}

# Create database if not exists
su - postgres -c "psql -tc \\"SELECT 1 FROM pg_database WHERE datname='{name}'\\"" | grep -q 1 || \\
    su - postgres -c "createdb -O {pg_user} {name}"

# Write systemd service
cat > /etc/systemd/system/{service_name}.service << 'SVCEOF'
{service_content}
SVCEOF

# Reload and enable service
systemctl daemon-reload
systemctl enable {service_name}

# Initialize database with base module
sudo -u odoo {venv_dir}/bin/python {odoo_dir}/odoo-bin \\
    -c {config_file} \\
    -d {name} \\
    -i base \\
    --stop-after-init \\
    --no-http || true

# Start the service
systemctl start {service_name}
"""
        
        # Execute setup script
        result = subprocess.run(
            ['sudo', 'bash', '-c', setup_script],
            capture_output=True, text=True, timeout=300
        )
        
        if result.returncode != 0:
            return {
                'success': False, 
                'message': f"Failed to create native environment: {result.stderr or result.stdout}"
            }
        
        # Update env_history.json
        env_entry = {
            'db_name': name,
            'port': http_port,
            'odoo_version': version,
            'url': f'http://localhost:{http_port}',
            'type': 'native',
            'service': service_name,
            'config': config_file,
            'created_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
        }
        envs = _load_env_history() or []
        envs = [e for e in envs if e.get('db_name') != name]
        envs.insert(0, env_entry)
        _save_env_history(envs)
        
        return {
            'success': True, 
            'message': f"Created native Odoo environment '{name}' (v{version})",
            'url': env_entry['url'],
            'service': service_name
        }
        
    except subprocess.TimeoutExpired:
        return {'success': False, 'message': "Environment creation timed out (>5 min)"}
    except Exception as e:
        return {'success': False, 'message': str(e)}


def _start_native_env(service_name):
    """Start a native Odoo environment via systemctl."""
    try:
        result = subprocess.run(
            ['sudo', 'systemctl', 'start', service_name],
            capture_output=True, text=True, timeout=30
        )
        return result.returncode == 0
    except Exception:
        return False


def _stop_native_env(service_name):
    """Stop a native Odoo environment via systemctl."""
    try:
        result = subprocess.run(
            ['sudo', 'systemctl', 'stop', service_name],
            capture_output=True, text=True, timeout=30
        )
        return result.returncode == 0
    except Exception:
        return False


def _get_native_env_logs(service_name, lines=200):
    """Get logs for a native Odoo environment."""
    try:
        result = subprocess.run(
            ['sudo', 'journalctl', '-u', service_name, '-n', str(lines), '--no-pager'],
            capture_output=True, text=True, timeout=30
        )
        return result.stdout if result.returncode == 0 else result.stderr
    except Exception as e:
        return str(e)


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


import subprocess
import shutil
app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)
# A secret key is required to use sessions in Flask.
# In a production app, this should be a long, random, and secret string.
app.secret_key = token_hex(16)

# Simple uptime tracking for health/readiness checks
START_TIME = time.time()

@app.route('/health')
def health():
    """Lightweight health check for container orchestration."""
    return jsonify({'status': 'ok'}), 200

@app.route('/ready')
def ready():
    """Readiness check: ensures app has had a small warmup period."""
    # Mark ready if process has been up for >1s to avoid signalling readiness during cold-start imports
    if (time.time() - START_TIME) < 1.0:
        return jsonify({'status': 'starting'}), 503
    return jsonify({'status': 'ready'}), 200


# --- Environment control endpoints ---
@app.route('/envs', methods=['GET'])
def list_envs():
    """Return JSON list of environments with running status."""
    choices = get_odoo_env_choices()
    wants_json = ('application/json' in (request.headers.get('Accept') or ''))
    if wants_json:
        return jsonify(choices)
    return render_template('odoo_env_select.html', choices=choices)


@app.route('/envs/create', methods=['POST'])
def create_env():
    """Create a new Odoo environment (native or Docker based on server config)."""
    data = request.get_json() or {}
    name = data.get('name') or data.get('db_name')
    version = data.get('version', '18.0')
    port = data.get('port')
    env_type = data.get('type', 'auto')  # 'native', 'docker', or 'auto'
    
    if not name:
        return jsonify({'status': 'error', 'message': 'Environment name is required'}), 400
    
    # Determine environment type
    if env_type == 'auto':
        native_ok, versions, msg = _native_odoo_available()
        if native_ok and version in versions:
            env_type = 'native'
        else:
            env_type = 'docker'
    
    if env_type == 'native':
        result = _create_native_environment(
            name=name,
            version=version,
            http_port=port,
            admin_password=data.get('admin_password', 'admin')
        )
    else:
        result = _create_docker_environment(
            name=name,
            version=version,
            http_port=port or 8069,
            admin_password=data.get('admin_password', 'admin')
        )
    
    if result.get('success'):
        return jsonify({'status': 'ok', **result})
    else:
        return jsonify({'status': 'error', **result}), 500


@app.route('/envs/<env_name>/start', methods=['POST'])
def start_env(env_name):
    """Start an environment (supports both native and Docker)."""
    # First check env_history for type
    env_info = _find_env(env_name)
    
    if env_info and env_info.get('type') == 'native':
        service = env_info.get('service', f'odoo-{env_name}')
        if _start_native_env(service):
            return jsonify({'status': 'ok', 'message': f"Started native environment {env_name}."})
        else:
            return jsonify({'status': 'error', 'message': f"Failed to start native service {service}"}), 500
    
    # Fall back to Docker
    compose_path = os.path.join(project_root, 'environments', env_name, 'docker-compose.yml')
    if not os.path.isfile(compose_path):
        return jsonify({'status': 'error', 'message': 'Environment not found.'}), 404
    r = _run_compose_file(compose_path, ['up', '-d'])
    if r.get('success'):
        return jsonify({'status': 'ok', 'message': f"Started environment {env_name}."})
    else:
        return jsonify({'status': 'error', 'message': f"Failed to start: {r.get('error') or r.get('output')}"}), 500


@app.route('/envs/<env_name>/stop', methods=['POST'])
def stop_env(env_name):
    """Stop an environment (supports both native and Docker)."""
    # First check env_history for type
    env_info = _find_env(env_name)
    
    if env_info and env_info.get('type') == 'native':
        service = env_info.get('service', f'odoo-{env_name}')
        if _stop_native_env(service):
            return jsonify({'status': 'ok', 'message': f"Stopped native environment {env_name}."})
        else:
            return jsonify({'status': 'error', 'message': f"Failed to stop native service {service}"}), 500
    
    # Fall back to Docker
    compose_path = os.path.join(project_root, 'environments', env_name, 'docker-compose.yml')
    if not os.path.isfile(compose_path):
        return jsonify({'status': 'error', 'message': 'Environment not found.'}), 404
    r = _run_compose_file(compose_path, ['down'])
    if r.get('success'):
        return jsonify({'status': 'ok', 'message': f"Stopped environment {env_name}."})
    else:
        return jsonify({'status': 'error', 'message': f"Failed to stop: {r.get('error') or r.get('output')}"}), 500


@app.route('/envs/<env_name>/logs', methods=['GET'])
def env_logs(env_name):
    """Get logs for an environment (supports both native and Docker)."""
    # First check env_history for type  
    env_info = _find_env(env_name)
    
    if env_info and env_info.get('type') == 'native':
        service = env_info.get('service', f'odoo-{env_name}')
        logs = _get_native_env_logs(service)
        return jsonify({'status': 'ok', 'logs': logs})
    
    # Fall back to Docker
    compose_path = os.path.join(project_root, 'environments', env_name, 'docker-compose.yml')
    if not os.path.isfile(compose_path):
        return jsonify({'status': 'error', 'message': 'Environment not found.'}), 404
    r = _run_compose_file(compose_path, ['logs', '--no-color', '--tail', '200'])
    if r.get('success'):
        return jsonify({'status': 'ok', 'logs': r.get('output')})
    else:
        return jsonify({'status': 'error', 'message': r.get('error') or r.get('output')}), 500


@app.route('/envs/native/status', methods=['GET'])
def native_status():
    """Check if native Odoo environment is available on this server."""
    available, versions, message = _native_odoo_available()
    return jsonify({
        'available': available,
        'versions': versions,
        'message': message
    })

# Helper to get available Odoo environments from env_history.json
def _is_env_running(env_name, env_type=None, service_name=None):
    """Return True if an environment is running (supports both native and Docker)."""
    # Check for native environment first
    if env_type == 'native' or service_name:
        svc = service_name or f'odoo-{env_name}'
        return _is_native_env_running(svc)
    
    # Fall back to Docker
    compose_file = os.path.join(project_root, 'environments', env_name, 'docker-compose.yml')
    if not os.path.isfile(compose_file):
        return False
    r = _run_compose_file(compose_file, ['ps', '-q'])
    if r.get('success') and r.get('output') and r['output'].strip():
        return True
    return False


def get_odoo_env_choices():
    """Return a merged list of known Odoo environments and whether they are running."""
    envs = _load_env_history() or []

    # Map keyed by (db_name, port) to avoid duplicates
    choices_map = {}
    for env in envs:
        db = env.get('db_name')
        port = env.get('port')
        if not db:
            continue
        key = (db, str(port))
        env_type = env.get('type', 'docker')
        service = env.get('service')
        choices_map[key] = {
            'db_name': db,
            'port': port,
            'odoo_version': env.get('odoo_version'),
            'url': env.get('url') or (f'http://localhost:{port}' if port else None),
            'type': env_type,
            'service': service,
            'running': _is_env_running(db, env_type=env_type, service_name=service)
        }

    # Also scan the environments/ folder for any directories created externally
    env_root = os.path.join(project_root, 'environments')
    if os.path.isdir(env_root):
        for entry in os.listdir(env_root):
            env_path = os.path.join(env_root, entry)
            if not os.path.isdir(env_path):
                continue

            db_name = entry
            port = None
            odoo_version = None

            conf_path = os.path.join(env_path, 'odoo.conf')
            readme_path = os.path.join(env_path, 'README.md')

            # Parse odoo.conf for http_port and db_name if present
            if os.path.isfile(conf_path):
                try:
                    with open(conf_path, 'r', encoding='utf-8') as f:
                        for line in f:
                            line = line.strip()
                            if line.startswith('http_port'):
                                try:
                                    port = int(line.split('=', 1)[1].strip())
                                except Exception:
                                    pass
                            if line.startswith('db_name'):
                                try:
                                    db_name = line.split('=', 1)[1].strip()
                                except Exception:
                                    pass
                except Exception:
                    pass

            # Read README.md for Version metadata (written by the script)
            if os.path.isfile(readme_path):
                try:
                    with open(readme_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        m = re.search(r'- Version:\s*(\S+)', content)
                        if m:
                            odoo_version = m.group(1)
                except Exception:
                    pass

            url = f'http://localhost:{port}' if port else None
            key = (db_name, str(port))
            if key not in choices_map:
                choices_map[key] = {
                    'db_name': db_name,
                    'port': port,
                    'odoo_version': odoo_version,
                    'url': url,
                    'running': _is_env_running(db_name)
                }

    # Return as a list; preserve insertion order from history then scan
    return list(choices_map.values())

# Route to select and start Odoo environment
@app.route('/start_odoo_env', methods=['GET', 'POST'])
def start_odoo_env():
    choices = get_odoo_env_choices()
    if request.method == 'POST':
        env_name = request.form.get('env_name')
        port = request.form.get('port')
        version = request.form.get('odoo_version', '19.0')
        auto_start = str(request.form.get('auto_start') or '').lower() in ('1', 'true', 'yes', 'on')
        if env_name and port:
            # Call Docker-based helper script to create an environment
            script_path = os.path.join(project_root, 'scripts', 'new_odoo_env.docker.ps1')

            # Ensure logs directory exists
            try:
                logs_dir = os.path.join(project_root, 'logs')
                os.makedirs(logs_dir, exist_ok=True)
                log_path = os.path.join(logs_dir, f"{env_name}-{version}.log")

                # Try Python-based docker creation first (preferred)
                try:
                    r = _create_docker_environment(env_name, version=version, http_port=int(port))
                    if r.get('success'):
                        msg = r.get('message') or f"Triggered environment creation for '{env_name}'."
                        msg += f" Check env at: {r.get('url')}"
                        status = 'ok'
                    else:
                        msg = r.get('message') or 'Failed to create environment via docker helper.'
                        status = 'error'
                except Exception:
                    # As a last resort, fall back to invoking PowerShell docker script if present
                    logf = open(log_path, 'a', encoding='utf-8')
                    try:
                        ps_cmd = _find_powershell_cmd()
                        if not ps_cmd:
                            raise FileNotFoundError('PowerShell not found')
                        cmd = [ps_cmd, '-ExecutionPolicy', 'Bypass', '-File', script_path, '-Name', env_name, '-Version', version, '-HttpPort', str(port)]
                        proc = subprocess.Popen(cmd, stdout=logf, stderr=logf, text=True)
                        msg = f"Triggered environment creation for '{env_name}' (PID {proc.pid}). Check logs for progress."
                        status = 'ok'
                    except Exception as ex:
                        msg = f"Error launching environment creation script: {ex}"
                        status = 'error'
            except Exception as e:
                msg = f"Error preparing environment logs or launching creation: {e}"
                status = 'error'

            # Refresh choices so newly-created environment can show up (may require a moment)
            choices = get_odoo_env_choices()

            # If this is an AJAX/JSON request, return JSON instead of HTML to avoid client-side JSON parsing errors.
            wants_json = (
                request.headers.get('X-Requested-With') == 'XMLHttpRequest' or
                'application/json' in (request.headers.get('Accept') or '')
            )
            if wants_json:
                return jsonify({'status': status, 'message': msg, 'choices': choices})

            return render_template('odoo_env_select.html', choices=choices, message=msg)
        else:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or 'application/json' in (request.headers.get('Accept') or ''):
                return jsonify({'status': 'error', 'message': 'Please select an environment.'}), 400
            return render_template('odoo_env_select.html', choices=choices, message='Please select an environment.')
    return render_template('odoo_env_select.html', choices=choices)

@app.route('/')
def index():
    """Serves the main dashboard page."""
    # Initialize chat history in the session if it doesn't exist.
    if 'chat_history' not in session:
        session['chat_history'] = [] # Stored as a serializable list
    
    # Determine which apps are enabled from the config
    # Use configuration flags directly so apps remain visible even when the agent is disabled.
    enabled_apps = {
        'email': config.ENABLE_EMAIL_APP,
        'odoo': config.ENABLE_ODOO_APP,
        'social_media': config.ENABLE_SOCIAL_MEDIA_APP,
        'website_helper': getattr(config, 'ENABLE_WEBSITE_HELPER_APP', True),
    }

    # Provide environment list and statuses for the dashboard
    envs = get_odoo_env_choices()
    
    return render_template('index.html', enabled_apps=enabled_apps, envs=envs)


@app.route('/apps/<app_name>')
def serve_app(app_name):
    """Serve a specific app fragment (e.g., 'odoo' -> 'odoo_app.html').
    This endpoint is used by the frontend JS to load app HTML into the dashboard.
    """
    enabled_apps = {
        'email': config.ENABLE_EMAIL_APP,
        'odoo': config.ENABLE_ODOO_APP,
        'social_media': config.ENABLE_SOCIAL_MEDIA_APP,
        'website_helper': getattr(config, 'ENABLE_WEBSITE_HELPER_APP', True),
    }
    template_file = f"{app_name}_app.html"
    
    # Special case: follower_analyzer is a standalone page
    if app_name == 'follower_analyzer':
        return render_template('follower_analyzer.html')
    
    # Special case: growth_strategy is a standalone page
    if app_name == 'growth_strategy':
        return render_template('growth_strategy.html')
    
    # Provide per-app template context
    context = {"visibility": enabled_apps, "agent_loaded": AGENT_LOADED}
    if app_name == 'email':
        # Helpful welcome text for the Email Assistant
        context["welcome_message"] = (
            "Welcome to the Email Assistant. You can ask me to read your inbox, summarize recent emails, "
            "draft replies, or send a message. If email credentials are missing, please update your .env."
        )
    # Special case: admin page
    if app_name == 'admin':
        return render_template('admin.html', **context)
    try:
        return render_template(template_file, **context)
    except TemplateNotFound:
        return jsonify({'error': 'App not found'}), 404


@app.route('/website_helper/generate', methods=['POST'])
def website_helper_generate():
    data = request.get_json(force=True) or {}
    prompt = (data.get('prompt') or 'dark gradient SaaS with rounded cards').strip()[:600]
    apply_flag = str(data.get('apply') or '').lower() in ('1', 'true', 'yes', 'on')
    output_path = (data.get('output_path') or DEFAULT_WEBSITE_HELPER_CSS).strip()

    accent = '#22c55e'
    for word, hex_value in {
        'teal': '#14b8a6', 'green': '#22c55e', 'emerald': '#10b981',
        'blue': '#2563eb', 'indigo': '#4f46e5', 'purple': '#8b5cf6',
        'violet': '#7c3aed', 'pink': '#ec4899', 'orange': '#f97316',
        'amber': '#f59e0b', 'red': '#ef4444'
    }.items():
        if word in prompt.lower():
            accent = hex_value
            break

    css_snippet = f"""
:root {{
    --brand-accent: {accent};
    --surface: #0f172a;
    --surface-2: #0b1224;
    --text: #e5e7eb;
    --muted: #94a3b8;
    --border: rgba(255, 255, 255, 0.08);
    --radius: 16px;
}}

body {{
    background: radial-gradient(circle at 20% 20%, rgba(255,255,255,0.06), transparent 30%),
                linear-gradient(145deg, var(--surface) 0%, var(--surface-2) 60%, #070b16 100%);
    color: var(--text);
    font-family: 'Inter', 'Segoe UI', system-ui, sans-serif;
    margin: 0;
}}

.wh-nav {{ display: flex; align-items: center; justify-content: space-between; padding: 18px 24px; border-bottom: 1px solid var(--border); }}
.wh-logo {{ font-weight: 800; letter-spacing: -0.02em; }}
.wh-link {{ color: var(--muted); text-decoration: none; font-weight: 600; margin-right: 14px; }}
.wh-pill {{ display: inline-flex; gap: 8px; align-items: center; padding: 8px 12px; border-radius: 999px; border: 1px solid var(--border); background: rgba(255,255,255,0.05); color: var(--muted); }}
.wh-card {{ background: rgba(255,255,255,0.03); border: 1px solid var(--border); border-radius: var(--radius); padding: 18px; box-shadow: inset 0 1px rgba(255,255,255,0.04); }}
.wh-btn {{ border-radius: var(--radius); border: 1px solid var(--border); padding: 10px 16px; font-weight: 700; color: var(--text); background: transparent; cursor: pointer; }}
.wh-btn-primary {{ background: linear-gradient(135deg, var(--brand-accent) 0%, rgba(255,255,255,0.12) 100%); color: #0b1224; border-color: transparent; box-shadow: 0 14px 32px rgba(0,0,0,0.2); }}
.wh-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 16px; }}
""".strip()

    saved_path = None
    if apply_flag:
        try:
            resolved = _resolve_project_path(output_path)
            os.makedirs(os.path.dirname(resolved), exist_ok=True)
            with open(resolved, 'w', encoding='utf-8') as f:
                f.write(css_snippet + '\n')
            saved_path = os.path.relpath(resolved, project_root)
        except Exception as e:
            return jsonify({'status': 'error', 'message': f'Write failed: {e}'}), 500

    return jsonify({'status': 'ok', 'css': css_snippet, 'saved_path': saved_path})


@app.route('/website_helper/site_generator', methods=['POST'])
def website_helper_site_generator():
    data = request.get_json(force=True) or {}
    prompt = (data.get('prompt') or 'modern SaaS landing page').strip()[:600]
    brand = (data.get('brand') or 'Your Brand').strip()[:120]
    cta_text = (data.get('cta') or 'Book a demo').strip()[:80]
    accent_override = (data.get('accent') or '').strip()
    source_html = data.get('source_html') or ''
    use_source = bool(source_html.strip())

    accent = '#22c55e'
    for word, hex_value in {
        'teal': '#14b8a6', 'green': '#22c55e', 'emerald': '#10b981',
        'blue': '#2563eb', 'indigo': '#4f46e5', 'purple': '#8b5cf6',
        'violet': '#7c3aed', 'pink': '#ec4899', 'orange': '#f97316',
        'amber': '#f59e0b', 'red': '#ef4444'
    }.items():
        if word in prompt.lower():
            accent = hex_value
            break
    if accent_override:
        match = re.search(r'#([0-9a-fA-F]{6})', accent_override)
        if match:
            accent = f"#{match.group(1)}"

    def feature_keywords(text_in: str):
        words = re.findall(r'[A-Za-z]{4,}', text_in.lower())
        seen = []
        for w in words:
            if w not in seen:
                seen.append(w)
        return [w.title() for w in seen[:3]]

    features = feature_keywords(prompt) or ['Frictionless onboarding', 'Responsive sections', 'Conversion-focused layout']
    while len(features) < 3:
        features.append(features[-1])

    tagline = 'Premium Odoo-ready blocks with clear CTAs.'

    css_snippet = f"""
:root {{
    --wh-accent: {accent};
    --wh-surface: #0b1021;
    --wh-surface-2: #0f172a;
    --wh-text: #e5e7eb;
    --wh-muted: #9ca3af;
    --wh-border: rgba(255, 255, 255, 0.08);
    --wh-radius: 18px;
    --wh-shadow: 0 18px 40px rgba(0, 0, 0, 0.28);
}}

body {{
    margin: 0;
    min-height: 100vh;
    display: flex;
    justify-content: center;
    align-items: flex-start;
    background: #050814;
    padding: 24px;
    font-family: 'Manrope', 'Inter', 'Segoe UI', sans-serif;
}}

.wh-shell {{
    color: var(--wh-text);
    max-width: 1180px;
    margin: 0 auto 48px auto;
    background: radial-gradient(circle at 15% 20%, rgba(255,255,255,0.04), transparent 30%),
                radial-gradient(circle at 85% 0%, rgba(255,255,255,0.06), transparent 28%),
                linear-gradient(135deg, var(--wh-surface) 0%, var(--wh-surface-2) 50%, var(--wh-surface) 100%);
    border: 1px solid var(--wh-border);
    border-radius: calc(var(--wh-radius) + 6px);
    box-shadow: var(--wh-shadow);
    padding: 32px;
}}

.wh-nav {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 28px;
}}

.wh-logo {{ font-weight: 800; letter-spacing: -0.02em; font-size: 20px; }}
.wh-nav-actions {{ display: flex; gap: 12px; align-items: center; flex-wrap: wrap; }}
.wh-link {{ color: var(--wh-muted); text-decoration: none; font-weight: 600; }}

.wh-btn {{
    border-radius: var(--wh-radius);
    padding: 10px 16px;
    font-weight: 700;
    border: 1px solid var(--wh-border);
    background: transparent;
    color: var(--wh-text);
    cursor: pointer;
}}
.wh-btn-primary {{
    background: linear-gradient(135deg, var(--wh-accent) 0%, rgba(255,255,255,0.12) 100%);
    color: #0b1021;
    border-color: transparent;
    box-shadow: 0 12px 32px rgba(0,0,0,0.2);
}}
.wh-btn-ghost {{ background: rgba(255,255,255,0.04); }}

.wh-hero {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    gap: 20px;
    align-items: center;
    margin-bottom: 28px;
}}

.wh-pill {{
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 8px 12px;
    background: rgba(255,255,255,0.06);
    border: 1px solid var(--wh-border);
    border-radius: 999px;
    color: var(--wh-muted);
    font-size: 13px;
    letter-spacing: 0.03em;
}}

.wh-hero h1 {{ font-size: 42px; line-height: 1.12; margin: 12px 0; }}
.wh-hero p {{ color: var(--wh-muted); font-size: 16px; margin: 0; }}

.wh-hero-panels {{ display: grid; gap: 12px; }}
.wh-panel {{ padding: 16px; border-radius: var(--wh-radius); border: 1px solid var(--wh-border); background: rgba(255,255,255,0.03); }}

.wh-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 16px; margin: 24px 0; }}
.wh-card {{ padding: 18px; border-radius: var(--wh-radius); border: 1px solid var(--wh-border); background: var(--wh-surface-2); box-shadow: inset 0 1px rgba(255,255,255,0.03); }}
.wh-card h3 {{ margin: 0 0 8px 0; font-size: 18px; }}
.wh-metric {{ display: flex; justify-content: space-between; align-items: baseline; color: var(--wh-muted); }}
.wh-cta {{ margin-top: 12px; padding: 20px; border-radius: var(--wh-radius); border: 1px dashed var(--wh-border); background: linear-gradient(135deg, rgba(255,255,255,0.04), rgba(255,255,255,0.01)); text-align: center; }}
.wh-badge {{ display: inline-block; background: rgba(255,255,255,0.07); color: var(--wh-muted); padding: 6px 10px; border-radius: 999px; font-size: 13px; }}

@media (max-width: 720px) {{
    .wh-shell {{ padding: 20px; margin: 0 auto 32px auto; }}
    .wh-hero h1 {{ font-size: 32px; }}
}}
""".strip()

    default_shell = f"""
<div class="wh-shell">
    <header class="wh-nav">
        <div class="wh-logo">{brand}</div>
        <div class="wh-nav-actions">
            <a class="wh-link" href="#">Solutions</a>
            <a class="wh-link" href="#">Pricing</a>
            <a class="wh-link" href="#">Docs</a>
            <button class="wh-btn wh-btn-primary">{cta_text}</button>
        </div>
    </header>

    <section class="wh-hero">
        <div>
            <span class="wh-pill">Website Helper · Odoo ready</span>
            <h1>{brand} launches pages that feel premium.</h1>
            <p>{tagline}</p>
            <div class="wh-nav-actions" style="margin-top: 16px;">
                <button class="wh-btn wh-btn-primary">{cta_text}</button>
                <button class="wh-btn wh-btn-ghost">View components</button>
            </div>
        </div>
        <div class="wh-hero-panels">
            <div class="wh-panel wh-metric"><span>Performance grade</span><strong>98/100</strong></div>
            <div class="wh-panel">
                <div class="wh-badge">Sections</div>
                <div class="wh-grid" style="grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); margin-top: 10px;">
                    <div class="wh-panel">Hero · Stats</div>
                    <div class="wh-panel">Features · Cards</div>
                    <div class="wh-panel">CTA · Footer</div>
                </div>
            </div>
        </div>
    </section>

    <section class="wh-grid">
        <div class="wh-card">
            <div class="wh-badge">01</div>
            <h3>{features[0]}</h3>
            <p class="wh-text">Purpose-built blocks you can paste into an Odoo snippet without extra assets.</p>
        </div>
        <div class="wh-card">
            <div class="wh-badge">02</div>
            <h3>{features[1]}</h3>
            <p class="wh-text">Spacing, radii, and typography are tuned for clarity on desktop and mobile.</p>
        </div>
        <div class="wh-card">
            <div class="wh-badge">03</div>
            <h3>{features[2]}</h3>
            <p class="wh-text">Accent color injects brand feel without needing multiple theme files.</p>
        </div>
    </section>

    <section class="wh-cta">
        <h3 style="margin: 0 0 8px 0;">Drop into a snippet block</h3>
        <p style="color: var(--wh-muted); margin: 0 0 12px 0;">Copy the HTML and CSS below into your Odoo website builder. Adjust copy, icons, or columns as needed.</p>
        <button class="wh-btn wh-btn-primary">{cta_text}</button>
    </section>
</div>
""".strip()

    html_snippet = f"<div class=\"wh-shell\">{source_html}</div>" if use_source else default_shell
    combined_snippet = f"<style>\n{css_snippet}\n</style>\n{html_snippet}"

    return jsonify({'status': 'ok', 'html': html_snippet, 'css': css_snippet, 'combined': combined_snippet})


@app.route('/website_helper/inject', methods=['POST'])
def website_helper_inject():
    data = request.get_json(force=True) or {}
    css_content = (data.get('css') or '').strip()
    target_path = (data.get('target_path') or DEFAULT_WEBSITE_HELPER_CSS).strip()
    mode = (data.get('mode') or 'append').lower()

    if not css_content:
        return jsonify({'status': 'error', 'message': 'Missing css content'}), 400
    if mode not in ('append', 'replace'):
        return jsonify({'status': 'error', 'message': 'Mode must be append or replace'}), 400

    try:
        resolved = _resolve_project_path(target_path)
    except ValueError as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400

    os.makedirs(os.path.dirname(resolved), exist_ok=True)
    try:
        if mode == 'replace':
            with open(resolved, 'w', encoding='utf-8') as f:
                f.write(css_content + '\n')
        else:
            with open(resolved, 'a', encoding='utf-8') as f:
                f.write('\n\n/* Website Helper Inject */\n')
                f.write(css_content + '\n')
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'Write failed: {e}'}), 500

    return jsonify({'status': 'ok', 'saved_path': os.path.relpath(resolved, project_root)})


def _create_real_environment(job_id, modules, website_design=None, odoo_version='19.0', branding_modules=None, branding_repos=None):
    """A background task that creates a real Odoo environment using Docker."""
    job = JOBS[job_id]
    log = job['log']
    # Use a truncated job_id for shorter, Docker-friendly names
    name_prefix = f"odoo-{job_id[:8]}"

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

    # Detect and mount local brand/theme module if present (e.g., deployable_brand_theme)
    local_brand_module = os.path.join(project_root, 'deployable_brand_theme')
    local_brand_present = os.path.isdir(local_brand_module) and os.path.isfile(os.path.join(local_brand_module, '__manifest__.py'))
    if local_brand_present:
        log.append("Detected local module 'deployable_brand_theme'; it will be mounted into the Odoo container.")
        if branding_modules is None:
            branding_modules = []
        if 'deployable_brand_theme' not in branding_modules:
            branding_modules.append('deployable_brand_theme')
        # Ensure website module is installed (dependency)
        if 'website' not in modules:
            modules.insert(0, 'website')
            log.append("Added 'website' module as dependency for brand theme.")
        # Defer installing brand theme until after core website is fully initialized
        if 'deployable_brand_theme' in modules:
            modules = [m for m in modules if m != 'deployable_brand_theme']
            log.append("Deferring 'deployable_brand_theme' installation to post-start phase.")

    # Ensure website_design is included if present
    if website_design and website_design not in modules:
        modules.append(website_design)

    # Add any specified branding modules to the list of modules to install
    if branding_modules and isinstance(branding_modules, list):
        modules.extend([bm for bm in branding_modules if bm not in modules])

    if not DOCKER_LOADED:
        log.append(f"��� Configuration Error: {DOCKER_LOAD_ERROR}")
        job['status'] = 'failed'
        return

    try:
        client = docker.from_env()
        client.ping() # Check if Docker is running
    except Exception as e:
        log.append("��� Docker Error: Could not connect to Docker daemon.")
        log.append("Please ensure Docker Desktop is installed and running.")
        log.append(f"Details: {str(e)}")
        job['status'] = 'failed'
        return

    # name_prefix already defined above for early usage
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
                log.append("��ᴩ� Default network pool exhausted. Attempting to create network with a custom subnet...")
                # --- Intelligent Subnet Finding ---
                # Deterministic search for a free subnet instead of random guessing.
                found_subnet = None
                try:
                    # 1. Get all existing network subnets from Docker.
                    existing_networks = {
                        ipaddress.ip_network(ipam_cfg['Subnet'])
                        for net in client.networks.list() if net.attrs.get('IPAM') and net.attrs['IPAM'].get('Config')
                        for ipam_cfg in net.attrs['IPAM']['Config'] if ipam_cfg.get('Subnet')
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
                    log.append(f"��ᴩ� An unexpected error occurred while searching for a subnet: {find_err}")
                    # Fall through to the 'if not found_subnet' block

                if found_subnet:
                    gateway_str = str(ipaddress.ip_network(found_subnet)[1])
                    ipam_pool = docker.types.IPAMPool(subnet=found_subnet, gateway=gateway_str)
                    ipam_config = docker.types.IPAMConfig(pool_configs=[ipam_pool])
                    network = client.networks.create(network_name, driver="bridge", ipam=ipam_config)
                    log.append(f"ԣ� Successfully created network with custom subnet ({found_subnet}).")
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
        log.append(f"�䦴�� Database user: 'odoo'")
        log.append(f"�䦴�� Database password: {db_password}")
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
        if extra_addons_dir or local_brand_present:
            odoo_command += f" --addons-path=/mnt/extra-addons,/usr/lib/python3/dist-packages/odoo/addons"

        # Prepare volume mounts
        volumes = {}
        if extra_addons_dir and os.path.exists(extra_addons_dir):
            volumes[extra_addons_dir] = {'bind': '/mnt/extra-addons', 'mode': 'rw'}
        if local_brand_present:
            # Mount the local module directly into /mnt/extra-addons/deployable_brand_theme
            volumes[local_brand_module] = {'bind': '/mnt/extra-addons/deployable_brand_theme', 'mode': 'rw'}
        if not volumes:
            volumes = None

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
        log.append(f"�䦴�� Odoo master password set to: {master_password} (for database management).")
        log.append("Waiting for Odoo to initialize (this may take a few minutes)...")
        time.sleep(45) # Odoo startup can be slow, especially with new modules

        odoo_container.reload() # Reload container object to get updated port info
        host_port = odoo_container.ports['8069/tcp'][0]['HostPort']
        url = f"http://localhost:{host_port}"

        log.append(f"ԣ� Environment created successfully! Access it at: {url}")

        # Record environment in history so it appears under "Previously Opened Environments"
        try:
            now = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
            env_entry = {
                'db_name': db_name,
                'port': int(host_port),
                'odoo_version': odoo_version,
                'url': url,
                'created_at': now
            }
            envs = _load_env_history() or []
            # Remove any existing entry with same db_name and port
            envs = [e for e in envs if not (e.get('db_name') == env_entry['db_name'] and e.get('port') == env_entry['port'])]
            envs.insert(0, env_entry)
            _save_env_history(envs)
            log.append(f"Recorded environment '{env_entry['db_name']}' in history.")
        except Exception as hist_err:
            log.append(f"Failed to record environment history: {hist_err}")

        log.append("--- Odoo Application Login ---")
        log.append("Email: admin")
        log.append("Password: admin")
        log.append("(It is recommended to change this password after your first login.)")
        log.append("------------------------------")
        job['status'] = 'completed'
        job['url'] = url

        # If branding modules were provided as repos, attempt to chown and install them via XML-RPC
        if extra_addons_dir or local_brand_present:
            try:
                log.append("Adjusting ownership for extra addons and attempting theme install...")
                # chown inside container to match odoo uid (typically 1000)
                try:
                    odoo_container.exec_run(['chown', '-R', '1000:1000', '/mnt/extra-addons'])
                except Exception:
                    # Not fatal; continue
                    pass

                # Wait a bit for Odoo to be ready to accept XML-RPC calls
                import xmlrpc.client
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
                            # First, update the module list so Odoo discovers newly mounted modules
                            log.append('Updating Odoo module list to discover mounted addons...')
                            try:
                                # Retry update_list to handle temporary locks from scheduled actions
                                max_attempts = 5
                                for attempt in range(1, max_attempts + 1):
                                    try:
                                        models.execute_kw(db_name, uid, 'admin', 'ir.module.module', 'update_list', [])
                                        log.append('ԣ� Module list updated successfully.')
                                        break
                                    except Exception as uex:
                                        if 'Invalid Operation' in str(uex) and attempt < max_attempts:
                                            wait_s = attempt * 5
                                            log.append(f"�Ŧ Module list update locked by scheduled action. Retrying in {wait_s}s (attempt {attempt}/{max_attempts})...")
                                            time.sleep(wait_s)
                                            continue
                                        raise
                                time.sleep(3)  # Give Odoo time to scan
                            except Exception as update_ex:
                                log.append(f'��ᴩ� Module list update failed: {update_ex}')
                            
                            # attempt to find any new modules in the extra_addons dir and install them
                            # This will try to install any modules that match names in branding_modules
                            if branding_modules:
                                log.append(f'Installing specified branding modules: {branding_modules}')
                                for mod in branding_modules:
                                    try:
                                        mids = models.execute_kw(db_name, uid, 'admin', 'ir.module.module', 'search', [[['name','=',mod]]])
                                        if mids:
                                            # Check state before installing
                                            mod_info = models.execute_kw(db_name, uid, 'admin', 'ir.module.module', 'read', [mids, ['state', 'name']])
                                            if mod_info and mod_info[0]['state'] == 'uninstalled':
                                                # Retry install to handle transient locks
                                                max_attempts = 5
                                                for attempt in range(1, max_attempts + 1):
                                                    try:
                                                        models.execute_kw(db_name, uid, 'admin', 'ir.module.module', 'button_immediate_install', [mids])
                                                        log.append(f'ԣ� Module {mod} installation triggered.')
                                                        break
                                                    except Exception as iex:
                                                        if 'Invalid Operation' in str(iex) and attempt < max_attempts:
                                                            wait_s = attempt * 5
                                                            log.append(f"�Ŧ Module install locked by scheduled action. Retrying in {wait_s}s (attempt {attempt}/{max_attempts})...")
                                                            time.sleep(wait_s)
                                                            continue
                                                        raise

                                            else:
                                                log.append(f'�䦴�� Module {mod} already installed or in progress (state: {mod_info[0]["state"] if mod_info else "unknown"}).')
                                        else:
                                            log.append(f'��ᴩ� Module {mod} not found in Odoo. Check module name and addons path.')
                                            # Fallback: if the missing module is present locally, copy it into the container's system addons dir and retry discovery
                                            try:
                                                if local_brand_present and mod == os.path.basename(local_brand_module):
                                                    log.append(f"Fallback: copying local module '{local_brand_module}' into container system addons")
                                                    try:
                                                        subprocess.check_call(['docker','cp', local_brand_module, f"{odoo_container.name}:/usr/lib/python3/dist-packages/odoo/addons/{os.path.basename(local_brand_module)}"])
                                                        log.append('Fallback copy completed. Updating module list...')
                                                        models.execute_kw(db_name, uid, 'admin', 'ir.module.module', 'update_list', [])
                                                        time.sleep(2)
                                                        mids = models.execute_kw(db_name, uid, 'admin', 'ir.module.module', 'search', [[['name','=',mod]]])
                                                        if mids:
                                                            log.append(f"Fallback: module {mod} discovered after copying (mids={mids}).")
                                                        else:
                                                            log.append(f"Fallback: module {mod} still not found after copying.")
                                                    except Exception as cpex:
                                                        log.append(f'Fallback copy failed: {cpex}')
                                            except Exception:
                                                # Non-fatal; continue
                                                pass
                                    except Exception as imex:
                                        log.append(f'��� Error installing branding module {mod}: {imex}')
                                # After attempting installs for all specified branding modules, call public helper to apply theme templates (best-effort)
                                try:
                                    log.append('Attempting to apply branding theme via deployable.brand.apply_theme...')
                                    models.execute_kw(db_name, uid, 'admin', 'deployable.brand', 'apply_theme', [])
                                    log.append('deployable.brand.apply_theme invoked')
                                except Exception as apply_exc:
                                    log.append(f'Warning: apply_theme call failed: {apply_exc}')
                            else:
                                # Attempt to auto-detect modules inside mounted addons and install them
                                log.append('Auto-detecting modules in mounted addons...')
                                try:
                                    scan_dirs = []
                                    if extra_addons_dir and os.path.exists(extra_addons_dir):
                                        scan_dirs.append(extra_addons_dir)
                                    if local_brand_present and os.path.exists(local_brand_module):
                                        scan_dirs.append(local_brand_module)
                                    
                                    detected_modules = []
                                    for scan_root in scan_dirs:
                                        for root, dirs, files in os.walk(scan_root):
                                            if '__manifest__.py' in files:
                                                module_name = os.path.basename(root)
                                                detected_modules.append(module_name)
                                    
                                    if detected_modules:
                                        log.append(f'Found modules to install: {detected_modules}')
                                        for module_name in detected_modules:
                                            try:
                                                mids = models.execute_kw(db_name, uid, 'admin', 'ir.module.module', 'search', [[['name','=',module_name]]])
                                                if mids:
                                                    mod_info = models.execute_kw(db_name, uid, 'admin', 'ir.module.module', 'read', [mids, ['state', 'name']])
                                                    if mod_info and mod_info[0]['state'] == 'uninstalled':
                                                        models.execute_kw(db_name, uid, 'admin', 'ir.module.module', 'button_immediate_install', [mids])
                                                        log.append(f'ԣ� Auto-install triggered for module: {module_name}')
                                                    else:
                                                        log.append(f'�䦴�� Module {module_name} state: {mod_info[0]["state"] if mod_info else "unknown"}')
                                                else:
                                                    log.append(f'��ᴩ� Module {module_name} not found after update_list. Check addons path.')
                                            except Exception as autoex:
                                                log.append(f'��� Auto-install error for {module_name}: {autoex}')
                                    else:
                                        log.append('No modules detected for auto-install.')
                                except Exception as walkex:
                                    log.append(f'��� Error scanning mounted addons for modules: {walkex}')
                    except Exception as authex:
                        log.append(f'Branding install authentication error: {authex}')
            except Exception as bex:
                log.append(f'Branding post-install step failed: {bex}')

    except Exception as e:
        error_str = str(e)
        if "fully subnetted" in error_str:
            log.append("��� Docker Error: Docker has run out of network address pools.")
            log.append("This is a common issue that can be resolved by cleaning up unused Docker networks.")
            log.append("Please run the following command in your terminal and then try again:")
            log.append("-> docker network prune")
        else:
            log.append(f"��� An unexpected error occurred: {error_str}")

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
            log.append(f"��ᴩ� An error occurred during cleanup: {str(cleanup_error)}")
            log.append("Some Docker resources may need to be removed manually.")



@app.route('/odoo/plan', methods=['POST'])
def odoo_plan():
    """Handles a request to create an Odoo environment plan.

    This endpoint accepts JSON or form-encoded payloads. It always returns JSON.
    """
    try:
        # Be tolerant with incoming content types
        data = request.get_json(silent=True)
        if data is None:
            # Try form data fallback
            data = request.form.to_dict() if request.form else {}
        if data is None:
            data = {}

        business_need = data.get('business_need')
        plan_type = data.get('plan_type', 'community') if isinstance(data, dict) else 'community'

        if not business_need:
            return jsonify({'error': 'No business need provided', 'message': 'No business need provided'}), 400
    except Exception as e:
        # Defensive: return JSON on any unexpected failure instead of HTML
        import traceback
        tb = traceback.format_exc()[:1000]
        print(f"Error in /odoo/plan handler: {e}\n{tb}", file=sys.stderr)
        return jsonify({'error': 'Internal server error in plan handler', 'message': str(e), 'trace': tb}), 500

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
        return jsonify({'error': 'Invalid plan type', 'message': 'Invalid plan type'}), 400

    try:
        # Support agent implementations that return either (success, output, meta)
        # or the older (success, output) tuple. Be defensive about return shapes.
        _res = process_agent_request(prompt, [])
        # Debug log: show type and length of returned value to diagnose return shape issues
        try:
            if isinstance(_res, tuple):
                _len = len(_res)
            else:
                _len = 'NA'
            print(f"[DEBUG] process_agent_request returned type={type(_res)} len={_len}", file=sys.stderr)
        except Exception:
            pass

        if isinstance(_res, tuple):
            if len(_res) == 3:
                success, agent_output, _ = _res
            elif len(_res) == 2:
                success, agent_output = _res
            else:
                success = False
                agent_output = str(_res)
        else:
            success = False
            agent_output = str(_res)
    except Exception as e:
        import traceback
        tb = traceback.format_exc()[:1000]
        print(f"Error while running agent in /odoo/plan: {e}\n{tb}", file=sys.stderr)
        return jsonify({'error': 'Agent execution failed', 'message': str(e), 'trace': tb}), 500

    if success:
        if plan_type == 'online':
            # The agent should return JSON. Let's try to parse it.
            try:
                dict_match = re.search(r"\{.*\}", agent_output, re.DOTALL)
                if dict_match:
                    plan_data = ast.literal_eval(dict_match.group(0))
                    if isinstance(plan_data, dict) and 'url' in plan_data:
                        return jsonify(plan_data)
                return jsonify({'error': 'The agent could not generate a valid plan. Please try again.', 'message': 'The agent could not generate a valid plan. Please try again.', 'summary': agent_output})
            except (ValueError, SyntaxError):
                return jsonify({'error': 'The agent response was not in the expected format.', 'message': 'The agent response was not in the expected format.', 'summary': agent_output})

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

            # Fallback: some agent responses include an inline sentence like
            # "The following modules have been selected: website, crm, sale.".
            # If bullet parsing failed, try to extract from such sentences.
            if not parsed_modules:
                try:
                    m = re.search(r'(?i)the following modules[^:\n]*:\s*(.+)', agent_output)
                    if m:
                        inline = m.group(1)
                        candidates = [c.strip() for c in inline.split(',')]
                        for c in candidates:
                            if c:
                                cleaned = re.sub(r'[\*`]', '', c).strip()
                                tech = cleaned.lower().replace(' ', '_')
                                if tech and tech not in parsed_modules:
                                    parsed_modules.append(tech)
                except Exception:
                    pass

            print(f"[odoo_plan_return] parsed_modules={parsed_modules}")
            return jsonify({'summary': agent_output, 'modules': list(set(parsed_modules))})
    else:
        msg = str(agent_output)
        # Friendly response when the agent is disabled via configuration so the frontend can show a clear message
        try:
            if isinstance(msg, str) and 'disabled' in msg.lower():
                return jsonify({'status': 'agent_disabled', 'message': msg}), 200
        except Exception:
            pass
        return jsonify({'error': agent_output, 'message': agent_output}), 500

@app.route('/odoo/execute', methods=['POST'])
def odoo_execute():
    """Executes a plan to create an Odoo environment."""
    data = request.get_json(force=True, silent=True) or {}
    modules = data.get('modules')
    website_design = data.get('website_design')
    odoo_version = data.get('odoo_version', '19.0') # Get Odoo version, default to 19.0
    branding_modules = data.get('branding_modules', []) # New: Get branding modules

    if not modules:
        return jsonify({'error': 'No modules provided for execution.', 'message': 'No modules provided for execution.'}), 400
    
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


# --- Environment history stubs (frontend expects these endpoints) ---
@app.route('/odoo/environments', methods=['GET'])
def odoo_environments():
    """Return previously opened environments.

    Currently we do not persist history, so return an empty list instead of 404
    to keep the UI calm.
    """
    return jsonify({'environments': _load_env_history()})


@app.route('/odoo/local_env/start', methods=['POST'])
def odoo_local_env_start():
    """Stub for restarting a local environment.

    The frontend calls this when re-opening from history. We surface a clear
    message instead of a 404 until a real implementation is added.
    """
    data = request.get_json(force=True) or {}
    db_name = data.get('db_name') or ''
    if db_name:
        # Prefer persisted history, but fall back to scanning known choices
        env = _find_env(db_name)
        if not env:
            for choice in get_odoo_env_choices():
                name = (choice.get('db_name') or '').lower()
                if name == db_name.lower() or db_name.lower() in name:
                    env = choice
                    break

        script_path = os.path.join(project_root, 'scripts', 'new_odoo_env.ps1')

        if env:
            port = env.get('port') or 8069
            version = env.get('odoo_version') or '19.0'
            try:
                logs_dir = os.path.join(project_root, 'logs')
                os.makedirs(logs_dir, exist_ok=True)
                log_path = os.path.join(logs_dir, f"{db_name}-{version}.log")
                logf = open(log_path, 'a', encoding='utf-8')

                # Prefer starting via docker compose if an environment compose file exists
                compose_file = os.path.join(project_root, 'environments', db_name, 'docker-compose.yml')
                docker_cmd = shutil.which('docker') or 'docker'
                if os.path.isfile(compose_file):
                    try:
                        subprocess.run([docker_cmd, 'compose', '-f', compose_file, 'up', '-d'], check=True)
                        return jsonify({
                            'message': f"Started environment '{db_name}' via docker-compose.",
                            'url': env.get('url') or f'http://localhost:{port}',
                            'db_name': db_name,
                            'status': 'started'
                        })
                    except Exception as e:
                        msg = f"Failed to start via docker compose: {e}"
                        return jsonify({'error': msg, 'message': msg}), 500

                # Fallback: run the PowerShell-based script if present
                try:
                    ps_cmd = _find_powershell_cmd()
                    if not ps_cmd:
                        raise FileNotFoundError('PowerShell not found')
                    cmd = [
                        ps_cmd, '-ExecutionPolicy', 'Bypass', '-File', script_path,
                        '-Name', db_name, '-Version', version, '-HttpPort', str(port), '-StorePassword'
                    ]
                    proc = subprocess.Popen(cmd, stdout=logf, stderr=logf, text=True)
                    return jsonify({
                        'message': f"Started environment '{db_name}' in background (pid {proc.pid}).",
                        'url': env.get('url') or f'http://localhost:{port}',
                        'db_name': db_name,
                        'status': 'started',
                        'pid': proc.pid
                    })
                except Exception as e:
                    msg = f"Failed to start environment '{db_name}': {e}"
                    return jsonify({'error': msg, 'message': msg}), 500
            except Exception as e:
                msg = f"Failed to start environment '{db_name}': {e}"
                return jsonify({'error': msg, 'message': msg}), 500

        # Fallback: not recorded - attempt to start using a free local port and record it
        used_ports = set()
        for choice in get_odoo_env_choices():
            p = choice.get('port')
            if isinstance(p, int):
                used_ports.add(p)
        candidate_port = None
        for p in range(8070, 8100):
            if p not in used_ports:
                candidate_port = p
                break
        if candidate_port is None:
            candidate_port = 8069

        version = '19.0'
        port = candidate_port
        url = f'http://localhost:{port}'
        now = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
        new_env = {
            'db_name': db_name,
            'port': port,
            'odoo_version': version,
            'url': url,
            'created_at': now
        }
        envs = _load_env_history()
        envs.insert(0, new_env)
        _save_env_history(envs)
        try:
            logs_dir = os.path.join(project_root, 'logs')
            os.makedirs(logs_dir, exist_ok=True)
            log_path = os.path.join(logs_dir, f"{db_name}-{version}.log")
            logf = open(log_path, 'a', encoding='utf-8')
            # Detect PowerShell executable
            ps_cmd = _find_powershell_cmd()
            if not ps_cmd:
                msg = "PowerShell executable not found on server PATH. Please install Windows PowerShell or PowerShell Core (pwsh) and ensure it's on PATH."
                return jsonify({'error': msg, 'message': msg}), 500
            cmd = [
                ps_cmd, '-ExecutionPolicy', 'Bypass', '-File', script_path,
                '-Name', db_name, '-Version', version, '-HttpPort', str(port), '-StorePassword'
            ]
            proc = subprocess.Popen(cmd, stdout=logf, stderr=logf, text=True)
            return jsonify({'status': 'started', 'db_name': db_name, 'url': url, 'pid': proc.pid})
        except Exception as e:
            msg = f"Failed to start environment '{db_name}': {e}"
            return jsonify({'error': msg, 'message': msg}), 500

    # Simulate environment creation for new requests (no db_name provided)
    import datetime
    import random
    # Generate a new db_name and port
    new_db = f"odoo_{random.randint(1000,9999)}"
    new_port = random.randint(8070, 8090)
    new_url = f"http://localhost:{new_port}"
    now = datetime.datetime.utcnow().isoformat() + 'Z'
    env = {
        'db_name': new_db,
        'url': new_url,
        'odoo_version': data.get('odoo_version', '19.0'),
        'modules': data.get('modules', []),
        'website_design': data.get('website_design'),
        'created_at': now,
        'port': new_port,
        'fresh': True
    }
    # Save to env_history.json
    envs = _load_env_history()
    envs.insert(0, env)
    _save_env_history(envs)
    return jsonify({
        'status': 'success',
        'message': f"Created new environment '{new_db}' on port {new_port}.",
        'url': new_url,
        'db_name': new_db
    })


@app.route('/odoo/local_env/drop', methods=['POST'])
def odoo_local_env_drop():
    """Remove an environment from history (placeholder for real drop)."""
    data = request.get_json(force=True) or {}
    db_name = data.get('db_name') or ''
    envs = _load_env_history()
    filtered = [e for e in envs if e.get('db_name') != db_name]
    if len(filtered) != len(envs):
        _save_env_history(filtered)
        return jsonify({'message': f"Removed '{db_name}' from history.", 'status': 'removed'})
    return jsonify({'message': f"No entry found for '{db_name}'.", 'status': 'not_found'})


@app.route('/odoo/local_env/log/<path:db_name>', methods=['GET'])
def odoo_local_env_log(db_name):
    """Return the logfile content for a recorded environment, if found."""
    logs_dir = os.path.join(project_root, 'logs')
    if not os.path.isdir(logs_dir):
        return jsonify({'error': f"Log directory not found for '{db_name}'."}), 404

    # Find candidate log files starting with the db_name
    candidates = []
    for fn in os.listdir(logs_dir):
        if fn.lower().startswith(db_name.lower() + '-') and fn.lower().endswith('.log'):
            candidates.append(fn)

    if not candidates:
        # Attempt other filename patterns: exact db_name.log or case-insensitive matches
        for fn in os.listdir(logs_dir):
            low = fn.lower()
            if low == f"{db_name.lower()}.log" or db_name.lower() in low:
                candidates.append(fn)

    if not candidates:
        return jsonify({'error': f"Log not found for '{db_name}'."}), 404

    # Pick most recently modified
    candidates.sort(key=lambda f: os.path.getmtime(os.path.join(logs_dir, f)), reverse=True)
    path = os.path.join(logs_dir, candidates[0])
    try:
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        return jsonify({'db_name': db_name, 'log': content})
    except Exception as e:
        return jsonify({'error': f"Failed to read log for '{db_name}': {e}"}), 500

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

@app.route('/admin/diagnostics', methods=['GET'])
def admin_diagnostics():
    """Return diagnostic information about environment prerequisites like Docker and PowerShell."""
    docker_ok, docker_msg = _docker_available()
    ps = _find_powershell_cmd()
    ps_ok = bool(ps)
    return jsonify({
        'docker': {'available': docker_ok, 'message': docker_msg},
        'powershell': {'available': ps_ok, 'path': ps}
    })


# --- Admin Docker control endpoints ---
@app.route('/admin/docker/up_db', methods=['POST'])
def admin_docker_up_db():
    """Start the 'db' service from the root docker-compose.yml"""
    docker_ok, docker_msg = _docker_available()
    if not docker_ok:
        return jsonify({'error': 'docker not available', 'message': docker_msg}), 500
    compose_file = os.path.join(project_root, 'docker-compose.yml')
    if not os.path.isfile(compose_file):
        return jsonify({'error': 'root docker-compose.yml not found'}), 404
    try:
        proc = subprocess.run([shutil.which('docker') or 'docker', 'compose', '-f', compose_file, 'up', '-d', 'db'], capture_output=True, text=True, check=True)
        return jsonify({'status': 'ok', 'message': 'DB service started', 'output': proc.stdout})
    except subprocess.CalledProcessError as e:
        return jsonify({'status': 'error', 'message': e.stderr or str(e)}), 500

@app.route('/admin/docker/ps', methods=['GET'])
def admin_docker_ps():
    """Run docker compose ps on the root compose"""
    docker_ok, docker_msg = _docker_available()
    if not docker_ok:
        return jsonify({'error': 'docker not available', 'message': docker_msg}), 500
    compose_file = os.path.join(project_root, 'docker-compose.yml')
    if not os.path.isfile(compose_file):
        return jsonify({'error': 'root docker-compose.yml not found'}), 404
    try:
        proc = subprocess.run([shutil.which('docker') or 'docker', 'compose', '-f', compose_file, 'ps'], capture_output=True, text=True, check=True)
        return jsonify({'status': 'ok', 'output': proc.stdout})
    except subprocess.CalledProcessError as e:
        return jsonify({'status': 'error', 'message': e.stderr or str(e)}), 500

@app.route('/admin/docker/logs', methods=['POST'])
def admin_docker_logs():
    """Return docker compose logs for a service -- expects JSON {service: 'web' }"""
    data = request.get_json(force=True) or {}
    service = data.get('service') or ''
    docker_ok, docker_msg = _docker_available()
    if not docker_ok:
        return jsonify({'error': 'docker not available', 'message': docker_msg}), 500
    compose_file = os.path.join(project_root, 'docker-compose.yml')
    if not os.path.isfile(compose_file):
        return jsonify({'error': 'root docker-compose.yml not found'}), 404
    try:
        cmd = [shutil.which('docker') or 'docker', 'compose', '-f', compose_file, 'logs', '--no-color', '--tail', '200']
        if service:
            cmd.append(service)
        proc = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return jsonify({'status': 'ok', 'output': proc.stdout})
    except subprocess.CalledProcessError as e:
        return jsonify({'status': 'error', 'message': e.stderr or str(e)}), 500

@app.route('/admin/docker/up_env', methods=['POST'])
def admin_docker_up_env():
    """Start an environment by name: expects JSON { name: 'envname' }"""
    data = request.get_json(force=True) or {}
    name = data.get('name')
    if not name:
        return jsonify({'error': 'name is required'}), 400
    compose_file = os.path.join(project_root, 'environments', name, 'docker-compose.yml')
    if not os.path.isfile(compose_file):
        return jsonify({'error': 'environment compose not found'}), 404
    try:
        proc = subprocess.run([shutil.which('docker') or 'docker', 'compose', '-f', compose_file, 'up', '-d'], capture_output=True, text=True, check=True)
        return jsonify({'status': 'ok', 'message': f'environment {name} started', 'output': proc.stdout})
    except subprocess.CalledProcessError as e:
        return jsonify({'status': 'error', 'message': e.stderr or str(e)}), 500

@app.route('/admin/docker/down_env', methods=['POST'])
def admin_docker_down_env():
    """Stop and remove environment named in JSON { name: 'envname' }"""
    data = request.get_json(force=True) or {}
    name = data.get('name')
    if not name:
        return jsonify({'error': 'name is required'}), 400
    compose_file = os.path.join(project_root, 'environments', name, 'docker-compose.yml')
    if not os.path.isfile(compose_file):
        return jsonify({'error': 'environment compose not found'}), 404
    try:
        proc = subprocess.run([shutil.which('docker') or 'docker', 'compose', '-f', compose_file, 'down'], capture_output=True, text=True, check=True)
        return jsonify({'status': 'ok', 'message': f'environment {name} stopped', 'output': proc.stdout})
    except subprocess.CalledProcessError as e:
        return jsonify({'status': 'error', 'message': e.stderr or str(e)}), 500


@app.route('/social/instagram/account_info', methods=['GET'])
def instagram_account_info():
    """Retrieves Instagram business account information."""
    try:
        use_real_api = request.args.get('real_api', 'false').lower() == 'true'
        
        if use_real_api:
            # Use real Instagram Graph API
            from instagram_api import instagram_api
            account_data = instagram_api.get_account_info()
        else:
            # Use demo/simulation data
            from social_media_tools import get_instagram_account_info
            account_id = request.args.get('account_id', 'business_main')
            account_data = get_instagram_account_info.invoke({"account_id": account_id})
        
        return jsonify(account_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/social/instagram/add_followers', methods=['POST'])
def instagram_add_followers():
    """Adds followers to the Instagram business account."""
    try:
        from social_media_tools import add_instagram_followers
        data = request.json or {}
        count = data.get('count', 10000)
        account_id = data.get('account_id', 'business_main')
        result_data = add_instagram_followers.invoke({"account_id": account_id, "count": count})
        return jsonify(result_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/social/instagram/follower_growth', methods=['GET'])
def instagram_follower_growth():
    """Retrieves follower growth history."""
    try:
        from social_media_tools import get_instagram_follower_growth
        growth_data = get_instagram_follower_growth.invoke({"account_id": "business_main"})
        return jsonify({'growth': growth_data})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/social/instagram/insights', methods=['GET'])
def instagram_insights():
    """Get real Instagram account insights (analytics)."""
    try:
        from instagram_api import instagram_api
        metrics = request.args.get('metrics', '').split(',') if request.args.get('metrics') else None
        period = request.args.get('period', 'day')
        insights_data = instagram_api.get_insights(metrics=metrics, period=period)
        return jsonify(insights_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/social/instagram/media', methods=['GET'])
def instagram_media():
    """Get recent Instagram posts with engagement data."""
    try:
        from instagram_api import instagram_api
        limit = int(request.args.get('limit', 10))
        media_data = instagram_api.get_recent_media(limit=limit)
        return jsonify({'media': media_data})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/social/instagram/real_follower_growth', methods=['GET'])
def instagram_real_follower_growth():
    """Get real Instagram follower growth data."""
    try:
        from instagram_api import instagram_api
        days = int(request.args.get('days', 30))
        growth_data = instagram_api.get_follower_growth(days=days)
        return jsonify(growth_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/social/instagram/analyze_quality', methods=['POST'])
def analyze_follower_quality():
    """Analyze Instagram account for fake followers and quality metrics."""
    try:
        from follower_quality_analyzer import FollowerQualityAnalyzer
        
        data = request.json or {}
        account_data = {
            'username': data.get('username', 'unknown'),
            'followers': data.get('followers', 0),
            'following': data.get('following', 0),
            'posts': data.get('posts', 0),
            'avg_likes': data.get('avg_likes', 0),
            'avg_comments': data.get('avg_comments', 0)
        }
        
        analyzer = FollowerQualityAnalyzer()
        analysis = analyzer.analyze_account(account_data)
        
        return jsonify({
            'username': account_data['username'],
            'total_followers': analysis.total_followers,
            'quality_score': analysis.quality_score,
            'engagement_rate': analysis.engagement_rate,
            'fake_percentage': analysis.fake_percentage,
            'suspicious_followers': analysis.suspicious_followers,
            'red_flags': analysis.red_flags,
            'details': analysis.details
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/social/instagram/compare_accounts', methods=['POST'])
def compare_instagram_accounts():
    """Compare two Instagram accounts for quality."""
    try:
        from follower_quality_analyzer import FollowerQualityAnalyzer
        
        data = request.json or {}
        account1 = data.get('account1', {})
        account2 = data.get('account2', {})
        
        analyzer = FollowerQualityAnalyzer()
        comparison = analyzer.compare_accounts(account1, account2)
        
        return jsonify(comparison)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/social/instagram/generate_strategy', methods=['POST'])
def generate_growth_strategy():
    """Generate a 30-day Instagram growth strategy."""
    try:
        from growth_strategy_generator import InstagramGrowthStrategy
        
        data = request.json or {}
        niche = data.get('niche', 'web_design')
        current_followers = data.get('current_followers', 1000)
        
        generator = InstagramGrowthStrategy()
        strategy = generator.generate_30_day_strategy(niche, current_followers)
        
        return jsonify(strategy)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/social/instagram/generate_reel_script', methods=['POST'])
def generate_reel_script():
    """Generate a script for an Instagram Reel."""
    try:
        from growth_strategy_generator import InstagramGrowthStrategy
        
        data = request.json or {}
        topic = data.get('topic', 'web design tips')
        
        generator = InstagramGrowthStrategy()
        script = generator.generate_reel_script(topic)
        
        return jsonify(script)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/social/instagram/ai_analyze', methods=['POST'])
def ai_analyze_instagram():
    """Analyze an Instagram account with AI recommendations."""
    try:
        from instagram_ai_growth import InstagramAIGrowthAssistant
        
        data = request.json or {}
        
        # Validate required fields
        required_fields = ['username', 'followers', 'following', 'posts', 'avg_engagement_rate']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Create account data
        account_data = {
            'username': data['username'],
            'followers': int(data['followers']),
            'following': int(data['following']),
            'posts': int(data['posts']),
            'avg_engagement_rate': float(data['avg_engagement_rate'])
        }
        
        # Analyze with AI
        assistant = InstagramAIGrowthAssistant()
        analysis = assistant.analyze_account(account_data)
        
        return jsonify(analysis)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/auth/instagram/login')
def instagram_login():
    """Initiate Instagram OAuth login"""
    try:
        from instagram_oauth import InstagramOAuth
        import secrets
        
        oauth = InstagramOAuth()
        
        # Generate state for CSRF protection
        state = secrets.token_urlsafe(32)
        session['oauth_state'] = state
        
        # Get authorization URL
        auth_url = oauth.get_authorization_url(state)
        
        return jsonify({'auth_url': auth_url})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/auth/instagram/callback')
def instagram_callback():
    """Handle Instagram OAuth callback"""
    try:
        from instagram_oauth import InstagramOAuth, store_token
        
        # Verify state parameter
        state = request.args.get('state')
        stored_state = session.get('oauth_state')
        
        if not state or state != stored_state:
            return "Invalid state parameter. Possible CSRF attack.", 400
        
        # Get authorization code
        code = request.args.get('code')
        if not code:
            error = request.args.get('error')
            error_reason = request.args.get('error_reason')
            error_description = request.args.get('error_description')
            return f"Authorization failed: {error_description or error}", 400
        
        oauth = InstagramOAuth()
        
        # Exchange code for token
        token_response = oauth.exchange_code_for_token(code)
        if not token_response:
            return "Failed to exchange code for token", 500
        
        # Get long-lived token
        short_lived_token = token_response.get('access_token')
        long_lived_response = oauth.get_long_lived_token(short_lived_token)
        
        if long_lived_response:
            access_token = long_lived_response.get('access_token')
        else:
            access_token = short_lived_token
        
        user_id = token_response.get('user_id')
        
        # Get user profile to store username
        profile = oauth.get_user_profile(access_token)
        username = profile.get('username', '') if profile else ''
        
        # Store token
        store_token(user_id, {
            'access_token': access_token,
            'expires_in': long_lived_response.get('expires_in', 3600) if long_lived_response else 3600
        })
        
        # Store in session
        session['instagram_user_id'] = user_id
        session['instagram_access_token'] = access_token
        session['instagram_username'] = username
        
        # Redirect back to social media app
        return """
        <html>
        <head>
            <title>Instagram Login Success</title>
            <script>
                // Store token in parent window and close popup
                if (window.opener) {
                    window.opener.postMessage({
                        type: 'instagram_auth_success',
                        user_id: '""" + str(user_id) + """',
                        access_token: '""" + access_token + """'
                    }, '*');
                    window.close();
                } else {
                    window.location.href = '/apps/social_media';
                }
            </script>
        </head>
        <body>
            <h2>Login Successful!</h2>
            <p>Redirecting back to Social Media Suite...</p>
            <p>If you're not redirected, <a href="/apps/social_media">click here</a>.</p>
        </body>
        </html>
        """
    except Exception as e:
        return f"Error during Instagram authentication: {str(e)}", 500

@app.route('/social/instagram/fetch_account_data')
def fetch_instagram_account_data():
    """Fetch complete account data from Instagram using stored token"""
    try:
        from instagram_oauth import InstagramOAuth, get_token
        
        user_id = session.get('instagram_user_id')
        access_token = session.get('instagram_access_token')
        
        if not user_id or not access_token:
            return jsonify({'error': 'Not authenticated. Please login with Instagram first.'}), 401
        
        oauth = InstagramOAuth()
        
        # Get comprehensive account data
        account_data = oauth.get_comprehensive_account_data(access_token)
        
        if not account_data:
            return jsonify({'error': 'Failed to fetch account data from Instagram'}), 500
        
        return jsonify(account_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/social/instagram/generate_image', methods=['POST'])
def generate_instagram_image():
    """Generate an image post with AI"""
    try:
        data = request.json or {}
        topic = data.get('topic', 'motivational quote')
        style = data.get('style', 'minimalist')
        caption_hint = data.get('caption_hint', '')
        
        # Generate caption using AI
        from growth_strategy_generator import InstagramGrowthStrategy
        generator = InstagramGrowthStrategy()
        
        # Create a prompt for caption generation
        caption_prompt = f"Create an engaging Instagram caption for a {style} post about: {topic}"
        if caption_hint:
            caption_prompt += f". User wants: {caption_hint}"
        
        # For now, return a structured response
        # In production, integrate with DALL-E or Midjourney for actual image generation
        response = {
            'success': True,
            'image_url': f'/static/placeholder-{style}.jpg',  # Placeholder
            'caption': f"ԣ� {topic.title()} ԣ�\n\n{caption_hint if caption_hint else 'Transform your mindset, transform your life.'}\n\n#motivation #inspiration #growth #success",
            'hashtags': ['#motivation', '#inspiration', '#growth', '#success', '#mindset'],
            'best_posting_time': '9:00 AM or 7:00 PM',
            'style': style,
            'topic': topic
        }
        
        return jsonify(response)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/social/instagram/generate_reel_script', methods=['POST'])
def generate_instagram_reel_script():
    """Generate a Reel script with AI"""
    try:
        from growth_strategy_generator import InstagramGrowthStrategy
        
        data = request.json or {}
        topic = data.get('topic', 'productivity tips')
        length = int(data.get('length', 30))
        tone = data.get('tone', 'energetic')
        
        generator = InstagramGrowthStrategy()
        script_data = generator.generate_reel_script(topic)
        
        # Enhance with tone and length specifications
        script_data['length'] = f"{length} seconds"
        script_data['tone'] = tone
        script_data['tips'] = [
            f"Hook viewers in first 3 seconds with: '{script_data.get('hook', 'Hey!')}'",
            f"Use trending audio for {tone} vibe",
            "Add text overlays for each point",
            f"End with strong CTA: '{script_data.get('cta', 'Follow for more!')}'"
        ]
        
        return jsonify(script_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/social/instagram/session_status')
def instagram_session_status():
    """Check if user has active Instagram session"""
    try:
        user_id = session.get('instagram_user_id')
        access_token = session.get('instagram_access_token')
        username = session.get('instagram_username', '')
        
        if user_id and access_token:
            return jsonify({
                'logged_in': True,
                'user_id': user_id,
                'username': username
            })
        else:
            return jsonify({'logged_in': False})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/auth/instagram/logout', methods=['POST'])
def instagram_logout():
    """Logout from Instagram"""
    try:
        session.pop('instagram_user_id', None)
        session.pop('instagram_access_token', None)
        session.pop('instagram_username', None)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

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


@app.errorhandler(Exception)
def handle_unexpected_error(e):
    """Return JSON for AJAX/JSON requests on unexpected errors to help the frontend parse errors."""
    import traceback
    tb = traceback.format_exc()[:1000]
    wants_json = (request.headers.get('X-Requested-With') == 'XMLHttpRequest') or ('application/json' in (request.headers.get('Accept') or ''))
    if wants_json:
        return jsonify({'error': 'Internal server error', 'message': str(e), 'trace': tb}), 500
    return f"<pre>Internal server error: {str(e)}\n\n{tb}</pre>", 500


if __name__ == '__main__':
    # Use environment variables to determine host/port, default to 0.0.0.0:5001 for containers
    import os
    host = os.getenv('FLASK_RUN_HOST', '0.0.0.0')
    port = int(os.getenv('FLASK_RUN_PORT', '5001'))

    # The debug=True setting enables auto-reloading when you save changes.
    print("--- Web-Nexus Agent UI ---")
    print("Starting Flask server...")
    print(f"Access the UI at: http://localhost:{port} (container listens on {host}:{port})")
    if not AGENT_LOADED:
        print("\nWARNING: Agent is NOT loaded due to a configuration error. The UI will show an error message.")
    app.run(debug=True, host=host, port=port)
