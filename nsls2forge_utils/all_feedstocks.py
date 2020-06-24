'''
This code is a rework of
https://github.com/regro/cf-scripts/blob/master/conda_forge_tick/all_feedstocks.py
for use by nsls-ii-forge's own auto-tick bot.
'''
import datetime
import logging
import netrc

import github3

logger = logging.getLogger(__name__)


def get_all_feedstocks_from_github(organization=None, username=None, token=None):
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
            name = repo.name
            if name.endswith("-feedstock"):
                name = name.split("-feedstock")[0]
                logger.info(name)
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
    return names


def get_all_feedstocks(cached=False, **kwargs):
    '''
    Gets all feedstocks either from GitHub or from names.txt if flag is specified.

    Parameters
    ----------
    cached: bool, optional
        Specified if client wants to take repository names from names.txt.
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
        logger.info("reading names")
        with open("names.txt", "r") as f:
            names = f.read().split()
        return names
    names = get_all_feedstocks_from_github(**kwargs)
    return names


def main(args=None):
    # TODO: move organization to global CONFIG file
    organization = 'nsls-ii-forge'
    names = get_all_feedstocks(cached=False, organization=organization)
    # write each repository name to a file
    with open("names.txt", "w") as f:
        for name in names:
            f.write(f'{name}\n')


if __name__ == "__main__":
    main()
