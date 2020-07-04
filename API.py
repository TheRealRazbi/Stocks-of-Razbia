import webbrowser
from getpass import getpass
import requests
import pickle
import json
import os
import asyncio
from asyncirc.protocol import IrcProtocol
from asyncirc.server import Server
from irclib.parser import Message
from database import User
from custom_tools import validate_input
import database
from sqlalchemy.inspection import inspect
import database
import contexts
# from commands import buy_stocks
import commands


class API:
    def __init__(self, overlord=None, loop=None):
        self.overlord = overlord
        self.client_id = 'vLylBKwHLDIPfhUkOKexM2f6xhLe7rqmKJaeU0kB'
        self.streamlabs_token = ''
        self.twitch_key = ''
        self.load_keys()
        self.name = self.get_user()['twitch']['name'].strip()
        self.users = []
        self.conn = None
        self.commands = {'!buy_stocks': (commands.buy_stocks, "!buy_stocks <amount> <company>")}
        self.loop = loop

    def load_keys(self):
        self.load_streamlabs_key()
        self.load_twitch_key()

    def load_streamlabs_key(self):
        try:
            with open("lib/streamlabs_key", "rb") as f:
                try:
                    self.streamlabs_token = pickle.load(f)
                except EOFError:
                    self.generate_streamlabs_token()
                if self.streamlabs_token is None:
                    self.generate_streamlabs_token()

        except FileNotFoundError:
            with open("lib/streamlabs_key", "w"):
                pass
            self.load_streamlabs_key()

    def load_twitch_key(self):
        try:
            with open("lib/twitch_key", "rb") as f:
                try:
                    twitch_key = pickle.load(f)
                except EOFError:
                    twitch_key = self.generate_twitch_key()
                if twitch_key is None:
                    twitch_key = self.generate_twitch_key()
            self.twitch_key = twitch_key
        except FileNotFoundError:
            with open("lib/twitch_key", "w"):
                pass
            self.load_twitch_key()

    def generate_twitch_key(self):
        input(
            "Despite what the site will say, after you generate the token, put it back here so the minigame can read the chat. Press any key to continue...")
        webbrowser.open("https://twitchapps.com/tmi/")
        self.twitch_key = getpass("Please generate an IRC token and paste it here: ").strip()
        with open("lib/twitch_key", "wb") as f:
            pickle.dump(self.twitch_key, f)
        return self.twitch_key

    def generate_streamlabs_token(self):
        webbrowser.open("https://streamlabs.com/api/v1.0/authorize?response_type=code&client_id=vLylBKwHLDIPfhUkOKexM2f6xhLe7rqmKJaeU0kB&redirect_uri=https://razbi.funcity.org/stocks-chat-minigame/generate_token/&scope=points.read+points.write")
        token = validate_input("Please input the generated token: ", character_min=40, hidden=True)

        with open("lib/streamlabs_key", "wb") as f:
            pickle.dump(token, f)

        self.streamlabs_token = token
        return self.streamlabs_token

    def get_points(self, user: str):
        url = "https://streamlabs.com/api/v1.0/points"
        querystring = {"access_token": self.streamlabs_token,
                       "username": user,
                       "channel": self.name}
        res = requests.request("GET", url, params=querystring)
        return json.loads(res.text)

    def get_user(self, *args):
        url = "https://streamlabs.com/api/v1.0/user"
        querystring = {"access_token": self.streamlabs_token}
        response = requests.request("GET", url, params=querystring)
        return json.loads(response.text)

    @staticmethod
    async def fetch(session, url):
        async with session.get(url) as response:
            return await response.text()

    async def handler(self, conn, message: Message):
        # print("This is a user message", message)
        print(f"Parameters: {message.parameters[1]}")
        username = message.prefix.user
        print(f"User: {username}")

        command_name, *args = message.parameters[1].split()
        if command_name in self.commands:
            session = database.Session()
            ctx = contexts.UserContext(await self.generate_user(username, session=session), self, session=session)
            try:
                self.commands[command_name][0](ctx, *args)
            except commands.ConversionError as e:

                self.send_chat_message(f'Usage: {self.commands[command_name][1]}')
            except commands.CompanyNotFound:
                pass
        # commands.buy_stocks(ctx, message.parameters[1])
        # print()
        # params = message.parameters[1].lower()

        # commands.buy_stocks()

    @staticmethod
    async def fetch_user(name, session):
        return session.query(User).filter_by(name=name).first()

    @staticmethod
    async def generate_user(name, session=None):
        local_session = False
        if session is None:
            local_session = True
            session = database.Session()
        user = session.query(User).filter_by(name=name).first()
        if not user:
            user = User(name=name)
            session.add(user)
            session.commit()
        if local_session:
            session.close()
        return user

    async def start_read_chat(self):
        server = [Server("irc.chat.twitch.tv", 6667, password=self.twitch_key)]
        self.conn = IrcProtocol(server, nick=self.name, loop=self.loop)
        self.conn.register('PRIVMSG', self.handler)
        await self.conn.connect()
        self.conn.send(f"JOIN #{self.name}")
        # self.conn.send(f"PRIVMSG #{self.name} hello")
        await asyncio.sleep(24 * 60 * 60 * 365)

    def send_chat_message(self, message):
        if self.conn:
            self.conn.send(f"PRIVMSG #{self.name} :{message}")
            print(f"Message sent {message}")
        else:
            print('No connection yet')

    def subtract_points(self, user, amount):
        url = "https://streamlabs.com/api/v1.0/points/subtract"
        querystring = {"access_token": self.streamlabs_token,
                       "username": user,
                       "channel": self.name,
                       "points": amount}
        return json.loads(requests.request("POST", url, data=querystring).text)
        # print(res.text)


if __name__ == '__main__':
    pass
    api = API()

    loop = asyncio.get_event_loop()
    # api = API()
    # print(api.get_user('razbith3player'))
    # print(api.get_points('nerzul007'))
    # print(api.twitch_key)
    try:
        loop.run_until_complete(api.start_read_chat())
    finally:
        loop.stop()
    # print(type(api.twitch_key))
    # api.read_chat()
    # loop.run_until_complete(api.read_chat())
