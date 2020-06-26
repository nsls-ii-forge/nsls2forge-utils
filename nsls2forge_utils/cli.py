import argparse

from .check_results import check_conda_channels, check_package_version
from .all_feedstocks import _list_all_handle_args, _clone_all_handle_args


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
                           'cmd': args.cmd}
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
                             help=('GitHub username for authentication'))
    list_parser.add_argument('-t', '--token', dest='token',
                             default=None, type=str,
                             help=('GitHub token for authentication'))

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
                              help=('directory to clone feedstocks to'))

    # Set function to handle arguments
    clone_parser.set_defaults(func=_clone_all_handle_args)

    args = parser.parse_args()
    args.func(args)
