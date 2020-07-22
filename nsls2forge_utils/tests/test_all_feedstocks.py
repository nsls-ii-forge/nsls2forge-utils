import os

from nsls2forge_utils.all_feedstocks import (
	get_all_feedstocks_from_github,
	get_all_feedstocks,
	clone_all_feedstocks,
	all_feedstocks_info
)

def test_all_feedstocks_from_github():
	names = get_all_feedstocks_from_github()
	assert names is None
	names = get_all_feedstocks_from_github(organization='nsls-ii-forge')
	archived_names = get_all_feedstocks_from_github(organization='nsls-ii-forge',
													archived=True)
	size_names = len(names)
	size_archived = len(archived_names)
	assert size_archived >= size_names
	assert size_names > 0
	assert size_archived > 0


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
	os.makedirs('./feedstocks/event-model-feedstock', exist_ok=True)
	os.makedirs('./feedstocks/bluesky-feedstock', exist_ok=True)
	names = get_all_feedstocks(cached=True, feedstocks_dir='./feedstocks/')
	assert 'event-model' in names
	assert 'bluesky' in names
	assert len(names) == 2
	os.rmdir('./feedstocks/event-model-feedstock')
	os.rmdir('./feedstocks/bluesky-feedstock')


def test_clone_all_feedstocks():
	pass


def test_all_feedstocks_info():
	pass
