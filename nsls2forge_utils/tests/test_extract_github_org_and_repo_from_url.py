import pytest

from nsls2forge_utils.dashboard import (_extract_github_org_and_repo,
                                        _extract_github_org_and_repo_from_url)


def test_extract_org_and_repo():
    (org, repo) = _extract_github_org_and_repo('qtmodern')
    assert (org, repo) == ('gmarull', 'qtmodern')


@pytest.mark.parametrize(
    'url,expected',
    [('https://www.github.com/gmarull/qtmodern', ('gmarull', 'qtmodern')),
     ('http://www.github.com/gmarull/qtmodern', ('gmarull', 'qtmodern')),
     ('https://github.com/gmarull/qtmodern', ('gmarull', 'qtmodern')),
     ('something', ('', ''))
     ]
)
def test_extract_org_and_repo_from_url(url, expected):
    org, repo = _extract_github_org_and_repo_from_url(url)
    assert (org, repo) == expected
