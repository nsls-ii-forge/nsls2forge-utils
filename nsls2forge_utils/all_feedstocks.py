'''
This code is a rework of
https://github.com/regro/cf-scripts/blob/master/conda_forge_tick/all_feedstocks.py
for use by nsls-ii-forge's own auto-tick bot.
'''
import github3
import os
import datetime
import logging

logger = logging.getLogger(__name__)


def get_all_feedstocks_from_github(organization, **kwargs):
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
    if 'username' not in kwargs:
        username = os.environ['USERNAME']
    else:
        username = kwargs['username']
    if 'password' not in kwargs:
        password = os.environ['PASSWORD']
    else:
        password = kwargs['password']
    gh = github3.login(username, password)
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


def get_all_feedstocks(organization, username=None, password=None, cached=False):
    '''
    Gets all feedstocks either from GitHub or from names.txt if flag is specified.

    Parameters
    ----------
    organization: str
        Name of organization on GitHub.
    username: str, optional
        Name of user on GitHub for authentication.
        Uses environment variable if not specified.
    password: str, optional
        Password of user on GitHub for authentication.
        Uses environment variable if username not specified.
    cached: bool, optional
        Specified if client wants to take repository names from names.txt.

    Returns
    -------
    names: list or None
        List of repository names that end with '-feedstock' (stripped).
        None if no organization or username is specified.
    '''
    if cached:
        logger.info("reading names")
        with open("names.txt", "r") as f:
            names = f.read().split()
        return names
    if organization == '':
        logger.info("No GitHub organization specified.")
        return None
    names = get_all_feedstocks_from_github(organization, username=username, password=password)
    return names


def main(args=None):
    organization = 'nsls-ii-forge'
    names = get_all_feedstocks(organization, cached=False)
    # write each repository name to a file
    with open("names.txt", "w") as f:
        for name in names:
            f.write(f'{name}\n')


if __name__ == "__main__":
    main()
