'''
This code is a rework of
https://github.com/regro/cf-scripts/blob/master/conda_forge_tick/all_feedstocks.py
This version was not importable so the functions had to be copied here.
We will be importing conda-smithy functionality.
'''
import datetime
import logging
import netrc

import github3

from nsls2forge_utils.io import _write_list_to_file, read_file_to_list

logger = logging.getLogger(__name__)


def get_all_feedstocks_from_github(organization=None, username=None, token=None,
                                   archived=False):
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
    archived: bool, optional
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
    gh = github3.login(username, token)
    org = gh.organization(organization)
    repos = org.repositories()
    names = []
    try:
        for repo in repos:
            if repo.archived and not archived:
                continue
            name = repo.name
            if name.endswith("-feedstock"):
                name = name.split("-feedstock")[0]
                logger.info(f'Found feedstock: {name}')
                names.append(name)
    except github3.GitHubError:
        msg = ["Github rate limited. "]
        c = gh.rate_limit()["resources"]["core"]
        if c["remaining"] == 0:
            ts = c["reset"]
            msg.append("API timeout, API returns at")
            msg.append(
                datetime.datetime.utcfromtimestamp(ts).strftime("%Y-%m-%dT%H:%M:%SZ"),
            )
        logger.warning(" ".join(msg))
        raise
    logger.info(f'Found {len(names)} feedstocks from {organization}.')
    return names


def get_all_feedstocks(cached=False, filepath='names.txt', **kwargs):
    '''
    Gets all feedstocks either from GitHub or from names.txt if flag is specified.

    Parameters
    ----------
    cached: bool, optional
        Specified if client wants to take repository names from names.txt.
    filepath: str, optional
        Path to file to read from if cached = True. Default value is 'names.txt'.
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
        logger.info(f"Reading names from cache ({filepath})")
        names = read_file_to_list(filepath)
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
    feedstocks.clone_all(gh_org=organization,
                         feedstocks_dir=feedstocks_dir)


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
                               archived=args.archived)
    names = sorted(names)
    if args.write:
        _write_list_to_file(names, args.filepath, sort=False)

    for name in names:
        print(name)
    print(f'Total feedstocks: {len(names)}')


def main(args=None):
    # TODO: move organization to global CONFIG file
    organization = 'nsls-ii-forge'
    names = get_all_feedstocks(cached=False, organization=organization)
    # write each repository name to a file
    _write_list_to_file(names, 'names.txt', sort=True)
    clone_all_feedstocks(organization, './feedstocks')


if __name__ == "__main__":
    main()
