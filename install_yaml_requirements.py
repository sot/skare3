#!/usr/bin/env python

"""
Install the RUN requirements in the given conda build recipe YAML file. All packages are downloaded
from the conda channels given. If not conda channel is given, then conda-forge is used.
Valid conda channel names include any conda channel in ska3-conda on CXC (e.g. flight, test).
"""

import os
import sys
import subprocess
import requests
import pathlib
import logging
import argparse
import urllib.parse


class SkaException(Exception):
    pass


DEFAULT_CHANNELS = [
    "conda-forge",
]


def get_channels(args):
    if "CONDA_PASSWORD" not in os.environ:
        raise SkaException("CONDA_PASSWORD environmental variable is not defined")
    channels = args.channel
    if not channels:
        channels = DEFAULT_CHANNELS

    ska3_conda = \
        f"https://ska:{os.environ['CONDA_PASSWORD']}@cxc.cfa.harvard.edu/mta/ASPECT/ska3-conda"
    url = urllib.parse.urlparse(ska3_conda)
    session = requests.Session()
    session.auth = (url.username, url.password)
    auth = session.post(f"{url.scheme}://{url.hostname}")
    if auth.status_code != 200:
        raise SkaException("Cannot authenticate with Ska conda server")

    for i, channel in enumerate(channels):
        req = session.get(f"{url.scheme}://{url.hostname}{url.path}/{channel}/index.html")
        if req.status_code == 200:
            channels[i] = f"{ska3_conda}/{channel}"
            logging.info(f'{channel} -> {channels[i]}')

    return channels


def insure_installed(module, package=None):
    import importlib

    if package is None:
        package = module

    try:
        importlib.import_module(module)
    except ModuleNotFoundError:
        logging.info(f"Installing {package}")
        try:
            subprocess.run(["conda", "install", "-y", package])
        except FileNotFoundError:
            raise SkaException("Conda is not installed") from None


# These options are passed to conda_build.metadata.select_lines after reading meta.yaml.
# This causes, for example, the lines that read " # [win]" to be read only on win-64.
PLATFORM_OPTIONS = {
    "linux-64": {"linux": True, "linux64": True},
    "osx-64": {"osx": True, "osx64": True},
    "win-64": {"win": True, "win64": True},
}


def install_pkgs(pkgs):
    from conda_build.config import Config

    config = Config()
    if config.platform not in pkgs["platforms"]:
        return

    channels = sum([["-c", c] for c in pkgs["channels"]], [])
    if channels:
        channels = ["--override-channels"] + channels

    try:
        p = subprocess.run("mamba", capture_output=True)
        assert p.returncode == 0
        executable = "mamba"
    except Exception:
        executable = "conda"

    cmd = [executable, "install", "-y"] + pkgs["options"] + channels + pkgs["packages"]
    logging.info(" ".join(cmd))
    subprocess.run(cmd, check=True)


def install_yaml_requirements(meta_yaml, channels):
    import yaml
    from conda_build.config import Config
    from conda_build.metadata import select_lines

    with open(meta_yaml) as fh:
        meta = fh.read()

    config = Config()
    data = select_lines(meta, PLATFORM_OPTIONS[config.target_subdir], {})
    data = yaml.load(data, Loader=yaml.BaseLoader)

    dependencies = data["requirements"].get("run", [])
    install_pkgs(
        {
            "channels": channels,
            "options": [],
            "platforms": [config.platform],
            "packages": dependencies,
        }
    )


def get_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("yaml_file", type=pathlib.Path)
    parser.add_argument("-c", "--channel", action="append", default=[])
    return parser


def main():
    args = get_parser().parse_args()

    logging.basicConfig(level="INFO")

    channels = get_channels(args)
    # insure_installed("yaml", "pyyaml")
    install_yaml_requirements(args.yaml_file, channels=channels)


if __name__ == "__main__":
    try:
        main()
    except SkaException as e:
        logging.fatal(f"Error: {e}")
        sys.exit(1)
