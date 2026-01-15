#!/usr/bin/env python3
import os
import json
import argparse

APP_DIR = os.path.dirname(os.path.abspath(__file__))
KEYS_FILE = os.path.join(APP_DIR, 'authorized_keys.json')

def load_keys():
    try:
        with open(KEYS_FILE, 'r') as f:
            return json.load(f)
    except Exception:
        return []

def save_keys(keys):
    with open(KEYS_FILE, 'w') as f:
        json.dump(keys, f, indent=2)

def add_key(key):
    keys = load_keys()
    if key in keys:
        print('exists')
        return
    keys.append(key)
    save_keys(keys)
    print('added')

def remove_key(key):
    keys = load_keys()
    if key not in keys:
        print('not_found')
        return
    keys.remove(key)
    save_keys(keys)
    print('removed')

def list_keys():
    keys = load_keys()
    for k in keys:
        print(k)

def main():
    p = argparse.ArgumentParser(description='Manage authorized license keys file')
    sub = p.add_subparsers(dest='cmd')
    a = sub.add_parser('add')
    a.add_argument('key')
    r = sub.add_parser('remove')
    r.add_argument('key')
    l = sub.add_parser('list')

    args = p.parse_args()
    if args.cmd == 'add':
        add_key(args.key)
    elif args.cmd == 'remove':
        remove_key(args.key)
    elif args.cmd == 'list':
        list_keys()
    else:
        p.print_help()

if __name__ == '__main__':
    main()
