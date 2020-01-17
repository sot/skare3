#!/usr/bin/env python3

from skare3.tools import github
import os
import re
import json
import argparse


API = None


def get_repository_info(owner_repo):
    global API
    owner, repo = owner_repo.split('/')

    last_tag = API.get(f'repos/{owner}/{repo}/releases/latest').json()
    tag_info = API.get(f'repos/{owner}/{repo}/git/ref/tags/{last_tag["tag_name"]}').json()
    tag_sha = tag_info['object']['sha']
    rel_commit = API.get(f'repos/{owner}/{repo}/commits/{tag_sha}').json()
    commit_date = rel_commit['commit']['author']['date']

    commits = API.get(f'repos/{owner}/{repo}/commits',
                      params={'sha':'master', 'since': commit_date}).json()
    commits = commits[:-1]  # remove the commit associated to the release

    branches = API.get(f'repos/{owner}/{repo}/branches').json()
    n_branches = len(branches)

    issue_page = API.get(f'repos/{owner}/{repo}/issues', params={'per_page':100}).json()
    issues = issue_page
    while len(issue_page) == 100:
        issue_page = API.get(f'repos/{owner}/{repo}/issues', params={'per_page':100}).json()
        issues += issue_page
    n_pr = len([i for i in issues if 'pull_request' in i])
    n_issues = len(issues) - n_pr

    merges = []
    for commit in commits:
        msg = commit['commit']['message']
        match = re.match('Merge pull request (?P<pr>.+) from (?P<branch>\S+)\n\n(?P<description>.+)', msg)
        if match:
            msg = match.groupdict()
            merges.append(f'PR{msg["pr"]}: {msg["description"]}')

    repo_info = {
        'owner': owner,
        'name': repo,
        'last_tag': last_tag["tag_name"],
        'last_tag_date': last_tag['published_at'],
        'commits': len(commits),
        'merges': len(merges),
        'merge_info': merges,
        'issues': n_issues,
        'pull_requests': n_pr,
        'branches': n_branches
    }
    return repo_info


def get_repositories_info(repositories):
    info = []
    for owner_repo in repositories:
        print(owner_repo)
        info.append(get_repository_info(owner_repo))
    return info


def main():
    global API

    parser = argparse.ArgumentParser()
    parser.add_argument('-o', default='repository_info.json')
    parser.add_argument('-u')
    args = parser.parse_args()
    print(f'user is {args.u}')

    if args.u:
        github.init(user=args.u)
        API = github.GITHUB_API

    info = get_repositories_info([
        'sot/Chandra.Maneuver',
        'sot/Chandra.Time',
        'sot/Quaternion',
        'sot/Ska.DBI',
        'sot/Ska.File',
        'sot/Ska.Matplotlib',
        'sot/Ska.Numpy',
        'sot/Ska.ParseCM',
        'sot/Ska.Shell',
        'sot/Ska.Sun',
        'sot/Ska.arc5gl',
        'sot/Ska.astro',
        'sot/Ska.ftp',
        'sot/Ska.quatutil',
        'sot/Ska.tdb',
        'sot/acdc',
        'sot/acis_taco',
        'sot/agasc',
        'sot/annie',
        'sot/chandra_aca',
        'sot/cmd_states',
        'sot/cxotime',
        'sot/eng_archive',
        'sot/hopper',
        'sot/kadi',
        'sot/maude',
        'sot/mica',
        'sot/parse_cm',
        'sot/proseco',
        'sot/pyyaks',
        'sot/ska_path',
        'sot/ska_sync',
        'sot/sparkles',
        'sot/starcheck',
        'sot/tables3_api',
        'sot/testr',
        'sot/xija'
    ])
    with open(args.o, 'w') as f:
        json.dump(info, f, indent=2)


if __name__ == '__main__':
    main()
