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
import logging.config
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
import itertools
from pathlib import Path
from urllib.parse import urlparse, urlunparse


logger = logging.getLogger("skare3")


def get_conda_list(
    conda_lists=(), packages=(), subdirs=(), channels=(), override_channels=False
):
    conda_options = []
    for channel in channels:
        conda_options += ["-c", channel]
    if override_channels:
        conda_options += ["--override-channels"]

    if conda_lists:
        return _conda_list_from_files(conda_lists)
    elif packages:
        return _conda_list_from_search(
            packages, conda_options=conda_options, subdirs=subdirs
        )
    else:
        return _default_conda_list(" ".join(conda_options))


@functools.cache
def _default_conda_list(conda_options=None):
    # get list of all installed packages
    cmd = ["conda", "list", "--json"]
    if conda_options:
        cmd += conda_options.split()
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    stdout, _ = proc.communicate()
    return json.loads(stdout.decode())


def _conda_list_from_files(filenames):
    missing = []
    conda_list = []
    for filename in filenames:
        if not Path(filename).exists():
            missing.append(filename)
            continue
        with open(filename) as fh:
            conda_list += json.load(fh)
    if missing:
        raise Exception(f"Missing conda list files: {', '.join(missing)}")
    return conda_list


def _conda_list_from_search(packages, conda_options=None, subdirs=()):
    conda_list = []
    cmd = ["conda", "search", "--json"]
    if conda_options:
        cmd += conda_options

    if subdirs:
        cmds = [cmd + ["--subdir", subdir] for subdir in subdirs]
    else:
        cmds = [cmd]
    for pkg_spec, cmd in tqdm.tqdm(itertools.product(packages, cmds)):
        proc = subprocess.Popen(cmd + [pkg_spec], stdout=subprocess.PIPE)
        stdout, _ = proc.communicate()
        if proc.returncode == 0:
            result = json.loads(stdout.decode())
            if len(result) > 1:
                msg = f"Search for {pkg_spec} yields more than one package:"
                for name in result:
                    msg += f"\n  {name}"
                raise Exception(msg)
            result = list(result.values())[0]
            result = [pkg for pkg in result if match(pkg, pkg_spec)]
            if len(result) > 1:
                msg = f"Search for {pkg_spec} yields more than one package:"
                for pkg in result:
                    msg += f"\n  {pkg['name']}-{pkg['version']}-{pkg['build']} {pkg['channel']}"
                raise Exception(msg)
            if result:
                url = urlparse(result[0]["url"])
                url = url._replace(
                    path=url.path.replace(
                        f"/{result[0]['subdir']}/{result[0]['fn']}", ""
                    )
                )
                conda_list.append(
                    {
                        "name": result[0]["name"],
                        "version": result[0]["version"],
                        "build": result[0]["build"],
                        "platform": result[0]["subdir"],
                        "url": result[0]["url"],
                        "dist_name": f"{result[0]['name']}-{result[0]['version']}-{result[0]['build']}",
                        "base_url": urlunparse(url),
                    }
                )
    return conda_list


def match(package, spec_string):
    """
    Check if a package info matches a spec string.

    If present, the version must be an exact match.

    Parameters
    ----------
    package : dict
        Usually the output of `conda list --json`
    spec_string : str
        a string of the form <name>[=[=]<version>[=<build>]]

    Returns
    -------
    bool
    """
    if m := re.match(
        r"(?P<name>[-_a-zA-Z0-9]+)==?(?P<version>\S+)=(?P<build>\S+)", spec_string
    ):
        parts = m.groupdict()
        return (
            parts["name"] == package["name"]
            and parts["version"] == package["version"]
            and parts["build"] == package["build"]
        )
    elif m := re.match(r"(?P<name>[-_a-zA-Z0-9]+)==?(?P<version>\S+)", spec_string):
        parts = m.groupdict()
        return (
            parts["name"] == package["name"] and parts["version"] == package["version"]
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
        conda_list = get_conda_list()

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
                patches[pkg["platform"]]["patch_instructions_version"] = (
                    upstream_patches[url]["patch_instructions_version"]
                )
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
    logger.debug("Merging patch instructions")
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
        conda_list = get_conda_list()

    if packages:
        # only consider the ones requested
        tmp = []
        # a single pkg_string can match multiple entries in the list (from different platforms)
        for pkg in conda_list:
            for pkg_string in packages:
                if match(pkg, pkg_string):
                    tmp.append(pkg)
                    break
            else:
                logger.warning(f"Package spec {pkg_string} not found")
        conda_list = tmp

    tmpdir = Path()
    for pkg in tqdm.tqdm(conda_list):
        if list((base_dir / pkg["platform"]).glob(f"{pkg['dist_name']}*")):
            continue
        try:
            pkg["base_url"] = pkg["base_url"].replace(
                "cxc.cfa.harvard.edu/mta/ASPECT", "icxc.cfa.harvard.edu/aspect"
            )
            logger.debug(
                f"Trying {pkg['base_url']}/{pkg['platform']}/{pkg['dist_name']}.tar.bz2"
            )
            proc = subprocess.run(
                [
                    "wget",
                    f"{pkg['base_url']}/{pkg['platform']}/{pkg['dist_name']}.tar.bz2",
                ],
                capture_output=True,
            )
            if proc.returncode != 0:
                logger.debug(
                    f"Trying {pkg['base_url']}/{pkg['platform']}/{pkg['dist_name']}.conda"
                )
                proc = subprocess.run(
                    [
                        "wget",
                        f"{pkg['base_url']}/{pkg['platform']}/{pkg['dist_name']}.conda",
                    ],
                    capture_output=True,
                )
            if proc.returncode != 0:
                logger.debug(f"Failed {pkg['dist_name']}")
                fail.append(pkg)
            else:
                platform = base_dir / pkg["platform"]
                platform.mkdir(exist_ok=True, parents=True)
                output = list(tmpdir.glob(f"{pkg['dist_name']}*"))
                if output:
                    logger.debug(f"Moving {output[0]} -> {platform}")
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


def load_patches(path):
    """
    Load patch instructions from a directory or compressed file.

    If the path is a directory, the function will check whether there is a compressed file in the
    directory. If there is a compressed file and also JSON files, then it will issue a warning,
    since this should normally not happen, and it will read from the JSON files.
    """
    path = Path(path)
    if path.is_dir():
        json_files = list(path.glob("*/patch_instructions.json"))
        zip_file = path / "patch_instructions.tar.bz2"
        if json_files and zip_file.exists():
            logger.warning(
                f"Directory {path} has both json and zipped patch files. Loading from JSON files."
            )
        if zip_file.exists() and not json_files:
            return _read_zipped_patch_files(zip_file)
        else:
            return _read_patch_files(path)

    elif path.name[-8:] == ".tar.bz2":
        return _read_zipped_patch_files(path)
    else:
        raise Exception(
            f"Cannot read patch instructions: {path} (it must be a directory or a .tar.bz2 file)"
        )


def _read_patch_files(path):
    logger.debug(f"Loading patches from JSON files at {path}")
    patches = {}
    patch_files = path.glob("*/patch_instructions.json")
    for patch_file in patch_files:
        with open(patch_file) as fh:
            platform = patch_file.parent.name
            patches[platform] = json.load(fh)
    return patches


def _read_zipped_patch_files(filename):
    logger.debug(f"Loading patches from {filename}")
    with tempfile.TemporaryDirectory() as tmpdir:
        with tarfile.open(filename, "r:bz2") as zf:
            zf.extractall(tmpdir)
            return _read_patch_files(Path(tmpdir))


def save_patches(patches, output_dir, if_exists=None, zip_patches=True):
    """
    Save patch instructions in a directory.

    Parameters
    ----------
    patches : dict
        The patch instructions
    output_dir : Path
        Directory where to put the patches.
    if_exists : str (optional)
        One of:
        - 'overwrite'. Discard any patches that might be in the output directory.
        - 'merge'. Merge these patches with the existing ones.
        - anything else will cause an exception of there are patches in the output directory
    zip_patches : bool
        Whether to store in a compressed file (True) or in JSON files (False).
    """
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

    logger.debug(f"Saving patches in {output_dir}")
    # save in a temporary directory
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


def configure_logging():
    logging.config.dictConfig(
        {
            "version": 1,
            "formatters": {
                "default": {"format": "%(levelname)-8s %(message)s"}  # noqa
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "default",
                    "level": "DEBUG",
                },
            },
            "loggers": {
                "skare3": {
                    "level": "INFO",
                    "handlers": ["console"],
                    "propagate": False,
                },
            },
            "root": {"level": "WARNING", "handlers": ["console"]},
        }
    )


def get_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "items",
        nargs="*",
        help=(
            "If --merge-patches is given, this should be a list of JSON files to merge. "
            "If --merge-patches is given, this is a list of spec strings listing packages. "
            "Each spec string must be of the form <name>[==<version>]."
            "If the list is empty, all installed packages are fetched. "
        ),
    )
    parser.add_argument(
        "--out",
        "-o",
        type=Path,
        default=Path("packages"),
        help="directory where to place packages and patch instructions.",
    )
    parser.add_argument(
        "--conda-list",
        type=Path,
        action="append",
        default=[],
        help="File(s) with the output of `conda list --json`, one for each environment.",
    )
    parser.add_argument("--zip", action="store_true", default=True, help="Zip patches")
    parser.add_argument(
        "--no-zip", action="store_false", dest="zip", help="Do not zip patches"
    )
    parser.add_argument(
        "--no-patches",
        dest="get_patches",
        action="store_false",
        help="Do not get patches",
    )
    parser.add_argument(
        "--no-packages",
        dest="get_packages",
        action="store_false",
        help="Do not get packages",
    )
    parser.add_argument(
        "--merge-patches",
        action="store_true",
        dest="merge_patches",
        help="Do not get anything, just merge the given patch instructions.",
    )
    parser.add_argument(
        "--if-patches-exist",
        default="merge",
        choices=["merge", "overwrite"],
        help="What to do if patch instructions already exist",
    )
    parser.add_argument(
        "--log-level", default="INFO", choices=["debug", "info", "warning"]
    )
    parser.add_argument(
        "--channel", "-c", help="Conda channel", action="append", default=[]
    )
    parser.add_argument(
        "--subdir",
        help="Conda subdir (noarch, linux-64, etc)",
        action="append",
        default=[],
    )
    parser.add_argument(
        "--override-channels",
        action="store_true",
        default=False,
        help="Override default conda channels",
    )
    return parser


def main():
    configure_logging()

    parser = get_parser()
    args = parser.parse_args()

    logger.setLevel(args.log_level.upper())

    for line in pprint.pformat(vars(args)).split("\n"):
        logger.info(line)

    if args.merge_patches:
        items = [load_patches(item) for item in args.items]
        patches = merge_patch_instructions(items)
        save_patches(
            patches, args.out, if_exists=args.if_patches_exist, zip_patches=args.zip
        )
    else:
        conda_list = get_conda_list(
            packages=args.items,
            conda_lists=args.conda_list,
            channels=args.channel,
            override_channels=args.override_channels,
            subdirs=args.subdir,
        )

        if args.get_patches:
            patches = get_patch_instructions(args.items, conda_list=conda_list)
            save_patches(
                patches, args.out, if_exists=args.if_patches_exist, zip_patches=args.zip
            )
        if args.get_packages:
            get_packages(args.items, conda_list=conda_list, output_dir=args.out)


if __name__ == "__main__":
    main()
