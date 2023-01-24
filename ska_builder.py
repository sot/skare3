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
from fnmatch import fnmatch
import time

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
    parser.add_argument("--build-list",
                        help="List of packages to build (in order)")
    parser.add_argument('--exclude',
                        action='append',
                        default=[],
                        dest='excludes',
                        help="Exclude packages that match glob pattern"),
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
    parser.add_argument('--ska3-overwrite-version',
                        metavar='[<initial-version>:]<final-version>',
                        help="This option is intended to overwrite ska3-* meta-package versions "
                             "when building/testing pre-releases. If the initial version is not "
                             "given, it is assumed to be the same as the final version with the "
                             "pre-release portion of the version string removed.")

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
        repo.remotes.upstream.fetch()

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
    pkg_path = Path(src_dir) / 'pkg_defs' / name
    shutil.copytree(PKG_DEFS_PATH / name, pkg_path)

    if args.ska3_overwrite_version and re.match(r'ska3-\S+$', name):
        skare3_old_version, skare3_new_version = args.ska3_overwrite_version.split(':')
        print(f'  - overwriting skare3 meta-package version '
              f'{skare3_old_version} -> {skare3_new_version}')
        overwrite_skare3_version(skare3_old_version, skare3_new_version, pkg_path)

    try:
        version = subprocess.check_output(['python', 'setup.py', '--version'],
                                          cwd=os.path.join(src_dir, name))
        version = version.decode().split()[-1].strip()
        print(f'  - SKA_PKG_VERSION={version}')
    except Exception:
        version = ''
    os.environ['SKA_PKG_VERSION'] = version

    cmd_list = ["conda", "build", str(pkg_path),
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
    print('-' * 80)
    is_windows = os.name == 'nt'  # Need shell below for Windows
    subprocess.run(cmd_list, check=True, shell=is_windows).check_returncode()


def build_list_packages(pkg_names, args, src_dir, build_dir):
    failures = []
    tstart = time.time()

    for pkg_name in pkg_names:
        print()
        print('*' * 80)
        print(f'*** {pkg_name} (build start: {time.time() - tstart:.1f} secs)')
        print('*' * 80)
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

        if any(fnmatch(pkg_name, exclude) for exclude in args.excludes):
            print(f'Skipping excluded package {pkg_name}')
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


def overwrite_skare3_version(current_version, new_version, pkg_path):
    """
    Replaces `current_version` by `new_version` in the meta.yaml file located at `pkg_path`.

    This is not a general replacement. The version is replaced if:

      - the line matches the pattern "  version: <current_version>"
      - the line matches the pattern "  <pkg_name> ==<current_version>"

    with possible whitespace before/after, or whitespace around the colon or equality operator.

    Note that this function would not replace the version string if the "version" tag and the value
    are not in the same line, even though this is correct yaml syntax.

    :param current_version: str
    :param new_version: str
    :param pkg_path: pathlib.Path
    :return:
    """
    meta_file = pkg_path / 'meta.yaml'
    with open(meta_file) as fh:
        lines = fh.readlines()
    for i, line in enumerate(lines):
        m = re.search(r'(\s+)?version(\s+)?:(\s+)?(?P<version>(\S+)+)', line)
        if m:
            version = m.groupdict()['version']
            if version == str(current_version):
                print(f'    - version: {current_version} -> {new_version}')
                lines[i] = line.replace(current_version, new_version)
        m = re.search(r'(\s+)?(?P<name>\S+)(\s+)?==(\s+)?(?P<version>(\S+)+)', line)
        if m:
            info = m.groupdict()
            if re.match(r'ska3-\S+$', info['name']) and info['version'] == current_version:
                print(f'    - {info["name"]} dependency: {current_version} -> {new_version}')
                lines[i] = line.replace(current_version, new_version)

    with open(meta_file, 'w') as f:
        for line in lines:
            f.write(line)


def main():
    args = get_opt()

    if args.ska3_overwrite_version:
        """
        the value of  args.ska3_overwrite_version can be of the forms:
        - `<initial-version>:<final-version>`.
        - `<final-version>`.
        
        In the first case, there is nothing to do. In the second case, we assume that the final
        version is the same as the final version but removing the release candidate part
        (i.e.: something that looks like "rcN" or "aN" or "bN").
        """
        if ':' not in args.ska3_overwrite_version:
            rc = re.match(
                r"""(?P<version>
                    (?P<release>\S+)     # release segment (usually N!N.N.N but not enforced here)
                    (a|b|rc)[0-9]+       # pre-release segment (rcN, aN or bN, required)
                    (\+(?P<label>\S+))?  # label fragment (an optional string)
                )$""",
                args.ska3_overwrite_version,
                re.VERBOSE
            )
            if not rc:
                raise Exception(f'wrong format for ska3_overwrite_version: '
                                f'{args.ska3_overwrite_version}')
            version_info = rc.groupdict()
            version_info["label"] = f'+{version_info["label"]}' if version_info["label"] else ''
            args.ska3_overwrite_version = \
                f'{version_info["release"]}{version_info["label"]}:{version_info["version"]}'

    if args.packages:
        pkg_names = args.packages
    else:
        if args.build_list:
            with open(args.build_list) as fh:
                pkg_names = [line.strip() for line in fh
                             if not re.match(r'\s*#', line) and line.strip()]
        else:
            pkg_names = [str(pth.name) for pth in PKG_DEFS_PATH.glob('*') if pth.is_dir()]
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
