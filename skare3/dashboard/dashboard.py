#!/usr/bin/env python3

import json
from jinja2 import Environment, PackageLoader, select_autoescape
import argparse


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', default='repository_info.json')
    parser.add_argument('-o', default='index.html')
    args = parser.parse_args()

    with open(args.i, 'r') as f:
        packages = sorted(json.load(f), key=lambda p: p['name'])

    env = Environment(
        loader=PackageLoader('skare3.dashboard', 'templates'),
        autoescape=select_autoescape(['html', 'xml'])
    )

    template = env.get_template('dashboard-watable.tpl')

    with open(args.o, 'w') as out:
        out.write(template.render(title='Skare3 Packages', packages=packages))


if __name__ == '__main__':
    main()