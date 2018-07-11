import os
import subprocess
import git
import yaml

ska_conda_path = os.path.abspath(os.path.dirname(__file__))
pkg_defs_path = os.path.join(ska_conda_path, "pkg_defs")
build_list = os.path.join(ska_conda_path, "build_order.txt")
no_source_pkgs = ['ska3-flight', 'ska3-core', 'ska3-dev', 'ska3-pinned', 'ska3-template']

class SkaBuilder(object):

    def __init__(self, build_root='.', user='sot', git_repo_path='git@github.com:{user}/{name}.git'):
        self.user = user
        self.git_repo_path = git_repo_path
        self.build_dir = os.path.abspath(os.path.join(build_root, "builds"))
        self.src_dir = os.path.abspath(os.path.join(build_root, "src"))
        os.environ["SKA_TOP_SRC_DIR"] = self.src_dir

    def _clone_repo(self, name, tag=None):
        if name in no_source_pkgs:
            return
        print("Cloning source %s." % name)
        clone_path = os.path.join(self.src_dir, name)
        if not os.path.exists(clone_path):
            # Try ssh first to avoid needing passwords for the private repos
            # We could add these ssh strings to the meta.yaml for convenience
            # The default ssh is not going to work if the package name doesn't match the
            # top-level git repo name (cmd_states, eng_archive)
            try:
                repo = git.Repo.clone_from(self.git_repo_path.format(user=self.user, name=name), clone_path)
                assert not repo.bare
                print("Clonied via default ssh git")
            except:
                yml = os.path.join(pkg_defs_path, name, "meta.yaml")
                with open(yml) as f:
                    requires = False
                    while not requires:
                        line = f.readline().strip()
                        if line.startswith("path:"):
                            requires = True
                    data = yaml.load(f)
                    url = data['about']['home']
                repo = git.Repo.clone_from(url, clone_path)
                print("Cloned from url {}".format(url))
        else:
            repo = git.Repo(clone_path)
            repo.remotes.origin.fetch()
            repo.remotes.origin.fetch("--tags")
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
                    self.build_dir, "--no-test",
                    "--no-anaconda-upload", "--skip-existing"]
        subprocess.run(cmd_list, check=True)

    def build_one_package(self, name, tag=None):
        repo = self._get_repo(name, tag)
        self._build_package(name)

    def build_list_packages(self):
        with open(build_list, "r") as f:
            for line in f.readlines():
                pkg_name = line.strip()
                if not pkg_name.startswith("#"):
                    self.build_one_package(pkg_name)

    def build_all_packages(self):
        self.build_list_packages()
