from os.path import normpath, basename, dirname, join
from typing import List


def get_path_at_level(path: str, level: int) -> str:
    """
    Get a subsection of the path
    :param path: Path to be analyzed
    :param level: Size of the subsection
    :return: Subsection of the path
    """
    norm_path = normpath(path)
    to_fuse = []
    for _ in range(level+1):
        to_fuse.append(basename(norm_path))
        norm_path = dirname(norm_path)

    new_path = ""
    for i in range(level+1, 0, -1):
        new_path = join(new_path, to_fuse[i-1])

    return new_path


def names_are_unique(unique_names: List[str]) -> bool:
    """
    Check if elements of a list are unique
    :param unique_names: List of element
    :return: True if that's the case
    """
    return len(set(unique_names)) == len(unique_names)


def exclude_params(name: str) -> str:
    """
    Crop the name if it discovers parameters at the end
    @param name: Name ot inspect
    @return: Name without params
    """
    params_index = name.find('?')
    if params_index >= 0:
        name = name[0:params_index]
    return name


def get_unique_names(to_download: List[str]):
    """
    From a list of MP3s url to download, create a pair made of the URL and a
    unique name where we can save the file locally
    :param to_download: List of MP3s url
    :return: List of (url, name)
    """
    level = 0
    unique_names = []
    while True:
        for name in to_download:
            if not names_are_unique(unique_names):
                continue  # No need to compute other paths as we already have a conflict
            unique_names.append(get_path_at_level(name, level))

        # Check if all names are uniques
        if names_are_unique(unique_names):
            break

        unique_names.clear()
        level += 1

    pairs = []
    for i in range(len(to_download)):
        pairs.append((to_download[i],
                      exclude_params(unique_names[i]
                                     .replace('/', '_')
                                     .replace('\\', '_')
                                     .replace('%20', ' '))))

    return pairs
