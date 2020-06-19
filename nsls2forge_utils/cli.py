import argparse

from .check_results import check_conda_channels, check_package_version


def main():
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


if __name__ == '__main__':
    sys.exit(main())
