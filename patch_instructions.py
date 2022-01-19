#!/usr/bin/env python

"""
This script takes care of fetching patch instructions from upstream repositories. See
https://docs.conda.io/projects/conda-build/en/latest/concepts/generating-index.html#repodata-patching
to learn more about this.

While both Anaconda and conda-forge maintain a set of python scripts to generate these patch
instructions (which are stored in JSON format), we just get their patch instructions and try to
merge them. Hopefully this will work... famous last words.
"""


import json
import re
import logging
import subprocess
import requests
import collections
import argparse
from pathlib import Path


def match(package, spec_string):
    """
    Check if a package info matches a spec string.

    If present, the version must be an exact match.

    Parameters
    ----------
    package : dict
        Usually the output of `conda list --json`
    spec_string : str
        a string of the form <name>[==<version>]

    Returns
    -------
    bool
    """
    m = re.match(r'(?P<name>[-_a-zA-Z0-9]+)(==)?(?P<version>\S+)?', spec_string)
    if m:
        parts = m.groupdict()
        return (
            parts['name'] == package['name']
            and ((parts['version'] is None) or (parts['version'] == package['version']))
        )
    return False


def get_patch_instructions(packages=()):
    """
    Fetch patch instructions from upstream repositories.

    Parameters
    ----------
    packages : list
        A list of dictionaries. Usually the output of `conda list --json`

    Returns
    -------
    dict
    """
    # get all installed packages
    p = subprocess.Popen(['conda', 'list', '--json'], stdout=subprocess.PIPE)
    stdout, stderr = p.communicate()
    package_info = json.loads(stdout.decode())
    if packages:
        # only consider the ones requested
        tmp = []
        for pkg_string in packages:
            for pkg in package_info:
                if match(pkg, pkg_string):
                    tmp.append(pkg)
                    break
            else:
                logging.warning(f'Package spec {pkg_string} not found')
        package_info = tmp
    # get patch instruction from all upstream repositories
    urls = set(['{base_url}/{platform}'.format(**p) for p in package_info])
    rc = {url: requests.get(f'{url}/patch_instructions.json') for url in urls}
    upstream_patches = {url: json.loads(r.content.decode()) for url, r in rc.items() if r.ok}
    # put those instructions in our on dictionary
    patches = collections.defaultdict(lambda: {'packages': {}, 'remove': [], 'revoke': []})
    for pkg in package_info:
        url = '{base_url}/{platform}'.format(**pkg)
        if url in upstream_patches:
            key = None
            if f"{pkg['dist_name']}.tar.bz2" in upstream_patches[url]['packages']:
                key = f"{pkg['dist_name']}.tar.bz2"
            elif f"{pkg['dist_name']}.conda" in upstream_patches[url]['packages']:
                key = f"{pkg['dist_name']}.conda"
            if key is not None:
                patches[pkg['platform']]['packages'][key] = upstream_patches[url]['packages'][key]
                if ('patch_instructions_version' in patches[pkg['platform']]
                    and (patches[pkg['platform']]['patch_instructions_version']
                         != upstream_patches[url]['patch_instructions_version'])):
                    logging.warning('patch_instructions_version mismatch')
                patches[pkg['platform']]['patch_instructions_version'] = \
                    upstream_patches[url]['patch_instructions_version']
    patches = dict(patches)
    return patches


def merge_patch_instructions(filenames):
    """
    Merges a list of JSON files into a single one.

    This assumes that the JSON file has a top-level dictionary with the following keys:
    packages, remove, revoke, patch_instructions_version.

    The reason for this is that we make patch files in each platform, which results in potentially
    different JSON files for the noarch directory, since it depends on the packages actually
    installed. We then gather all packages and need to merge the patches.
    """
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
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        'action',
        choices=['get', 'merge'],
        help="Action to perform."
    )
    parser.add_argument(
        'items',
        nargs='*',
        help=(
            'If action==merge: a list of JSON files to merge. '
            'If action==get: spec strings listing packages we want patch instructions for. '
            'If not provided, patch instructions are fetched for all installed packages. '
            'Each spec string must be of the form <name>[==<version>].'
        )
    )
    parser.add_argument(
        '--out', '-o', type=Path, default=Path('patch_instructions'),
        help='directory where to place patch_instructions.json files.'
    )
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
