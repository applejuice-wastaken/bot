import typing

import aiofiles
import pathlib

import os

import difflib

from . import Flag
from .abc import FlagRetriever

def folder_path(name=None):
    self_dir = os.path.dirname(__file__)
    if name is None:
        return os.path.join(self_dir, 'local')
    else:
        return os.path.join(self_dir, 'local', name)

class LocalFlagRetriever(FlagRetriever):
    def __init__(self):
        self.files = {}

        images = {}
        aliases = {}

        for file in os.listdir(folder_path()):
            path = folder_path(file)
            path_obj = pathlib.Path(path)
            pos = path_obj.name.find(".")
            name, extension = path_obj.name[:pos], path_obj.name[pos + 1:]

            if extension == "meta":
                with open(path) as fp:
                    for line in fp:
                        command, content = line.split("=")
                        command = command.strip()
                        content = content.strip()

                        if command == "alias":
                            aliases[content] = name

                        else:
                            ValueError(f"Unknown command {command}")
            else:
                images[name] = path
                aliases[name] = name

        for alias, image in aliases.items():
            self.files[alias] = images[image]

        print(self.files)

    @property
    def schema(self):
        return "local"

    # noinspection PyTypeChecker
    async def get_flag(self, name) -> typing.Optional[Flag]:
        match = difflib.get_close_matches(name, self.files.keys(), 1, 0.8)
        if match:
            return Flag(self.files[match[0]], match[0], str(self), is_remote=False)

    def __str__(self):
        return "local storage"
