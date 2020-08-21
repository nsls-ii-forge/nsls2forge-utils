'''
This code is a rework of
https://github.com/regro/cf-scripts/blob/master/conda_forge_tick/all_feedstocks.py
This version was not importable so the functions had to be copied here.
We will be importing conda-smithy functionality.
'''
import datetime
import logging
import netrc
import os
import glob

from github import Github, GithubException
import git
import markdown
import pandas as pd
import requests
from bs4 import BeautifulSoup
from tabulate import tabulate

from nsls2forge_utils.io import (
    _write_list_to_file,
    read_file_to_list
)

logger = logging.getLogger(__name__)


def get_all_feedstocks_from_github(organization=None, username=None, token=None,
                                   include_archived=False):
    '''
    Gets all public feedstock repository names from the GitHub organization
    (e.g. nsls-ii-forge).

    Parameters
    ----------
    organization: str
        Name of organization on GitHub.
    username: str, optional
        Name of user on GitHub for authentication.
        Uses value from ~/.netrc if not specified.
    password: str, optional
        Password of user on GitHub for authentication.
        Uses value from ~/.netrc if not specified.
    include_archived: bool, optional
        Includes archived feedstocks in returned list
        when set to True.

    Returns
    -------
    names: list, None
        List of repository names that end with '-feedstock' (stripped).
        None if no organization is specified.
    '''
    if organization is None:
        logger.critical('No GitHub organization sepcified.')
        return None
    if username is None:
        netrc_file = netrc.netrc()
        username, _, token = netrc_file.hosts['github.com']
    names = []
    gh = Github(username, token)
    org = gh.get_organization(organization)
    try:
        repos = org.get_repos()
        for repo in repos:
            if repo.archived and not include_archived:
                continue
            name = repo.name
            if name.endswith("-feedstock"):
                name = name.split("-feedstock")[0]
                logger.info(f'Found feedstock: {name}')
                names.append(name)
    except GithubException:
        msg = ["Github rate limited. "]
        remaining, _ = gh.rate_limiting
        if remaining == 0:
            ts = gh.rate_limiting_resettime
            msg.append("API timeout, API returns at")
            msg.append(
                datetime.datetime.utcfromtimestamp(ts).strftime("%Y-%m-%dT%H:%M:%SZ"),
            )
        logger.warning(" ".join(msg))
        raise
    logger.info(f'Found {len(names)} feedstocks from {organization}.')
    return names


def get_all_feedstocks(cached=False, filepath='names.txt',
                       feedstocks_dir='./feedstocks/', **kwargs):
    '''
    Gets all feedstocks either from GitHub or from names.txt if flag is specified.

    Parameters
    ----------
    cached: bool, optional
        Specified if client wants to take repository names from names.txt.
    filepath: str, optional
        Path to file to read from if cached = True. Default value is 'names.txt'.
    feedstocks_dir: str, optional
        Second place to try if cached = True. Default value is './feedstocks/'.
    kwargs: dict, optional
        Organization, username and token should be specified here for authentication
        if cached = False.

    Returns
    -------
    names: list or None
        List of repository names that end with '-feedstock' (stripped).
        None if no organization or username is specified and cached = False.
    '''
    if cached:
        if os.path.exists(filepath):
            print(f"Reading names from cache ({filepath})")
            names = read_file_to_list(filepath)
        elif os.path.exists(feedstocks_dir):
            print(f'Reading names from cloned repo cache ({feedstocks_dir})')
            names = sorted(glob.glob(feedstocks_dir + "*-feedstock"))
            names = [n.replace('-feedstock', '').replace(feedstocks_dir, '') for n in names]
        else:
            logger.critical('No cached feedstocks found')
            return []
        logger.info(f'Found {len(names)} feedstocks.')
        return names
    names = get_all_feedstocks_from_github(**kwargs)
    return names


def clone_all_feedstocks(organization, feedstocks_dir):
    '''
    Clones all feedstock repos from organization to local feedstocks_dir.
    Uses conda-smithy's clone all utility.

    Parameters
    ----------
    organization: str
        GitHub organization to clone feedstock repos from.
    feedstocks_dir: str
        Path to local directory to place cloned feedstocks.
    '''
    from conda_smithy import feedstocks
    print(f'Cloning all feedstocks from {organization}...')
    feedstocks.clone_all(gh_org=organization,
                         feedstocks_dir=feedstocks_dir)


def all_feedstocks_info(feedstocks_dir='./feedstocks/'):
    '''
    Gathers and prints version and other Git info about all currently cloned
    feedstocks

    Parameters
    ----------
    feedstocks_dir: str, optional
        Directory where cloned feedstocks are. Default is './feedstocks/'.

    Returns
    -------
    df: pd.DataFrame
        Table with name, branch, changed, and version info
    '''
    all_feedstocks = get_all_feedstocks(cached=True, feedstocks_dir=feedstocks_dir)
    info = []
    for i, feedstock in enumerate(all_feedstocks):
        feedstock += '-feedstock'
        print(f'Getting info from {feedstock}...')
        repo_path = os.path.join(feedstocks_dir, feedstock)
        # Get version info from README.md's badge via requesting the info from svg:
        try:
            with open(os.path.join(repo_path, 'README.md')) as f:
                html_text = markdown.markdown(f.read())
                html = BeautifulSoup(html_text, features='lxml')
                svg = html.findAll('img', attrs={'alt': 'Conda Version'})[0]
                r = requests.get(svg.attrs['src'])
                svg_html = BeautifulSoup(r.text, features='lxml')
                version_tag = svg_html.findAll('text')[-1]
                version = version_tag.text
        except Exception:
            version = ''

        # Extract info from git:
        repo = git.Repo(repo_path)
        info.append([feedstock, repo.active_branch.name, repo.is_dirty(), version])

    columns = ['Name', 'Branch', 'Changed?', 'Version']
    df = pd.DataFrame(info, columns=columns)
    print(tabulate(df, headers=df.columns))
    return df


def _info_handle_args(args):
    all_feedstocks_info(feedstocks_dir=args.feedstocks_dir)


def _clone_all_handle_args(args):
    print(f'Cloning feestocks from {args.organization}...')
    clone_all_feedstocks(args.organization, args.feedstocks_dir)


def _list_all_handle_args(args):
    if not args.cached and args.organization is None:
        print('ERROR: Organization must be specified unless '
              'cached flag is used. Use -h or --help for help.')
        return
    names = get_all_feedstocks(cached=args.cached,
                               organization=args.organization,
                               username=args.username,
                               token=args.token,
                               filepath=args.filepath,
                               include_archived=args.include_archived)
    names = sorted(names)
    if args.write:
        print(f'Writing names to {args.filepath}...')
        _write_list_to_file(names, args.filepath, sort=False)

    for name in names:
        print(name)
    print(f'Total feedstocks: {len(names)}')
