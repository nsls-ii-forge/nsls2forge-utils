"""
This code is a rework of
https://github.com/xpdAcq/mission-control/blob/master/tools/update_readme.py
This version was not importable so the
functions had to be re-implemented here.
"""
from urllib.parse import urlparse

from .all_feedstocks import get_all_feedstocks
from .meta_utils import get_attribute


def _extract_github_org_and_repo_from_url(url):
    url = urlparse(url)
    if url is not None and url.netloc == 'github.com':
        path = url.path.strip('/').split('/')
        if len(path) == 0:
            return '', ''
        elif len(path) == 1:
            path.append('')
        return path[-2], path[-1]
    return '', ''


def _extract_github_org_and_repo(pkg):
    # get org from home url
    home_str = get_attribute('about home', pkg, 'nsls-ii-forge')
    org, repo = _extract_github_org_and_repo_from_url(home_str)
    # if home url failed try dev_url
    if org == '':
        dev_url = get_attribute('about dev_url', pkg, 'nsls-ii-forge')
        org, repo = _extract_github_org_and_repo_from_url(dev_url)
    return org, repo


def create_dashboard_from_list(names=[]):
    '''
    Creates a table of packages with their build status, health, versions,
    and downloads. Feedstocks must be from the nsls-ii-forge GitHub organization.

    Parameters
    ----------
    names: list
        List of feedstock package names to use as entries in the dashboard

    Returns
    -------
    str
        Dashboard content in formatted string
    '''
    main_format = dict(
      build='[![Build Status](https://dev.azure.com/nsls2forge/nsls2forge/_apis/build/status/{name}-feedstock)]'
            '(https://dev.azure.com/nsls2forge/nsls2forge/_build)',
      health='[![Code Health](https://landscape.io/github/nsls-ii-forge/{name}-feedstock/master/'
             'landscape.svg?style=flat)](https://landscape.io/github/nsls-ii-forge/{name}-feedstock/master)',
      cf_version='[![conda-forge version](https://img.shields.io/conda/vn/conda-forge/{name})]'
                 '(https://anaconda.org/conda-forge/{name})',
      nsls_version='[![nsls2forge version](https://img.shields.io/conda/vn/nsls2forge/{name})]'
                   '(https://anaconda.org/nsls2forge/{name})',
      defaults_version='[![defaults version](https://img.shields.io/conda/vn/anaconda/{name})]'
                       '(https://anaconda.org/anaconda/{name})',
      pypi_version='[![PyPI version](https://img.shields.io/pypi/v/{name})](https://pypi.org/project/{name}/)',
      github_version='[![GitHub version](https://img.shields.io/github/v/tag/{org}/{repo})]'
                     '(https://github.com/{org}/{repo})',
      downloads='[![Downloads](https://img.shields.io/conda/dn/nsls2forge/{name})]'
                '(https://anaconda.org/nsls2forge/{name})')

    row_string = ('|[{name}](https://github.com/nsls-ii-forge/{name}-feedstock)|{build} <br/> {health}'
                  '|{nsls_version} <br/> {pypi_version} <br/> {defaults_version} <br/> '
                  '{cf_version} <br/> {github_version}|{downloads}|\n')
    header = ('# Feedstock Packages Build Status\n\n'
              '| Repo | Build <br/> Health | nsls2forge <br/> PyPI <br/> defaults <br/> conda-forge <br/>'
              ' GitHub <br/> Versions | Downloads|\n|:-------:|'
              ':-----------:|:---------------:|:--------------:|\n')

    dashboard = header
    for pkg in names:
        print(f'Formatting {pkg}...')
        org, repo = _extract_github_org_and_repo(pkg)
        if repo == '':
            repo = pkg
        tmp = row_string.format(**main_format, name=pkg, org=org, repo=repo)
        dashboard += tmp.format(name=pkg, org=org, repo=repo)
    return dashboard


def create_dashboard(names=None, write_to='README.md'):
    '''
    Creates a table of packages with their build status, health, conda-forge version,
    nsls2forge version, PyPI version, Anaconda version, GitHub version,
    and number of downloads from nsls2forge conda channel.
    Feedstocks must be from nsls-ii-forge GitHub organization.

    Parameters
    ----------
    names: str, optional
        filepath to text file containing feedstock repo names
        without the -feedstock suffix
    write_to: str, optional
        filepath to markdown file to write output to

    Returns
    -------
    int
        number of packages being displayed in the dashboard
    '''
    description = '''# Project Management\nReleases, Installers, Specs, and more!\n'''
    out = description
    if names is None:
        pkgs = sorted(get_all_feedstocks(organization='nsls-ii-forge'))
    else:
        pkgs = sorted(get_all_feedstocks(cached=True, filepath=names))
    out += create_dashboard_from_list(pkgs)
    with open(write_to, 'w') as f:
        f.write(out)
    return len(pkgs)


if __name__ == '__main__':
    create_dashboard()
