"""
This code is a rework of
https://github.com/xpdAcq/mission-control/blob/master/tools/update_readme.py
This version was not importable so the
functions had to be re-implemented here.
"""
from nsls2forge_utils.all_feedstocks import get_all_feedstocks
from nsls2forge_utils.io import read_file_to_list


def create_dashboard(names=None, write_to='README.md'):
    '''
    Creates a table of packages with their build status, health, conda-forge version,
    nsls2forge version, and number of downloads from nsls2forge.
    Feedstocks must be from nsls-ii-forge GitHub organization.

    Parameters
    ----------
    names: str, optional
        filepath to text file containing feedstock repo names
        without the -feedstock suffix
    write_to: str, optional
        filepath to markdown file to write output to
    '''
    # TODO: Azure Pipeline direct pipeline link
    # TODO: Add codecov badge if available
    main_format = dict(
      build='[![Build Status](https://dev.azure.com/nsls2forge/nsls2forge/_apis/build/status/{name}-feedstock)]'
            '(https://dev.azure.com/nsls2forge/nsls2forge/_build)',
      health='[![Code Health](https://landscape.io/github/nsls-ii-forge/{name}-feedstock/master/'
             'landscape.svg?style=flat)](https://landscape.io/github/nsls-ii-forge/{name}-feedstock/master)',
      cf_version='[![Anaconda-Server Badge](https://anaconda.org/conda-forge/{name}/badges/version.svg)]'
                 '(https://anaconda.org/conda-forge/{name})',
      nsls_version='[![Anaconda-Server Badge](https://anaconda.org/nsls2forge/{name}/badges/version.svg)]'
                   '(https://anaconda.org/nsls2forge/{name})',
      downloads='[![Anaconda-Server Badge](https://anaconda.org/nsls2forge/{name}/badges/downloads.svg)]'
                '(https://anaconda.org/nsls2forge/{name})')

    row_string = '''|[{name}](https://github.com/nsls-ii-forge/{name}-feedstock)|{build}|{health}
    |{cf_version} <br/> {nsls_version}|{downloads}|\n'''
    description = '''# Project Management
    Releases, Installers, Specs, and more!
    '''
    header = '''# Feedstock Packages Build status\n
    | Repo | Build | Health | CF Version <br/> NSLS Version | Downloads|
    |:-------:|:-----:|:------:|:------:|:------:|
    '''

    out = description
    if names is None:
        pkgs = sorted(get_all_feedstocks(organization='nsls-ii-forge'))
    else:
        pkgs = sorted(read_file_to_list(names))
    out += header
    for pkg in pkgs:
        tmp = row_string.format(**main_format, name=pkg)
        out += tmp.format(name=pkg)
    with open(write_to, 'w') as f:
        f.write(out)


if __name__ == '__main__':
    create_dashboard()
