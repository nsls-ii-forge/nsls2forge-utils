import datetime
import os
from typing import Any, List

import requests
import github3
import logging

logger = logging.getLogger(__name__)

def get_all_feedstocks_from_github() -> List[str]:
    org = github3.organization('nsls-ii-forge')
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


def get_all_feedstocks(cached: bool = False) -> List[str]:
    if cached:
        logger.info("reading names")
        with open("names.txt", "r") as f:
            names = f.read().split()
        return names

    names = get_all_feedstocks_from_github()
    return names


def main(args: Any = None) -> None:
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
        names = get_all_feedstocks(cached=False)
        with open("names_are_active.flag", "w") as fp:
            fp.write("no")

    with open("names.txt", "w") as f:
        for name in names:
            f.write(name)
            f.write("\n")


if __name__ == "__main__":
    main()
