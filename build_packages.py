#!/usr/bin/env python

import os
import argparse
import git
import subprocess

build_list = "build_order.txt"

if os.uname().sysname == "Darwin":
    os.environ["MACOSX_DEPLOYMENT_TARGET"] = "10.9"

class SkaBuilder(object):

    def __init__(self, ska_root=None):
        if ska_root is None:
            ska_root = "/data/acis/ska3_pkg/"
        self.ska_root = ska_root
        self.ska_build_dir = os.path.join(self.ska_root, "builds")
        self.ska_src_dir = os.path.join(self.ska_root, "src")
        os.environ["SKA_TOP_SRC_DIR"] = self.ska_src_dir

    def build_one_package(self, name):

        print("Building package %s." % name)

        cmd_list = ["conda", "build", name, "--croot",
                    self.ska_build_dir,
                    "--no-anaconda-upload"]

        subprocess.run(cmd_list)

    def build_all_packages(self):
        with open(build_list, "r") as f:
            for line in f.readlines():
                pkg_name = line.strip()
                if not pkg_name.startswith("#"):
                    self.build_one_package(pkg_name)


    def build_updated_packages(self):
        pass

parser = argparse.ArgumentParser(description="Build Ska Conda packages.")

parser.add_argument("mode", type=str, help="The build mode. Either 'all' for all "
                                           "packages, 'updated' for updated "
                                           "packages, or a specific package name.")
parser.add_argument("--ska_root", type=str, 
                    help="The path to the root directory for the Ska packages. "
                         "Default: /data/acis/ska3_pkg")

args = parser.parse_args()

ska_builder = SkaBuilder(ska_root=args.ska_root)

if args.mode == "all":
    ska_builder.build_all_packages()
elif args.mode == "updated":
    ska_builder.build_updated_packages()
else:
    ska_builder.build_one_package(args.mode)
