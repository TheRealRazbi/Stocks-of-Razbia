import webbrowser
from getpass import getpass
from typing import Union, Dict

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
from termcolor import colored
import contextlib


class API:
    def __init__(self, overlord=None, loop=None, prefix="!"):
        self.overlord = overlord
        self.client_id = 'vLylBKwHLDIPfhUkOKexM2f6xhLe7rqmKJaeU0kB'
        self._cache = {}
        self.streamlabs_key = ''
        self.twitch_key = ''
        # self._tokens_ready = False
        self.twitch_key_requires_refreshing = False
        self.load_keys()
        self._name = None
        self.users = []
        self.conn = None
        self.prefix = prefix
        self.commands: Dict[str, Union[commands.Command, commands.Group]] = {}
        self.loop = loop
        self.started = False
        self.console_buffer = ["example1", "example2"]
        self.not_sent_buffer = []

    def load_keys(self):
        session = database.Session()
        self.load_key(key_name='streamlabs_key', session=session)
        self.load_key(key_name='twitch_key', session=session)
        self.validate_twitch_token()
        # if self.twitch_key and self.streamlabs_key and self.currency_system and self.validate_twitch_token():
        #     self.tokens_ready = True
        # if self.tokens_ready:

    def load_key(self, key_name, session=None):
        if session is None:
            session = database.Session()
        key_db = session.query(database.Settings).get(key_name)
        if key_db:
            setattr(self, key_name, key_db.value)
        else:
            if os.path.exists(f'lib/{key_name}'):
                with open(f'lib/{key_name}', 'rb') as f:
                    key = pickle.load(f)
                session.add(database.Settings(key=f'{key_name}', value=key))
                session.commit()
                os.remove(f'lib/{key_name}')
            # else:
            #     setattr(self, key_name, generate_function())

    def generate_twitch_key(self, session=None):
        input(colored(
            "Despite what the site will say, after you generate the token, put it back here so the minigame can read the chat. Press any key to continue...", 'red'))
        # self.twitch_key = getpass("Please generate an IRC token and paste it here: ").strip()
        print(f"""
{colored("For security reasons if you are streaming right now: "
        "Please switch to a scene without Window Capture of the browser and without DisplayCapture, as the token will be shown in blank text.", 'red')}""")
        input("Press enter to continue with that warning in mind: ")
        webbrowser.open("https://twitchapps.com/tmi/")
        self.twitch_key = validate_input("Please generate the twitch IRC token and paste it here: ", color='magenta', character_min=30, character_max=30)

        if session is None:
            session = database.Session()
        twitch_key_db = session.query(database.Settings).get('twitch_key')
        if twitch_key_db:
            twitch_key_db.value = self.twitch_key
        else:
            session.add(database.Settings(key='twitch_key', value=self.twitch_key))
        session.commit()
        # with open("lib/twitch_key", "wb") as f:
        #     pickle.dump(self.twitch_key, f)
        return self.twitch_key

    def generate_streamlabs_key(self, session=None):
        print(f"""
{colored("For security reasons if you are streaming right now: "
        "Please switch to a scene without Window Capture of the browser and without DisplayCapture, as the token will be shown in blank text.", 'red')}""")
        input("Press enter to continue with that warning in mind: ")

        webbrowser.open("https://streamlabs.com/api/v1.0/authorize?response_type=code&client_id=vLylBKwHLDIPfhUkOKexM2f6xhLe7rqmKJaeU0kB&redirect_uri=https://razbi.funcity.org/stocks-chat-minigame/generate_token/&scope=points.read+points.write")
        self.streamlabs_key = validate_input("Please input the generated token: ", character_min=40, character_max=40, color='magenta')

        # with open("lib/streamlabs_key", "wb") as f:
        #     pickle.dump(token, f)
        if session is None:
            session = database.Session()
        streamlabs_key_db = session.query(database.Settings).get('streamlabs_key')
        if streamlabs_key_db:
            streamlabs_key_db.value = self.streamlabs_key
        else:
            session.add(database.Settings(key='streamlabs_key', value=self.streamlabs_key))
        session.commit()

        # self.streamlabs_key = token
        return self.streamlabs_key

    def get_points(self, user: str):
        if self.currency_system == 'streamlabs' and self.tokens_ready:
            url = "https://streamlabs.com/api/v1.0/points"
            querystring = {"access_token": self.streamlabs_key,
                           "username": user,
                           "channel": self.name}
            res = requests.request("GET", url, params=querystring)
            return json.loads(res.text)

    def get_user(self, *args):
        if self.currency_system == 'streamlabs' and self.tokens_ready:
            url = "https://streamlabs.com/api/v1.0/user"
            querystring = {"access_token": self.streamlabs_key}
            response = requests.request("GET", url, params=querystring)
            response_loaded = json.loads(response.text)
            if 'twitch' not in response_loaded.keys():
                print("Didn't find 'twitch' in the api.get_user(). Something's really wrong, Tell Razbi")
                print(response_loaded)
            return response_loaded

    @staticmethod
    async def fetch(session, url):
        async with session.get(url) as response:
            return await response.text()

    async def create_context(self, username, session):
        user = await self.generate_user(username, session=session)
        return contexts.UserContext(user=user, api=self, session=session)

    async def handler(self, conn, message: Message):
        # print("This is a user message", message)
        text: str = message.parameters[1].lower()
        # print(f"Parameters: {text}")

        username = message.prefix.user
        # print(f"User: {username}")
        if not text.startswith(self.prefix):
            return
        text = text[len(self.prefix):]
        command_name, *args = text.split()
        if command_name in self.commands:
            with contextlib.closing(database.Session()) as session:
                ctx = await self.create_context(username, session)
                try:
                    self.commands[command_name](ctx, *args)
                except commands.BadArgumentCount as e:
                    self.send_chat_message(f'Usage: {self.prefix}{e.usage}')
                except commands.CommandError as e:
                    self.send_chat_message(e.msg)

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
        while not self.started:
            await asyncio.sleep(.5)
        server = [Server("irc.chat.twitch.tv", 6667, password=f'oauth:{self.twitch_key}')]
        self.conn = IrcProtocol(server, nick=self.name, loop=self.loop)
        self.conn.register('PRIVMSG', self.handler)
        await self.conn.connect()
        self.conn.send(f"JOIN #{self.name}")
        print(f"{colored('Ready to read chat commands', 'green')}. "
              f"To see all basic commands type {colored('!stocks', 'magenta')} in the twitch chat")
        self.clear_unsent_buffer()
        # print(self.conn.connected)
        # await asyncio.sleep(2)
        # print(self.conn.connected)
        # self.conn.send(f"PRIVMSG #{self.name} :REEEEEEEEEEEEE")
        # self.conn.send(f"PRIVMSG #{self.name} hello")
        # print(self.twitch_key)
        await asyncio.sleep(24 * 60 * 60 * 365 * 100)

    def send_chat_message(self, message: str):
        if self.conn.connected:
            # self.clear_unsent_buffer()
            self.conn.send(f"PRIVMSG #{self.name} :{message}")
            if message != '':
                print(f"{colored('Message sent:', 'cyan')} {colored(message, 'yellow')}")
                self.console_buffer.append(message)
        else:
            print(f'{colored("No connection yet", "red")}')
            self.not_sent_buffer.append(message)

    def clear_unsent_buffer(self):
        if self.not_sent_buffer:
            temp_buffer = self.not_sent_buffer
            self.not_sent_buffer = []
            for element in temp_buffer:
                self.send_chat_message(element)

    def subtract_points(self, user: str, amount: int):
        if self.currency_system == 'streamlabs' and self.tokens_ready:
            url = "https://streamlabs.com/api/v1.0/points/subtract"
            querystring = {"access_token": self.streamlabs_key,
                           "username": user,
                           "channel": self.name,
                           "points": amount}

            return json.loads(requests.request("POST", url, data=querystring).text)["points"]

    def upgraded_subtract_points(self, user: User, amount: int, session):
        if amount < 0:
            user.gain += -amount
        elif amount > 0:
            user.lost += amount
        session.commit()
        self.subtract_points(user.name, amount)

    def command(self, **kwargs):
        return commands.command(registry=self.commands, **kwargs)

    def group(self, **kwargs):
        return commands.group(registry=self.commands, **kwargs)

    @property
    def name(self):
        if self._name:
            return self._name
        if self.tokens_ready:
            self._name = self.get_user()['twitch']['name'].strip()
            return self._name

    @property
    def currency_system(self):
        if 'currency_system' in self._cache.keys():
            return self._cache['currency_system']
        session = database.Session()
        currency_system_db = session.query(database.Settings).get('currency_system')
        if currency_system_db is not None:
            self._cache['currency_system'] = currency_system_db.value
        else:
            self._cache['currency_system'] = ''
            session.add(database.Settings(key='currency_system', value=''))
            session.commit()
        return self._cache['currency_system']

    def mark_dirty(self, setting):
        if f'{setting}' in self._cache.keys():
            del self._cache[setting]

    def validate_twitch_token(self):
        if not self.twitch_key:
            return False
        url = 'https://id.twitch.tv/oauth2/validate'
        querystring = {'Authorization': f'OAuth {self.twitch_key}'}
        res = requests.get(url=url, headers=querystring)
        if res.status_code == 200:
            self.twitch_key_requires_refreshing = False
            return True
        elif res.status_code == 401:
            print("Twitch Token expired. Refreshing Token whenever possible...")
            # requests.get(url='https://razbi.funcity.org/stocks-chat-minigame/twitch/refresh_token',
            #              params={'access_token': self.twitch_key})
            # webbrowser.open(f'https://razbi.funcity.org/stocks-chat-minigame/twitch/refresh_token?access_token={self.twitch_key}')
            # requests.get(url=f'https://razbi.funcity.org/stocks-chat-minigame/twitch_login')
            self.twitch_key_requires_refreshing = True
            # print(self.twitch_key_requires_refreshing)
            return False
        elif res.status_code >= 500:
            print("server errored or... something. better tell Razbi")
            return False
        raise ValueError("A response code appeared that Razbi didn't handle")
        # print(res.status_code)
        # print(res.text)

    @property
    def tokens_ready(self):
        if 'tokens_ready' in self._cache:
            return self._cache['tokens_ready']
        if self.twitch_key and self.streamlabs_key and self.currency_system and self.validate_twitch_token():
            self._cache['tokens_ready'] = True
            return True
        return False

    # @tokens_ready.setter
    # def tokens_ready(self, other):
    #     pass


if __name__ == '__main__':
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
