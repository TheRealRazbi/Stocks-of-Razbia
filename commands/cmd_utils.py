__all__ = ["convert", "prepare_args", "handle_annotations_args", "handle_mandatory_arg_count", "handle_arg_names", "order_and_convert_args"]

import inspect

import typing as t

from . import exc
from .converters import Converter, registered_converters


def is_optional(field):
    return t.get_origin(field) is t.Union and \
           type(None) in t.get_args(field)


def convert(ctx, annotation, arg):
    if is_optional(annotation):
        annotation = t.get_args(annotation)[0]

    if isinstance(annotation, Converter):
        return annotation.convert(ctx, arg)
    elif isinstance(annotation, list):
        for converter in annotation:
            try:
                return registered_converters[converter].convert(ctx, arg)
            except exc.ConversionError:
                pass
        raise exc.ProperArgumentNotProvided(arg_name=arg)
    elif annotation in registered_converters:
        return registered_converters[annotation].convert(ctx, arg)
    raise exc.ConverterNotFound("No converter found ...")


def prepare_args(ctx, command: "Command", args: t.Sequence[str], mandatory_arg_count: int, unordered_args: bool,
                 arg_names: t.Sequence[str], sequence_arg: str):
    len_diff = len(args) - len(command.args)
    if len_diff < 0:
        if mandatory_arg_count > len(args):
            raise exc.BadArgumentCount("I have no idea what is this | mandatory_arg_count > args", func=command)
    if unordered_args:
        assert len(arg_names) == len(command.args)
        return order_and_convert_args(ctx,
                                      needed_args={name: annotation for name, annotation in zip(arg_names, command.args)},
                                      raw_args=args,
                                      mandatory_arg_count=mandatory_arg_count,
                                      sequence_arg=sequence_arg
                                      )
    else:
        return [
            convert(ctx, annotation, arg)
            for annotation, arg
            in zip(command.args, args)
        ]


def order_and_convert_args(ctx, needed_args: t.Dict[str, any], raw_args: t.Sequence, mandatory_arg_count: int, sequence_arg='') -> dict:
    """
    Orders arguments to allow for users to pass unordered args.
    Make sure to order the converters by specificity, the most specific first, 
    because it checks the converters in order and stops when finds one
    :type ctx: Context needed by the converter to parse the arguments
    :param needed_args:
    Key is a string representing the name of the returned value. E.g.: name
    Value is the annotation, or a list of annotations of the function argument. It has to have a registered converter E.g.: <type: int>
    :param raw_args: a Sequence of all the strings to be parsed
    :param mandatory_arg_count: the required number of arguments to not require optional arguments
    :param sequence_arg: if specified, it returns that argument as a list containing every time it's converter parsed successfully
    """
    converted_values = {}
    for arg in raw_args:
        for name, annotation in needed_args.items():
            if name in converted_values and name != sequence_arg:
                continue
            try:
                converted_arg = convert(ctx, annotation, arg)
            except (exc.ProperArgumentNotProvided, exc.ConversionError):
                continue
            else:
                if name == sequence_arg:
                    if name in converted_values:
                        converted_values[name].append(converted_arg)
                    else:
                        converted_values[name] = [converted_arg]
                else:
                    converted_values[name] = converted_arg
                break

    if len(converted_values) < mandatory_arg_count:
        for name in needed_args.keys():
            if name not in converted_values:
                raise exc.ProperArgumentNotProvided(arg_name=name)

    return converted_values


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


def handle_mandatory_arg_count(args: tuple):
    res = 0
    for arg in args:
        if not is_optional(arg):
            res += 1
    return res


def handle_arg_names(func):
    sig = inspect.signature(func)
    names = list(sig.parameters.keys())
    names = names[1:]  # remove context from the list of names
    return names


if t.TYPE_CHECKING:
    from . import Command
