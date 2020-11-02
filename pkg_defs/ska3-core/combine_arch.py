#!/usr/bin/env python
"""
Make a combined arch-specific core package list from a set of json files with lists of
packages in conda environments.
"""
from skare3_tools import packages
import json
import jinja2
import argparse


def parser():
    parser_ = argparse.ArgumentParser(description=__doc__)
    parser_.add_argument("--name", help="name of the package", default="ska3-core")
    parser_.add_argument("--version", help="new package version", default="")
    parser_.add_argument("--env", action="append", help="environment file", default=[])
    parser_.add_argument("--subtract-env", action="append")
    parser_.add_argument("--out",
                         help="filename for output file with combined list of files"
                              " for use in metapackage ")
    return parser_


def get_environments(envs):
    environments = {}
    print(f'Reading environments for {envs}:')
    for env in envs:
        try:
            platform, filename = env.split('=')
        except ValueError:
            print(f' - skipped {env}')
            continue
        print(f' + {platform}: {filename}')
        with open(filename) as fh:
            environments[platform] = {p['name']: p for p in json.load(fh)}
    return environments


def main():
    args = parser().parse_args()

    # This defines the "core" packages as everything that is not a ska package
    # with some exceptions
    exceptions = ['sherpa', 'prompt-toolkit']
    ska_packages = [p['package'] for p in packages.get_package_list()
                    if p['package'] and p['package'] not in exceptions]

    environments = get_environments(args.env)
    subtract_environments = get_environments(args.subtract_env)

    for platform in environments:
        remove_keys = []
        for package in environments[platform]:
            if (platform in subtract_environments
                    and package in subtract_environments[platform]
                    and subtract_environments[platform][package]['version']
                    == environments[platform][package]['version']):
                remove_keys.append(package)
        for package in remove_keys:
            del environments[platform][package]

    package_names = sorted(set(sum([list(e.keys()) for e in environments.values()], [])))
    all_packages = []
    for p in package_names:
        versions = sorted(set(
            [environments[e][p]['version'].strip() for e in environments if p in environments[e]]
        ))
        for v in versions:
            platforms = sorted([e for e in environments
                                if p in environments[e] and environments[e][p]['version'] == v])
            platforms = [] if len(platforms) == len(environments) else platforms
            all_packages.append({
                'name': p,
                'platforms': ' or '.join(platforms),
                'version': v
            })

    tpl = jinja2.Template(YAML_TPL)
    meta = tpl.render(
        package=args.name,
        version=args.version,
        requirements=[p for p in all_packages if p['name'] not in ska_packages]
    )
    if args.out:
        with open(args.out, 'w') as fh:
            fh.write(meta)
    else:
        print(meta)


YAML_TPL = """---
package:
  name: {{ package }}
  version: {{ version }}

requirements:
  run:
  {%- for p in requirements %}
    - {{ p.name }} =={{ p.version }}{%if p.platforms %}  # [{{ p.platforms }}]{% endif %}
  {%- endfor %}

"""


if __name__ == "__main__":
    main()
