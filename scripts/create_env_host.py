#!/usr/bin/env python3
import sys, os, json
# Ensure project root is on sys.path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)
import app

name = 'Zisanda Hub'
print('Creating environment:', name)
port = app._find_next_available_port(base_port=8069, max_port=9000)
print('Selected port:', port)
res = app._create_docker_environment(name=name, version='19.0', env_mode='development', http_port=port)
print(json.dumps(res, indent=2))
