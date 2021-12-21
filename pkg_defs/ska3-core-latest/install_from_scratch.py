#!/usr/bin/env python

import os
import subprocess
import pathlib
import logging

assert "CONDA_PASSWORD" in os.environ, "CONDA_PASSWORD environmental variable is not defined"

CHANNELS = [
    'defaults',
    'conda-forge',
    f'https://ska:{os.environ["CONDA_PASSWORD"]}@cxc.cfa.harvard.edu/mta/ASPECT/ska3-conda/flight'
]


# This is a list of packages to be installed before installing whatever is in meta.yaml
PACKAGES = [
    {
        'channels': CHANNELS,
        'options': [],
        'packages': ['numpy', 'matplotlib', 'scipy', 'pandas', 'astropy', 'pyyaml', 'conda-build']
    },
    {  # these come from conda-forge
        'channels': CHANNELS,
        'options': ['--no-channel-priority'],
        'packages': ['qt', 'pyqt']
    },
    {  # this version is set so it is not the latest
        'channels': CHANNELS,
        'options': [],
        'packages': ['django==3.1.7']
    },
]


# These options are passed to conda_build.metadata.select_lines after reading meta.yaml.
# This causes, for example, the lines that read " # [win]" to be read only on win-64.
PLATFORM_OPTIONS = {
    'linux-64': {'linux': True, 'linux64': True},
    'osx-64': {'osx': True, 'osx64': True},
    'win-64': {'win': True, 'win64': True}
}


def install_pkgs(pkgs):
    channels = sum([['-c', c] for c in pkgs['channels']], [])
    cmd = ['mamba', 'install', '-y'] + pkgs['options'] + channels + pkgs['packages']
    logging.info(' '.join(cmd))
    subprocess.run(cmd)


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
        [data['requirements'][k] for k in ['build', 'run'] if k in data['requirements']],
        []
    )
    install_pkgs({
        'channels': CHANNELS,
        'options': [],
        'packages': dependencies,
    })


def main():
    logging.basicConfig(level="INFO")

    for pkgs in PACKAGES:
        install_pkgs(pkgs)

    meta_yaml = pathlib.Path(__file__).parent / 'meta.yaml'
    install_yaml_requirements(meta_yaml)


if __name__ == '__main__':
    main()
