from typing import runtime_checkable, Protocol, Type, Optional
from database import Company

registered_converters = {}


@runtime_checkable
class Converter(Protocol):
    @classmethod
    def convert(cls, ctx, arg):
        ...


class ConversionError(Exception):
    pass


class BasicConverter:
    type: Type
    msg: Optional[str] = None

    @classmethod
    def convert(cls, ctx, arg):
        try:
            return cls.type(arg)
        except TypeError as e:
            raise ConversionError(cls.msg or "Not a valid value")


class CompanyConverter(Converter):
    @classmethod
    def convert(cls, ctx, arg: str):
        company = ctx.api.overlord.find_company(arg.lower())
        if company is None:
            raise ConversionError("Company doesn't exist")
        return company


def register_converter(converter, type=None):
    if type is None:
        type = converter.type
    registered_converters[type] = converter


def create_basic_converter(name, t: Type, msg=None):
    converter = type(name, (BasicConverter,), dict(type=t, msg=msg))
    register_converter(converter, t)
    return converter


IntConverter = create_basic_converter("IntConverter", int, msg="Not a valid integer")
StrConverter = create_basic_converter("StrConverter", str, msg="This should never happen, if you ever see this message, things got REAL wrong.")
register_converter(CompanyConverter, Company)
