import os

import markdown
from bs4 import BeautifulSoup

from nsls2forge_utils.dashboard import create_dashboard


def test_no_feedstocks():
    # create file with empty line
    with open('names.txt', 'w') as f:
        f.close()
    create_dashboard(names='names.txt', write_to='test.md')
    with open('test.md', 'r') as f:
        html_text = markdown.markdown(f.read())
        html = BeautifulSoup(html_text, features='lxml')
        assert len(html.findAll('img')) == 0
    os.remove('names.txt')
    os.remove('test.md')


def test_one_feedstock():
    expected_status = (
        'https://dev.azure.com/nsls2forge/nsls2forge'
        '/_apis/build/status/event-model-feedstock'
    )
    expected_health = (
        'https://landscape.io/github/nsls-ii-forge/'
        'event-model-feedstock/master/landscape.svg?style=flat'
    )
    expected_cf = (
        'https://img.shields.io/conda/vn/conda-forge/event-model'
    )
    expected_nsls2 = (
        'https://img.shields.io/conda/vn/nsls2forge/event-model'
    )
    expected_default = (
        'https://img.shields.io/conda/vn/anaconda/event-model'
    )
    expected_pypi = (
        'https://img.shields.io/pypi/v/event-model'
    )
    expected_github = (
        'https://img.shields.io/github/v/tag/bluesky/event-model'
    )
    expected_downloads = (
        'https://img.shields.io/conda/dn/nsls2forge/event-model'
    )
    with open('names.txt', 'w') as f:
        f.write('event-model')
    create_dashboard(names='names.txt', write_to='test.md')
    with open('test.md', 'r') as f:
        html_text = markdown.markdown(f.read())
        html = BeautifulSoup(html_text, features='lxml')
        build_status = html.findAll('img', attrs={'alt': 'Build Status'})
        num_rows = len(build_status)
        build_status = build_status[0]
        health = html.find('img', attrs={'alt': 'Code Health'})
        cf = html.find('img', attrs={'alt': 'conda-forge version'})
        nsls2 = html.find('img', attrs={'alt': 'nsls2forge version'})
        defaults = html.find('img', attrs={'alt': 'defaults version'})
        pypi = html.find('img', attrs={'alt': 'PyPI version'})
        github = html.find('img', attrs={'alt': 'GitHub version'})
        downloads = html.find('img', attrs={'alt': 'Downloads'})
        assert num_rows == 1
        assert expected_status in str(build_status)
        assert expected_health in str(health)
        assert expected_cf in str(cf)
        assert expected_nsls2 in str(nsls2)
        assert expected_default in str(defaults)
        assert expected_pypi in str(pypi)
        assert expected_github in str(github)
        assert expected_downloads in str(downloads)
    os.remove('names.txt')
    os.remove('test.md')


def test_fake_feedstock():
    fake_name = 'djfjkahdflkv'
    with open('names.txt', 'w') as f:
        f.write(fake_name)
    create_dashboard(names='names.txt', write_to='test.md')
    with open('test.md', 'r') as f:
        html_text = markdown.markdown(f.read())
        html = BeautifulSoup(html_text, features='lxml')
        svgs = html.findAll('img', attrs={'alt': 'Build Status'})
        assert len(svgs) == 1
        assert fake_name + '-feedstock' in str(svgs[0])
    os.remove('names.txt')
    os.remove('test.md')


def test_rows():
    names = ['event-model', 'analysis', 'collection',
             'bluesky', 'cachey', 'srw']
    expected_rows = 6
    with open('names.txt', 'w') as f:
        for name in names:
            f.write(f'{name}\n')
    num_rows = create_dashboard(names='names.txt', write_to='test.md')
    with open('test.md', 'r') as f:
        html_text = markdown.markdown(f.read())
        html = BeautifulSoup(html_text, features='lxml')
        svgs = html.findAll('img', attrs={'alt': 'Build Status'})
        assert expected_rows == num_rows
        assert expected_rows == len(svgs)
    os.remove('names.txt')
    os.remove('test.md')
