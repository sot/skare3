#!/usr/bin/python

import re
import os
import sys
import stat
import tarfile as Tarfile
from glob import glob
import shutil
from copy import deepcopy

import pexpect
import yaml
import ska_version

try:
    set()
except NameError:
    from sets import Set as set

VERSION = '$Id: install.py 366 2008-12-09 15:40:03Z aldcroft $'


def get_options():
    """Get options.
    Output: (opt, args)"""
    from optparse import OptionParser
    parser = OptionParser()
    parser.set_defaults()

    parser.add_option("--prefix",
                      default="/proj/sot/ska/dev",
                      help="Installation prefix",
                      )
    parser.add_option("--arch",
                      default="arch",
                      help="Prefix directory for arch-specific directories",
                      )
    parser.add_option("--build",
                      help="Root build directory",
                      )
    parser.add_option("--pkgs",
                      default="/proj/sot/ska/pkgs",
                      help="Packages directory",
                      )
    parser.add_option("--manifest",
                      default="pkgs.manifest",
                      help="Packages manifest",
                      )
    parser.add_option("--config",
                      default=['env_vars'],
                      action="append",
                      help=("Installation config with optional module name "
                            "<config>:<module_name>"),
                      )
    parser.add_option("--confirm",
                      action="store_true",
                      help="Confirm before installing any package"
                      )
    parser.add_option("--python",
                      default='/usr/bin/python',
                      help="Python used for building virtual python",
                      )
    parser.add_option("--perl",
                      default="/usr/bin/perl",
                      help="Perl used for building modules",
                      )
    parser.add_option("--verbose",
                      action="store_true",
                      help="Verbose output",
                      )
    parser.add_option("--no-env-vars",
                      action="store_true",
                      help="Do not do default env var setup prior to processing",
                      )
    parser.add_option("--allow-errors",
                      action="store_true",
                      help="Allow build/test errors and automatically continue",
                      )
    parser.add_option("--installing-anaconda",
                      action="store_true",
                      help="If installing anaconda do not touch prefix_arch files",
                      )

    return parser.parse_args()

try:
    from string import Template
    class MyTemplate(Template):
        pattern = r"""%(delim)s(?:           # ?: is non-capturing group
                  (?P<escaped>$^) |          # Escape sequence that cannot happen
                  (?P<named>%(id)s)      |   # delimiter and a Python identifier
                  {(?P<braced>%(id)s)}   |   # delimiter and a braced identifier
                  (?P<invalid>)              # Other ill-formed delimiter exprs
                  )
                  """ % {'delim' : re.escape('$'),
                         'id'    : r'[_a-z][_a-z0-9]*' }
except ImportError:
    pass

def fix_paths(envs):
    """For the specified env vars that represent a search path, make sure that the
    paths are unique.  This allows the environment setting script to be lazy
    and not worry about it.  This routine gives the right-most path precedence."""

    # Process env vars that are contained in the PATH_ENVS set
    for key in set(envs.keys()) & set(('PATH', 'PERLLIB', 'PERL5LIB', 'PYTHONPATH',
                                       'LD_LIBRARY_PATH', 'MANPATH', 'INFOPATH')):
        path_ins = envs[key].split(':')
        pathset = set()
        path_outs = []
        # Working from right to left add each path that hasn't been included yet.
        for path in reversed(path_ins):
            if path not in pathset:
                pathset.add(path)
                path_outs.append(path)
        envs[key] = ':'.join(reversed(path_outs))

def parse_keyvals(keyvalstr):
    """Parse the key=val pairs from the newline-separated string.  Return dict of key=val pairs."""
    re_keyval = re.compile(r'([\w_]+) \s* = \s* (.*)', re.VERBOSE)
    keyvals = keyvalstr.splitlines()
    keyvalout = {}
    for keyval in keyvals:
        m = re.search(re_keyval, keyval.strip())
        if m:
            key, val = m.groups()
            keyvalout[key] = val
    return keyvalout

def sendline_expect_func(prompt):
    """Returns a convenience method to monkey-patch into pexpect.spawn.""" 
    def sendline_expect(self, cmd, quiet=False):
        """Send a command and expect the given prompt.  Return the 'before' part"""
        if quiet:
            logfile_read = self.logfile_read
            self.logfile_read = None

        self.sendline(cmd)
        self.expect(prompt)

        if prompt.search(cmd):
            self.expect(prompt)
        if quiet:
            self.logfile_read = logfile_read

        return os.linesep.join(self.before.splitlines()[1:])

    return sendline_expect

def bash(cmdstr, logfile=sys.stdout, keep_env=None):
    """Run the command string cmdstr in a bash shell.  It can have multiple
    lines.  Each line is separately sent to the shell.  The exit status is
    checked if the shell comes back with a PS1 prompt. Bash control structures
    like if or for use prompt PS2 and in this case status is not checked.  At
    the end the 'printenv' command is issued in order to find any changes to
    the environment that occurred as a result of the commands.  If exit status
    is non-zero at any point then processing is terminated and the bad exit
    status value is returned.

    Input: command string
    Output: exit status"""

    if opt.verbose:
        print '\nRunning command(s):'
        print MyTemplate(cmdstr).safe_substitute(dict(os.environ)), '\n'

    os.environ['PS1'] = PROMPT1
    os.environ['PS2'] = PROMPT2
    shell = pexpect.spawn('/bin/bash --noprofile --norc --noediting', timeout=1e8)
    shell.delaybeforesend = 0.01
    shell.logfile_read=logfile
    shell.expect(r'.+')

    for line in cmdstr.splitlines():
        shell.sendline_expect(line)
        if re_PROMPT.match(shell.after).group(1) == '>':
            try:
                exitstr = shell.sendline_expect('echo $?', quiet=True).strip()
                exitstatus = int(exitstr)
            except ValueError:
                print "\n\n Shell / expect got out of sync:"
                print " Response to 'echo $?' was apparently '%s'\n\n" % exitstr
                raise
                
            if exitstatus > 0:
                print
                return exitstatus

    # Update os.environ based on changes to environment made by cmdstr
    if keep_env:
        currenv = dict(os.environ)
        newenv = parse_keyvals(shell.sendline_expect("printenv", quiet=True))
        fix_paths(newenv)
        for key in newenv.keys():
            if key not in currenv or currenv[key] != newenv[key]:
                print 'Updating os.environ[%s] = "%s"' % (key, newenv[key])
                os.environ[key] = newenv[key]

    shell.close()
    print
    return 0

class Module(object):
    installcfgs = {}
    
    def __init__(self, modcfg, installcfg):
        # First set attributes from installcfg
        for key, val in installcfg.items():
            if key != 'modules':
                setattr(self, key, deepcopy(val))
        # Then override attr from modcfg
        for key, val in modcfg.items():
            try:
                getattr(self, key).update(val)
            except (TypeError, AttributeError):
                setattr(self, key, deepcopy(val))

        # Finally for the cmds do any expansions
        for key, val in self.cmds.items():
            if val.startswith('^'):
                self.cmds[key] = Module.installcfgs[val[1:].strip()]['cmds'][key]

    def __getattr__(self, attr):
        "Return None for any non-existent attributes"
        return None

    def run_cmds(self, cmdtyp):
        """Run the cmdtyp cmds.  If a module directory is defined then chdir there first."""
        if cmdtyp not in self.cmds:
            return True
        cmds = 'export LD_RUN_PATH\n' + self.cmds[cmdtyp]
        if self.moduledir:
            cmds = 'cd %s\n' % self.moduledir + cmds
        return 0 == bash(cmds, keep_env=self.keep_env)

    def untar(self, build_dir, pkg_dir, pkgs_manifest, extract=True):
        """Get the module tar file from pkg_dir and untar in build dir.  If the untarred
        module already exists in the build_dir then remove it first."""

        # Don't do anything if no tarfile is specified
        if not self.file:
            if self.autofile:
                self.file = self.name
                for autofile in self.autofile:
                    self.file = re.sub(autofile['in'], autofile['out'], self.file)
            else:
                return

        # Resolve the tarfile glob and make sure one file from pkgs_manifest matches
        tarfileglob = os.path.join(pkg_dir, self.file)
        tarfiles = [x for x in glob(tarfileglob) if os.path.basename(x) in pkgs_manifest]
        if len(tarfiles) != 1:
            raise RuntimeError, '%s glob matched %d files in package manifest' % (tarfileglob, len(tarfiles))
        else:
            tarfile = tarfiles[0]
        
        # Process with python tarfile module.  The first member will be the directory
        # name - catch that in order to determine where the tar will get extracted.
        self.tarfile = os.path.basename(tarfile)
        if self.moduledir and os.path.exists(self.moduledir):
            print "Removing existing module build dir", self.moduledir
            shutil.rmtree(self.moduledir)
        tar = Tarfile.open(tarfile)
        for member in tar:
            if self.tardir is None:
                tardir_paths = os.path.split(member.name)
                self.tardir = tardir_paths[0] or tardir_paths[1]
                self.moduledir = os.path.join(build_dir, self.tardir)
                # Kinda yucky -- allow for setting extract=False to just run through to this point
                # in order to set self.moduledir
                if not extract:
                    return
            print member.name
            tar.extract(member, build_dir)

def print_header(symbol, message):
    print '\n' + symbol * 40
    print symbol, message
    print symbol * 40

def make_version_file(version_file):
    if os.path.exists(version_file):
        os.remove(version_file)
    f = open(version_file, 'w')
    f.write("#!/bin/sh\n")
    f.write("echo '%s'\n" % ska_version.version)
    f.close()
    os.chmod(version_file,
             stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH |
             stat.S_IWUSR | stat.S_IWGRP |
             stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

# Start of main routine

# Get program options and arguments
opt, arg = get_options()

# Give pexpect.spawn a new convenience method that sends a line and expects the prompt
PROMPT1 = r'Install-\t> '
PROMPT2 = r'Install-\t- '
re_PROMPT = re.compile(r'Install-\d\d:\d\d:\d\d([->]) ')
pexpect.spawn.sendline_expect = sendline_expect_func(re_PROMPT)


# Set the prefix and arch_prefix (latter is architecture dependent installation prefix)
bash("""eval `./template/bin/sysarch -bash`
        export platform_os_generic
        export hw_cpu_generic""",
     keep_env=True)

os.environ['perl'] = opt.perl
os.environ['python'] = opt.python
os.environ['prefix'] = prefix = os.path.abspath(opt.prefix)
os.environ['prefix_arch'] = os.path.join(os.environ['prefix'], opt.arch,
                                         os.environ['platform_os_generic'])
build_dir =  os.path.join(os.path.abspath(opt.build or os.path.join(prefix, 'build')),
                          os.environ['platform_os_generic'])
os.environ['build_dir'] = build_dir 
os.environ['pkg_dir'] = pkg_dir = os.path.abspath(opt.pkgs)
os.environ['installer_dir'] = os.path.abspath(os.path.dirname(__file__))
os.environ['LD_RUN_PATH'] = os.path.join(os.environ['prefix_arch'], 'lib')

# Make sure that the required build and install dirs exist.
#   (this could be made into a cfg file)
for dirname, subdirs in (('build_dir', ['']),
                         ('prefix', ['bin', 'lib/perl/lib', 'include']),
                         ('prefix_arch', ['bin', 'lib', 'include'])):
    if dirname == 'prefix_arch' and opt.installing_anaconda:
        # Don't make prefix_arch and sub-dirs if installing anaconda, this must
        # not exist for the Anaconda install script to work.
        continue
    for subdir in subdirs:
        path = os.path.join(os.environ[dirname], subdir)
        if not os.path.exists(path):
            print 'Making dir', path
            os.makedirs(path)

# Get pkgs manifest and copy to prefix
pkgs = [x.strip() for x in open(opt.manifest)]

if not opt.installing_anaconda:
    # Create link to system perl from arch dir if perl hasn't been built
    arch_perl = os.path.join(os.environ['prefix_arch'], 'bin/perl')
    if not os.path.exists(arch_perl):
        os.symlink(opt.perl, arch_perl)

# Remove the default 'env_vars' configuration if --no-env-var specified
if opt.no_env_vars:
    opt.config.pop(0)

# Do the modules installation by iterating over the yaml 'install' sections
# (delimited by '---' in the yaml cfg file) in each config file
for configfile in opt.config:
    print_header('#', 'Config file: ' + configfile)

    # Config file can accept a single additional module_name arg like:
    # <config_file>:<module_name>.  In this case only that module will
    # be processed.
    if ':' in configfile:
        configfile, module_name = configfile.split(':')
    else:
        module_name = None

    # Allow for skipping the '.cfg' extension
    if os.path.splitext(configfile)[1] == '':
        configfile = configfile + '.cfg'

    for install in yaml.load_all(open(os.path.join('cfg', configfile)).read()):
        # Save each content type installation spec for subsequent use
        Module.installcfgs[install.get('content', 'default')] = install
        # Append any 'configfiles' list elements to the list of config files to be read
        opt.config.extend(install.get('configfiles', []))

        if 'modules' in install:
            print_header('*', 'Installing: ' + install['content'])

        # Install each module for the content type
        for modcfg in install.get('modules', []):
            module = Module(modcfg, install)
            # If module name was supplied then only process that module
            if module_name is not None and module.name != module_name:
                continue
            print_header('-', 'Module: ' + module.name)
            os.environ['module'] = module.name

            # If spec'd the 'require' cmds must succeed else the module is
            # skipped, e.g. if it won't build on a particular platform or some
            # dependency is not met.
            if not module.run_cmds('require'):
                print 'Skipping because require failed.'
                continue

            # Do an initial dry-run through untar in order to figure out what the module
            # build directory (moduledir) will be.  This is needed to check .installed.
            module.untar(build_dir, pkg_dir, pkgs, extract=False)
            os.environ['module_dir'] = module.moduledir or ''

            # Check that the tar package is in the package manifest
            if module.tarfile and module.tarfile not in pkgs:
                print 'Package %s from %s is not in pkg.manifest' % (module.tarfile, pkg_dir)
                sys.exit(1)

            # If the test cmds exist and succeed, and .installed exists in the
            # module build directory then move on to next module
            if ('test' in module.cmds and module.run_cmds('test')):
                print module.name, 'is already installed.\n'
                continue

            print '\nInstalling', module.name

            if opt.confirm:
                print 'Confirm install (y/N)? ',
                if not raw_input().lower().strip().startswith('y'):
                    print 'Skipping installation'
                    continue

            # Untar the module into the build directory
            module.untar(build_dir, pkg_dir, pkgs)

            # Do the actual build and install
            for cmdtyp in ('build', 'install'):
                print 'Running', cmdtyp
                if not module.run_cmds(cmdtyp):
                    print '%s failed, continue anyway (y/n)?' % cmdtyp.capitalize(),
                    if opt.allow_errors:
                        print 'YES (auto)'
                    elif not raw_input().lower().strip().startswith('y'):
                        sys.exit(1)

            # If possible touch the .installed file in the module's build directory
            if module.moduledir:
                open(os.path.join(module.moduledir, '.installed'), 'w').close()

            # Make sure the test_cmds now pass.  If not, try to removed the .installed file
            if not module.run_cmds('test'):
                try:
                    os.unlink(os.path.join(module.moduledir, '.installed'))
                except:
                    pass
                print 'Module %s passed install step but failed test cmds, continue anyway (y/n)?' % module.name,
                if opt.allow_errors:
                    print 'YES (auto)'
                elif not raw_input().lower().strip().startswith('y'):
                    sys.exit(1)

if not opt.installing_anaconda:
    ok = True
    if opt.confirm:
        print 'Update ska_version and pkgs.manifest (y/N)? ',
        if not raw_input().lower().strip().startswith('y'):
            ok = False

    if ok:
        print 'Updating pkgs.manifest and ska_version'
        bash('cp -p ' + opt.manifest + ' ${prefix_arch}/')
        make_version_file(os.path.join(os.environ['prefix_arch'], 'bin', 'ska_version'))
