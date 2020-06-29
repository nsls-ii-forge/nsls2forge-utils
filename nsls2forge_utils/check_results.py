import importlib
import logging
import subprocess
from distutils.version import LooseVersion
from subprocess import PIPE

logger = logging.getLogger(__name__)


def check_conda_channels(forbidden_channel='conda-forge',
                         cmd='conda list --show-channel-url',
                         ignore_exception=False):
    """Check conda channels.

    This function checks if the list of channels does not have "forbidden"
    channels (useful for validation of the resulted packages from a feedstock).

    Parameters:
    -----------
    forbidden_channel: str, optional
        a channel to warn about if it is found in the package list in a conda
        environment
    cmd: str, optional
        a command to check a list of packages in a conda environment
    ignore_exception: bool, optional
        a flag to print the list of packages from the channels which are forbidden
        and proceed without exiting if set to True
    """

    # TODO: use later once https://github.com/conda/conda/pull/9998 resolved
    # (either merged or instructions how to properly use the function provided)
    # from conda.cli.main_list import list_packages
    # pkgs = list_packages(os.environ['CONDA_PREFIX'], show_channel_urls=True)
    # for p in pkgs[1]:
    #     if 'conda-forge' in p:
    #         print(p)

    res = subprocess.run(cmd.split(), stdout=PIPE, stderr=PIPE)
    pkgs = res.stdout.decode().split('\n')

    failed_packages = []
    for p in pkgs:
        if forbidden_channel in p:
            failed_packages.append(p)

    if failed_packages:
        formatted = '\n'.join(failed_packages)
        msg = f'Packages from the "{forbidden_channel}" channel found:\n{formatted}'
        if ignore_exception:
            print(msg)
        else:
            raise RuntimeError(msg)
    else:
        print(f'No packages were installed from {forbidden_channel}.')


def check_package_version(package=None, expected_version=None):
    """Check package version.

    Parameters:
    -----------
    package: str
        a package to check the version for
    expected_version: str
        minimum expected version of the package
    """
    if package is None:
        raise ValueError(f'Wrong package name: {package}')
    if expected_version is None:
        raise ValueError(f'Wrong expected version: {expected_version}')

    pkg = importlib.import_module(package)
    pkg_version = pkg.__version__
    if LooseVersion(pkg_version) < expected_version:
        raise ValueError(f'The found version ("{pkg_version}") of "{package}" '
                         f'is less than the expected version '
                         f'({expected_version})')
    else:
        print(f'The found version ({pkg_version}) of "{package}" is more or '
              f'equal the expected version ({expected_version})')
