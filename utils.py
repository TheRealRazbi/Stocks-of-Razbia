import datetime
from enum import Enum

from termcolor import colored


class CurrencySystem(Enum):
    STREAMLABS = 'streamlabs'
    STREAM_ELEMENTS = 'stream_elements'
    STREAMLABS_LOCAL = 'streamlabs_local'


class EmbedColor(Enum):
    GREEN = 0x39c050
    RED = 0xba3b4e
    GRAY = 0x404040
    BLUE = 0x6791e4


def generate_colored_function(color):
    def wrapper(message: str, print_=False, add_time=False, milliseconds=True):
        message = colored(message, color)
        if add_time:
            message = wrap_time(message=message, milliseconds=milliseconds)
        if print_:
            print(message)
        return message

    return wrapper


green = generate_colored_function('green')
red = generate_colored_function('red')
magenta = generate_colored_function('magenta')
yellow = generate_colored_function('yellow')
white = generate_colored_function('white')
blue = generate_colored_function('blue')
cyan = generate_colored_function('cyan')


def wrap_time(message: str, milliseconds=True):
    now = datetime.datetime.now()
    res = f"{colored(now.strftime('%H : %M'), 'cyan')}"
    if milliseconds:
        res = f"{res}[{colored(now.strftime('%S.%f'), 'magenta')}]"
    return f'{res} | {message}'


def print_with_time(message: str, color: str = None, milliseconds=True):
    print(f"{wrap_time(colored(message, color) if color else message, milliseconds=milliseconds)}")
