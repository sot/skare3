#!/usr/bin/env python

import json
import logging
import subprocess
import requests
import collections
import argparse
from pathlib import Path


def get_patch_instructions(packages=()):
    p = subprocess.Popen(['conda', 'list', '--json'] + list(packages), stdout=subprocess.PIPE)
    stdout, stderr = p.communicate()
    packages = json.loads(stdout.decode())
    urls = set(['{base_url}/{platform}'.format(**p) for p in packages])
    rc = {url: requests.get(f'{url}/patch_instructions.json') for url in urls}
    upstream_patches = {url: json.loads(r.content.decode()) for url, r in rc.items() if r.ok}
    patches = collections.defaultdict(lambda: {'packages': {}, 'remove': [], 'revoke': []})
    for pkg in packages:
        url = '{base_url}/{platform}'.format(**pkg)
        if url in upstream_patches:
            key = None
            if f"{pkg['dist_name']}.tar.bz2" in upstream_patches[url]['packages']:
                key = f"{pkg['dist_name']}.tar.bz2"
            elif f"{pkg['dist_name']}.conda" in upstream_patches[url]['packages']:
                key = f"{pkg['dist_name']}.conda"
            if key is not None:
                patches[pkg['platform']]['packages'][key] = upstream_patches[url]['packages'][key]
                if 'patch_instructions_version' in patches[pkg['platform']] and patches[pkg['platform']]['patch_instructions_version'] != upstream_patches[url]['patch_instructions_version']:
                    logging.warning('patch_instructions_version mismatch')
                patches[pkg['platform']]['patch_instructions_version'] = upstream_patches[url]['patch_instructions_version']
    patches = dict(patches)
    return patches


def merge_patch_instructions(filenames):
    result = {'packages': {}, 'remove': [], 'revoke': []}
    for f in filenames:
        with open(f) as fh:
            patches = json.load(fh)
            result['packages'].update(patches['packages'])
            result['remove'] += patches['remove']
            result['revoke'] += patches['revoke']
            result['patch_instructions_version'] = patches['patch_instructions_version']
    result['remove'] = list(set(result['remove']))
    result['revoke'] = list(set(result['revoke']))
    return result


def get_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['get', 'merge'])
    parser.add_argument('items', nargs='*')
    parser.add_argument('--out', '-o', type=Path, default=Path('patch_instructions'))
    return parser


def main():
    args = get_parser().parse_args()

    if args.action == 'get':
        patches = get_patch_instructions(args.items)
        for platform in patches:
            (args.out / platform).mkdir(parents=True, exist_ok=True)
            with open(args.out / platform / 'patch_instructions.json', 'w') as fh:
                json.dump(patches[platform], fh, indent=2)
    elif args.action == 'merge':
        patches = merge_patch_instructions(args.items)
        args.out.mkdir(parents=True, exist_ok=True)
        with open(args.out / 'patch_instructions.json', 'w') as fh:
            json.dump(patches, fh, indent=2)


if __name__ == '__main__':
    main()
