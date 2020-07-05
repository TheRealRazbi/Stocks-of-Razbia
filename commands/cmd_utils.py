__all__ = ["convert", "prepare_args", "handle_annotations_args"]

import inspect

import typing as t

from . import exc
from .converters import Converter, registered_converters


def convert(ctx, annotation, arg):
    if isinstance(annotation, Converter):
        return annotation.convert(ctx, arg)
    elif annotation in registered_converters:
        return registered_converters[annotation].convert(ctx, arg)
    raise exc.ConverterNotFound("No converter found ...")


def prepare_args(ctx, command: "Command", args: t.Sequence[str]):
    len_diff = len(args) - len(command.args)
    if len_diff > 0:
        raise exc.BadArgumentCount("I have no idea what is this | len_diff > 0", func=command)
    elif len_diff < 0:
        raise exc.BadArgumentCount("I have no idea what is this | len_diff < 0", func=command)

    return [
        convert(ctx, annotation, arg)
        for annotation, arg
        in zip(command.args, args)
    ]


def handle_annotations_args(func):
    sig = inspect.signature(func)
    params = list(sig.parameters.values())
    params = params[1:]  # remove context from the list of params
    return [
        param.annotation
        if param.annotation is not sig.empty
        else str
        for param in params
    ]


if t.TYPE_CHECKING:
    from . import Command
