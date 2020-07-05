from typing import List
import asyncio
import math
from database import Company
from database import User
# from API import API
from converters import BasicConverter
import inspect
from converters import Converter, ConversionError, registered_converters, ConverterNotFound, CompanyNotFound
import database


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
    if isinstance(annotation, Converter):
        return annotation.convert(ctx, arg)
    elif annotation in registered_converters:
        return registered_converters[annotation].convert(ctx, arg)
    raise ConverterNotFound("No converter found ...")


def prepare_args(ctx, command: Command, args: List[str]):
    # print(args)
    # print(command.args)
    converted_args = []
    len_diff = len(args) - len(command.args)
    if len_diff > 0:
        raise ConversionError("I have no idea what is this | len_diff > 0")
    elif len_diff < 0:
        raise ConversionError("I have no idea what is this | len_diff < 0")

    return [
        convert(ctx, annotation, arg)
        for annotation, arg
        in zip(command.args, args)
    ]


@command()
def buy_stocks(ctx, amount: int, company: Company):
    points = ctx.user.points(ctx.api)
    cost = math.ceil(amount*company.stock_price)
    if points >= cost:
        ctx.api.send_chat_message(f"@{ctx.user.name} just bought {amount} {company.abbv} for {cost} points")
        share = ctx.session.query(database.Shares).filter_by(user_id=ctx.user.id, company_id=company.id).first()
        if share:
            share.amount += amount
            ctx.session.commit()
        else:
            ctx.session.add(database.Shares(user_id=ctx.user.id, company_id=company.id, amount=amount))
            ctx.session.commit()
        ctx.api.subtract_points(ctx.user.name, cost)
    else:
        ctx.api.send_chat_message(f"@{ctx.user.name} has  {points} points and requires {cost} aka {cost-points} more")


@command()
def sell_stocks(ctx, amount: int, company: Company):
    cost = math.ceil(amount*company.stock_price)
    share = ctx.session.query(database.Shares).get((ctx.user.id, company.id))
    if share and share.amount >= amount:
        ctx.api.subtract_points(ctx.user.name, -cost)
        share.amount -= amount
        ctx.session.commit()
        ctx.api.send_chat_message(f"@{ctx.user.name} has sold {amount} stocks for {cost} points")
    else:
        message = f"@{ctx.user.name} doesn't have {amount} stocks at company {company.abbv} to sell it. "
        if share:
            message += f"They require {amount-share.amount} more"
        ctx.api.send_chat_message(message)


@command()
def info_company(ctx, company: Company):
    ctx.api.send_chat_message(company)


@command()
def test_turtle(ctx, thing: str):
    message = ""
    for i in range(100):
        message += "thing"

    ctx.api.send_chat_message(message)


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

