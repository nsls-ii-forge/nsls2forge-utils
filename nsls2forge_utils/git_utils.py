'''
This is a rework of
https://github.com/regro/cf-scripts/blob/31ffe0333e9b53d4bce03818c5dee3f08559baea/conda_forge_tick/git_utils.py
Some of the code was not importable so the
function had to be copied and reimplemented here
'''
import time
import os

import github3
from conda_forge_tick.xonsh_utils import indir, env
from conda_forge_tick.git_utils import feedstock_repo
from conda_forge_tick.git_xonsh_utils import fetch_repo
from doctr.travis import run_command_hiding_token as doctr_run


def fork_url(feedstock_url, username, organization='nsls-ii-forge'):
    '''
    Replaces organization in GitHub URL with the username for a feedstock

    Parameters
    ----------
    feedstock_url: str
        URL of the feedstock repository on GitHub
    username: str
        GitHub user to replace organization in URL
    organization: str, optional
        GitHub organization to replace in URL. Default is
        nsls-ii-forge.
    '''
    beg, end = feedstock_url.rsplit("/", 1)
    beg = beg[:-len(organization)]  # chop off organization
    url = beg + username + "/" + end
    return url


def feedstock_url(fctx, organization='nsls-ii-forge', protocol="ssh"):
    '''
    Returns the URL for a feedstock repository on GitHub

    Parameters
    ----------
    fctx: FeedstockContext
        Node attributes of feedstock in dependency graph
    organization: str, optional
        GitHub organization to place in URL. Default is
        nsls-ii-forge
    protocol: str, optional
        The git protocol to use in the URL. Default is ssh.

    Returns
    -------
    url: str
        Git URL to feedstock repository on GitHub
    '''
    feedstock = fctx.feedstock_name + "-feedstock"
    if feedstock.startswith("http://github.com/"):
        return feedstock
    elif feedstock.startswith("https://github.com/"):
        return feedstock
    elif feedstock.startswith("git@github.com:"):
        return feedstock
    protocol = protocol.lower()
    if protocol == "http":
        url = f"http://github.com/{organization}/{feedstock}.git"
    elif protocol == "https":
        url = f"https://github.com/{organization}/{feedstock}.git"
    elif protocol == "ssh":
        url = f"git@github.com:{organization}/{feedstock}.git"
    else:
        msg = "Unrecognized github protocol {0!r}, must be ssh, http, or https."
        raise ValueError(msg.format(protocol))
    return url


def get_repo(ctx, fctx, branch, organization='nsls-ii-forge', feedstock=None,
             protocol="ssh", pull_request=True, fork=False):
    """
    Get the feedstock repo from the specified GitHub organization

    Parameters
    ----------
    ctx: MigratorSessionContext
        Context for GitHub interaction/authentication
    fctx: FeedstockContext
        Attributes of the feedstock from the dependency graph
    branch: str
        Remote branch name to use
    organization: str, optional
        GitHub organization to get repository from
    feedstock: str, optional
        The feedstock to clone, if None use $FEEDSTOCK
    protocol: str, optional
        The git protocol to use, defaults to ``ssh``
    pull_request: bool, optional
        If true issue pull request, defaults to true
    fork: bool, optional
        If true create a fork, defaults to false

    Returns
    -------
    tuple
        Feedstock directory and Repository object for the feedstock
    """
    gh = ctx.gh
    # first, let's grab the feedstock locally
    upstream = feedstock_url(fctx=fctx, protocol=protocol, organization=organization)
    if fork:
        origin = fork_url(upstream, ctx.github_username)
    else:
        origin = upstream
    feedstock_reponame = feedstock_repo(fctx=fctx)
    if pull_request or fork:
        repo = gh.repository(organization, feedstock_reponame)
        if repo is None:
            fctx.attrs["bad"] = f"{fctx.package_name}: does not match feedstock name\n"
            return False

    # Check if fork exists
    if fork:
        try:
            fork_repo = gh.repository(ctx.github_username, feedstock_reponame)
        except github3.GitHubError:
            fork_repo = None
        if fork_repo is None or (hasattr(fork_repo, "is_null") and fork_repo.is_null()):
            print(f"Fork of {feedstock_reponame} doesn't exist, "
                  f"creating feedstock fork under {ctx.github_username}...")
            repo.create_fork()
            # Sleep to make sure the fork is created before we go after it
            time.sleep(5)

    feedstock_dir = os.path.join(ctx.rever_dir, fctx.package_name + "-feedstock")

    if fetch_repo(
        feedstock_dir=feedstock_dir, origin=origin, upstream=upstream, branch=branch,
    ):
        return feedstock_dir, repo
    else:
        return None


def push_repo(session_ctx, fctx, feedstock_dir, body, repo, title, head, branch,
              fork=False, organization='nsls-ii-forge'):
    """
    Push a repository up to GitHub

    Parameters
    ----------
    session_ctx: MigratorSessionContext
        Context for GitHub interaction/authentication
    fctx: FeedstockContext
        Attributes of the feedstock from the dependency graph
    feedstock_dir: str
        The feedstock directory
    body: str
        The PR body
    repo: github3.Repository
        Object for GitHub API call
    title: str
        The PR title
    head: str
        Head branch name and user/org (ex. 'nsls-ii-forge:v1.0.1_h58425')
    branch: str
        The branch name (same one in head)
    fork: bool, optional
        Change deploy repository if fork was made. Default is False.
    organization: str, optional
        GitHub organization to deploy changes to. Default is nsls-ii-forge.

    Returns
    -------
    pr_json: dict
        The dict representing the PR, can be used with `from_json`
        to create a PR instance.
    """
    with indir(feedstock_dir), env.swap(RAISE_SUBPROC_ERROR=False):
        # Setup push from doctr
        # Copyright (c) 2016 Aaron Meurer, Gil Forsyth
        token = session_ctx.github_password
        if fork:
            deploy_repo = f'{session_ctx.github_username}/{fctx.feedstock_name}-feedstock'
        else:
            deploy_repo = f'{organization}/{fctx.feedstock_name}-feedstock'
        if session_ctx.dry_run:
            repo_url = f"https://github.com/{deploy_repo}.git"
            print(f"dry run: adding remote and pushing up branch for {repo_url}")
        else:
            doctr_run(
                [
                    "git",
                    "remote",
                    "add",
                    f"{organization}_remote",
                    f"https://{token}@github.com/{deploy_repo}.git",
                ],
                token=token.encode("utf-8"),
            )

            doctr_run(
                ["git", "push", "--set-upstream", f"{organization}_remote", branch],
                token=token.encode("utf-8"),
            )
    # lastly make a PR for the feedstock
    print(f"Creating {organization} feedstock pull request...")
    if session_ctx.dry_run:
        print(f"dry run: create pr with title: {title}")
        return None
    else:
        pr = repo.create_pull(title, "master", head, body=body)
        if pr is None:
            print(f"Failed to create pull request for {feedstock_dir}-feedstock!")
            return None
        else:
            print(f"Pull request created at {pr.html_url}")
    # Return a json object so we can remake the PR if needed
    pr_dict = pr.as_dict()
    return pr_dict
