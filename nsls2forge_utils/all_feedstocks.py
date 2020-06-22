import requests
import github3
import logging

logger = logging.getLogger(__name__)


def get_all_feedstocks_from_github(organization):
    '''
    Gets all public feedstock repository names from the nsls-ii-forge organization.


    Parameters
    ----------
    organization : str
        Name of organization on GitHub.

    Returns
    -------
    names : List
        List of repository names that end with '-feedstock' (stripped).
    '''
    org = github3.organization(organization)
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
        c = org.ratelimit_remaining()
        if c == 0:
            msg.append("API timeout.")
        logger.warning(" ".join(msg))
        raise
    return names


def get_all_feedstocks(organization, cached=False):
    '''
    Gets all feedstocks either from GitHub or from names.txt if flag is specified.

    Parameters
    ----------
    organization : str
        Name of organization on GitHub.
    cached : bool
        Specified if client wants to take repository names from names.txt.

    Returns
    -------
    names : List
        List of repository names that end with '-feedstock' (stripped).
    '''
    if cached:
        logger.info("reading names")
        with open("names.txt", "r") as f:
            names = f.read().split()
        return names

    names = get_all_feedstocks_from_github(organization)
    return names


def main(args=None):
    organization = 'nsls-ii-forge'
    # see if json exists for active feedstocks
    try:
        logger.info("fetching active feedstocks from admin-migrations")
        r = requests.get(
            "https://raw.githubusercontent.com/nsls-ii-forge/admin-migrations/"
            "master/data/all_feedstocks.json"
        )
        if r.status_code != 200:
            r.raise_for_status()

        names = r.json()["active"]
        with open("names_are_active.flag", "w") as fp:
            fp.write("yes")
    except Exception as e:
        logger.critical("admin-migrations all feedstocks failed: %s", repr(e))
        logger.critical("defaulting to the local version")
        names = get_all_feedstocks(organization, cached=False)
        with open("names_are_active.flag", "w") as fp:
            fp.write("no")

    # write each repository name to a file
    with open("names.txt", "w") as f:
        for name in names:
            f.write(name)
            f.write("\n")


if __name__ == "__main__":
    main()
