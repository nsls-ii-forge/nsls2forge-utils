import requests


def read_file_to_list(path):
    '''
    Reads file and places contents in a list line by line.

    Parameters
    ----------
    path: str
        Path to file to read from.

    Returns
    -------
    list
        Contains contents of file line by line.
    '''
    contents = []
    with open(path, 'r') as fp:
        contents = fp.read().splitlines()
    return contents


def _write_list_to_file(contents, path, sort=False):
    '''
    Writes items in contents to specified file line by line.

    Parameters
    ----------
    contents: list
        List containing items to place in file.
    path: str
        Path to file to write to.
    sort: bool, optional
        Will sort items in contents before writing to file.
    '''
    if sort:
        contents = sorted(contents)
    with open(path, 'w') as fp:
        for item in contents:
            fp.write(f'{item}\n')


def _fetch_file(organization, name, filepath):
    '''
    Fetches a file from specified GitHub organization and
    returns the text

    Parameters
    ----------
    organization: str
        GitHub organization the file belongs to
    name: str
        Feedstock repository name belonging to organization
    filepath: str
        Path to requested file in feedstock repository
    '''
    response = requests.get(
        "https://raw.githubusercontent.com/"
        f"{organization}/{name}-feedstock/master/{filepath}",
    )
    if response.status_code != 200:
        print(
            f"Something odd happened when fetching recipe {name}: {response.status_code}",
        )
        return response

    text = response.content.decode("utf-8")
    return text
