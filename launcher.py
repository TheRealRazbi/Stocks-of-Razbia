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

import pkg_resources

os.system("cls")


def start_screen(first='Start'):
    print(f"1 - {colored(first, color='cyan')}\n"
          f"2 - {colored('Check for Updates', color='green')}\n"
          f"3 - {colored('Quit', color='red')}\n")
    choice = validate_input('Pick one: ', requires_int=True, int_range=(1, 3))
    if choice == 3:
        quit()
    elif choice == 2:
        check_for_updates()
    elif choice == 1:
        start_program()


def check_for_updates():
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
    print(f"{colored('If you want the program to automatically check updates and start automatically upon open. Please check the config', 'red')}")
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

