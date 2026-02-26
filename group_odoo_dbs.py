#!/usr/bin/env python3
"""
Group Odoo DB containers by their given name (from env_history.json) or by container name.

Usage:
  python group_odoo_dbs.py

The script reads `env_history.json` in the current directory (if present) and calls
`docker ps` to list running containers. It attempts to match containers to entries in
`env_history.json` by comparing published ports. If a match is found, the container
is grouped under the `db_name` from the history; otherwise it falls back to the
container name.
"""
import json
import os
import re
import subprocess
from collections import defaultdict

ENV_HISTORY = 'env_history.json'


def load_env_history(path=ENV_HISTORY):
    if not os.path.exists(path):
        return []
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return []


def docker_ps_lines():
    fmt = '{{.ID}}|{{.Names}}|{{.Image}}|{{.Ports}}'
    try:
        out = subprocess.check_output(['docker', 'ps', '--format', fmt], text=True)
    except Exception as e:
        print('Failed to run `docker ps`:', e)
        return []
    return [line for line in out.splitlines() if line.strip()]


def inspect_labels(container_id):
    try:
        out = subprocess.check_output(['docker', 'inspect', '--format', "{{json .Config.Labels}}", container_id], text=True)
        if not out.strip() or out.strip() == 'null':
            return {}
        return json.loads(out)
    except Exception:
        return {}


def extract_published_ports(port_field):
    # Examples of port_field values:
    # - "0.0.0.0:63198->8069/tcp"
    # - "63198:8069/tcp"
    # - "5432/tcp"
    # Return list of published (host) ports as ints.
    ports = []
    if not port_field:
        return ports
    # Find patterns like 0.0.0.0:63198->8069 or 63198:8069
    for m in re.finditer(r'(?:0\.0\.0\.0:)?(\d+)(?:->|:)', port_field):
        try:
            ports.append(int(m.group(1)))
        except ValueError:
            continue
    return ports


def parse_docker_ps_line(line):
    parts = line.split('|')
    if len(parts) != 4:
        return None
    cid, name, image, ports = parts
    published = extract_published_ports(ports)
    return {
        'id': cid,
        'name': name,
        'image': image,
        'ports_raw': ports,
        'published_ports': published,
        'labels': {},
        'display_name': name,
    }


def group_containers():
    history = load_env_history()
    # map published port -> db_name
    port_to_db = {entry.get('port'): entry.get('db_name') for entry in history if entry.get('port')}

    lines = docker_ps_lines()
    containers = [parse_docker_ps_line(l) for l in lines]
    containers = [c for c in containers if c]

    # Build name frequency maps for prefix heuristics
    names = [c['name'] for c in containers]
    prefix1_counts = defaultdict(int)
    prefix2_counts = defaultdict(int)
    for n in names:
        parts = re.split(r'[-_]', n)
        if parts:
            prefix1_counts[parts[0]] += 1
        if len(parts) >= 2:
            prefix2 = parts[0] + '-' + parts[1]
            prefix2_counts[prefix2] += 1

    groups = defaultdict(list)

    # Inspect containers for compose labels and set a friendly display name
    for c in containers:
        labels = inspect_labels(c['id'])
        c['labels'] = labels or {}
        # If service label exists, prefer it as display name
        service = labels.get('com.docker.compose.service') if labels else None
        if service:
            c['display_name'] = service

    for c in containers:
        matched_db = None
        for p in c['published_ports']:
            if p in port_to_db:
                matched_db = port_to_db[p]
                break
        if matched_db:
            key = matched_db
        else:
            # If a compose project label exists, group by it
            project = c['labels'].get('com.docker.compose.project')
            if project:
                key = project
            else:
                # Prefer Docker Compose project grouping by name prefix when possible
                name = c['name']
                if '-' in name:
                    prefix = name.split('-', 1)[0]
                    count_children = sum(1 for n in names if n.startswith(prefix + '-'))
                    if count_children >= 2:
                        key = prefix
                    else:
                        parts = re.split(r'[-_]', name)
                        if len(parts) >= 2:
                            p2 = parts[0] + '-' + parts[1]
                            if prefix2_counts.get(p2, 0) >= 2:
                                key = p2
                            elif prefix1_counts.get(parts[0], 0) >= 2:
                                key = parts[0]
                            else:
                                key = name
                        else:
                            key = name
                else:
                    key = name

        groups[key].append(c)

    return groups


def print_groups(groups):
    if not groups:
        print('No groups found.')
        return
    for key, items in groups.items():
        print(f"\nGroup: {key}  ({len(items)} container(s))")
        for c in items:
            ports = c['published_ports'] or []
            # show display_name (service) when available, else full container name
            disp = c.get('display_name') or c['name']
            print(f" - {disp}  (container={c['name']}) image={c['image']}  ports={ports}  raw_ports='{c['ports_raw']}'")


def main():
    groups = group_containers()
    print_groups(groups)


if __name__ == '__main__':
    main()
