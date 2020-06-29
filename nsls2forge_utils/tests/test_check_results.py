import subprocess

def test_imports():
    from nsls2forge_utils.check_results import (check_conda_channels,  # noqa
                                                check_package_version)  # noqa


def test_default_channel():
	msg = 'No packages were installed from conda-forge.\n'
	command = 'conda create --name df && conda activate df && check-results -t channels'
	res = subprocess.run(command, shell=True, text=True)
	assert res.returncode == 0


def test_forbidden_channel():
	command = ('conda init --all && conda create --name fc '
			  '&& conda config --env --add channels conda-forge '
			  '&& conda activate fc && check-results -t channels')
	res = subprocess.run(command, shell=True, text=True)
	assert res.returncode == 1


def test_forbidden_channel_ignore():
	command = ('conda init --all && conda create --name fc '
			  '&& conda config --env --add channels conda-forge '
			  '&& conda activate fc && check-results -t channels -i')
	res = subprocess.run(command, shell=True, text=True)
	assert res.returncode == 0
