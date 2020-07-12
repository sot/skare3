"""Fix dependencies in repodata.json in a conda repository ``name``.

For driver see https://github.com/ContinuumIO/anaconda-issues/issues/11920

This depends on files {name}/repodata_{arch}.json that have been generated
with ``upload_packages.py``. These include the dependencies as defined
by the original upstream (e.g. pkgs/main) repodata.json. These may be more
liberal than those within the package itself for reasons I don't understand.
"""

import argparse
import bz2
import json
from pathlib import Path
import collections
from upload_packages import process_packages


def get_opt():
    parser = argparse.ArgumentParser(description="Fix repodata.json dependencies")

    parser.add_argument("repo_dir",
                        type=str,
                        help="Root dir for conda package repository")

    args = parser.parse_args()
    print(args)
    return args


def main():
    args = get_opt()

    # Collect package repodata supplied by upload_packages which includes the
    # desired dependencies. For each arch there will typically be packages for
    # that arch along with noarch.
    pkgs_by_subdir = collections.defaultdict(dict)
    for arch in ('win-64', 'linux-64', 'osx-64'):
        repo_file = Path(args.repo_dir, f'repodata_{arch}.json')
        if repo_file.exists():
            print(f'Reading {repo_file}')
            repodata = json.load(open(repo_file))
            for name, pkg in repodata.items():
                pkgs_by_subdir[pkg['subdir']][name] = pkg
        else:
            print(f'Skipping {repo_file}')

    print('Contents of repodata_{arch} files')
    for arch, pkgs in pkgs_by_subdir.items():
        print(f'********* {arch} ***********')
        for name in pkgs:
            print(name)

    for subdir, pkgs_fix in pkgs_by_subdir.items():
        repo_file = Path(args.repo_dir, subdir, f'repodata.json')
        if repo_file.exists():
            print(f'Reading {repo_file}')
            with open(repo_file) as fh:
                repodata = json.load(fh)

            packages = repodata['packages'].copy()
            packages.update(repodata['packages.conda'])
            for name in packages:
                print(name)
            for name, package in packages.items():
                if package['depends'] != pkgs_fix[name]['depends']:
                    print(f'Fixing {subdir} {name}')
                    package['depends'] = pkgs_fix[name]['depends']
                else:
                    print(f'OK {subdir} {name}')

            repodata['packages'] = packages

            with open(repo_file, 'w') as fh:
                print(f'Writing {repo_file}')
                json.dump(repodata, fh)
            with open(repo_file, 'rb') as fh_in, bz2.open(str(repo_file) + '.bz2', 'wb') as fh_out:
                print(f'Writing {repo_file}.bz2')
                fh_out.writelines(fh_in)
            
        else:
            print(f'Skipping {repo_file}')


if __name__ == '__main__':
    main()
