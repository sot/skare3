#!/usr/bin/env python

"""
This script takes care of fetching packages and patch instructions from upstream repositories. See
https://docs.conda.io/projects/conda-build/en/latest/concepts/generating-index.html#repodata-patching
to learn more about patches.

While both Anaconda and conda-forge maintain a set of python scripts to generate these patch
instructions (which are stored in JSON format), we just get their patch instructions and try to
merge them. Hopefully this will work... famous last words.
"""


import json
import os
import re
import logging
import subprocess
import requests
import collections
import argparse
import tarfile
import tempfile
import shutil
import functools
import pprint
import tqdm
from pathlib import Path

logging.basicConfig(level="DEBUG")

logger = logging.getLogger("skare3")


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
    m = re.match(r"(?P<name>[-_a-zA-Z0-9]+)(==)?(?P<version>\S+)?", spec_string)
    if m:
        parts = m.groupdict()
        return parts["name"] == package["name"] and (
            (parts["version"] is None) or (parts["version"] == package["version"])
        )
    return False


def get_patch_instructions(packages=(), conda_list=None):
    """
    Fetch patch instructions from upstream repositories.

    Parameters
    ----------
    packages : list
        A list of string. A package spec like "cfitsio==4.2.0". It must be a package in the conda list.
    conda_list : list
        A list of dictionaries. Usually the output of `conda list --json`

    Returns
    -------
    dict
        The patch instructions
    """
    if conda_list is None:
        # get all installed packages
        p = subprocess.Popen(["conda", "list", "--json"], stdout=subprocess.PIPE)
        stdout, _ = p.communicate()
        conda_list = json.loads(stdout.decode())
    if packages:
        # only consider the ones requested
        tmp = []
        for pkg_string in packages:
            for pkg in conda_list:
                if match(pkg, pkg_string):
                    tmp.append(pkg)
                    break
            else:
                logger.warning(f"Package spec {pkg_string} not found")
        conda_list = tmp

    # get patch instruction from all upstream repositories
    urls = set(["{base_url}/{platform}".format(**p) for p in conda_list])
    rc = {url: requests.get(f"{url}/patch_instructions.json") for url in urls}
    upstream_patches = {
        url: json.loads(r.content.decode()) for url, r in rc.items() if r.ok
    }

    with open("debug.json", "w") as fh:
        json.dump(upstream_patches, fh)

    # put those instructions in our on dictionary
    patches = collections.defaultdict(
        lambda: {"packages": {}, "packages.conda": {}, "remove": [], "revoke": []}
    )
    for pkg in conda_list:
        url = "{base_url}/{platform}".format(**pkg)

        if url in upstream_patches:
            key = None
            pkgs_key = None
            if f"{pkg['dist_name']}.tar.bz2" in upstream_patches[url]["packages"]:
                key = f"{pkg['dist_name']}.tar.bz2"
                pkgs_key = "packages"
            elif f"{pkg['dist_name']}.conda" in upstream_patches[url]["packages"]:
                key = f"{pkg['dist_name']}.conda"
                pkgs_key = "packages"
            elif (
                "packages.conda" in upstream_patches[url]
                and f"{pkg['dist_name']}.conda"
                in upstream_patches[url]["packages.conda"]
            ):
                key = f"{pkg['dist_name']}.conda"
                pkgs_key = "packages.conda"

            if key is not None:
                patches[pkg["platform"]][pkgs_key][key] = upstream_patches[url][
                    pkgs_key
                ][key]
                if "patch_instructions_version" in patches[pkg["platform"]] and (
                    patches[pkg["platform"]]["patch_instructions_version"]
                    != upstream_patches[url]["patch_instructions_version"]
                ):
                    logger.warning("patch_instructions_version mismatch")
                patches[pkg["platform"]][
                    "patch_instructions_version"
                ] = upstream_patches[url]["patch_instructions_version"]
    patches = dict(patches)
    return patches


def _merge_patch_instructions(patch_instructions):
    """
    Merges a list of path instructions.

    This asumes each entry in the path instructions list is dictionary with the following keys:
    packages, packages.conda, remove, revoke, patch_instructions_version.

    The reason for this is that we make patch files in each platform, which results in potentially
    different JSON files for the noarch directory, since it depends on the packages actually
    installed. We then gather all packages and need to merge the patches.
    """
    result = {"packages": {}, "packages.conda": {}, "remove": [], "revoke": []}
    for patches in patch_instructions:
        result["packages"].update(patches["packages"])
        result["packages.conda"].update(patches.get("packages.conda", {}))
        result["remove"] += patches["remove"]
        result["revoke"] += patches["revoke"]
        result["patch_instructions_version"] = patches["patch_instructions_version"]
    result["remove"] = list(set(result["remove"]))
    result["revoke"] = list(set(result["revoke"]))
    return result


def merge_patch_instructions(patch_instructions):
    """
    Merges a list of path instructions.

    This asumes each entry in the path instructions list is dictionary with the following keys:
    packages, packages.conda, remove, revoke, patch_instructions_version.

    The reason for this is that we make patch files in each platform, which results in potentially
    different JSON files for the noarch directory, since it depends on the packages actually
    installed. We then gather all packages and need to merge the patches.
    """
    platforms = set([key for item in patch_instructions for key in item.keys()])
    patches = {
        platform: _merge_patch_instructions(
            [item[platform] for item in patch_instructions if platform in item]
        )
        for platform in platforms
    }
    return patches


def get_packages(packages=(), conda_list=None, output_dir=None):
    """
    Fetch packages from upstream repositories.

    Parameters
    ----------
    conda_list : list
        A list of dictionaries. Usually the output of `conda list --json`.
    output_dir : Path
        Directory where to put the packages (each platform in its own subdirectory).

    Returns
    -------
    list
        List of failures
    """
    fail = []
    base_dir = output_dir if output_dir is not None else Path()
    if conda_list is None:
        # get all installed packages
        p = subprocess.Popen(["conda", "list", "--json"], stdout=subprocess.PIPE)
        stdout, _ = p.communicate()
        conda_list = json.loads(stdout.decode())
    if packages:
        # only consider the ones requested
        tmp = []
        for pkg_string in packages:
            for pkg in conda_list:
                if match(pkg, pkg_string):
                    tmp.append(pkg)
                    break
            else:
                logger.warning(f"Package spec {pkg_string} not found")
        conda_list = tmp
    pprint.pprint(conda_list)
    tmpdir = Path()
    for pkg in tqdm.tqdm(conda_list):
        try:
            pkg["base_url"] = pkg["base_url"].replace(
                "cxc.cfa.harvard.edu/mta/ASPECT", "icxc.cfa.harvard.edu/aspect"
            )
            proc = subprocess.run(
                [
                    "wget",
                    f"{pkg['base_url']}/{pkg['platform']}/{pkg['dist_name']}.tar.bz2",
                ],
                capture_output=True,
            )
            if proc.returncode != 0:
                proc = subprocess.run(
                    [
                        "wget",
                        f"{pkg['base_url']}/{pkg['platform']}/{pkg['dist_name']}.conda",
                    ],
                    capture_output=True,
                )
            if proc.returncode != 0:
                fail.append(pkg)
            else:
                platform = base_dir / pkg["platform"]
                platform.mkdir(exist_ok=True, parents=True)
                output = list(tmpdir.glob(f"{pkg['dist_name']}*"))
                if output:
                    shutil.move(output[0], platform)
                else:
                    raise Exception(
                        f"Could not find downloaded file '{pkg['dist_name']}*' at {tmpdir}"
                    )
        except Exception as e:
            logger.warning(f"fail {pkg['dist_name']}: {e}")
            fail.append(pkg)
    return fail


@functools.cache
def _with_wget():
    return subprocess.run(["wget", "--help"], capture_output=True) == 0


def wget(url, destination):
    logger.debug(f"wget {url} -> {destination}")
    if _with_wget():
        filename = _wget(url)
    else:
        filename = _wget_alt(url)
    if filename:
        destination.mkdir(parents=True, exist_ok=True)
        shutil.move(filename, destination)
        return filename


def _wget(url):
    proc = subprocess.run(["wget", url], capture_output=True)
    if proc.returncode == 0:
        return Path(url).name


def _wget_alt(url, destination):
    """
    Wget alternative, in case wget is not present.
    """
    r = requests.get(url, stream=True)
    if r.status_code != 200:
        return

    url = Path(url)
    output_dir = Path(destination)
    output_dir.mkdir(parents=True, exist_ok=True)
    with open(output_dir / url.name, "wb") as fh:
        for chunk in r.iter_content(chunk_size=1024):
            if chunk:
                fh.write(chunk)
                fh.flush()
    return url.name


def _read_patch_files(path):
    patches = {}
    patch_files = path.glob("*/patch_instructions.json")
    for patch_file in patch_files:
        with open(patch_file) as fh:
            platform = patch_file.parent.name
            patches[platform] = json.load(fh)
    return patches


def load_patches(path):
    path = Path(path)
    if path.is_dir():
        return _read_patch_files(path)
    elif path.name[-8:] == ".tar.bz2":
        with tempfile.TemporaryDirectory() as tmpdir:
            with tarfile.open(path, "r:bz2") as zf:
                zf.extractall(tmpdir)
                return _read_patch_files(Path(tmpdir))
    else:
        raise Exception(
            f"Cannot read patch instructions: {path} (it must be a directory or a .tar.bz2 file)"
        )


def save_patches(patches, output_dir, if_exists=None, zip_patches=True):
    output_dir = Path(output_dir)

    # these are the files that will be overwritten by this function
    if not zip_patches:
        existing_patch_files = list(output_dir.glob("*/patch_instructions.json"))
    else:
        existing_patch_files = list(output_dir.glob("patch_instructions.tar.bz2"))

    existing_patches = {}
    if existing_patch_files:
        # check whether we want to merge or overwrite
        if if_exists == "overwrite":
            logger.debug(f"Removing existing patches in {output_dir.absolute()}")
        elif if_exists == "merge":
            logger.debug(f"Merging patches into {output_dir.absolute()}")
            existing_patches = load_patches(output_dir)
            patches = merge_patch_instructions([patches, existing_patches])
        else:
            msg = f"Patch instructions already exist at {output_dir.absolute()}: "
            msg += ", ".join([str(file) for file in existing_patch_files])
            raise Exception(msg)

    # merge if needed, and then save in a temporary directory
    with tempfile.TemporaryDirectory() as td:
        tempdir = Path(td)

        for platform in patches:
            # save in tmpdir
            (tempdir / platform).mkdir(parents=True, exist_ok=True)
            with open(tempdir / platform / "patch_instructions.json", "w") as fh:
                json.dump(patches[platform], fh, indent=2)

        output_dir.mkdir(parents=True, exist_ok=True)
        if zip_patches:
            with tarfile.open(output_dir / "patch_instructions.tar.bz2", "w:bz2") as zf:
                for file in tempdir.glob("*/*.json"):
                    zf.add(str(file), arcname=file.relative_to(tempdir))
        else:
            for file in existing_patch_files:
                logger.debug(f"rm {file}")
                os.unlink(file)
            for platform in patches:
                logger.debug(
                    f"mv {platform}/patch_instructions.json -> {output_dir / platform}"
                )
                (output_dir / platform).mkdir(parents=True, exist_ok=True)
                shutil.move(
                    tempdir / platform / "patch_instructions.json",
                    output_dir / platform / "patch_instructions.json",
                )


def get_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action", choices=["get", "merge-patches"], help="Action to perform."
    )
    parser.add_argument(
        "items",
        nargs="*",
        help=(
            "If action==merge-patches: a list of JSON files to merge. "
            "If action==get: spec strings listing packages. "
            "If not provided, all installed packages are fetched. "
            "Each spec string must be of the form <name>[==<version>]."
        ),
    )
    parser.add_argument(
        "--out",
        "-o",
        type=Path,
        default=Path("packages"),
        help="directory where to place packages and patch instructions.",
    )
    parser.add_argument("--conda-list", type=Path)
    parser.add_argument("--zip", action="store_true")
    parser.add_argument("--no-patches", dest="get_patches", action="store_false")
    parser.add_argument("--no-packages", dest="get_packages", action="store_false")
    parser.add_argument("--if-patches-exist", choices=["merge", "overwrite"])
    return parser


def main():
    parser = get_parser()
    args = parser.parse_args()

    for line in pprint.pformat(vars(args)).split("\n"):
        logger.info(line)

    conda_list = None
    if args.conda_list:
        if not args.conda_list.exists():
            parser.exit(status=1, message=f"{args.conda_list} does not exist")
        with open(args.conda_list) as fh:
            conda_list = json.load(fh)

    if args.action == "get":
        if args.get_patches:
            patches = get_patch_instructions(args.items, conda_list=conda_list)
            save_patches(
                patches, args.out, if_exists=args.if_patches_exist, zip_patches=args.zip
            )
        if args.get_packages:
            get_packages(args.items, conda_list=conda_list, output_dir=args.out)
    elif args.action == "merge-patches":
        items = [load_patches(item) for item in args.items]
        patches = merge_patch_instructions(items)
        save_patches(
            patches, args.out, if_exists=args.if_patches_exist, zip_patches=args.zip
        )


if __name__ == "__main__":
    main()
