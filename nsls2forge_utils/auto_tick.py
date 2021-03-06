'''
This code is a rework of
https://github.com/regro/cf-scripts/blob/master/conda_forge_tick/auto_tick.py
This version was not completely importable so the functions had to be copied
here and reimplemented.
We still import some functionality from conda_forge_tick
'''
import logging
import time
import os
import glob
from urllib.error import URLError
import traceback
import json
from uuid import uuid4
from subprocess import SubprocessError, CalledProcessError
import shutil

import github3
import networkx as nx

from conda_forge_tick.utils import (
    frozen_to_json_friendly,
    setup_logger,
    eval_cmd,
    dump_graph,
    load_graph,
    LazyJson
)
from conda_forge_tick.contexts import (
    MigratorContext,
    FeedstockContext,
    MigratorSessionContext
)
from conda_forge_tick.migrators import (
    Version,
    PipMigrator,
    MigrationYaml,
    LicenseMigrator,
    CondaForgeYAMLCleanup,
    ExtraJinja2KeysCleanup,
    Jinja2VarsCleanup,
)
from conda_forge_tick.auto_tick import (
    _compute_time_per_migrator,
)
from conda_forge_tick.status_report import write_version_migrator_status
from conda_forge_tick.git_utils import is_github_api_limit_reached
from conda_forge_tick.xonsh_utils import indir, env
from conda_forge_tick.mamba_solver import is_recipe_solvable

from .git_utils import (
    get_repo,
    push_repo
)
from .dashboard import create_dashboard_from_list

logger = logging.getLogger(__name__)

# change to increase PRs/run of the bot
# NOTE: this number gets doubled for Version migrations
PR_LIMIT = 5
MAX_PR_LIMIT = 50

# Set up types of migrators here
MIGRATORS = [
    Version(
        pr_limit=PR_LIMIT * 2,
        piggy_back_migrations=[
            Jinja2VarsCleanup(),
            PipMigrator(),
            LicenseMigrator(),
            CondaForgeYAMLCleanup(),
            ExtraJinja2KeysCleanup(),
        ],
    ),
]

BOT_RERUN_LABEL = {
    "name": "bot-rerun",
    "color": "#191970",
    "description": (
        "Apply this label if you want the bot to retry "
        "issuing a particular pull-request"
    ),
}


def bot_pr_body(self, feedstock_ctx):
    '''
    Creates the body text of a version pull request
    Used to overwrite conda_forge_tick.migrators.Version.pr_body function

    Parameters
    ----------
    feedstock_ctx: FeedstockContext
        The node attributes of the current feedstock

    Returns
    -------
    str
        Body text of pull request on GitHub for new version releases
    '''
    pred = [
        name
        for name in list(
            self.ctx.effective_graph.predecessors(feedstock_ctx.package_name),
        )
    ]
    # TODO: note that the closing logic needs to be modified when we
    #  issue PRs into other branches for backports
    open_version_prs = [
        muid["PR"]
        for muid in feedstock_ctx.attrs.get("PRed", [])
        if muid["data"].get("migrator_name") == "Version"
        # The PR is the actual PR itself
        and muid.get("PR", {}).get("state", None) == "open"
    ]

    # Display the url so that the maintainer can quickly click on it
    # in the PR body.
    about = feedstock_ctx.attrs.get("meta_yaml", {}).get("about", {})
    upstream_url = about.get("dev_url", "") or about.get("home", "")
    if upstream_url:
        upstream_url_link = ": see [upstream]({upstream_url})".format(
            upstream_url=upstream_url,
        )
    else:
        upstream_url_link = ""

    body = (
        "It is very likely that the current package version for this "
        "feedstock is out of date.\n"
        "Notes for merging this PR:\n"
        "1. Feel free to push to the bot's branch to update this PR if needed.\n"
        "2. The bot will almost always only open one PR per version.\n"
        "Checklist before merging this PR:\n"
        "- [ ] Dependencies have been updated if changed{upstream_url_link}\n"
        "- [ ] Tests have passed \n"
        "- [ ] Updated license if changed and `license_file` is packaged \n"
        "\n"
        "Note that the bot will stop issuing PRs if more than {max_num_prs} "
        "Version bump PRs "
        "generated by the bot are open. If you don't want to package a particular "
        "version please close the PR.\n\n"
        "{closes}".format(
            upstream_url_link=upstream_url_link,
            max_num_prs=self.max_num_prs,
            closes="\n".join(
                [f"Closes: #{muid['number']}" for muid in open_version_prs],
            ),
        )
    )
    # Statement here
    curr_pkg_name = feedstock_ctx.package_name
    pred.insert(0, curr_pkg_name)
    body += (
        "\n\nHere is a list of all the pending dependencies (and their "
        "versions) for this repo. The first package is the current feedstock package. "
        "Please double check all dependencies before merging.\n\n"
    )
    body += create_dashboard_from_list(pred)
    return body


def run(feedstock_ctx, migrator, protocol='ssh', pull_request=True,
        rerender=True, fork=False, organization='nsls-ii-forge', **kwargs):
    """
    For a given feedstock and migration run the migration and possibly submit
    pull request

    Parameters
    ----------
    feedstock_ctx: FeedstockContext
        The node attributes of the feedstock
    migrator: Migrator
        The migrator to run on the feedstock
    protocol: str, optional
        The git protocol to use, defaults to ``ssh``
    pull_request: bool, optional
        If true issue pull request, defaults to true
    rerender: bool
        Whether to rerender, defaults to true
    fork: bool
        If true create a fork, defaults to false
    organization: str, optional
        GitHub organization to get repo from
    gh: github3.GitHub, optional
        Object for communicating with GitHub, if None, build from $GITHUB_USERNAME
        and $GITHUB_PASSWORD, defaults to None
    kwargs: dict
        The key word arguments to pass to the migrator

    Returns
    -------
    migrate_return: MigrationUidTypedDict
        The migration return dict used for tracking finished migrations
    pr_json: dict
        The PR json object for recreating the PR as needed
    """
    # get the repo
    migrator.attrs = feedstock_ctx.attrs

    branch_name = migrator.remote_branch(feedstock_ctx) + "_h" + uuid4().hex[:6]

    # TODO: run this in parallel
    feedstock_dir, repo = get_repo(
        ctx=migrator.ctx.session,
        fctx=feedstock_ctx,
        branch=branch_name,
        organization=organization,
        feedstock=feedstock_ctx.feedstock_name,
        protocol=protocol,
        pull_request=pull_request,
        fork=fork,

    )

    recipe_dir = os.path.join(feedstock_dir, "recipe")

    # migrate the feedstock
    migrator.run_pre_piggyback_migrations(recipe_dir, feedstock_ctx.attrs, **kwargs)

    # TODO - make a commit here if the repo changed

    migrate_return = migrator.migrate(recipe_dir, feedstock_ctx.attrs, **kwargs)

    if not migrate_return:
        logger.critical(
            "Failed to migrate %s, %s",
            feedstock_ctx.package_name,
            feedstock_ctx.attrs.get("bad"),
        )
        eval_cmd(f"rm -rf {feedstock_dir}")
        return False, False

    # TODO - commit main migration here

    migrator.run_post_piggyback_migrations(recipe_dir, feedstock_ctx.attrs, **kwargs)

    # TODO commit post migration here

    # rerender, maybe
    diffed_files = []
    with indir(feedstock_dir), env.swap(RAISE_SUBPROC_ERROR=False):
        msg = migrator.commit_message(feedstock_ctx)  # noqa
        try:
            eval_cmd("git add --all .")
            eval_cmd(f"git commit -am '{msg}'")
        except CalledProcessError as e:
            logger.info(
                "could not commit to feedstock - "
                "likely no changes - error is '%s'" % (repr(e)),
            )
        if rerender:
            head_ref = eval_cmd("git rev-parse HEAD").strip()
            logger.info("Rerendering the feedstock")

            # In the event we can't rerender, try to update the pinnings,
            # then bail if it does not work again
            try:
                eval_cmd(
                    "conda smithy rerender -c auto --no-check-uptodate", timeout=300,
                )
            except SubprocessError:
                return False, False

            # If we tried to run the MigrationYaml and rerender did nothing (we only
            # bumped the build number and dropped a yaml file in migrations) bail
            # for instance platform specific migrations
            gdiff = eval_cmd(f"git diff --name-only {head_ref.strip()}...HEAD")

            diffed_files = [
                _
                for _ in gdiff.split()
                if not (
                    _.startswith("recipe")
                    or _.startswith("migrators")
                    or _.startswith("README")
                )
            ]

    if (
        (
            migrator.check_solvable
            and feedstock_ctx.attrs["conda-forge.yml"].get("bot", {}).get("automerge")
        )
        or feedstock_ctx.attrs["conda-forge.yml"]
        .get("bot", {})
        .get("check_solvable", False)
    ) and not is_recipe_solvable(feedstock_dir):
        eval_cmd(f"rm -rf {feedstock_dir}")
        return False, False

    if (
        isinstance(migrator, MigrationYaml)
        and not diffed_files
        and feedstock_ctx.attrs["name"] != "conda-forge-pinning"
    ):
        # spoof this so it looks like the package is done
        pr_json = {
            "state": "closed",
            "merged_at": "never issued",
            "id": str(uuid4()),
        }
    else:
        # push up
        try:
            if fork:
                head = f"{migrator.ctx.github_username}:{branch_name}"
            else:
                head = f"{organization}:{branch_name}"
            pr_json = push_repo(
                session_ctx=migrator.ctx.session,
                fctx=feedstock_ctx,
                feedstock_dir=feedstock_dir,
                body=migrator.pr_body(feedstock_ctx),
                repo=repo,
                title=migrator.pr_title(feedstock_ctx),
                head=head,
                branch=branch_name,
                fork=fork,
                organization=organization
            )

        # This shouldn't happen too often any more since we won't double PR
        except github3.GitHubError as e:
            if e.msg != "Validation Failed":
                raise
            else:
                print(f"Error during push {e}")
                print(f'Errors: {e.errors}')
                # If we just push to the existing PR then do nothing to the json
                pr_json = None
                ljpr = None
    if pr_json is not None:
        ljpr = LazyJson(
            os.path.join(migrator.ctx.session.prjson_dir, str(pr_json["id"]) + ".json"),
        )
        ljpr.update(**pr_json)
    else:
        ljpr = None
    # If we've gotten this far then the node is good
    feedstock_ctx.attrs["bad"] = False
    logger.info("Removing feedstock dir")
    eval_cmd(f"rm -rf {feedstock_dir}")
    return migrate_return, ljpr


def initialize_migrators(github_username="", github_password="", github_token=None,
                         dry_run=False):
    '''
    Setup graph, required contexts, and migrators

    Parameters
    ----------
    github_username: str, optional
        Username for bot on GitHub
    github_password: str, optional
        Password for bot on GitHub
    github_token: str, optional
        Token for bot on GitHub
    dry_run: bool, optional
        If true, does not submit pull requests on GitHub

    Returns
    -------
    tuple
        Migrator session to interact with GitHub and list of migrators.
        Currently only returns pre-defined migrators.
    '''
    gx = load_graph()
    smithy_version = eval_cmd("conda smithy --version").strip()
    pinning_version = json.loads(eval_cmd("conda list conda-forge-pinning --json"))[0][
        "version"
    ]
    for m in MIGRATORS:
        print(f'{getattr(m, "name", m)} graph size: {len(getattr(m, "graph", []))}')

    ctx = MigratorSessionContext(
        circle_build_url=os.getenv("CIRCLE_BUILD_URL", ""),
        graph=gx,
        smithy_version=smithy_version,
        pinning_version=pinning_version,
        github_username=github_username,
        github_password=github_password,
        github_token=github_token,
        dry_run=dry_run,
    )

    return ctx, MIGRATORS


def auto_tick(dry_run=False, debug=False, fork=False, organization='nsls-ii-forge'):
    '''
    Automatically update package versions and submit pull requests to
    associated feedstocks

    Parameters
    ----------
    dry_run: bool, optional
        Generate version migration yamls but do not run them
    debug: bool, optional
        Setup logging to be in debug mode
    fork: bool, optional
        Create a fork of the repo from the organization to $GITHUB_USERNAME
    organization: str, optional
        GitHub organization that manages feedstock repositories
    '''
    from conda_forge_tick.xonsh_utils import env

    if debug:
        setup_logger(logger, level="debug")
    else:
        setup_logger(logger)

    # set Version.pr_body to custom pr_body function
    Version.pr_body = bot_pr_body

    # TODO: use ~/.netrc instead
    github_username = env.get("GITHUB_USERNAME", "")
    github_password = env.get("GITHUB_TOKEN", "")
    github_token = env.get("GITHUB_TOKEN")
    global MIGRATORS

    print('Initializing migrators...')
    mctx, MIGRATORS = initialize_migrators(
        github_username=github_username,
        github_password=github_password,
        dry_run=dry_run,
        github_token=github_token,
    )

    # compute the time per migrator
    print('Computing time per migrator')
    (num_nodes, time_per_migrator, tot_time_per_migrator) = _compute_time_per_migrator(
        mctx,
    )
    for i, migrator in enumerate(MIGRATORS):
        if hasattr(migrator, "name"):
            extra_name = "-%s" % migrator.name
        else:
            extra_name = ""

        logger.info(
            "Total migrations for %s%s: %d - gets %f seconds (%f percent)",
            migrator.__class__.__name__,
            extra_name,
            num_nodes[i],
            time_per_migrator[i],
            time_per_migrator[i] / tot_time_per_migrator * 100,
        )

    print('Performing migrations...')
    for mg_ind, migrator in enumerate(MIGRATORS):

        mmctx = MigratorContext(session=mctx, migrator=migrator)
        migrator.bind_to_ctx(mmctx)

        good_prs = 0
        _mg_start = time.time()
        effective_graph = mmctx.effective_graph
        time_per = time_per_migrator[mg_ind]

        if hasattr(migrator, "name"):
            extra_name = "-%s" % migrator.name
        else:
            extra_name = ""

        logger.info(
            "Running migrations for %s%s: %d",
            migrator.__class__.__name__,
            extra_name,
            len(effective_graph.nodes),
        )

        possible_nodes = list(migrator.order(effective_graph, mctx.graph))

        # version debugging info
        if isinstance(migrator, Version):
            logger.info("possible version migrations:")
            for node_name in possible_nodes:
                with effective_graph.nodes[node_name]["payload"] as attrs:
                    logger.info(
                        "    node|curr|new|attempts: %s|%s|%s|%d",
                        node_name,
                        attrs.get("version"),
                        attrs.get("new_version"),
                        (
                            attrs.get("new_version_attempts", {}).get(
                                attrs.get("new_version", ""), 0,
                            )
                        ),
                    )

        for node_name in possible_nodes:
            with mctx.graph.nodes[node_name]["payload"] as attrs:
                # Don't let CI timeout, break ahead of the timeout so we make certain
                # to write to the repo
                # TODO: convert these env vars
                _now = time.time()
                if (
                    (
                        _now - int(env.get("START_TIME", time.time()))
                        > int(env.get("TIMEOUT", 600))
                    )
                    or good_prs >= migrator.pr_limit
                    or (_now - _mg_start) > time_per
                ):
                    break

                fctx = FeedstockContext(
                    package_name=node_name,
                    feedstock_name=attrs["feedstock_name"],
                    attrs=attrs,
                )

                print("\n", flush=True, end="")
                logger.info(
                    "%s%s IS MIGRATING %s",
                    migrator.__class__.__name__.upper(),
                    extra_name,
                    fctx.package_name,
                )
                try:
                    # Don't bother running if we are at zero
                    if (
                        dry_run
                        or mctx.gh.rate_limit()["resources"]["core"]["remaining"] == 0
                    ):
                        break
                    migrator_uid, pr_json = run(
                        feedstock_ctx=fctx,
                        migrator=migrator,
                        rerender=migrator.rerender,
                        protocol="https",
                        hash_type=attrs.get("hash_type", "sha256"),
                        fork=fork,
                        organization=organization
                    )
                    # if migration successful
                    if migrator_uid:
                        d = frozen_to_json_friendly(migrator_uid)
                        # if we have the PR already do nothing
                        if d["data"] in [
                            existing_pr["data"] for existing_pr in attrs.get("PRed", [])
                        ]:
                            pass
                        else:
                            if pr_json is None:
                                pr_json = {
                                    "state": "closed",
                                    "head": {"ref": "<this_is_not_a_branch>"},
                                }
                            d["PR"] = pr_json
                            attrs.setdefault("PRed", []).append(d)
                        attrs.update(
                            {
                                "smithy_version": mctx.smithy_version,
                                "pinning_version": mctx.pinning_version,
                            },
                        )

                except github3.GitHubError as e:
                    if e.msg == "Repository was archived so is read-only.":
                        attrs["archived"] = True
                    else:
                        logger.critical(
                            "GITHUB ERROR ON FEEDSTOCK: %s", fctx.feedstock_name,
                        )
                        if is_github_api_limit_reached(e, mctx.gh):
                            break
                except URLError as e:
                    logger.exception("URLError ERROR")
                    attrs["bad"] = {
                        "exception": str(e),
                        "traceback": str(traceback.format_exc()).split("\n"),
                        "code": getattr(e, "code"),
                        "url": getattr(e, "url"),
                    }
                except Exception as e:
                    logger.exception("NON GITHUB ERROR")
                    attrs["bad"] = {
                        "exception": str(e),
                        "traceback": str(traceback.format_exc()).split("\n"),
                    }
                else:
                    if migrator_uid:
                        # On successful PR add to our counter
                        good_prs += 1
                finally:
                    # Write graph partially through
                    if not dry_run:
                        dump_graph(mctx.graph)

                    eval_cmd(f"rm -rf {mctx.rever_dir}/*")
                    logger.info(os.getcwd())

    if not dry_run:
        logger.info(
            "API Calls Remaining: %d",
            mctx.gh.rate_limit()["resources"]["core"]["remaining"],
        )
    logger.info("Done")


def status_report():
    '''
    Write out the status of current/recent migrations and their
    pull requests on GitHub.

    Only works for Version migrations at the moment.
    '''
    print('Determining current status of migrations...')
    mctx, *_, migrators = initialize_migrators()
    if not os.path.exists("./status"):
        os.mkdir("./status")

    for migrator in migrators:
        if isinstance(migrator, Version):
            write_version_migrator_status(migrator, mctx)

    lst = [
        k
        for k, v in mctx.graph.nodes.items()
        if len(
            [
                z
                for z in v.get("payload", {}).get("PRed", [])
                if z.get("PR", {}).get("state", "closed") == "open"
                and z.get("data", {}).get("migrator_name", "") == "Version"
            ],
        )
        >= Version.max_num_prs
    ]
    with open("./status/could_use_help.json", "w") as f:
        json.dump(
            sorted(
                lst,
                key=lambda z: (len(nx.descendants(mctx.graph, z)), lst),
                reverse=True,
            ),
            f,
            indent=2,
        )
    print('Statuses have been placed in ./status')


def clean(include=None, exclude=None, yes=False):
    '''
    Cleans the current directory for a fresh run of the
    graph building and auto-tick process.

    Parameters
    ----------
    include: list, optional
        Files to be removed (default is all files required
        by the bot except names.txt)
    exclude: list, optional
        Files to keep if already included either by default
        or by user
    yes: bool, optional
        Automatically proceed with deletion if True
    '''
    to_be_removed = [
        './dask-worker-space/*',
        './node_attrs/*',
        './feedstocks/*',
        './pr_json/*',
        './versions/*',
        './status/*',
        'graph.json'
    ]
    to_be_removed = set(to_be_removed)
    if include is not None:
        include = set(include)
        to_be_removed = to_be_removed.union(include)
    if exclude is not None:
        exclude = set(exclude)
        to_be_removed = to_be_removed.difference(exclude)
    to_be_removed = list(to_be_removed)
    rm_string = '\n'.join(to_be_removed)
    warn_msg = (
        'WARNING: This will delete all files associated with creating the graph.\n'
        'This includes:\n\n'
        f'{rm_string}\n\n'
        'If you would like to exclude some file that is included, please run:\n'
        'auto-tick clean --exclude FILE1 FILE2\n\n'
        'If you would like to include some file that is excluded, please run:\n'
        'auto-tick clean --include FILE1 FILE2\n\n'
        'NOTE: If the same file exists in both include and exclude it will NOT be removed.'
    )
    print(warn_msg)
    if not yes:
        while not yes:
            yes_str = input('Do you want to continue? (y/n)\n')
            yes_str = yes_str.lower()[0]
            if yes_str == 'n':
                print('Aborting...')
                return
            elif yes_str == 'y':
                yes = True
    print('Removing files...')
    for path in to_be_removed:
        files = glob.glob(path, recursive=True)
        for file in files:
            try:
                os.remove(file)
            except IsADirectoryError:
                shutil.rmtree(file)
    print('Included files have been removed.')


def _run_handle_args(args):
    auto_tick(dry_run=args.dry_run, debug=args.debug, fork=args.fork,
              organization=args.organization)


def _status_handle_args(args):
    status_report()


def _clean_handle_args(args):
    clean(include=args.include, exclude=args.exclude, yes=args.yes)


if __name__ == '__main__':
    auto_tick(dry_run=True, debug=False)
