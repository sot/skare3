#!/usr/bin/env python

import os
import subprocess
import pathlib
import logging

assert (
    "CONDA_PASSWORD" in os.environ
), "CONDA_PASSWORD environmental variable is not defined"

CHANNELS = []


def get_package_list():
    """Packages to be installed before installing whatever is in meta.yaml
    """
    return [
        {
            # conda-build first so on windows it installs
            # m2-conda-epoch==20230914 and not msys2-conda-epoch (#1156)
            "channels": CHANNELS,
            "options": [],
            "packages": ["conda-build"],
        },
        {
            "channels": CHANNELS,
            "options": [],
            "packages": [
                "numpy",
                "matplotlib",
                "scipy",
                "pandas",
                "astropy",
                "pyyaml",
                "pyqt",
            ],
        },
        {  # 0.60 is incompatible with VS code debugger
            "channels": CHANNELS,
            "options": [],
            "packages": ["numba==0.59.1"],
        },
        {  # this version is set so it is not the latest
            "channels": CHANNELS,
            "options": [],
            "packages": ["django==3.1.7"],
        },
        # {  # later versions cause a conflict with nb_conda
        #     "channels": CHANNELS,
        #     "options": [],
        #     "packages": ["notebook==6.5.6"],
        # },
        {  # this is not in defaults or conda-forge (for now?)
            "channels": ["https://cxc.cfa.harvard.edu/conda/sherpa"] + CHANNELS,
            "options": [],
            "packages": ["sherpa"],
            "platform": ["linux-64", "osx-64", "osx-arm64"],
        },
    ]


# These options are passed to conda_build.metadata.select_lines after reading meta.yaml.
# This causes, for example, the lines that read " # [win]" to be read only on win-64.
PLATFORM_OPTIONS = {
    "linux-64": {"linux": True, "linux64": True, "arm64":   False},
    "osx-64": {"osx": True, "osx64": True, "arm64": False},
    "osx-arm64": {"osx": True, "osx64": True, "arm64":  True},
    "win-64": {"win": True, "win64": True, "arm64": False},
}


def install_pkgs(pkgs):
    # conda-build is imported here because it is not installed initially
    # (it is installed by this script)
    try:
        from conda_build.config import Config
        config = Config()
        if "platform" in pkgs and config.target_subdir not in pkgs["platform"]:
            return
    except ImportError:
        pass
    channels = sum([["-c", c] for c in pkgs["channels"]], [])
    if channels:
        channels = ["--override-channels"] + channels
    cmd = (
        ["mamba", "install", "-y"]
        + pkgs["options"]
        + channels
        + pkgs["packages"]
    )
    logging.info(" ".join(cmd))
    proc = subprocess.run(cmd)
    if proc.returncode != 0:
        raise RuntimeError(f"Error installing {pkgs['packages']}")


def install_yaml_requirements(meta_yaml):
    # imported here because they might not be present by default
    import yaml
    from conda_build.config import Config
    from conda_build.metadata import select_lines

    with open(meta_yaml) as fh:
        meta = fh.read()

    config = Config()
    data = select_lines(meta, PLATFORM_OPTIONS[config.target_subdir], {})
    data = yaml.load(data, Loader=yaml.BaseLoader)

    dependencies = sum(
        [
            data["requirements"][k]
            for k in ["build", "run"]
            if k in data["requirements"]
        ],
        [],
    )
    install_pkgs(
        {
            "channels": CHANNELS,
            "options": [],
            "packages": dependencies,
        }
    )


def get_parser():
    import argparse

    parser = argparse.ArgumentParser(
        description="Install core packages from ska3-core-latest/meta.yaml"
    )
    parser.add_argument(
        "--ska-channel", action="append", default=[], help="Ska channels to use"
    )
    parser.add_argument(
        "--conda-channel", action="append", default=[], help="Conda channels to use"
    )
    return parser


def main():
    logging.basicConfig(level="INFO")

    args = get_parser().parse_args()

    if not args.conda_channel:
        args.conda_channel.append("conda-forge")

    for channel in args.conda_channel:
        CHANNELS.append(channel)
    for channel in args.ska_channel:
        CHANNELS.append(
            f'https://ska:{os.environ["CONDA_PASSWORD"]}'
            f"@cxc.cfa.harvard.edu/mta/ASPECT/ska3-conda/{channel}"
        )

    try:
        for pkgs in get_package_list():
            install_pkgs(pkgs)

        meta_yaml = pathlib.Path(__file__).parent / "meta.yaml"
        install_yaml_requirements(meta_yaml)
    except Exception as e:
        logging.error(f"Error: {e}")


if __name__ == "__main__":
    main()
