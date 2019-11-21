#!/usr/bin/env python

import os
import subprocess
import git
import re
import argparse
import platform


parser = argparse.ArgumentParser(description="Build Ska Conda packages.")

parser.add_argument("package", type=str, nargs="?",
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
                    help="Authenticate using basic auth and https. Default is ssh.")

args = parser.parse_args()

raw_build_list = open(args.build_list).read()
BUILD_LIST = raw_build_list.split("\n")
# Remove any that are commented out for some reason
BUILD_LIST = [b for b in BUILD_LIST if not re.match(r"^\s*#", b)]
# And any that are just whitespace
BUILD_LIST = [b for b in BUILD_LIST if not re.match(r"^\s*$", b)]

if platform.uname().system == "Darwin":
    os.environ["MACOSX_DEPLOYMENT_TARGET"] = "10.14"  # Mojave

ska_conda_path = os.path.abspath(os.path.dirname(__file__))
pkg_defs_path = os.path.join(ska_conda_path, "pkg_defs")

BUILD_DIR = os.path.abspath(os.path.join(args.build_root, "builds"))
SRC_DIR = os.path.abspath(os.path.join(args.build_root, "src"))
os.environ["SKA_TOP_SRC_DIR"] = SRC_DIR

def clone_repo(name, tag=None):
    print("  - Cloning or updating source source %s." % name)
    clone_path = os.path.join(SRC_DIR, name)
    if not os.path.exists(clone_path):
        metayml = os.path.join(pkg_defs_path, name, "meta.yaml")
        meta = open(metayml).read()
        has_git = re.search("SKA_PKG_VERSION", meta) or re.search("GIT_DESCRIBE_TAG", meta)
        if not has_git:
            return None
        # It isn't clean yaml at this point, so just extract the string we want after "home:"
        url = re.search(r"home:\s*(\S+)", meta).group(1)
        if args.github_https:
            url = url.replace('git@github.com:', 'https://github.com/')
        else:
            url = url.replace('https://github.com/', 'git@github.com:')
        repo = git.Repo.clone_from(url, clone_path)
        print("  - Cloned from url {}".format(url))
    else:
        repo = git.Repo(clone_path)
        repo.remotes.origin.fetch()
        repo.remotes.origin.fetch("--tags")
        print("  - Updated repo in {}".format(clone_path))
    assert not repo.is_dirty()
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
        print("  - Checked out at {}".format(tag))


def build_package(name):
    print('*' * 80)
    print(name)
    print()
    pkg_path = os.path.join(pkg_defs_path, name)

    try:
        version = subprocess.check_output(['python', 'setup.py', '--version'],
                                          cwd=os.path.join(SRC_DIR, name))
        version = version.decode().split()[-1].strip()
    except Exception:
        version = ''
    os.environ['SKA_PKG_VERSION'] = version
    print(f'  - SKA_PKG_VERSION={version}')

    cmd_list = ["conda", "build", pkg_path,
                "--croot", BUILD_DIR,
                "--old-build-string",
                "--no-anaconda-upload",
                "--python", args.python,
                "--numpy", args.numpy,
                "--perl", args.perl]

    if not args.test:
        cmd_list.append("--no-test")
    if not args.force:
        cmd_list += ["--skip-existing"]
    cmd = ' '.join(cmd_list)
    print(f'  - {cmd}')
    print('*' * 80)
    is_windows = os.name == 'nt'  # Need shell below for Windows
    subprocess.run(cmd_list, check=True, shell=is_windows).check_returncode()


def build_one_package(name, tag=None):
    print("- Building package %s." % name)
    clone_repo(name, tag)
    build_package(name)
    print('')


def build_list_packages():
    failures = []
    for pkg_name in BUILD_LIST:
        try:
            build_one_package(pkg_name)
        # If there's a failure, confirm before continuing
        except Exception:
            print(f'{pkg_name} failed, continue anyway (y/n)?')
            if input().lower().strip().startswith('y'):
                failures.append(pkg_name)
                continue
            else:
                raise ValueError(f"{pkg_name} failed")
    if len(failures):
        raise ValueError("Packages {} failed".format(",".join(failures)))


def build_all_packages():
    build_list_packages()


if getattr(args, 'package'):
    build_one_package(args.package, tag=args.tag)
else:
    if args.tag is not None:
        raise ValueError("Cannot supply '--tag' without specific package'")
    build_all_packages()
