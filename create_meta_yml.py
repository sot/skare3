#!/usr/bin/env python
"""
Produce ska3-core-meta.yaml and ska3-flight-meta.yaml from a set of json files with lists of
packages in conda environments.
"""
from skare3_tools import packages
import json
import jinja2
import glob
import re

ska_packages = [p['package'] for p in packages.get_package_list() if p['package']]

filenames = glob.glob('ska3-shiny-*.json')
envs = {}
for filename in filenames:
    with open(filename) as fh:
        platform = re.match('ska3-shiny-(\S+).json', filename).group(1)
        envs[platform] = {p['name']:p for p in json.load(fh)}

package_names = sorted(set(sum([list(e.keys()) for e in envs.values()], [])))
all_packages = []
for p in package_names:
    versions = sorted(set([envs[e][p]['version'].strip() for e in envs if p in envs[e]]))
    for v in versions:
        r = {'name': p}
        platforms = sorted([e for e in envs if p in envs[e] and envs[e][p]['version'] == v])
        if len(platforms) == len(envs):
            platforms = ''
        else:
            platforms = ' or '.join(platforms)
        r['platforms'] = platforms
        r['version'] = v
        all_packages.append(r)


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

with open('ska3-flight-meta.yaml', 'w') as fh:
    tpl = jinja2.Template(YAML_TPL)
    fh.write(tpl.render(
        package='ska3-flight',
        version='2020.11',
        requirements=[p for p in all_packages
                      if p['name'] in ska_packages
                      and p['name'] not in ['ska3-flight-latest', 'sherpa', 'prompt-toolkit']]
    ))

with open('ska3-core-meta.yaml', 'w') as fh:
    tpl = jinja2.Template(YAML_TPL)
    fh.write(tpl.render(
        package='ska3-core',
        version='2020.11',
        requirements=[p for p in all_packages
                      if p['name'] in ['sherpa', 'prompt-toolkit']
                      or p['name'] not in ska_packages + ['ska3-flight-latest', 'ska3-core-latest']]
    ))
