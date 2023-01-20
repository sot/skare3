#!/usr/bin/env python

"""
Install a meta-project "from scratch" by first installing any environment file in its directory
and then installing the dependencies listed in its build recipe.
"""

import sys
import subprocess
import pathlib
import logging
import argparse


class SkaException(Exception):
    pass


def get_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "srcdir",
        help="The package name or directory where to find the build recipe",
        type=pathlib.Path
    )
    parser.add_argument(
        "-c",
        "--channel",
        action="append",
        help="The conda channel(s) to use when installing the dependencies.",
        default=[]
    )
    return parser


def main():
    args = get_parser().parse_args()

    logging.basicConfig(level="INFO")

    if args.srcdir.exists():
        srcdir = args.srcdir
    else:
        srcdir = pathlib.Path(__file__).parent / "pkg_defs" / args.srcdir

    if not srcdir.exists():
        raise SkaException(f"Neither directory exists: {args.srcdir}, {srcdir}")

    try:
        p = subprocess.run("mamba", capture_output=True)
        assert p.returncode == 0
        executable = "mamba"
    except Exception:
        executable = "conda"

    for env in sorted(srcdir.glob("*environment*.yml")):
        logging.info(f"Updating environment using {env}")
        subprocess.run([executable, "env", "update", "-f", env], check=True)

    cmd = [
        str(pathlib.Path(__file__).parent.absolute() / "install_yaml_requirements.py"),
        str(srcdir / "meta.yaml"),
    ]
    for ch in args.channel:
        cmd += ["-c", ch]
    logging.info(" ".join(cmd))
    subprocess.run(cmd, check=True)


if __name__ == "__main__":
    try:
        main()
    except SkaException as e:
        logging.fatal(f"Error: {e}")
        sys.exit(1)
