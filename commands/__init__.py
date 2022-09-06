import typing as t

from .exc import *
from .converters import *
from .cmd_utils import *


def _long_name(name, parent):
    if parent is not None:
        return f"{parent.long_name} {name}"
    return name


class Command:
    __slots__ = (
        "name", "long_name", "run", "args", "usage", "available_on_twitch", "mandatory_arg_count", "unordered_args",
        "arg_names",
        "sequence_arg", "specific_arg_usage")

    def __init__(self, func, name=None, usage="", parent=None, available_on_twitch=False, unordered_args: bool = False,
                 sequence_arg: str = None, specific_arg_usage: dict = None):
        name = name or func.__name__
        long_name = _long_name(name, parent)
        self.name = name
        self.available_on_twitch = available_on_twitch
        self.unordered_args = unordered_args
        self.sequence_arg = sequence_arg
        self.specific_arg_usage = {} if specific_arg_usage is None else specific_arg_usage

        self.long_name = long_name
        self.usage = f"{{name}} {usage}"

        self.run = func
        self.args = handle_annotations_args(func)
        self.mandatory_arg_count = handle_mandatory_arg_count(self.args)
        self.arg_names = handle_arg_names(func)

    def __call__(self, ctx, *args: str):
        if not self.available_on_twitch and not ctx.discord_message:
            raise exc.CommandError("This command can only be ran in Discord. discord.gg/swavy")
        prepared_args = prepare_args(ctx, self, args, self.mandatory_arg_count, self.unordered_args, self.arg_names,
                                     self.sequence_arg)
        if self.unordered_args:
            return self.run(ctx, **prepared_args)
        return self.run(ctx, *prepared_args)


class Group:
    __slots__ = ("name", "long_name", "sub_commands", "available_on_twitch")

    def __init__(self, name=None, parent=None, available_on_twitch=False):
        self.name = name
        self.long_name = _long_name(name, parent)
        self.available_on_twitch = available_on_twitch
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
