#!/usr/bin/env python3
import os
import json
import threading
from flask import Flask, request, jsonify
import requests
import time
from datetime import datetime

APP_DIR = os.path.dirname(os.path.abspath(__file__))
KEYS_FILE = os.path.join(APP_DIR, 'authorized_keys.json')
ADMIN_TOKEN = os.environ.get('ADMIN_TOKEN', 'change-me')

lock = threading.Lock()

def load_keys():
    try:
        with open(KEYS_FILE, 'r') as f:
            return json.load(f)
    except Exception:
        return []

def save_keys(keys):
    with open(KEYS_FILE, 'w') as f:
        json.dump(keys, f, indent=2)

CONNS_FILE = os.path.join(APP_DIR, 'connections.json')
BANS_FILE = os.path.join(APP_DIR, 'bans.json')
ATTEMPTS_LOG = os.path.join(APP_DIR, 'attempts.log')

def load_json(path, default):
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except Exception:
        return default

def save_json(path, data):
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)

# ensure ban/connections files exist
for p, d in ((CONNS_FILE, {}), (BANS_FILE, {"ips":[], "asns":[], "devices":[]})):
    if not os.path.exists(p):
        try:
            save_json(p, d)
        except Exception:
            pass

app = Flask(__name__)

# Ensure keys file exists and is valid JSON
if not os.path.exists(KEYS_FILE):
    try:
        with open(KEYS_FILE, 'w') as f:
            json.dump([], f)
    except Exception:
        pass


@app.route('/check', methods=['GET', 'POST'])
def check_key():
    # Accept key via GET param, JSON body or header
    key = request.args.get('key') or request.headers.get('X-License-Key')
    if not key and request.is_json:
        key = request.json.get('key')

    if not key:
        return jsonify({'result':'error', 'message':'no key provided'}), 400

    # Determine client IP (respect X-Forwarded-For if behind proxy)
    ip = request.headers.get('X-Forwarded-For', request.remote_addr)

    # simple ASN/org lookup
    asn = None
    org = None
    try:
        r = requests.get(f'https://ipinfo.io/{ip}/json', timeout=2)
        if r.status_code == 200:
            data = r.json()
            org = data.get('org')
            if org and org.startswith('AS'):
                asn = org.split(' ')[0]
    except Exception:
        pass

    # log attempt
    t = int(time.time())
    with open(ATTEMPTS_LOG, 'a') as f:
        f.write(json.dumps({'time':t, 'ip':ip, 'key': key}) + "\n")

    # check bans
    bans = load_json(BANS_FILE, {"ips":[], "asns":[], "devices":[]})
    if ip in bans.get('ips', []):
        return jsonify({'result':'banned'})
    if asn and asn in bans.get('asns', []):
        return jsonify({'result':'banned'})

    device_info = None
    if request.is_json:
        try:
            device_info = request.json.get('device_info') or request.json.get('device_name')
            device_name = request.json.get('device_name')
        except Exception:
            device_info = None
    else:
        device_name = None

    # check device bans
    if device_name and device_name in bans.get('devices', []):
        return jsonify({'result':'banned'})

    with lock:
        keys = load_keys()

    result = 'success' if key in keys else 'wrong'

    # update active connections
    conns = load_json(CONNS_FILE, {})
    # store by key and ip
    conns.setdefault(key, {})
    conns[key].update({'last_seen': t, 'ip': ip, 'asn': asn, 'org': org, 'device': device_name, 'device_info': device_info})
    save_json(CONNS_FILE, conns)

    return jsonify({'result': result})


@app.route('/heartbeat', methods=['POST'])
def heartbeat():
    # minimal heartbeat endpoint: expects JSON { key, device_name, device_info }
    if not request.is_json:
        return jsonify({'result':'error','message':'expected json body'}), 400
    key = request.json.get('key')
    device_name = request.json.get('device_name')
    device_info = request.json.get('device_info')
    if not key:
        return jsonify({'result':'error','message':'no key'}), 400

    ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    t = int(time.time())

    # ASN lookup best-effort
    asn = None
    org = None
    try:
        r = requests.get(f'https://ipinfo.io/{ip}/json', timeout=2)
        if r.status_code == 200:
            data = r.json()
            org = data.get('org')
            if org and org.startswith('AS'):
                asn = org.split(' ')[0]
    except Exception:
        pass

    # update active connections
    with lock:
        conns = load_json(CONNS_FILE, {})
        conns.setdefault(key, {})
        conns[key].update({'last_seen': t, 'ip': ip, 'asn': asn, 'org': org, 'device': device_name, 'device_info': device_info})
        save_json(CONNS_FILE, conns)

    return jsonify({'result':'ok'})

def require_admin():
    token = request.headers.get('X-Admin-Token')
    if not token or token != ADMIN_TOKEN:
        return False
    return True

@app.route('/admin/add', methods=['POST'])
def admin_add():
    if not require_admin():
        return jsonify({'result':'forbidden'}), 403
    if not request.is_json:
        return jsonify({'result':'error', 'message':'expected json body'}), 400
    key = request.json.get('key')
    if not key:
        return jsonify({'result':'error', 'message':'no key'}), 400

    with lock:
        keys = load_keys()
        if key in keys:
            return jsonify({'result':'exists'})
        keys.append(key)
        save_keys(keys)

    return jsonify({'result':'added'})

@app.route('/admin/remove', methods=['POST'])
def admin_remove():
    if not require_admin():
        return jsonify({'result':'forbidden'}), 403
    if not request.is_json:
        return jsonify({'result':'error', 'message':'expected json body'}), 400
    key = request.json.get('key')
    if not key:
        return jsonify({'result':'error', 'message':'no key'}), 400

    with lock:
        keys = load_keys()
        if key not in keys:
            return jsonify({'result':'not_found'})
        keys.remove(key)
        save_keys(keys)

    return jsonify({'result':'removed'})


@app.route('/admin/ban', methods=['POST'])
def admin_ban():
    if not require_admin():
        return jsonify({'result':'forbidden'}), 403
    if not request.is_json:
        return jsonify({'result':'error', 'message':'expected json body'}), 400
    typ = request.json.get('type')
    val = request.json.get('value')
    if not typ or not val:
        return jsonify({'result':'error', 'message':'missing type or value'}), 400
    bans = load_json(BANS_FILE, {"ips":[], "asns":[], "devices":[]})
    if typ == 'ip':
        if val in bans['ips']:
            return jsonify({'result':'exists'})
        bans['ips'].append(val)
    elif typ == 'asn':
        if val in bans['asns']:
            return jsonify({'result':'exists'})
        bans['asns'].append(val)
    elif typ == 'device':
        if val in bans['devices']:
            return jsonify({'result':'exists'})
        bans['devices'].append(val)
    else:
        return jsonify({'result':'error', 'message':'unknown type'}), 400
    save_json(BANS_FILE, bans)
    return jsonify({'result':'banned'})


@app.route('/admin/unban', methods=['POST'])
def admin_unban():
    if not require_admin():
        return jsonify({'result':'forbidden'}), 403
    if not request.is_json:
        return jsonify({'result':'error', 'message':'expected json body'}), 400
    typ = request.json.get('type')
    val = request.json.get('value')
    bans = load_json(BANS_FILE, {"ips":[], "asns":[], "devices":[]})
    if typ == 'ip' and val in bans['ips']:
        bans['ips'].remove(val)
    elif typ == 'asn' and val in bans['asns']:
        bans['asns'].remove(val)
    elif typ == 'device' and val in bans['devices']:
        bans['devices'].remove(val)
    else:
        return jsonify({'result':'not_found'})
    save_json(BANS_FILE, bans)
    return jsonify({'result':'unbanned'})


@app.route('/admin/connections', methods=['GET'])
def admin_connections():
    if not require_admin():
        return jsonify({'result':'forbidden'}), 403
    conns = load_json(CONNS_FILE, {})
    # convert timestamps to readable
    out = {}
    for k, v in conns.items():
        vv = v.copy()
        if 'last_seen' in vv:
            vv['last_seen_readable'] = datetime.utcfromtimestamp(vv['last_seen']).isoformat() + 'Z'
            # mark active if last_seen within 5 seconds
            now = int(time.time())
            vv['active'] = (now - vv.get('last_seen', 0)) <= 5
        out[k] = vv
    return jsonify({'result':'ok', 'connections': out})


@app.route('/admin/attempts', methods=['GET'])
def admin_attempts():
    if not require_admin():
        return jsonify({'result':'forbidden'}), 403
    lines = []
    try:
        with open(ATTEMPTS_LOG, 'r') as f:
            for line in f:
                try:
                    lines.append(json.loads(line.strip()))
                except Exception:
                    pass
    except Exception:
        pass
    return jsonify({'result':'ok', 'attempts': lines})

@app.route('/admin/list', methods=['GET'])
def admin_list():
    if not require_admin():
        return jsonify({'result':'forbidden'}), 403
    with lock:
        keys = load_keys()
    return jsonify({'result':'ok', 'keys':keys})

if __name__ == '__main__':
    # For quick testing only. Use gunicorn for production.
    port = int(os.environ.get('PORT', 5000))
    print('Starting license server on 0.0.0.0:%d' % port)
    app.run(host='0.0.0.0', port=port)
