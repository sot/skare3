"""Upload packages in current environment to upstream repo provider"""

import argparse
import getpass
import os
import subprocess
import json
from pathlib import Path, PosixPath

import paramiko


def get_opt():
    parser = argparse.ArgumentParser(description="Upload Ska Conda packages")

    parser.add_argument('packages', metavar='package', type=str, nargs='*',
                        help="Package to upload (default=all packages)")
    parser.add_argument("--host", type=str, default="kady.cfa.harvard.edu",
                        help="Remote host name (default='kady.cfa.harvard.edu'")
    parser.add_argument("--user", type=str, default="aca",
                        help="Remote user name (default='aca'")
    parser.add_argument("--repo-dir",
                        default='/proj/sot/ska/www/ASPECT_ICXC/ska3-conda/shiny',
                        type=str,
                        help="Root dir for conda package repository")
    parser.add_argument("--dry-run",
                        action="store_true",
                        help="Dry run, do not actually upload files")
    parser.add_argument("--force",
                        action="store_true",
                        help="Force package upload even if it exists")

    args = parser.parse_args()
    return args


def process_packages(args, sftp):
    pkgs_dir = Path(os.environ['CONDA_PREFIX_1']) / 'pkgs'

    result = subprocess.run(['conda', 'list', '--no-pip', '--json'], stdout=subprocess.PIPE)
    pkgs_json = result.stdout

    pkgs = json.loads(pkgs_json)

    for pkg in pkgs:
        if not args.packages or pkg['name'] in args.packages:
            process_package(args, sftp, pkgs_dir, pkg)


def process_package(args, sftp, pkgs_dir, pkg):
    pkg_defs_dir = Path.cwd() / 'pkg_defs'
    pkg_dir = pkgs_dir / pkg['dist_name']
    repodata = json.load(open(pkg_dir / 'info' / 'repodata_record.json'))
    platform = pkg['platform']  # noarch, win-64 etc
    name = pkg['name']
    version = pkg['version']
    filename = repodata['fn']
    pkg_file = pkgs_dir / filename

    if not pkg_file.exists():
        raise FileNotFoundError(f'file {pkg_file} not found')

    is_ska = (pkg_defs_dir / name).exists()
    print(f'{name}')
    print(f'  {version}')
    print(f'  {platform}')
    print(f'  is_ska: {is_ska}')

    lstat = pkg_file.stat()
    remote_pkg = PosixPath(args.repo_dir, platform, filename)
    try:
        print(f'Checking for {remote_pkg} on remote server')
        rstat = sftp.stat(str(remote_pkg))
    except Exception:
        exists = False
    else:
        exists = rstat.st_size == lstat.st_size

    if not exists or args.force:
        print(f'Uploading {filename}')
        if not args.dry_run:
            sftp.put(str(pkg_file), str(remote_pkg))
    else:
        print(f'Skipping {filename}, already exists')


def main():
    args = get_opt()
    password = getpass.getpass(f'Password for {args.user}: ')

    with paramiko.SSHClient() as ssh_client:
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh_client.connect(hostname=args.host, username=args.user, password=password)

        with ssh_client.open_sftp() as sftp:
            process_packages(args, sftp)


if __name__ == '__main__':
    main()
