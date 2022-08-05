__all__ = ["Converter", "registered_converters",
           "register_converter", "create_basic_converter"]

from typing import runtime_checkable, Protocol, Type, Optional

from . import exc
from database import Company, User
from multi_arg import IntOrStrAll, CompanyOrIntOrAll, CompanyOrInt, Percent, StocksStr, AllStr

registered_converters = {}


@runtime_checkable
class Converter(Protocol):
    @classmethod
    def convert(cls, ctx, arg: str):
        ...


def register_converter(converter, t=None):
    if t is None:
        t = converter.type
    registered_converters[t] = converter


def create_basic_converter(name, t: Type, msg=None):
    converter = type(name, (BasicConverter,), dict(type=t, msg=msg))
    register_converter(converter, t)
    return converter


class BasicConverter:
    type: Type
    msg: Optional[str] = None

    @classmethod
    def convert(cls, _, arg):
        try:
            return cls.type(arg)
        except ValueError as e:
            raise exc.ConversionError(
                arg,
                msg_format=(cls.msg or "{value} is not a valid value")
            ) from e


class CompanyConverter(Converter):
    @classmethod
    def convert(cls, ctx, arg: str):
        arg = arg.upper()
        company = Company.find_by_abbreviation(arg, ctx.session)
        if company is None:
            raise exc.CompanyNotFound(arg.lower())
        return company


class IntOrAllConverter(Converter):
    @classmethod
    def convert(cls, ctx, arg: str):
        arg = arg.lower()
        if arg == 'all':
            return arg
        try:
            arg = int(arg)
        except ValueError as e:
            raise exc.ConversionError(
                arg,
                msg_format="'{value}' needs to be either a number or 'all'"
            ) from e
        return arg


class SpecificStringConverter(Converter):
    strings_to_check = ()

    @classmethod
    def convert(cls, ctx, arg: str):
        arg = arg.lower()
        for string in cls.strings_to_check:
            if arg == string:
                return arg
        raise exc.ConversionError(
            arg,
            msg_format='{value} needs to be'f" one of these {(f'{thing}' for thing in cls.strings_to_check)}"
        )


class AllConverter(SpecificStringConverter):
    strings_to_check = ('all', )


class StocksConverter(SpecificStringConverter):
    strings_to_check = ('stocks', 'shares', 'stonks')


class CompanyOrAllStr(Converter):
    @classmethod
    def convert(cls, ctx, arg: str):
        arg = arg.lower()
        if arg == 'all':
            return arg
        try:
            arg = int(arg)
            return arg
        except ValueError:
            pass
        arg = arg.upper()
        company = Company.find_by_abbreviation(arg, ctx.session)
        if company is None:
            raise exc.ConversionError(f"'{arg}' is not 'all', not a number, nor a Company so it's")
        return company


class CompanyOrIntConverter(Converter):
    @classmethod
    def convert(cls, ctx, arg: str):
        arg = arg.lower()
        try:
            arg = int(arg)
            return arg
        except ValueError:
            pass
        arg = arg.upper()
        company = Company.find_by_abbreviation(arg, ctx.session)
        if company is None:
            raise exc.ConversionError(f"'{arg}' is not a number, nor a Company so it's")
        return company


class PercentConverter(Converter):
    @classmethod
    def convert(cls, ctx, arg: str):
        res = None
        if arg.endswith('%'):
            number_str, _, _ = arg.partition('%')
            try:
                raw_number = float(number_str)
            except ValueError:
                pass
            else:
                if raw_number <= 0:
                    raise exc.ConversionError(f"{arg} is lower or equal to 0")
                elif raw_number > 100:
                    raise exc.ConversionError(f"{arg} is above 100")
                res = raw_number / 100

        if res is None:
            raise exc.ConversionError(f"{arg} is not a valid percent, like '40%'")
        return res


class UserConverter(Converter):
    @classmethod
    def convert(cls, ctx, arg: str):
        if ctx.discord_message is None:
            raise exc.ConversionError("Command works only on discord.")
        user = None
        mentions = ctx.discord_message.mentions
        if len(mentions):
            user_id = mentions[0].id
            user = ctx.session.query(User).filter_by(discord_id=user_id).first()

        if user is None:
            raise exc.ConversionError(f"User '{arg}' not found.")
        return user


IntConverter = create_basic_converter(
    "IntConverter", int,
    msg="{value} is not a valid integer"
)
StrConverter = create_basic_converter(
    "StrConverter", str,
    msg="This should never happen, if you ever see this message, things got REAL wrong."
)
register_converter(CompanyConverter, Company)
register_converter(IntOrAllConverter, IntOrStrAll)
register_converter(CompanyOrAllStr, CompanyOrIntOrAll)
register_converter(CompanyOrIntConverter, CompanyOrInt)
register_converter(PercentConverter, Percent)
register_converter(UserConverter, User)
register_converter(StocksConverter, StocksStr)
register_converter(AllConverter, AllStr)
