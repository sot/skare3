import os
import subprocess
import git
import re
import os
import argparse

from ska_conda import SkaBuilder

if os.uname().sysname == "Darwin":
    os.environ["MACOSX_DEPLOYMENT_TARGET"] = "10.9"

parser = argparse.ArgumentParser(description="Build Ska Conda packages.")

parser.add_argument("package", type=str, nargs="?",
                    help="Package to build.  All updated packages will be built if no package supplied")
parser.add_argument("--tag", type=str,
                    help="Optional tag, branch, or commit to build for single package build (default is tag with most recent commit)")
parser.add_argument("--build-root", default=".", type=str,
                    help="Path to root directory for output conda build packages."
                         "Default: '.'")

args = parser.parse_args()

ska_builder = SkaBuilder(build_root=args.build_root)

if getattr(args, 'package'):
    ska_builder.build_one_package(args.package, tag=args.tag)
else:
    if args.tag is not None:
        raise ValueError("Cannot supply '--tag' without specific package'")
    ska_builder.build_all_packages()



ska_conda_path = os.path.abspath(os.path.dirname(__file__))
pkg_defs_path = os.path.join(ska_conda_path, "pkg_defs")
build_list = os.path.join(ska_conda_path, "build_order.txt")
no_source_pkgs = ['ska3-flight', 'ska3-core', 'ska3-dev', 'ska3-pinned', 'ska3-template',
                  'pytest-arraydiff', 'pytest-doctestplus', 'pytest-openfiles', 'pytest-remotedata',
                  'pytest-astropy', 'astropy',
                  'ipywidgets', 'widgetsnbextension']

class SkaBuilder(object):

    def __init__(self, build_root='.'):
        self.build_dir = os.path.abspath(os.path.join(build_root, "builds"))
        self.src_dir = os.path.abspath(os.path.join(build_root, "src"))
        os.environ["SKA_TOP_SRC_DIR"] = self.src_dir

    def _clone_repo(self, name, tag=None):
        if name in no_source_pkgs:
            return
        print("Cloning or updating source source %s." % name)
        clone_path = os.path.join(self.src_dir, name)
        if not os.path.exists(clone_path):
            metayml = os.path.join(pkg_defs_path, name, "meta.yaml")
            # It isn't clean yaml at this point, so just extract the string we want after "home:"
            meta = open(metayml).read()
            url = re.search("home:\s*(\S+)", meta).group(1)
            repo = git.Repo.clone_from(url, clone_path)
            print("Cloned from url {}".format(url))
        else:
            repo = git.Repo(clone_path)
            repo.remotes.origin.fetch()
            repo.remotes.origin.fetch("--tags")
            print("Updated repo in {}".format(clone_path))
        assert not repo.is_dirty()
        # I think we want the commit/tag with the most recent date, though
        # if we actually want the most recently created tag, that would probably be
        # tags = sorted(repo.tags, key=lambda t: t.tag.tagged_date)
        # I suppose we could also use github to get the most recent release (not tag)
        if tag is None:
            tags = sorted(repo.tags, key=lambda t: t.commit.committed_datetime)
            repo.git.checkout(tags[-1].name)
            if tags[-1].commit == repo.heads.master.commit:
                print("Auto-checked out at {} which is also tip of master".format(tags[-1].name))
            else:
                print("Auto-checked out at {} NOT AT tip of master".format(tags[-1].name))
        else:
            repo.git.checkout(tag)
            print("Checked out at {}".format(tag))


    def _get_repo(self, name, tag):
        if name in no_source_pkgs:
            return None
        repo_path = os.path.join(self.src_dir, name)
        self._clone_repo(name, tag)
        repo = git.Repo(repo_path)
        return repo

    def _build_package(self, name):
        print("Building package %s." % name)
        pkg_path = os.path.join(pkg_defs_path, name)
        cmd_list = ["conda", "build", pkg_path, "--croot",
                    self.build_dir, "--no-test", "--old-build-string",
                    "--no-anaconda-upload", "--skip-existing"]
        subprocess.run(cmd_list, check=True)

    def build_one_package(self, name, tag=None):
        repo = self._get_repo(name, tag)
        self._build_package(name)

    def build_list_packages(self):
        failures = []
        with open(build_list, "r") as f:
            for line in f.readlines():
                pkg_name = line.strip()
                if not pkg_name.startswith("#"):
                    try:
                        self.build_one_package(pkg_name)
                    # If there's a failure, confirm before continuing
                    except:
                        print(f'{pkg_name} failed, continue anyway (y/n)?')
                        if input().lower().strip().startswith('y'):
                            failures.append(pkg_name)
                            continue
                        else:
                            raise ValueError(f"{pkg_name} failed")
        if len(failures):
            raise ValueError("Packages {} failed".format(",".join(failures)))


    def build_all_packages(self):
        self.build_list_packages()
