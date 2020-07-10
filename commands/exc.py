class CommandError(Exception):
    @property
    def msg(self):
        if self.args:
            return self.args[0]
        return "An error occurred while running this command ..."


class ConverterNotFound(CommandError):
    pass


class BadArgumentCount(CommandError):
    def __init__(self, *args, func):
        super().__init__(*args)
        self.func = func

    @property
    def usage(self):
        return self.func.usage


class ConversionError(CommandError):
    msg_format = "{value} is not a valid value"

    def __init__(self, value, *args, msg=None, msg_format=None):
        msg = msg or (msg_format or self.msg_format).format(value=value)
        super().__init__(msg, value, *args)


class CompanyNotFound(ConversionError):
    msg_format = 'Company "{value}" not found'

# class CompanyNotFoundNorInt(ConversionError):
#     msg_format = ''
