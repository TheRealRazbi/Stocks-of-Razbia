__all__ = ["Converter", "registered_converters",
           "register_converter", "create_basic_converter"]

from typing import runtime_checkable, Protocol, Type, Optional, Sequence

from . import exc
from database import Company


registered_converters = {}


@runtime_checkable
class Converter(Protocol):
    @classmethod
    def convert(cls, ctx, arg):
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


IntConverter = create_basic_converter(
    "IntConverter", int,
    msg="{value} is not a valid integer"
)
StrConverter = create_basic_converter(
    "StrConverter", str,
    msg="This should never happen, if you ever see this message, things got REAL wrong."
)
register_converter(CompanyConverter, Company)
