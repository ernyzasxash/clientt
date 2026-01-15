#!/usr/bin/env python3
import os
import json
import threading
import requests
from datetime import datetime
from flask import Flask, request, jsonify

APP_DIR = os.path.dirname(os.path.abspath(__file__))
KEYS_FILE = os.path.join(APP_DIR, 'authorized_keys.json')
CONNECTIONS_FILE = os.path.join(APP_DIR, 'connections.json')
FAILED_LOGINS_FILE = os.path.join(APP_DIR, 'failed_logins.json')
BANS_FILE = os.path.join(APP_DIR, 'bans.json')
ADMIN_TOKEN = os.environ.get('ADMIN_TOKEN', 'change-me')

lock = threading.Lock()

def load_json(filepath, default=None):
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except Exception:
        return default if default is not None else []

def save_json(filepath, data):
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)

def get_asn_info(ip):
    """Fetch ASN info from IP using ip-api.com"""
    try:
        resp = requests.get(f"http://ip-api.com/json/{ip}?fields=org,asn,isp", timeout=2)
        if resp.status_code == 200:
            data = resp.json()
            return {
                "asn": data.get("asn", "N/A"),
                "org": data.get("org", "N/A"),
                "isp": data.get("isp", "N/A")
            }
    except Exception:
        pass
    return {"asn": "N/A", "org": "N/A", "isp": "N/A"}

def is_banned(ip, key, asn):
    """Check if IP, key, or ASN is banned"""
    bans = load_json(BANS_FILE, [])
    for ban in bans:
        if ban.get("type") == "ip" and ban.get("value") == ip:
            return True
        if ban.get("type") == "key" and ban.get("value") == key:
            return True
        if ban.get("type") == "asn" and ban.get("value") == asn:
            return True
    return False

def log_connection(ip, key, device_name, device_info, success):
    """Log connection attempt"""
    with lock:
        asn_info = get_asn_info(ip)
        conn = {
            "ip": ip,
            "key": key,
            "device_name": device_name or "Unknown",
            "device_info": device_info or {},
            "asn": asn_info.get("asn"),
            "org": asn_info.get("org"),
            "isp": asn_info.get("isp"),
            "timestamp": datetime.now().isoformat(),
            "success": success
        }
        
        if success:
            conns = load_json(CONNECTIONS_FILE, [])
            conns.append(conn)
            save_json(CONNECTIONS_FILE, conns)
        else:
            failed = load_json(FAILED_LOGINS_FILE, [])
            failed.append(conn)
            save_json(FAILED_LOGINS_FILE, failed)

app = Flask(__name__)

# Ensure files exist
for f in [KEYS_FILE, CONNECTIONS_FILE, FAILED_LOGINS_FILE, BANS_FILE]:
    if not os.path.exists(f):
        with open(f, 'w') as fp:
            json.dump([], fp)

@app.route('/check', methods=['GET', 'POST'])
def check_key():
    """License key check endpoint"""
    key = request.args.get('key') or request.headers.get('X-License-Key')
    if not key and request.is_json:
        key = request.json.get('key')
    
    device_name = request.args.get('device_name') or (request.json.get('device_name') if request.is_json else None)
    device_info = request.args.get('device_info') or (request.json.get('device_info') if request.is_json else None)
    
    ip = request.remote_addr
    
    if not key:
        return jsonify({'result': 'error', 'message': 'no key provided'}), 400
    
    # Check if banned
    asn_info = get_asn_info(ip)
    asn = asn_info.get("asn")
    if is_banned(ip, key, asn):
        log_connection(ip, key, device_name, device_info, False)
        return jsonify({'result': 'banned'})
    
    # Check key validity
    with lock:
        keys = load_json(KEYS_FILE, [])
    
    if key in keys:
        log_connection(ip, key, device_name, device_info, True)
        return jsonify({'result': 'success'})
    else:
        log_connection(ip, key, device_name, device_info, False)
        return jsonify({'result': 'wrong'})

def require_admin():
    token = request.headers.get('X-Admin-Token')
    if not token or token != ADMIN_TOKEN:
        return False
    return True

@app.route('/admin/connections', methods=['GET'])
def admin_connections():
    """List active connections"""
    if not require_admin():
        return jsonify({'result': 'forbidden'}), 403
    with lock:
        conns = load_json(CONNECTIONS_FILE, [])
    # Return only successful connections (active sessions)
    active = [c for c in conns if c.get('success')]
    return jsonify({'result': 'ok', 'connections': active})

@app.route('/admin/failed-logins', methods=['GET'])
def admin_failed_logins():
    """List failed login attempts"""
    if not require_admin():
        return jsonify({'result': 'forbidden'}), 403
    with lock:
        failed = load_json(FAILED_LOGINS_FILE, [])
    return jsonify({'result': 'ok', 'failed': failed})

@app.route('/admin/ban', methods=['POST'])
def admin_ban():
    """Add ban (IP, ASN, or key)"""
    if not require_admin():
        return jsonify({'result': 'forbidden'}), 403
    if not request.is_json:
        return jsonify({'result': 'error', 'message': 'expected json body'}), 400
    
    ban_type = request.json.get('type')  # 'ip', 'asn', 'key'
    value = request.json.get('value')
    reason = request.json.get('reason', '')
    
    if not ban_type or not value:
        return jsonify({'result': 'error', 'message': 'type and value required'}), 400
    
    if ban_type not in ['ip', 'asn', 'key']:
        return jsonify({'result': 'error', 'message': 'invalid type'}), 400
    
    with lock:
        bans = load_json(BANS_FILE, [])
        for b in bans:
            if b.get('type') == ban_type and b.get('value') == value:
                return jsonify({'result': 'exists'})
        
        bans.append({
            'type': ban_type,
            'value': value,
            'reason': reason,
            'timestamp': datetime.now().isoformat()
        })
        save_json(BANS_FILE, bans)
    
    return jsonify({'result': 'added'})

@app.route('/admin/unban', methods=['POST'])
def admin_unban():
    """Remove ban"""
    if not require_admin():
        return jsonify({'result': 'forbidden'}), 403
    if not request.is_json:
        return jsonify({'result': 'error', 'message': 'expected json body'}), 400
    
    ban_type = request.json.get('type')
    value = request.json.get('value')
    
    if not ban_type or not value:
        return jsonify({'result': 'error', 'message': 'type and value required'}), 400
    
    with lock:
        bans = load_json(BANS_FILE, [])
        bans = [b for b in bans if not (b.get('type') == ban_type and b.get('value') == value)]
        save_json(BANS_FILE, bans)
    
    return jsonify({'result': 'removed'})

@app.route('/admin/bans', methods=['GET'])
def admin_bans():
    """List all bans"""
    if not require_admin():
        return jsonify({'result': 'forbidden'}), 403
    with lock:
        bans = load_json(BANS_FILE, [])
    return jsonify({'result': 'ok', 'bans': bans})

@app.route('/admin/add', methods=['POST'])
def admin_add():
    """Add new key"""
    if not require_admin():
        return jsonify({'result': 'forbidden'}), 403
    if not request.is_json:
        return jsonify({'result': 'error', 'message': 'expected json body'}), 400
    key = request.json.get('key')
    if not key:
        return jsonify({'result': 'error', 'message': 'no key'}), 400
    
    with lock:
        keys = load_json(KEYS_FILE, [])
        if key in keys:
            return jsonify({'result': 'exists'})
        keys.append(key)
        save_json(KEYS_FILE, keys)
    
    return jsonify({'result': 'added'})

@app.route('/admin/remove', methods=['POST'])
def admin_remove():
    """Remove key"""
    if not require_admin():
        return jsonify({'result': 'forbidden'}), 403
    if not request.is_json:
        return jsonify({'result': 'error', 'message': 'expected json body'}), 400
    key = request.json.get('key')
    if not key:
        return jsonify({'result': 'error', 'message': 'no key'}), 400
    
    with lock:
        keys = load_json(KEYS_FILE, [])
        if key not in keys:
            return jsonify({'result': 'not_found'})
        keys.remove(key)
        save_json(KEYS_FILE, keys)
    
    return jsonify({'result': 'removed'})

@app.route('/admin/list', methods=['GET'])
def admin_list():
    """List all keys"""
    if not require_admin():
        return jsonify({'result': 'forbidden'}), 403
    with lock:
        keys = load_json(KEYS_FILE, [])
    return jsonify({'result': 'ok', 'keys': keys})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print('Starting extended license server on 0.0.0.0:%d' % port)
    app.run(host='0.0.0.0', port=port)
