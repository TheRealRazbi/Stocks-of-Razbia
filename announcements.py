import random
import re
from typing import Dict

from graphlib import TopologicalSorter
import dataclasses

format_pattern = re.compile(r"{(\w+)}")


@dataclasses.dataclass
class Announcement:
    contents: str
    randomize_from: bool = False

    def __str__(self):
        if self.randomize_from:
            return random.choice(self.content_list).strip()
        return self.contents

    @property
    def content_list(self):  # cache as needed maybe idk.
        return self.contents.split("|")

    @property
    def dependencies(self):
        for match in re.finditer(format_pattern, self.contents):
            yield match.groups()[0]


class AnnouncementDict(Dict[str, Announcement]):
    @classmethod
    def from_list(cls, lst):
        # noinspection PyArgumentList
        return cls((
                       element['name'],
                       Announcement(element['contents'], element['randomize_from'])
                   ) for element in lst)

    def to_list(self):
        return [{'name': key, **dataclasses.asdict(message)} for key, message in self.items()]

    def validate(self, result: Announcement):
        graph = TopologicalSorter()
        for dep in result.dependencies:
            graph.add(dep)
        for key, message in self.items():
            for dep in message.dependencies:
                graph.add(dep, key)
        graph.prepare()
        missing = graph._node2info.keys() - self.keys()
        if missing:
            raise ValueError(f"Missing items: {','.join(missing)}")

    def __getitem__(self, key):
        return str(super().__getitem__(key)).format_map(self)
