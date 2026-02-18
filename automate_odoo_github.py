# Automate Odoo Community Edition repo creation
# Default: Odoo 17.0, repo name 'odoo-community-17'
# Requires: requests, gitpython

import os
import subprocess
import requests

GITHUB_API = 'https://api.github.com'
ODOO_REPO = 'https://github.com/odoo/odoo.git'

# Credentials from environment variables
username = os.environ.get('GITHUB_USERNAME', 'Yamkia')
token = os.environ.get('GITHUB_TOKEN', '')  # Set GITHUB_TOKEN env var before running

def create_env_and_repo(odoo_version):
    folder = f'odoo-community-{odoo_version}'
    print(f"\nSetting up Odoo {odoo_version} in {folder}")
    # Create folder
    if not os.path.exists(folder):
        os.makedirs(folder)
    # Create virtual environment
    venv_path = os.path.join(folder, '.venv')
    if not os.path.exists(venv_path):
        subprocess.run(['python', '-m', 'venv', venv_path], check=True)
    # Check for odoo-bin
    odoo_bin_path = os.path.join(folder, 'odoo-bin')
    if not os.path.exists(odoo_bin_path):
        print(f"'odoo-bin' not found in {folder}. Recloning Odoo repository...")
        # Remove everything except .venv
        for item in os.listdir(folder):
            if item != '.venv':
                item_path = os.path.join(folder, item)
                if os.path.isdir(item_path):
                    import shutil
                    shutil.rmtree(item_path)
                else:
                    os.remove(item_path)
        subprocess.run(['git', 'clone', '--branch', odoo_version, '--depth', '1', ODOO_REPO, folder], check=True)
    else:
        print(f"'odoo-bin' found in {folder}. Skipping clone.")
    # Install dependencies
    req_path = os.path.join(folder, 'requirements.txt')
    if os.path.exists(req_path):
        print(f"Installing dependencies from {req_path}...")
        subprocess.run([os.path.join(venv_path, 'Scripts', 'pip'), 'install', '-r', req_path], check=True)
    else:
        print(f"No requirements.txt found in {folder}.")
    # Create GitHub repo
    repo_name = folder
    url = f"{GITHUB_API}/user/repos"
    headers = {'Authorization': f'token {token}'}
    data = {'name': repo_name, 'private': False, 'description': f'Odoo Community Edition {odoo_version}'}
    r = requests.post(url, json=data, headers=headers)
    if r.status_code == 201:
        print(f"GitHub repo '{repo_name}' created.")
        repo_url = r.json()['clone_url']
    elif r.status_code == 422:
        print(f"Repo '{repo_name}' already exists on GitHub.")
        repo_url = f"https://github.com/{username}/{repo_name}.git"
    else:
        print('Error creating repo:', r.text)
        return
    # Push code to GitHub
    cwd = os.getcwd()
    os.chdir(folder)
    # Remove 'origin' remote if it exists
    try:
        subprocess.run(['git', 'remote', 'remove', 'origin'], check=True)
    except subprocess.CalledProcessError:
        print("No existing 'origin' remote to remove, continuing.")
    # Add new origin
    subprocess.run(['git', 'remote', 'add', 'origin', repo_url], check=True)
    # Try to push the requested branch/tag
    result = subprocess.run(['git', 'rev-parse', '--verify', odoo_version], capture_output=True, text=True)
    if result.returncode == 0:
        # Branch/tag exists, push it
        try:
            subprocess.run(['git', 'push', '-u', 'origin', odoo_version], check=True)
            print(f"Pushed branch/tag '{odoo_version}' to GitHub.")
        except subprocess.CalledProcessError as e:
            print(f"Error pushing branch/tag '{odoo_version}': {e}. Trying to push current branch instead.")
            branch_result = subprocess.run(['git', 'rev-parse', '--abbrev-ref', 'HEAD'], capture_output=True, text=True)
            current_branch = branch_result.stdout.strip()
            subprocess.run(['git', 'push', '-u', 'origin', current_branch], check=True)
            print(f"Pushed current branch '{current_branch}' to GitHub.")
    else:
        # Branch/tag does not exist, push current branch
        branch_result = subprocess.run(['git', 'rev-parse', '--abbrev-ref', 'HEAD'], capture_output=True, text=True)
        current_branch = branch_result.stdout.strip()
        print(f"Branch/tag '{odoo_version}' not found. Pushing current branch '{current_branch}' instead.")
        subprocess.run(['git', 'push', '-u', 'origin', current_branch], check=True)
        print(f"Pushed current branch '{current_branch}' to GitHub.")
    os.chdir(cwd)
    print(f'Odoo Community Edition {odoo_version} pushed to GitHub repository.')
    print(f"\nTo run Odoo {odoo_version}, use these commands:")
    print(f"cd {folder}")
    print(f".\\.venv\\Scripts\\activate")
    print(f"python odoo-bin -c odoo.conf")

def main():
    print("Enter Odoo versions separated by commas (e.g. 16.0,17.0):")
    versions = input().replace(' ', '').split(',')
    for v in versions:
        if v:
            create_env_and_repo(v)

if __name__ == '__main__':
    main()
