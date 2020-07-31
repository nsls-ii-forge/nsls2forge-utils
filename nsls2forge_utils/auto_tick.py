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

import github3

from conda_forge_tick.git_utils import is_github_api_limit_reached
from conda_forge_tick.utils import (
    frozen_to_json_friendly,
    setup_logger,
    eval_cmd,
    dump_graph,
    load_graph
)
from conda_forge_tick.contexts import (
    MigratorContext,
    FeedstockContext,
    MigratorSessionContext
)
from conda_forge_tick.migrators import (
    Version,
    PipMigrator,
    LicenseMigrator,
    CondaForgeYAMLCleanup,
    ExtraJinja2KeysCleanup,
    Jinja2VarsCleanup,
)
from conda_forge_tick.auto_tick import (
    migration_factory,
    _compute_time_per_migrator,
    run
)

logger = logging.getLogger(__name__)

PR_LIMIT = 5
MAX_PR_LIMIT = 50

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


def initialize_migrators(github_username="", github_password="", github_token=None,
                         dry_run=False):
    temp = glob.glob("/tmp/*")
    gx = load_graph()
    smithy_version = eval_cmd("conda smithy --version").strip()
    pinning_version = json.loads(eval_cmd("conda list conda-forge-pinning --json"))[0][
        "version"
    ]
    migration_factory(MIGRATORS, gx)
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

    return ctx, temp, MIGRATORS


def auto_tick(**kwargs):
    # logging
    from conda_forge_tick.xonsh_utils import env

    debug = kwargs['debug']
    if debug:
        setup_logger(logger, level="debug")
    else:
        setup_logger(logger)

    github_username = env.get("USERNAME", "")
    github_password = env.get("PASSWORD", "")
    github_token = env.get("GITHUB_TOKEN")
    global MIGRATORS

    # ISSUE HERE WITH ../conda-forge-pinning-feedstock/recipe/migrations/arch_rebuild.txt
    mctx, temp, MIGRATORS = initialize_migrators(
        github_username=github_username,
        github_password=github_password,
        dry_run=kwargs['dry_run'],
        github_token=github_token,
    )

    # compute the time per migrator
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
                        kwargs['dry_run']
                        or mctx.gh.rate_limit()["resources"]["core"]["remaining"] == 0
                    ):
                        break
                    migrator_uid, pr_json = run(
                        feedstock_ctx=fctx,
                        migrator=migrator,
                        rerender=migrator.rerender,
                        protocol="https",
                        hash_type=attrs.get("hash_type", "sha256"),
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
                            if not pr_json:
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
                    if not kwargs['dry_run']:
                        dump_graph(mctx.graph)

                    eval_cmd(f"rm -rf {mctx.rever_dir}/*")
                    logger.info(os.getcwd())
                    for f in glob.glob("/tmp/*"):
                        if f not in temp:
                            eval_cmd(f"rm -rf {f}")

    if not kwargs['dry_run']:
        logger.info(
            "API Calls Remaining: %d",
            mctx.gh.rate_limit()["resources"]["core"]["remaining"],
        )
    logger.info("Done")


if __name__ == '__main__':
    auto_tick(dry_run=True, debug=True)
