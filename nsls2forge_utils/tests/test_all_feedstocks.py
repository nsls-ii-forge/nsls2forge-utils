import os
import shutil
import subprocess

from nsls2forge_utils.all_feedstocks import (
    get_all_feedstocks_from_github,
    get_all_feedstocks,
    all_feedstocks_info
)


def test_all_feedstocks_from_github():
    names = get_all_feedstocks_from_github()
    assert names is None
    names = get_all_feedstocks_from_github(organization='nsls-ii-forge')
    include_archived = get_all_feedstocks_from_github(organization='nsls-ii-forge',
                                                      include_archived=True)
    size_names = len(names)
    size_include_archived = len(include_archived)
    assert size_include_archived >= size_names
    assert size_names > 0
    assert size_include_archived > 0


def test_all_feedstocks():
    names = get_all_feedstocks()
    assert names is None
    with open('names.txt', 'w') as f:
        f.write('event-model\n')
        f.write('bluesky')
    names = get_all_feedstocks(cached=True)
    assert 'event-model' in names
    assert 'bluesky' in names
    assert len(names) == 2
    os.remove('names.txt')
    os.makedirs('./test_feedstocks/event-model-feedstock', exist_ok=True)
    os.makedirs('./test_feedstocks/bluesky-feedstock', exist_ok=True)
    names = get_all_feedstocks(cached=True, feedstocks_dir='./test_feedstocks/')
    assert 'event-model' in names
    assert 'bluesky' in names
    assert len(names) == 2
    shutil.rmtree('./test_feedstocks')


def test_all_feedstocks_info():
    cmd = ('git clone --depth 1 https://github.com/nsls-ii-forge/event-model-feedstock.git '
           './test_feedstocks/event-model-feedstock')
    subprocess.run(cmd, shell=True)
    df = all_feedstocks_info(feedstocks_dir='./test_feedstocks/')
    assert len(df.index) == 1
    assert df.size == 4
    assert list(df.columns) == ['Name', 'Branch', 'Changed?', 'Version']
    assert df['Name'].iloc[0] == 'event-model-feedstock'
    shutil.rmtree('./test_feedstocks')
