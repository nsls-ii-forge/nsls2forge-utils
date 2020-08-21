'''
This code is a rework of
https://github.com/regro/cf-scripts/blob/master/conda_forge_tick/make_graph.py
This version was not completely importable so the functions had to be copied
here and reimplemented.
We still import some functionality from conda_forge_tick
'''
import re
import logging
import os
import time
from concurrent.futures import as_completed
from copy import deepcopy

import networkx as nx
from shutil import copyfile

from .all_feedstocks import get_all_feedstocks
from .io import _fetch_file

logger = logging.getLogger(__name__)
pin_sep_pat = re.compile(r" |>|<|=|\[")

MAX_WORKERS = 20
NUM_GITHUB_THREADS = 2
DEBUG = False


def get_attrs(name, organization):
    '''
    Generates node attributes for feedstocks from their recipe files

    Parameters
    ----------
    name: str
        Feedstock repo name to fetch recipe files from
    organization: str
        Name of GitHub organization containing feedstock repos.

    Returns
    -------
    lzj: LazyJson
        Dictionary containing feedstock attributes with ability to dump
        to a JSON file
    '''
    # These fetches could be done via async/multiprocessing
    from conda_forge_tick.make_graph import populate_feedstock_attributes
    from conda_forge_tick.utils import LazyJson
    meta_yaml = _fetch_file(organization, name, "recipe/meta.yaml")
    conda_forge_yaml = _fetch_file(organization, name, "conda-forge.yml")

    lzj = LazyJson(f"node_attrs/{name}.json")
    with lzj as sub_graph:
        populate_feedstock_attributes(
            name,
            sub_graph,
            meta_yaml=meta_yaml,
            conda_forge_yaml=conda_forge_yaml
        )
    return lzj


def _build_graph_process_pool(gx, names, new_names, organization):
    '''
    Builds feedstock dependency graph using multiprocessing.

    Parameters
    ----------
    gx: nx.DiGraph
        Directional graph to update/add nodes
    names: list
        Full list of feedstock repo names
    new_names: list
        Subset of names containing new feedstock repo names
    organization: str
        Name of GitHub organization containing feedstock repos.
    '''
    from conda_forge_tick.utils import executor
    with executor("thread", max_workers=MAX_WORKERS) as pool:
        futures = {
            pool.submit(get_attrs, name, organization): name
            for name in names
        }
        logger.info("submitted all nodes")

        n_tot = len(futures)
        n_left = len(futures)
        start = time.time()
        eta = -1
        for f in as_completed(futures):
            n_left -= 1
            if n_left % 10 == 0:
                eta = (time.time() - start) / (n_tot - n_left) * n_left
            name = futures[f]
            try:
                sub_graph = {"payload": f.result()}
                logger.info("itr % 5d - eta % 5ds: finished %s", n_left, eta, name)
            except Exception as e:
                logger.error(
                    "itr % 5d - eta % 5ds: Error adding %s to the graph: %s",
                    n_left,
                    eta,
                    name,
                    repr(e),
                )
            else:
                if name in new_names:
                    gx.add_node(name, **sub_graph)
                else:
                    gx.nodes[name].update(**sub_graph)


def _build_graph_sequential(gx, names, new_names, organization):
    '''
    Builds feedstock dependency graph. Useful for debugging.
    Use _build_graph_process_pool instead.

    Parameters
    ----------
    gx: nx.DiGraph
        Directional graph to update/add nodes.
    names: list
        Full list of feedstock repo names.
    new_names: list
        Subset of names containing new feedstock repo names.
    organization: str
        Name of GitHub organization containing feedstock repos.
    '''
    for name in names:
        try:
            sub_graph = {
                "payload": get_attrs(name, organization)
            }
        except Exception as e:
            logger.error(f"Error adding {name} to the graph: {e}")
        else:
            if name in new_names:
                gx.add_node(name, **sub_graph)
            else:
                gx.nodes[name].update(**sub_graph)


def make_graph(names, organization, gx=None):
    '''
    Creates/Updates a dependency graph based on names of packages.
    The dependency graph is used to decide which packages
    need to be upgraded before others.

    Parameters
    ----------
    names: list
        List of package names for placement into the graph.
    organization: str
        Name of GitHub organization containing feedstock repos.
    gx: nx.DiGraph, optional
        Dependency graph to be updated.

    Returns
    -------
    gx: nx.DiGraph()
        New/Updated dependency graph displaying the relationships
        between packages listed in names.
    '''
    from conda_forge_tick.utils import LazyJson
    logger.info("reading graph")
    if gx is None:
        print('Creating graph from scratch...')
        gx = nx.DiGraph()
    else:
        print('Updating graph with new packages...')
    new_names = [name for name in names if name not in gx.nodes]
    old_names = [name for name in names if name in gx.nodes]
    assert gx is not None
    old_names = sorted(old_names, key=lambda n: gx.nodes[n].get("time", 0))
    total_names = new_names + old_names
    logger.info("start feedstock fetch loop")
    print('Fetching feedstock attributes...')

    builder = _build_graph_sequential if DEBUG else _build_graph_process_pool
    builder(gx, total_names, new_names, organization)
    logger.info("feedstock fetch loop completed")
    print('Finished fetching feedstock attributes')

    gx2 = deepcopy(gx)
    logger.info("inferring nodes and edges")
    print('Creating nodes and edges...')
    # make the outputs look up table so we can link properly
    outputs_lut = {
        k: node_name
        for node_name, node in gx.nodes.items()
        for k in node.get("payload", {}).get("outputs_names", [])
    }
    # add this as an attr so we can use later
    gx.graph["outputs_lut"] = outputs_lut
    strong_exports = {
        node_name
        for node_name, node in gx.nodes.items()
        if node.get("payload").get("strong_exports", False)
    }
    # This drops all the edge data and only keeps the node data
    gx = nx.create_empty_copy(gx)
    # TODO: label these edges with the kind of dep they are and their platform
    for node, node_attrs in gx2.nodes.items():
        with node_attrs["payload"] as attrs:
            # replace output package names with feedstock names via LUT
            deps = set(
                map(
                    lambda x: outputs_lut.get(x, x),
                    set().union(*attrs.get("requirements", {}).values()),
                )
            )

            # handle strong run exports
            overlap = deps & strong_exports
            requirements = attrs.get("requirements")
            if requirements:
                requirements["host"].update(overlap)
                requirements["run"].update(overlap)

        for dep in deps:
            if dep not in gx.nodes:
                # for packages which aren't feedstocks and aren't outputs
                # usually these are stubs
                lzj = LazyJson(f"node_attrs/{dep}.json")
                lzj.update(feedstock_name=dep, bad=False, archived=True)
                gx.add_node(dep, payload=lzj)
            gx.add_edge(dep, node)
    logger.info("new nodes and edges infered")
    print('Dependency graph complete')
    return gx


def update_versions_in_graph(gx):
    '''
    Updates the version numbers for packages in the graph if new
    versions are available
    Stores result in directory ./versions/

    Parameters
    ----------
    gx: nx.DiGraph
        Dependency graph to be updated
    '''
    from conda_forge_tick.update_upstream_versions import update_upstream_versions
    from conda_forge_tick.make_graph import update_nodes_with_new_versions
    os.makedirs("versions", exist_ok=True)
    print('Fetching new versions from their sources...')
    update_upstream_versions(gx)
    print('Updating versions in dependency graph...')
    update_nodes_with_new_versions(gx)
    print('Finished')


def list_dependencies_on(gx, pkg_name):
    '''
    Provides a list of package names that require pkg_name to be installed
    in order to function correctly

    Parameters
    ----------
    gx: nx.DiGraph
        Directinal graph with nodes as packages and dependencies as edges
    pkg_name: str
        Name of software package

    Returns
    -------
    list
        List of package names that require pkg_name to be installed
    '''
    return list(gx.successors(pkg_name))


def list_dependencies_of(gx, pkg_name):
    '''
    Provides a list of package names that pkg_name requires to be installed
    in order to function correctly

    Parameters
    ----------
    gx: nx.DiGraph
        Directinal graph with nodes as packages and dependencies as edges
    pkg_name: str
        Name of software package

    Returns
    -------
    list
        List of package names that pkg_name requires to be installed
    '''
    return list(gx.predecessors(pkg_name))


def _make_graph_handle_args(args):
    from conda_forge_tick.utils import load_graph, dump_graph
    from conda_forge_tick.make_graph import update_nodes_with_bot_rerun
    # get a list of all feedstocks from nsls-ii-forge
    global DEBUG
    DEBUG = args.debug
    global MAX_WORKERS
    MAX_WORKERS = args.max_workers
    organization = args.organization
    names = get_all_feedstocks(cached=args.cached, filepath=args.filepath,
                               organization=organization)
    if os.path.exists("graph.json"):
        gx = load_graph()
    else:
        gx = None
    print(f'Using {MAX_WORKERS} workers in process pool')
    gx = make_graph(names, organization, gx=gx)
    print("nodes w/o payload:", [k for k, v in gx.nodes.items() if "payload" not in v])
    update_nodes_with_bot_rerun(gx)
    print('Saving graph to graph.json')
    dump_graph(gx)


def _query_graph_handle_args(args):
    from conda_forge_tick.utils import load_graph
    if args.filepath != 'graph.json':
        copyfile(args.filepath, 'graph.json')
    gx = load_graph()
    if args.query == 'depends_on':
        dependencies = list_dependencies_on(gx, args.package)
        print(f'The following packages require {args.package} to be installed:')
        for dep in dependencies:
            print(dep)
        print(f'Total: {len(dependencies)}')
    elif args.query == 'depends_of':
        dependencies = list_dependencies_of(gx, args.package)
        print(f'{args.package} requires the following packages to be installed:')
        for dep in dependencies:
            print(dep)
        print(f'Total: {len(dependencies)}')
    else:
        print(f'Unknown query type: {args.query}')


def _update_handle_args(args):
    from conda_forge_tick.utils import load_graph
    if args.filepath != 'graph.json':
        copyfile(args.filepath, 'graph.json')
    gx = load_graph()
    update_versions_in_graph(gx)
