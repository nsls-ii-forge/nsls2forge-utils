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


def get_all_feedstocks_from_github(organization, username=None, token=None):
    '''
    Gets all public feedstock repository names from the GitHub organization
    (e.g. nsls-ii-forge).

    Parameters
    ----------
    organization: str
        Name of organization on GitHub.
    username: str, optional
        Name of user on GitHub for authentication.
        Uses environment variables if not specified.
    password: str, optional
        Password of user on GitHub for authentication.
        Uses environment variables if not specified.

    Returns
    -------
    names: list
        List of repository names that end with '-feedstock' (stripped).
    '''
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


def get_all_feedstocks(organization=None, cached=False, **kwargs):
    '''
    Gets all feedstocks either from GitHub or from names.txt if flag is specified.

    Parameters
    ----------
    organization: str, optional
        Name of organization on GitHub. Optional only if cached = True.
    cached: bool, optional
        Specified if client wants to take repository names from names.txt.
    kwargs: dict, optional
        Username and token may be specified here for authentication.

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
    if organization is None:
        logger.info("No GitHub organization specified.")
        return None
    if 'username' in kwargs and 'token' in kwargs:
        username = kwargs['username']
        token = kwargs['token']
    else:
        username = None
        token = None
    names = get_all_feedstocks_from_github(organization, username=username, token=token)
    return names


def main(args=None):
    # TODO: move organization to global CONFIG file
    organization = 'nsls-ii-forge'
    names = get_all_feedstocks(organization, cached=False)
    # write each repository name to a file
    with open("names.txt", "w") as f:
        for name in names:
            f.write(f'{name}\n')


if __name__ == "__main__":
    main()
