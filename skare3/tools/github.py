import logging
logging.basicConfig(level=logging.DEBUG)  # noqa
import getpass
import os
import requests
try:
    import keyring
except ModuleNotFoundError:
    keyring = None

from requests.auth import HTTPBasicAuth


class AuthException(Exception):
    pass


class RestException(Exception):
    pass


_logger = logging.getLogger('github')
GITHUB_API = None


def init(user=None, password=None):
    global GITHUB_API
    if GITHUB_API is None:
        api = GithubAPI(user=user, password=password)
        r = api.get('')
        if r.status_code == 401:
            raise AuthException(r.json()['message'])
        GITHUB_API = api
        _logger.info(f'Github interface initialized (user={user}')


class GithubAPI:
    def __init__(self, user=None, password=None):
        if user is None:
            if 'GITHUB_USER' in os.environ:
                user = os.environ['GITHUB_USER']
            else:
                user = input('Username: ')
        if password is None:
            if 'GITHUB_PASSWORD' in os.environ:
                password = os.environ['GITHUB_PASSWORD']
            elif keyring:
                password = keyring.get_password("skare3-github", user)
            if password is None:
                password = getpass.getpass()

        self.user = user
        self.auth = HTTPBasicAuth(self.user, password)
        self.headers = {"Accept": "application/json"}
        self.api_url = 'https://api.github.com'

    @staticmethod
    def check(response):
        if not response.ok:
            raise RestException(f'Error: {response.reason} ({response.status_code})')

    def __call__(self, path, method='get', params=None,
                 check=False, return_json=False, headers=(), **kwargs):
        if ':' in path:
            path = '/'.join([f'{{{p[1:]}}}' if p and p[0] == ':' else p for p in path.split('/')])
            path = path.format(**kwargs)
        if path and path[0] == '/':
            path = path[1:]
        url = f'{self.api_url}/{path}'
        _headers = self.headers.copy()
        _headers.update(headers)
        kwargs = {k: v for k, v in kwargs.items() if k in ['json']}
        _logger.debug('%s %s\n  headers: %s\n  params: %s,\n kwargs: %s',
                      url, method, _headers, params, kwargs)
        r = requests.request(method, url, headers=_headers, auth=self.auth, params=params, **kwargs)
        if check:
            self.check(r)
        if return_json:
            if r.content:
                result = r.json()
            else:
                result = {}
            if hasattr(result, 'keys'):
                result['response'] = {
                    'status_code': r.status_code,
                    'ok': r.ok,
                    'reason': r.reason
                }
            return result
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
        return Repository(api=self, owner=owner, repo=repo)


class _EndpointGroup:
    """
    Base class for grouping related endpoints.

    Related endpoints share some arguments. In the github case, that is the repository name/owner.
    """
    def __init__(self, repo):
        self.api = repo.api
        self.owner = repo.owner
        self.repo = repo.repo

    def _method_(self, method, url, **kwargs):
        kwargs.update(dict(owner=self.owner, repo=self.repo))
        url = url.format(**kwargs)
        return self.api(url, method=method, return_json=True, **kwargs)

    def _get(self, url, **kwargs):
        return self._method_('get', url, **kwargs)

    def _post(self, url, **kwargs):
        return self._method_('post', url, **kwargs)

    def _patch(self, url, **kwargs):
        return self._method_('patch', url, **kwargs)

    def _delete(self, url, **kwargs):
        return self._method_('delete', url, **kwargs)

    def _get_list_generator(self, url, limit=None, **kwargs):
        """
        Generator over items returned via a paginated endpoint.

        Github's API paginates the results when requests return multiple items.
        This method steps through the pages, returning items one by one.

        :param url:
        :param limit:
        :param kwargs:
        :return:
        """
        if 'params' not in kwargs:
            kwargs['params'] = {}
        page = 1
        count = 0
        while True:
            kwargs['params']['page'] = page
            r = self._get(url, **kwargs)
            print(type(r), r)
            if type(r) is not list:
                _logger.warning('_get_list_generator received a %s', type(r))
                break
            if len(r) == 0:
                break
            _logger.debug('_get_list_generator in page %s, %s entries', page, len(r))
            page += 1
            for item in r:
                yield item
                count += 1
                if limit and count >= limit:
                    raise StopIteration()

    def _get_list(self, *args, **kwargs):
        """
        Generator over items returned via a paginated endpoint.

        Github's API paginates the results when requests return multiple items.
        This method steps through the pages, returning a list of all items.

        :param args:
        :param kwargs:
        :return:
        """
        return [entry for entry in self._get_list_generator(*args, **kwargs)]


class Repository:
    def __init__(self, repo=None, owner=None, api=None):
        global GITHUB_API
        init()
        self.api = GITHUB_API if api is None else api
        if '/' in repo:
            self.owner, self.repo = repo.split('/')
        else:
            self.owner = owner
            self.repo = repo

        self.releases = Releases(self)
        self.tags = Tags(self)
        self.commits = Commits(self)
        self.issues = Issues(self)
        self.branches = Branches(self)
        self.checks = Checks(self)


class Releases(_EndpointGroup):
    def __call__(self, latest=False, tag_name=None, release_id=None):
        if sum([latest, bool(tag_name), bool(release_id)]) > 1:
            raise Exception('only one of latest, tag_name, release_id can be specified')
        if release_id:
            return self._get('repos/:owner/:repo/releases/:release_id',
                             release_id=release_id)
        elif latest:
            return self._get('repos/:owner/:repo/releases/latest')
        elif tag_name:
            return self._get('repos/:owner/:repo/releases/tags/:tag_name',
                             tag_name=tag_name)
        else:
            return self._get_list('repos/:owner/:repo/releases')

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
            True to identify the release as a prerelease.
            false to identify the release as a full release.
            Default: false
        """
        required = ['tag_name']
        optional = ['target_commitish', 'name', 'body', 'draft', 'prerelease']
        json = {k: kwargs[k] for k in required}
        json.update({k: kwargs[k]for k in optional if k in kwargs})
        kwargs = {k: v for k, v in kwargs.items() if k not in json}
        return self._post('repos/:owner/:repo/releases', json=json, **kwargs)

    def edit(self, release_id, **kwargs):
        """
        release_id: string
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
            true to identify the release as a prerelease,
            false to identify the release as a full release.
        """
        required = []
        optional = ['target_commitish', 'name', 'body', 'draft', 'prerelease']
        json = {k: kwargs[k] for k in required}
        json.update({k: kwargs[k]for k in optional if k in kwargs})
        kwargs = {k: v for k, v in kwargs.items() if k not in json}
        return self._patch('repos/:owner/:repo/releases/:release_id',
                           release_id=release_id,
                           json=json,
                           **kwargs)

    def delete(self, release_id):
        return self._delete('repos/:owner/:repo/releases/:release_id', release_id=release_id)


class Tags(_EndpointGroup):
    def __call__(self, tag_sha=None, name=None):
        if sum([bool(tag_sha), bool(name)]) > 1:
            raise Exception('only one of tag_sha, name can be specified')
        if tag_sha:
            return self._get('repos/:owner/:repo/git/tags/:tag_sha',
                             tag_sha=tag_sha)
        elif name:
            return self._get('repos/:owner/:repo/git/ref/tags/:name',
                             name=name)
        else:
            return self._get_list('repos/:owner/:repo/tags')

    def create(self, **kwargs):
        """
        tag: string. Required.
            The tag's name. This is typically a version (e.g., "v0.0.1").
        message: string. Required.
            The tag message.
        object: string. Required.
            The SHA of the git object this is tagging.
        type: string. Required.
            The type of the object we're tagging. Normally this is a commit
            but it can also be a tree or a blob.
        tagger: object
            An object with information about the individual creating the tag.

        The tagger object contains the following keys:
            name: string. The name of the author of the tag
            email: string. The email of the author of the tag
            date: string. When this object was tagged.
                This is a timestamp in ISO 8601 format: YYYY-MM-DDTHH:MM:SSZ.
        """
        required = ['tag', 'message', 'object', 'type']
        optional = ['tagger']
        json = {k: kwargs[k] for k in required}
        json.update({k: kwargs[k] for k in optional if k in kwargs})
        kwargs = {k: v for k, v in kwargs.items() if k not in json}
        return self._post('repos/:owner/:repo/git/tags', json=json, **kwargs)


class Commits(_EndpointGroup):
    def __call__(self, **kwargs):
        return self._get_list('repos/:owner/:repo/commits', **kwargs)


class Branches(_EndpointGroup):
    def __call__(self, **kwargs):
        return self._get_list('repos/:owner/:repo/branches', **kwargs)


class Issues(_EndpointGroup):
    def __call__(self, **kwargs):
        return self._get_list('repos/:owner/:repo/issues', **kwargs)

    def create(self, **kwargs):
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
            Logins for Users to assign to this issue.
            NOTE: Only users with push access can set assignees for new issues.
            Assignees are silently dropped otherwise.
        """
        required = ['title']
        optional = ['body', 'milestone', 'labels', 'assignees']
        json = {k: kwargs[k] for k in required}
        json.update({k: kwargs[k] for k in optional if k in kwargs})
        kwargs = {k: v for k, v in kwargs.items() if k not in json}
        return self._post('repos/:owner/:repo/issues', json=json, **kwargs)


class Checks(_EndpointGroup):
    def __call__(self, ref):
        # accept headers are custom because this endpoint is
        # on preview for developers and can change any time
        return self._get('repos/:owner/:repo/commits/:ref/check-runs',
                         headers={'Accept': 'application/vnd.github.antiope-preview+json'},
                         ref=ref)
