import sys
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
from quart import Quart, render_template, request, flash, redirect, url_for

os.system("cls")


def start_screen(first='Start'):
    print(f"1 - {colored(first, color='cyan')}\n"
          f"2 - {colored('Introduction', color='yellow')}\n"
          f"3 - {colored('Check for Updates', color='green')}\n"
          f"4 - {colored('Quit', color='red')}\n")
    if first == 'Start':
        print(colored("Please consider using the Print Explanations option in case it's unclear what the minigame does.", 'red'))
    choice = validate_input('Pick one: ', requires_int=True, int_range=(1, 4))
    if choice == 4:
        raise SystemExit(0)
    elif choice == 3:
        check_for_updates()
    elif choice == 1:
        start_program()
    elif choice == 2:
        print_intro()


def color_this(text: str, word_and_color: tuple):
    return text.replace(word_and_color[0], f"{colored(*word_and_color)}")


def color_with_list(text: str, words_and_colors: list):
    for word, color in zip(words_and_colors[::2], words_and_colors[1::2]):
        text = color_this(text, (word, color))
    return text


def print_intro():
    if os.path.exists('lib/code/'):
        try:
            with open("lib/code/explanation.txt", "r") as f:
                explanation = f.read().strip()
        except FileNotFoundError:
            with open("explanation.txt", "r") as f:
                explanation = f.read().strip()
        words_and_colors = ['companies', 'yellow', 'company', 'yellow', 'stocks', 'cyan', 'announcement', 'blue',
                            'month', 'green', 'months', 'green', 'announced', 'blue', 'bankrupt', 'red', 'users', 'magenta',
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
          f"Those are usually solved by deleting {colored('lib/db.sqlite', 'green')}")
    input("Press enter to continue...")
    porcelain.pull("lib/code/")
    print(f"{colored('Program Updated [if there was any update available, the following text should let you figure that out]', 'green')}")
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
        main()


if __name__ == '__main__':
    first = 'Start'
    if not os.path.exists('lib/code/'):
        first = 'Install'
    start_screen(first=first)

