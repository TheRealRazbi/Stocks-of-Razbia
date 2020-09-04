import sys
import time

from custom_tools import validate_input
import os
from termcolor import colored
from dulwich import porcelain
import asyncirc
import requests
from asyncirc.protocol import IrcProtocol
from asyncirc.server import Server
from irclib.parser import Message
import sqlalchemy
from sqlalchemy import Column, select, func, create_engine, event, ForeignKey
from sqlalchemy.sql import sqltypes as t
from sqlalchemy.ext.declarative import as_declarative
from sqlalchemy.orm import sessionmaker, exc, relationship
from sqlalchemy.ext.hybrid import hybrid_property
import sqlalchemy.ext.baked
from quart import Quart, render_template, request, flash, redirect, url_for, websocket
import wtforms
import markdown2
import traceback
import alembic
import alembic.config
import wtforms_components

os.system("cls")


def auto_update_check():
    if os.path.exists('lib/auto_update_enabled') and os.path.exists('lib/code/'):
        porcelain.pull("lib/code/")


def start_screen(first='Start'):
    auto_updates = False
    if os.path.exists('lib/auto_update_enabled'):
        auto_updates = True
    print(f"1 - {colored(first, color='cyan')}\n"
          # f"2 - {colored('Introduction', color='yellow')}\n"
          f"2 - {colored('Check for Updates', color='green')}\n"
          f"3 - {colored(f'Auto-updates: {auto_updates}', color='yellow')}\n"
          f"4 - {colored('Quit', color='red')}\n")
    # if first == 'Start':
    #     print(colored("Please consider using the 'Introduction' option in case it's unclear what the minigame does.", 'red'))
    choice = validate_input('Pick one: ', requires_int=True, int_range=(1, 4))
    if choice == 4:
        raise SystemExit(0)
    elif choice == 3:
        enable_auto_updates()
    elif choice == 2:
        check_for_updates()
    elif choice == 1:
        start_program()


def color_this(text: str, word_and_color: tuple):
    return text.replace(word_and_color[0], f"{colored(*word_and_color)}")


def color_with_list(text: str, words_and_colors: list):
    for word, color in zip(words_and_colors[::2], words_and_colors[1::2]):
        text = color_this(text, (word, color))
    return text


def print_intro():
    if os.path.exists('lib/code/'):
        try:
            with open("lib/code/introduction.md", "r") as f:
                explanation = f.read().strip()
        except FileNotFoundError:
            with open("introduction.md", "r") as f:
                explanation = f.read().strip()
        words_and_colors = ['companies', 'yellow', 'company', 'yellow', 'stocks', 'cyan', 'announcement', 'blue',
                            'month', 'green', 'months', 'green', 'announced', 'blue', 'bankrupt', 'red', 'users', 'magenta',
                            'my', 'cyan',
                            ]

        explanation = color_with_list(explanation, words_and_colors)
        print(f'\n{explanation}\n')
        start_screen()
    else:
        print(f"{colored('Please install the minigame first', 'red')}")
        start_screen(first='Install')


def check_for_updates():
    if not os.path.exists('lib/code/'):
        print(f"{colored('Please install the minigame first', 'red')}")
        start_screen(first='Install')

    print(f"If there's any error that prevents program from starting, please tell {colored('Razbi', 'magenta')} about it. "
          f"Those are usually solved by deleting {colored('lib/db.sqlite', 'green')} or by asking {colored('Razbi', 'magenta')} for an updated .exe")
    input("Press enter to continue... [this is just a warning]: ")
    porcelain.pull("lib/code/")
    print(f"{colored('Program Updated [if there was any update available, the following text should let you figure that out, no, really, I have no easy way of figuring it out]', 'green')}")
    start_screen()


def enable_auto_updates():
    if not os.path.exists('lib/code/'):
        print(f"{colored('Please install the minigame first', 'red')}")
        start_screen(first='Install')

    if os.path.exists('lib/auto_update_enabled'):
        print(f"Would you like to disable {colored('auto-updates', 'green')}?")
        print(f"1 - {colored('Yes', color='cyan')}\n"
              f"2 - {colored('No', color='red')}\n"
              )
        choice = validate_input('Pick one: ', requires_int=True, int_range=(1, 2))
        if choice == 1:
            os.remove('lib/auto_update_enabled')
            print(f"{colored('Auto-updates disabled', 'green')}")
        start_screen()
    else:
        print(f"Would you like to enable {colored('auto-updates', 'green')}?")
        print(f"1 - {colored('Yes', color='cyan')}\n"
              f"2 - {colored('No', color='red')}\n"
              )
        choice = validate_input('Pick one: ', requires_int=True, int_range=(1, 2))
        if choice == 1:
            with open('lib/auto_update_enabled', 'w'):
                pass
            print(f"{colored('Auto-updates enabled', 'green')}")
            print(f"Would you like to {colored('check-for-updates', 'green')} right now?")
            print(f"1 - {colored('Yes', color='cyan')}\n",
                  f"2 - {colored('No', color='red')}\n",
                  )
            choice = validate_input('Pick one: ', requires_int=True, int_range=(1, 2))
            if choice == 1:
                check_for_updates()
            else:
                start_screen()


def install_program():
    os.mkdir('lib/code/')
    porcelain.clone("https://github.com/TheRealRazbi/Stocks-of-Razbia.git", "lib/code")
    print(f"{colored('Program installed successful -------------------------------', 'green')}")


def start_program():
    # print(f"{colored('If you want the program to automatically check updates and start automatically upon open. Please check the config', 'red')}")
    if not os.path.exists('lib/'):
        os.mkdir('lib/')
    if not os.path.exists('lib/code/'):
        install_program()
        start_screen()
        return
    else:
        sys.path.append('lib/code')
        main = __import__("main").main
        try:
            main()
        except KeyboardInterrupt:
            raise SystemExit(0)
        except:
            if not os.path.exists('lib/crash-logs'):
                os.mkdir('lib/crash-logs')
            when = time.strftime('%H-%M-%S _ %d-%m-%Y')
            traceback.print_exc()
            with open(f'lib/crash-logs/{when}.txt', 'w') as f:
                traceback.print_exc(file=f)

            input(f"{colored('An unknown error has been encountered.', 'red')} Please send {colored('Razbi', 'magenta')} the crash-log found in the '{colored('lib/crash-logs/*moment_of_crash*', 'green')}' | "
                  f"{colored('lib/', 'green')} is in the same folder as the executable. Press any key to close the program...")


if __name__ == '__main__':
    auto_update_check()
    first = 'Start'
    if not os.path.exists('lib/code/'):
        first = 'Install'
    start_screen(first=first)

