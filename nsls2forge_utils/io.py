

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
    with open(path, 'r') as fp:
        return fp.readlines()


def _write_list_to_file(contents, path):
    '''
    Writes items in contents to specified file line by line.

    Parameters
    ----------
    contents: list
        List containing items to place in file.
    path: str
        Path to file to write to.
    '''
    with open(path, 'w') as fp:
        for item in contents:
            fp.write(f'{item}\n')
