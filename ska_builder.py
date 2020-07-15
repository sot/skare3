#!/usr/bin/env python

import sys
import os
import subprocess
import re
import argparse
import platform
import shutil
from pathlib import Path
import tempfile

import git
import jinja2
import yaml

PKG_DEFS_PATH = Path(__file__).parent / 'pkg_defs'


def get_opt():
    parser = argparse.ArgumentParser(description="Build Ska Conda packages.")

    parser.add_argument('packages', metavar='package', type=str, nargs='*',
                        help="Package to build (default=build all packages)")
    parser.add_argument("--tag", type=str,
                        help="Optional tag, branch, or commit to build for single package build"
                        " (default is tag with most recent commit)")
    parser.add_argument("--build-root", default=".", type=str,
                        help="Path to root directory for output conda build packages."
                        "Default: '.'")
    parser.add_argument("--build-list", default="./ska3_flight_build_order.txt",
                        help="List of packages to build (in order)")
    parser.add_argument("--test",
                        action="store_true",
                        help="Run test during build process")
    parser.add_argument("--force",
                        action="store_true",
                        help="Force build of package even if it exists")
    parser.add_argument("--arch-specific",
                        action="store_true",
                        help="Build only architecture-specific packages")
    parser.add_argument("--python",
                        default="3.8",
                        help="Target version of Python (default=3.8)")
    parser.add_argument("--perl",
                        default="5.26.2",
                        help="Target version of Perl (default=5.26.2)")
    parser.add_argument("--numpy",
                        default="1.18",
                        help="Build version of NumPy")
    parser.add_argument("--github-https", action="store_true", default=False,
                        help="Authenticate using basic auth and https. Default is ssh "
                        "except on Windows")
    parser.add_argument("--repo-url",
                        help="Use this URL instead of meta['about']['home']")

    args = parser.parse_args()
    return args


def clone_repo(name, args, src_dir, meta):
    tag = args.tag
    print("  - Cloning or updating source source %s." % name)
    clone_path = os.path.join(src_dir, name)

    # Upstream (home) URL is for the tags
    upstream_url = meta['about']['home']

    # URL for cloning
    if args.repo_url:
        url = args.repo_url
    else:
        url = upstream_url
        # Munge URL for different authentication if requested
        if args.github_https:
            url = url.replace('git@github.com:', 'https://github.com/')
        else:
            url = url.replace('https://github.com/', 'git@github.com:')

    repo = git.Repo.clone_from(url, clone_path)
    print("  - Cloned from url {}".format(url))

    if args.repo_url:
        # Get tags from the upstream URL
        repo.create_remote('upstream', upstream_url)
        repo.remotes.upstream.fetch('--tags')
    else:
        repo.remotes.origin.fetch('--tags')

    # I think we want the commit/tag with the most recent date, though
    # if we actually want the most recently created tag, that would probably be
    # tags = sorted(repo.tags, key=lambda t: t.tag.tagged_date)
    # I suppose we could also use github to get the most recent release (not tag)
    if tag is None:
        tags = sorted(repo.tags, key=lambda t: t.commit.committed_datetime)
        repo.git.checkout(tags[-1].name)
        if tags[-1].commit == repo.heads.master.commit:
            print("  - Auto-checked out at {} which is also tip of master".format(tags[-1].name))
        else:
            print("  - Auto-checked out at {} NOT AT tip of master".format(tags[-1].name))
    else:
        repo.git.checkout(tag)
        print(f'  - Checked out at {tag} and pulled')


def build_package(name, args, src_dir, build_dir):
    print('*' * 80)
    print(name)
    print()
    pkg_path = os.path.join(PKG_DEFS_PATH, name)

    try:
        version = subprocess.check_output(['python', 'setup.py', '--version'],
                                          cwd=os.path.join(src_dir, name))
        version = version.decode().split()[-1].strip()
    except Exception:
        version = ''
    os.environ['SKA_PKG_VERSION'] = version
    print(f'  - SKA_PKG_VERSION={version}')

    cmd_list = ["conda", "build", pkg_path,
                "--croot", str(build_dir),
                "--old-build-string",
                "--no-anaconda-upload",
                "--python", args.python,
                "--numpy", args.numpy,
                "--perl", args.perl]

    if not args.test:
        cmd_list.append("--no-test")

    if args.force:
        for path in Path(build_dir).glob(f'*/.cache/*/{name}-*'):
            print(f'Removing {path}')
            path.unlink()

        sys_prefix = Path(sys.prefix)
        if (sys_prefix.parent).name == 'envs':
            # Building in a miniconda env, can find packages one dir up in pkgs
            pkgs_dir = sys_prefix.parent.parent / 'pkgs'
            for path in pkgs_dir.glob(f'{name}-*'):
                print(f'Removing {path}')
                if path.is_dir():
                    shutil.rmtree(path)
                else:
                    path.unlink()

    else:
        cmd_list += ["--skip-existing"]

    cmd = ' '.join(cmd_list)
    print(f'  - {cmd}')
    print('*' * 80)
    is_windows = os.name == 'nt'  # Need shell below for Windows
    subprocess.run(cmd_list, check=True, shell=is_windows).check_returncode()


def build_list_packages(pkg_names, args, src_dir, build_dir):
    failures = []
    for pkg_name in pkg_names:
        # Read package meta.yaml text
        meta_file = PKG_DEFS_PATH / pkg_name / "meta.yaml"
        meta_text = meta_file.read_text()
        has_git = re.search(r'SKA_PKG_VERSION|GIT_DESCRIBE_TAG', meta_text)

        # Stub out the jinja context variables and parse meta.yaml
        macro = '{% macro compiler(arg) %}{% endmacro %}\n'
        meta = yaml.safe_load(jinja2.Template(macro + meta_text).render())

        if args.arch_specific and 'noarch' in meta.get('build', {}):
            print(f'Skipping noarch package {pkg_name}')
            continue

        print("- Building package %s." % pkg_name)
        try:
            if has_git:
                clone_repo(pkg_name, args, src_dir, meta)
            build_package(pkg_name, args, src_dir, build_dir)
            print('')
        except Exception:
            # If there's a failure, confirm before continuing
            print(f'{pkg_name} failed, continue anyway (y/n)?')
            if input().lower().strip().startswith('y'):
                failures.append(pkg_name)
                continue
            else:
                raise ValueError(f"{pkg_name} failed")
    if len(failures):
        raise ValueError("Packages {} failed".format(",".join(failures)))


def main():
    args = get_opt()

    if args.packages:
        pkg_names = args.packages
    else:
        if args.build_list:
            with open(args.build_list) as fh:
                pkg_names = [line.strip() for line in fh
                             if not re.match(r'\s*#', line) and line.strip()]
        else:
            pkg_names = [str(pth) for pth in PKG_DEFS_PATH.glob('*') if pth.is_dir()]
        pkg_names = sorted(pkg_names)

    print(f'Building packages {pkg_names}')

    system_name = platform.uname().system
    if system_name == 'Darwin':
        os.environ["MACOSX_DEPLOYMENT_TARGET"] = "10.14"  # Mojave
    elif system_name == 'Windows':
        # Always use https on Windows since it just works
        args.github_https = True

    build_dir = Path(args.build_root) / 'builds'
    with tempfile.TemporaryDirectory() as src_dir:
        print(f'Using temporary directory {src_dir} for cloning')
        os.environ["SKA_TOP_SRC_DIR"] = src_dir
        build_list_packages(pkg_names, args, src_dir, build_dir)


if __name__ == '__main__':
    main()
