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
        self.usage = f"{{name}} {usage}"

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

    async def __call__(self, ctx, *args):
        if not args:
            raise CommandError(f"Valid subcommands: {', '.join(self.remapped_sub_commands(ctx))}")
        sub_command_name, *rest = args
        sub_command_name = ctx.api.command_names.get((sub_command_name, self.name), sub_command_name)
        if sub_command_name not in self.sub_commands:
            raise CommandError(f"Valid subcommands: {', '.join(self.remapped_sub_commands(ctx))}")
        return await self.sub_commands[sub_command_name](ctx, *rest)

    def command(self, name=None, cls=Command, **kwargs):
        return command(name=name, cls=cls, registry=self.sub_commands, parent=self, **kwargs)

    def remapped_sub_commands(self, ctx):
        res = [
            new_command_name
            for (new_command_name, group_name), old_command_name
            in ctx.api.command_names.items()
            if group_name == self.name and old_command_name in self.sub_commands
        ]
        if res:
            return res
        else:
            return self.sub_commands


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
