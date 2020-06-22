from typing import List
import asyncio

from company import Company
from user import User
# from API import API
from converters import BasicConverter
import inspect
from converters import Converter, ConversionError, registered_converters


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


class Command:
    __slots__ = ("name", "run", "args")

    def __init__(self, func, name=None):
        self.name = name or func.__name__
        self.run = func
        self.args = handle_annotations_args(func)

    def __call__(self, ctx, *args):
        prepared_args = prepare_args(ctx, self, args)
        return self.run(ctx, *prepared_args)


def command(name=None):
    def decorator(func):
        return Command(func, name)

    return decorator


def convert(ctx, annotation, arg):
    print(registered_converters)
    if isinstance(annotation, Converter):
        return annotation.convert(ctx, arg)
    elif annotation in registered_converters:
        return registered_converters[annotation].convert(ctx, arg)
    raise ConversionError("No converter found ...")


def prepare_args(ctx, command: Command, args: List[str]):
    # print(args)
    # print(command.args)
    converted_args = []
    len_diff = len(args) - len(command.args)
    if len_diff > 0:
        raise ValueError("I have no idea what is this | len_diff > 0")
    elif len_diff < 0:
        raise ValueError("I have no idea what is this | len_diff < 0")

    return [
        convert(ctx, annotation, arg)
        for annotation, arg
        in zip(command.args, args)
    ]


@command()
def buy_stocks(ctx, amount: int, company_abbv: Company):
    print(ctx)
    pass


if __name__ == '__main__':
    pass
    # loop = asyncio.get_event_loop()
    # loop.run_until_complete(buy_stocks)
    # b = BuyCommand()
    # print(b.run.__annotations__)
    # buy_stocks(1, "reee")
    # api = API()
    # buy_stocks(1, '1')
    # ctx = Contdext(api, user)
    # prepared_args = prepare_args(ctx, command, args)
    # command(ctx, *args)

