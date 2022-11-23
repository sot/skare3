#!/usr/bin/env python

import os
import subprocess
import pathlib
import logging
import yaml


assert "CONDA_PASSWORD" in os.environ, "CONDA_PASSWORD environmental variable is not defined"

CHANNELS = [
    'conda-forge',
    'defaults',
    f'https://ska:{os.environ["CONDA_PASSWORD"]}@cxc.cfa.harvard.edu/mta/ASPECT/ska3-conda/flight'
]


# These options are passed to conda_build.metadata.select_lines after reading meta.yaml.
# This causes, for example, the lines that read " # [win]" to be read only on win-64.
PLATFORM_OPTIONS = {
    'linux-64': {'linux': True, 'linux64': True},
    'osx-64': {'osx': True, 'osx64': True},
    'win-64': {'win': True, 'win64': True}
}


def install_pkgs(pkgs):
    from conda_build.config import Config
    config = Config()
    if config.platform not in pkgs['platforms']:
        return

    channels = sum([['-c', c] for c in pkgs['channels']], [])
    cmd = ['mamba', 'install', '-y'] + pkgs['options'] + channels + pkgs['packages']
    logging.info(' '.join(cmd))
    subprocess.run(cmd, check=True)


def install_yaml_requirements(meta_yaml):
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
        'platforms': [config.platform],
        'packages': dependencies,
    })


def main():
    logging.basicConfig(level="INFO")

    srcdir = pathlib.Path(__file__).parent

    # note that base_environment is not updated here, because that updates python itself
    # and should be updated before calling this script
    for env in sorted(srcdir.glob('environment*.yml')):
        subprocess.run(['mamba', 'env', 'update', '-f', env], check=True)

    install_yaml_requirements(srcdir / 'meta.yaml')


if __name__ == '__main__':
    main()
