import datetime
from enum import Enum

import discord
from termcolor import colored


class CurrencySystem(Enum):
    STREAMLABS = 'streamlabs'
    STREAM_ELEMENTS = 'stream_elements'
    STREAMLABS_LOCAL = 'streamlabs_local'
    # LOCAL_POINTS =


class EmbedColor(Enum):
    GREEN = 0x39c050
    RED = 0xba3b4e
    GRAY = 0x404040
    BLUE = 0x6791e4
    PURPLE = 0x894eb1


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


def create_embed(title: str, content: dict = None, footer: str = None, author: str = None,
                 color: EmbedColor = EmbedColor.GRAY):
    embed = discord.Embed(title=title, color=color.value)
    if author:
        embed.set_author(name=author)

    if content:
        for key, value in content.items():
            embed.add_field(name=f"{key}", value=f"{value}", inline=True)
    if footer:
        embed.set_footer(
            text=footer)
    return embed


if __name__ == '__main__':
    import math


    def income(value_of_stocks):
        income = 0
        stacks_of_5k = value_of_stocks // 5000
        left_overs = value_of_stocks % 5000
        for cycle in range(stacks_of_5k):
            income_percent = max(((10 - cycle) / 100), 0.01)
            income += 5000 * income_percent

        income += left_overs * max(((10 - stacks_of_5k) / 100), 0.01)

        return math.ceil(income)


    def main():
        # for value_of_stocks in range(1_000_000, 101_000_000, 1_000_000):
        while True:
            try:
                value_of_stocks = int(input("Value Of Stocks: "))
            except ValueError:
                print("Quit")
                break
            else:
                print(f'{value_of_stocks:,} worth = {income(value_of_stocks):,} points')


    main()
