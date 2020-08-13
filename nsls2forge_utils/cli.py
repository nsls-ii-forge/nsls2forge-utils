import logging
logging.captureWarnings(True)
import argparse  # noqa: E402
import sys  # noqa: E402

from .check_results import check_conda_channels, check_package_version  # noqa: E402
from .meta_utils import get_attribute, download_from_source  # noqa: E402
from .all_feedstocks import (  # noqa: E402
    _list_all_handle_args,
    _clone_all_handle_args,
    _info_handle_args
)
from .dashboard import create_dashboard  # noqa: E402
from .graph_utils import (  # noqa: E402
    _make_graph_handle_args,
    _query_graph_handle_args,
    _update_handle_args
)


def check_results():
    parser = argparse.ArgumentParser(
        description='Check various parameters of a generated conda package.')

    types_of_check = ('channels', 'version')

    # Type of the check
    parser.add_argument('-t', '--check-type', dest='check_type',
                        choices=types_of_check, default=None,
                        help=(f'a type of check to perform. One of '
                              f'{", ".join(types_of_check)}'))

    # Check channels
    parser.add_argument('-f', '--forbidden-channel', dest='forbidden_channel',
                        default='conda-forge', type=str,
                        help=('a channel to warn about if it is found in the '
                              'package list in a conda environment'))
    parser.add_argument('-c', '--cmd', dest='cmd',
                        default='conda list --show-channel-url', type=str,
                        help=('a command to check a list of packages in a '
                              'conda environment'))

    # Ignore forbidden channel exception to continue execution
    parser.add_argument('-i', '--ignore-exception', dest='ignore_exception',
                        action='store_true',
                        help=('a flag to print the list of packages from the '
                              'channels which are forbidden and proceed '
                              'without exiting if set to True'))

    # Check versions
    parser.add_argument('-p', '--package', dest='package',
                        default=None, type=str,
                        help='a package to check the version for')
    parser.add_argument('-e', '--expected-version', dest='expected_version',
                        default=None, type=str,
                        help='minimum expected version of the package')

    args = parser.parse_args()

    if args.check_type is None:
        parser.print_help()

    if args.check_type == 'channels':
        channels_kwargs = {'forbidden_channel': args.forbidden_channel,
                           'cmd': args.cmd,
                           'ignore_exception': args.ignore_exception}
        check_conda_channels(**channels_kwargs)
    elif args.check_type == 'version':
        version_kwargs = {'package': args.package,
                          'expected_version': args.expected_version}
        check_package_version(**version_kwargs)


def all_feedstocks():
    parser = argparse.ArgumentParser(
        description=('List/Clone all feedstock repositories from cache or GitHub '))

    # Give GitHub organization name
    parser.add_argument('-o', '--organization', dest='organization',
                        default=None, type=str,
                        help=('GitHub organization to get feedstocks from '
                              '(must be specified if not cached)'))

    subparsers = parser.add_subparsers(help='sub-command help')
    # Subparser for 'list' command
    list_parser = subparsers.add_parser('list',
                                        help=('lists all feedstocks from cache '
                                              'or GitHub'))
    # Give GitHub username and token
    list_parser.add_argument('-u', '--username', dest='username',
                             default=None, type=str,
                             help=('GitHub username for authentication. '
                                   'Uses ~/.netrc by default'))
    list_parser.add_argument('-t', '--token', dest='token',
                             default=None, type=str,
                             help=('GitHub token for authentication. '
                                   'Uses ~/.netrc by default'))

    # Set file path
    list_parser.add_argument('-f', '--filepath', dest='filepath',
                             default='names.txt', type=str,
                             help=('filepath to write feedstock names to '
                                   '(default is names.txt)'))
    # write to file flag
    list_parser.add_argument('-w', '--write', dest='write',
                             action='store_true',
                             help=('writes the feedstock names to a file.'))

    # Set cached to true
    list_parser.add_argument('-c', '--cached', dest='cached',
                             action='store_true',
                             help=('read the names of feedstocks from the cache'))

    list_parser.add_argument('-a', '--include-archived', dest='include_archived',
                             action='store_true',
                             help=('Includes archived feedstocks in returned list '
                                   'when set to True.'))

    # Set function to handle arguments
    list_parser.set_defaults(func=_list_all_handle_args)

    # Subparser for 'clone' command
    clone_parser = subparsers.add_parser('clone',
                                         help=('Clones all feedstocks from GitHub. '
                                               'Uses ~/.conda-smithy/github.token for '
                                               'authentication'))

    # Set feedstock dir to clone to
    clone_parser.add_argument('-f', '--feedstocks-dir', dest='feedstocks_dir',
                              default='./feedstocks', type=str,
                              help=('Directory to clone feedstocks to. Default is '
                                    './feedstocks'))

    # Set function to handle arguments
    clone_parser.set_defaults(func=_clone_all_handle_args)

    info_parser = subparsers.add_parser('info',
                                        help=('Gathers and prints version and other Git '
                                              'info about all currently cloned feedstocks'))

    info_parser.add_argument('-f', '--feedstocks-dir', dest='feedstocks_dir',
                             default='./feedstocks/', type=str,
                             help=('Directory where cloned feedstocks are; '
                                   'default is ./feedstocks/'))

    info_parser.set_defaults(func=_info_handle_args)

    args = parser.parse_args()

    # check for no arguments and print help
    if len(sys.argv) == 1:
        parser.print_help()
        parser.exit(message='Please specify organization and sub-command...\n')

    args.func(args)


def meta_utils():
    parser = argparse.ArgumentParser(
        description=('Extract and operate on information from meta.yaml '
                     'feedstock files'))

    # Get attribute from meta.yaml
    parser.add_argument('-g', '--get', dest='attributes',
                        nargs='+',
                        help=('Get an attribute from meta.yaml file '))

    # Download package flag
    parser.add_argument('-d', '--download', dest='download',
                        action='store_true',
                        help=('Dowload source tar.gz file for package'))

    # Give GitHub organization name
    parser.add_argument('-o', '--organization', dest='organization',
                        default=None, type=str,
                        help=('GitHub organization to get feedstocks from '
                              '(must be specified if not cached)'))

    # Package name
    parser.add_argument('-p', '--package', dest='package',
                        default=None, type=str,
                        help=('Software package name with feedstock available'))

    # Cached flag
    parser.add_argument('-c', '--cached', dest='cached',
                        action='store_true',
                        help=('Specify to use cached feedstock. Must be '
                              'in feedstocks/ dir in current working directory. '
                              'Works well with default behavior of all-feedstocks clone'))

    args = parser.parse_args()
    if args.download:
        url, sha256 = download_from_source(args.package,
                                           organization=args.organization,
                                           cached=args.cached)
        print(f'Successfully downloaded {url}\nsha256: {sha256}')
    else:
        args.attributes = ' '.join(args.attributes)
        attr = get_attribute(args.attributes, args.package,
                             organization=args.organization,
                             cached=args.cached)
        print(f'{args.attributes}: {attr}')


def dashboard():
    parser = argparse.ArgumentParser(
        description='Create a dashboard of feedstocks belonging to nsls-ii-forge')

    parser.add_argument('-n', '--names', dest='names',
                        default=None, type=str,
                        help=('filepath to text file containing feedstock repo names '
                              'without the -feedstock suffix (optional)'))

    parser.add_argument('-w', '--write', dest='write',
                        default='README.md', type=str,
                        help=('filepath to markdown file to write output to'))

    args = parser.parse_args()

    create_dashboard(names=args.names)


def graph_utils():
    parser = argparse.ArgumentParser(
        description=('Create a dependency graph of feedstock packages '
                     'or query information from an existing one'))

    subparsers = parser.add_subparsers(help='sub-command help')

    make_parser = subparsers.add_parser('make',
                                        help='Create a dependency graph')

    make_parser.add_argument('-o', '--organization', dest='organization',
                             default=None, type=str,
                             help=('GitHub organization to get recipe files from'))

    make_parser.add_argument('-c', '--cached', dest='cached',
                             action='store_true',
                             help=('Specify if feedstock names are to be pulled from '
                                   'a text file'))

    make_parser.add_argument('-f', '--filepath', dest='filepath',
                             default='names.txt', type=str,
                             help=('Path to text file containing feedstock names'))

    make_parser.add_argument('-d', '--debug', dest='debug',
                             action='store_true',
                             help=('Specify to create graph sequentially instead of in '
                                   'parallel'))

    make_parser.add_argument('-m', '--max-workers', dest='max_workers',
                             default=20, type=int,
                             help=('Maximum number of workers in process pool to build graph '
                                   '(default is 20)'))

    make_parser.set_defaults(func=_make_graph_handle_args)

    info_parser = subparsers.add_parser('info',
                                        help=('Query information from existing graph'))

    info_parser.add_argument('-f', '--filepath', dest='filepath',
                             default='graph.json', type=str,
                             help=('Path to JSON file where the graph is stored'))

    info_parser.add_argument('-p', '--package', dest='package',
                             default=None, type=str,
                             help=('Package to get information about'))

    info_parser.add_argument('-q', '--query', dest='query',
                             choices=['depends_on', 'depends_of'], default=None,
                             type=str,
                             help=('Type of information to get from the graph'))

    info_parser.set_defaults(func=_query_graph_handle_args)

    update_parser = subparsers.add_parser('update',
                                          help=('Update package versions in graph from '
                                                'various sources'))

    update_parser.add_argument('-f', '--filepath', dest='filepath',
                               default='graph.json', type=str,
                               help=('Path to JSON file where the graph is stored'))

    update_parser.set_defaults(func=_update_handle_args)

    args = parser.parse_args()

    args.func(args)


def auto_tick():
    from .auto_tick import (
        _status_handle_args,
        _run_handle_args,
        _clean_handle_args
    )
    parser = argparse.ArgumentParser(
        description=('Issues PRs if packages are out of date or need to be migrated'))

    subparsers = parser.add_subparsers(help='sub-command help')

    run_parser = subparsers.add_parser('run', help='Run migrations and issue PRs')

    run_parser.add_argument('-d', '--debug', dest='debug',
                            action='store_true',
                            help=('Run migrations in debug mode (more verbose)'))

    run_parser.add_argument('--dry-run', dest='dry_run',
                            action='store_true',
                            help=('Perform the migrations without making changes or '
                                  'issuing PRs'))

    run_parser.add_argument('-f', '--fork', dest='fork',
                            action='store_true',
                            help=('Create fork of feedstock repositories'))

    run_parser.add_argument('-o', '--organization', dest='organization',
                            default='nsls-ii-forge', type=str,
                            help=('GitHub organization to perform migrations on'))

    run_parser.set_defaults(func=_run_handle_args)

    status_parser = subparsers.add_parser('status', help='Get status of current migrations/PRs')

    status_parser.set_defaults(func=_status_handle_args)

    clean_parser = subparsers.add_parser('clean', help=('Clean current directory of files needed '
                                                        'to run the bot'))

    clean_parser.add_argument('-i', '--include', dest='include',
                              type=str, nargs='+', default=None,
                              help=('List of files to be removed. Default are those associated '
                                    'with running the bot from scratch'))

    clean_parser.add_argument('-e', '--exclude', dest='exclude',
                              type=str, nargs='+', default=None,
                              help=('Files to keep if already included either by default or by user'))

    clean_parser.add_argument('-y', '--yes', dest='yes',
                              action='store_true',
                              help=('Skip question to proceed with removal'))

    clean_parser.set_defaults(func=_clean_handle_args)

    args = parser.parse_args()

    args.func(args)
