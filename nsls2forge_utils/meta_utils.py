import hashlib
import os

import requests

from nsls2forge_utils.io import _fetch_file


def _fetch_and_parse_meta_yaml(name, organization=None, cached=False):
    from conda_forge_tick.utils import parse_meta_yaml
    if cached:
        filepath = f'./{name}-feedstock/recipe/meta.yaml'
        if not os.path.exists(filepath):
            filepath = filepath.replace('./', 'feedstocks/', 1)
        if not os.path.exists(filepath):
            raise RuntimeError(f'Cached feedstock {name} does not exist. Place '
                               'cloned repo in ./ or ./feedstocks/ and try again.')
        with open(filepath, 'r') as f:
            meta_yaml = f.read()
    else:
        if organization is None:
            raise ValueError(f'No organization provided for {name}')
        meta_yaml = _fetch_file(organization, name, 'recipe/meta.yaml')
    if isinstance(meta_yaml, requests.Response):
        return None
    return parse_meta_yaml(meta_yaml)


def get_attribute(attribute, name, organization=None, cached=False):
    '''
    Gets the source url for a package using its feedstock meta.yaml

    Parameters
    ----------
    name: str
        Package name of feedstock (must be a feedstock in organization)
    organization: str, optional
        GitHub organization to fetch the meta.yaml file from
    cached: bool
        When True, uses local feedstocks/ directory to pull recipe from
        associated feedstock

    Returns
    -------
    str or dict or list
        Value of attribute in meta.yaml file

    Examples
    --------
    >>> get_attribute('source url', 'event-model', organization='nsls-ii-forge')
    https://pypi.io/packages/source/e/event-model/event-model-1.15.2.tar.gz

    >>> get_attribute('package', 'event-model', organization='nsls-ii-forge')
    {'name': 'event-model', 'version': '1.15.2'}

    >>> get_attribute('requirements run', 'event-model', organization='nsls-ii-forge')
    ['python >=3.6', 'jsonschema', 'numpy']
    '''
    meta_yaml = _fetch_and_parse_meta_yaml(name,
                                           organization=organization,
                                           cached=cached)
    if meta_yaml is None:
        return None
    tags = attribute.split(' ')
    curr_attr = meta_yaml
    for tag in tags:
        if tag not in curr_attr:
            return None
        curr_attr = curr_attr[tag]
    return curr_attr


def download_from_source(name, organization=None, cached=False):
    '''
    Downloads a package given a feedstock meta.yaml

    Parameters
    ----------
    name: str
        Package name of feedstock (must be a feedstock in organization)
    organization: str, optional
        GitHub organization to fetch the meta.yaml file from
    cached: bool
        When True, uses local feedstocks/ directory to pull recipe from
        associated feedstock

    Returns
    -------
    tuple[str, str]
        Source url and sha256 hash for downloaded file
    '''
    meta_yaml = _fetch_and_parse_meta_yaml(name,
                                           organization=organization,
                                           cached=cached)
    url = meta_yaml['source']['url']
    filename = os.path.split(url)[-1]
    response = requests.get(url, stream=True)
    if response.status_code != 200:
        raise RuntimeError(f'Failed to get package from {url}: {response.status_code}')
    with open(filename, 'wb') as f:
        contents = response.raw.read()
        f.write(contents)
        sha256_hash = hashlib.sha256(contents).hexdigest()
    return (url, sha256_hash)
