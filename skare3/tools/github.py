import logging
import requests
from requests.auth import HTTPBasicAuth
import getpass


class RestException(Exception):
    pass


GITHUB_API = None

class GithubAPI:
    def __init__(self, user=None, password=None):
        if user is None:
            user = input('Username: ')
        if password is None:
            password = getpass.getpass()

        self.user = user
        self.auth = HTTPBasicAuth(self.user, password)
        self.headers = {"Accept": "application/json"}
        self.api_url = 'https://api.github.com'


    def check(self, response):
        if not response.ok:
            raise RestException(f'Error: {response.reason} ({response.status_code})')

    def __call__(self, path, method='get', params=None, check=False, **kwargs):
        url = f'{self.api_url}/{path}'
        r = requests.request(method, url, headers=self.headers, auth=self.auth, params=params, **kwargs)
        if check:
            self.check(r)
        return r

    def get(self, path, params=None, **kwargs):
        r = self(path, method='get', params=params, **kwargs)
        return r

    def post(self, path, params=None, **kwargs):
        r = self(path, method='post', json=params, **kwargs)
        return r


    def put(self, path, params=None, **kwargs):
        r = self(path, method='put', json=params, **kwargs)
        return r

    def patch(self, path, params=None, **kwargs):
        r = self(path, method='patch', json=params, **kwargs)
        return r

    def repo(self, owner, repo):
        return Repository(self, owner, repo)


class Repository:
    def __init__(self, owner, repo, api=None):
        global GITHUB_API
        self.api = api
        if self.api is None:
            if GITHUB_API is None:
                GITHUB_API = GithubAPI()
            self.api = GITHUB_API
        self.owner = owner
        self.repo = repo

        self.releases = Releases(self)
        self.tags = Tags(self)
        self.commits = Commits(self)
        self.issues = Issues(self)
        self.branches = Branches(self)

class Releases:
    def __init__(self, repo):
        self.api = repo.api
        self.owner = repo.owner
        self.repo = repo.repo


    def __call__(self, latest=False, tag_name=None, release_id=None):
        if sum([latest, bool(tag_name), bool(release_id)]) > 1:
            raise Exception('only one of latest, tag_name, release_id can be specified')
        if release_id:
            r = self.api.get(f'repos/{self.owner}/{self.repo}/releases/{release_id}')
        elif latest:
            r = self.api.get(f'repos/{self.owner}/{self.repo}/releases/latest')
        elif tag_name:
            r = self.api.get(f'repos/{self.owner}/{self.repo}/releases/tags/{tag_name}')
        else:
            r = self.api.get(f'repos/{self.owner}/{self.repo}/releases')
        return r.json()

    def create(self, **kwargs):
        """
        tag_name: string. Required. The name of the tag.
        target_commitish: string.
            Specifies the commitish value that determines where the Git tag is created from.
            Can be any branch or commit SHA. Unused if the Git tag already exists.
            Default: the repository's default branch (usually master).
        name: string.
            The name of the release.
        body: string.
            Text describing the contents of the tag.
        draft: boolean.
            True to create a draft (unpublished) release, false to create a published one.
            Default: false
        prerelease: boolean.
            True to identify the release as a prerelease. false to identify the release as a full release.
            Default: false
        """
        r = self.api.post(f'repos/{self.owner}/{self.repo}/releases', params=kwargs)
        return r.json()

    def edit(self, release_id, **kwargs):
        """
        tag_name: string
            The name of the tag.
        target_commitish: string
            Specifies the commitish value that determines where the Git tag is created from.
            Can be any branch or commit SHA. Unused if the Git tag already exists.
            Default: the repository's default branch (usually master).
        name: string
            The name of the release.
        body: string
            Text describing the contents of the tag.
        draft: boolean
            true makes the release a draft, and false publishes the release.
        prerelease: boolean
            true to identify the release as a prerelease, false to identify the release as a full release.
        """
        r = self.api.patch(f'repos/{self.owner}/{self.repo}/releases/{release_id}', params=kwargs)
        return r.json()

    def delete(self, release_id):
        r = self.api.delete(f'repos/{self.owner}/{self.repo}/releases/{release_id}')
        return r.json()

class Tags:
    def __init__(self, repo):
        self.api = repo.api
        self.owner = repo.owner
        self.repo = repo.repo

    def __call__(self, tag_sha=None, name=None):
        if sum([bool(tag_sha), bool(name)]) > 1:
            raise Exception('only one of tag_sha, name can be specified')
        if tag_sha:
            r = self.api.get(f'repos/{self.owner}/{self.repo}/git/tags/{tag_sha}')
        elif name:
            r = self.api.get(f'repos/{self.owner}/{self.repo}/git/ref/tags/{name}')
        else:
            r = self.api.get(f'repos/{self.owner}/{self.repo}/tags')
        return r.json()

    def create(self, **kwargs):
        """
        tag: string. Required.
            The tag's name. This is typically a version (e.g., "v0.0.1").
        message: string. Required.
            The tag message.
        object: string. Required.
            The SHA of the git object this is tagging.
        type: string. Required.
            The type of the object we're tagging. Normally this is a commit but it can also be a tree or a blob.
        tagger: object
            An object with information about the individual creating the tag.

        The tagger object contains the following keys:
            name: string. The name of the author of the tag
            email: string. The email of the author of the tag
            date: string. When this object was tagged. This is a timestamp in ISO 8601 format: YYYY-MM-DDTHH:MM:SSZ.
        """
        r = self.api.post(f'repos/{self.owner}/{self.repo}/git/tags')
        return r.json()


class Commits:
    def __init__(self, repo):
        self.api = repo.api
        self.owner = repo.owner
        self.repo = repo.repo

    def __call__(self):
        r = self.api.get(f'repos/{self.owner}/{self.repo}/commits')
        return r.json()


class Branches:
    def __init__(self, repo):
        self.api = repo.api
        self.owner = repo.owner
        self.repo = repo.repo

    def __call__(self):
        r = self.api.get(f'repos/{self.owner}/{self.repo}/branches')
        return r.json()


class Issues:
    def __init__(self, repo):
        self.api = repo.api
        self.owner = repo.owner
        self.repo = repo.repo

    def __call__(self):
        r = self.api.get(f'repos/{self.owner}/{self.repo}/issues')
        return r.json()

    def create(self, title, **kwargs):
        """
        title: string Required. The title of the issue.
        body: string The contents of the issue.
        milestone: integer
            The number of the milestone to associate this issue with.
            NOTE: Only users with push access can set the milestone for new issues.
            The milestone is silently dropped otherwise.
        labels: array of strings
            Labels to associate with this issue.
            NOTE: Only users with push access can set labels for new issues.
            Labels are silently dropped otherwise.
        assignees: array of strings
            Logins for Users to assign to this issue. NOTE: Only users with push access can set assignees for new issues. Assignees are silently dropped otherwise.
        """
        params = {'title': title}
        params.update(kwargs)
        r = self.api.post(f'repos/{self.owner}/{self.repo}/issues', params=params)
        return r.json()
