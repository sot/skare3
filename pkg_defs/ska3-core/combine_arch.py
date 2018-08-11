import json
import argparse
import numpy as np
from distutils.version import LooseVersion

parser = argparse.ArgumentParser(description="Make a combined arch-specific core package list")
parser.add_argument("--linux",
                    help="conda list json file with list of linux packages")
parser.add_argument("--osx",
                    help="conda list json file with list of osx packages")
parser.add_argument("--out",
                    help="filename for output file with combined list of files"
                    " for use in metapackage ")
args = parser.parse_args()


def core_pkgs(pkgs):
    # This defines the "core" packages as everything that came from defaults
    # channel except the conda (conda, conda-build, conda-env, etc) packages
    core = {p['name']:p['version'] for p in pkgs if ((p['channel'] == 'defaults')
                                                     & (not p['name'].startswith('conda')))}
    return core

pkgs = {'linux': core_pkgs(json.load(open(args.linux))),
        'osx': core_pkgs(json.load(open(args.osx)))}

full = np.unique(list(pkgs['linux']) + list(pkgs['osx']))

pkglist = []
for p in full:
    # For packages that are automatically installed (by dependency request) on both
    # OSes, here we've just selected the minimum version to require.  The actual set of 
    # packages still needs to be tested after creation.
    if p in pkgs['linux'] and p in pkgs['osx']:
        versions = [pkgs['linux'][p], pkgs['osx'][p]]
        versions.sort(key=LooseVersion)
        pkglist.append("   - {} =={}".format(p, versions[0]))
    if p in pkgs['linux'] and p not in pkgs['osx']:
        pkglist.append("   - {} =={} [linux]".format(p, pkgs['linux'][p]))
    if p in pkgs['osx'] and p not in pkgs['linux']:
        pkglist.append("   - {} =={} [osx]".format(p, pkgs['osx'][p]))

open(args.out, 'w').write("\n".join(pkglist))
