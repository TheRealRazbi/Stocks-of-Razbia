import typing as t

from .exc import *
from .converters import *
from .cmd_utils import *


def _long_name(name, parent):
    if parent is not None:
        return f"{parent.long_name} {name}"
    return name


class Command:
    __slots__ = ("name", "long_name", "run", "args", "usage")

    def __init__(self, func, name=None, usage="", parent=None):
        name = name or func.__name__
        long_name = _long_name(name, parent)
        self.name = name

        self.long_name = long_name
        self.usage = f"{long_name} {usage}"

        self.run = func
        self.args = handle_annotations_args(func)

    def __call__(self, ctx, *args: str):
        prepared_args = prepare_args(ctx, self, args)
        return self.run(ctx, *prepared_args)


class Group:
    __slots__ = ("name", "long_name", "sub_commands")

    def __init__(self, name=None, parent=None):
        self.name = name
        self.long_name = _long_name(name, parent)
        self.sub_commands = {}

    def __call__(self, ctx, *args):
        if not args:
            raise CommandError("Valid subcommands : " + ", ".join(self.sub_commands.keys()))
        sub_command_name, *rest = args
        if sub_command_name in self.sub_commands:
            return self.sub_commands[sub_command_name](ctx, *rest)

    def command(self, name=None, cls=Command, **kwargs):
        return command(name=name, cls=cls, registry=self.sub_commands, parent=self, **kwargs)


def command(*, name=None, cls=Command, registry: t.Dict[str, t.Callable] = None, **kwargs):
    def decorator(func):
        cmd = cls(func, name=name, **kwargs)
        if registry is not None:
            registry[cmd.name] = cmd
        return cmd
    return decorator


def group(*, name=None, cls=Group, registry: t.Dict[str, t.Callable] = None, **kwargs):
    grp = cls(name=name, **kwargs)
    if registry is not None:
        registry[grp.name] = grp
    return grp
