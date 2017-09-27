import pathlib


def children(*path):
    path = pathlib.Path(*path)
    if path.is_dir():
        for child in path.iterdir():
            yield child
    elif path.is_file():
        yield path


def children_names(*path):
    for child in children(*path):
        yield child.name
