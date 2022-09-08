import ast
from typing import Union, Dict
import requests
import pickle
import os
import asyncio
from asyncirc.protocol import IrcProtocol
from asyncirc.server import Server
from irclib.parser import Message

from message_manager import create_twitch_messenger, create_discord_messenger
from discord_manager import DiscordManager
from token_manager import TokenManager
from database import User, get_object_by_kwargs, AsyncSession
import database
import contexts
import commands
import discord
from termcolor import colored
from more_tools import CachedProperty, BidirectionalMap
from customizable_stuff import load_command_names, load_message_templates
from utils import CurrencySystem, print_with_time, green


class API:
    def __init__(self, overlord=None, loop=None, prefix="!"):
        self.overlord = overlord
        self._cache = {}
        self.token_manager = TokenManager()
        if self.currency_system:
            self.token_manager.set_currency_system(getattr(CurrencySystem, self.currency_system.upper()))
        self.discord_manager = DiscordManager(self)

        self.twitch_client_id = 'q4nn0g7b07xfo6g1lwhp911spgutps'
        self.twitch_key_requires_refreshing = False
        self.twitch_key_just_refreshed = False
        self.stream_elements_key_requires_refreshing = False
        self.stream_elements_key_just_refreshed = False
        self._name = None
        self.users = []
        self.conn = None
        self.prefix = prefix
        self.commands: Dict[str, Union[commands.Command, commands.Group]] = {}
        self.loop = loop
        self.started = asyncio.Event()
        self.console_buffer = ['placeholder']
        self.use_local_points_instead = True  # only use local points for offline testing and nothing else TODO remove on deploy

        # self.command_names = {('acquire', None): 'buy', ('my', None): 'my', ('income', 'my'): 'income'}
        self.command_names = {}
        self.load_command_names()
        # self.command_names = {
        #     ('stocks', None): 'stocks',
        #     ('stonks', None): 'stocks',
        # }
        self.channel_name = None
        self.console_buffer_done = []
        self.not_sent_buffer = []

        self.streamlabs_local_send_buffer = ''
        self.streamlabs_local_receive_buffer = ''
        self.streamlabs_local_buffer_lock = asyncio.Lock()
        self.streamlabs_local_send_buffer_event = asyncio.Event()
        self.streamlabs_local_receive_buffer_event = asyncio.Event()

    def load_key(self, key_name, session=None):
        if session is None:
            session = database.AsyncSession()
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

    async def create_context(self, session, username: str = None, user_id: str = None,
                             discord_message: discord.Message = None):
        user = await self.generate_user(name=username, user_id=user_id, session=session)
        if discord_message is None:
            send_message = create_twitch_messenger(self)
        else:
            send_message = create_discord_messenger(discord_message)

        return contexts.UserContext(user=user, api=self, session=session, discord_message=discord_message,
                                    send_message=send_message)

    async def handler(self, conn, message: Union[Message, str]):
        text: str = message.parameters[1].lower()
        if not text.startswith(self.prefix):
            return
        username = message.prefix.user

        text_without_prefix = text[len(self.prefix):]
        await self.run_command(username=username, text_without_prefix=text_without_prefix)

    async def run_command(self, text_without_prefix, user_id: str = None, username: str = None,
                          discord_message: discord.Message = None):
        text_without_prefix = text_without_prefix.lower()
        old_command_name, *args = text_without_prefix.split()
        command_name = self.command_names.get((old_command_name, None), old_command_name)
        command_name, _, group_name = command_name.partition(" ")
        if group_name:
            args.insert(0, group_name)
        if command_name in self.commands:
            session = database.AsyncSession()
            ctx = await self.create_context(session, user_id=user_id, username=username,
                                            discord_message=discord_message)
            command = self.commands[command_name]
            try:
                # if not command.available_on_twitch and not ctx.discord_message:
                #     await ctx.send_message("This command can only be ran in Discord. discord.gg/swavy")  # this is the discord of the person I am updating the bot for
                #     print_with_time(f"Command {command} not available on twitch chat")
                #     return
                await command(ctx, *args)
                # noinspection PyTypeChecker
            except commands.BadArgumentCount as e:
                await ctx.send_message(f'@{ctx.user.name} Usage: {self.prefix}{e.usage(name=old_command_name)}')
            except commands.ProperArgumentNotProvided as e:
                if e.arg_name in command.specific_arg_usage:
                    await ctx.send_message(command.specific_arg_usage[e.arg_name])

            except commands.CommandError as e:
                await ctx.send_message(e.msg)
            session.close()

    async def generate_user(self, user_id: str = None, name: str = None, session: AsyncSession = None,
                            discord_id: str = None):
        if user_id is None and name is None:
            raise ValueError("Tried generating a user without any user_id or name")

        local_session = False
        if session is None or type(session) is not AsyncSession:
            local_session = True
            session = AsyncSession()

        user = None
        if name and not user_id:
            user = await get_object_by_kwargs(User, session, name=name)
            user_id = await self.token_manager.twitch_token_manager.username_to_id(username=name)

        if user_id and user is None:
            user = await get_object_by_kwargs(User, session, id=user_id)

        if user is None:
            if user_id and not name:
                name = await self.token_manager.twitch_token_manager.id_to_username(user_id=user_id)
            if name and not user_id:
                user_id = await self.token_manager.twitch_token_manager.username_to_id(username=name)
            user = User(id=user_id, name=name)
            session.add(user)
        if discord_id:
            user.discord_id = discord_id
        await session.commit()
        if local_session:
            await session.close()
        return user

    async def start_read_chat(self):
        await self.tokens_ready
        await self.started.wait()
        await self.update_channel_name()
        server = [Server("irc.chat.twitch.tv", 6667, password=f'oauth:{self.token_manager.twitch_token_manager.token}')]
        self.conn = IrcProtocol(server, nick=self.name, loop=self.loop)
        self.conn.register('PRIVMSG', self.handler)
        await self.conn.connect()
        if not self.conn.connected:
            raise ConnectionError("Could not connect to twitch IRC")
        self.conn.send(f"JOIN #{self.channel_name}")
        print(f"{colored('Ready to read chat commands', 'green')}. "
              f"To see all basic commands type {colored('!stocks', 'magenta')} in the twitch chat")
        self.clear_unsent_buffer()
        if self.currency_system == 'streamlabs_local':
            await self.ping_streamlabs_local()
        # self.conn.send(f"PRIVMSG #{self.name} :I'm testing if this damn thing works")
        # self.conn.send(f"PRIVMSG #{self.name} :hello")
        await asyncio.sleep(24 * 60 * 60 * 365 * 100)

    def send_chat_message(self, message: str):
        if message == '':
            return

        if self.conn and self.conn.connected:
            self.conn.send(f"PRIVMSG #{self.channel_name} :{message}")
            print(f"{colored('Message sent:', 'cyan')} {colored(message, 'yellow')}")
            self.console_buffer.append(str(message))
        else:
            self.not_sent_buffer.append(message)

    def clear_unsent_buffer(self):
        if self.not_sent_buffer:
            temp_buffer = self.not_sent_buffer
            self.not_sent_buffer = []
            for element in temp_buffer:
                self.send_chat_message(element)

    async def add_points(self, user: str, amount: int):
        await self.tokens_ready

        if await self.tokens_ready:
            if self.currency_system == 'streamlabs':
                if self.channel_name is None:
                    await self.update_channel_name()
                url = "https://streamlabs.com/api/v1.0/points/subtract"
                querystring = {"access_token": self.streamlabs_key,
                               "username": user,
                               "channel": self.channel_name,
                               "points": -amount}

                res = requests.post(url, data=querystring)
                if res.status_code == 200:
                    points = res.json()["points"]
                    return points
                else:
                    raise ValueError(f'Error while setting points. Request: {res.content}')
            elif self.currency_system == 'stream_elements':
                url = f'https://api.streamelements.com/kappa/v2/points/{await self.stream_elements_id()}/{user}/{amount}'
                headers = {'Authorization': f'OAuth {self.stream_elements_key}'}
                res = requests.put(url, headers=headers)
                # print(res.json())
                if res.status_code == 200:
                    points = res.json()["newAmount"]
                    return points
                raise ValueError(
                    f"Error encountered while adding points with stream_elements system. HTTP Code {res.status_code}. "
                    "Please tell Razbi about it.")

                # return requests.put(url, headers=headers).json()["newAmount"]
            elif self.currency_system == 'streamlabs_local':
                await self.request_streamlabs_local_message(f'!add_points {user} {amount}')
                return 'it worked, I guess'

            raise ValueError(f"Unavailable Currency System: {self.currency_system}")
        raise ValueError("Tokens not ready for use. Tell Razbi about this.")

    async def update_channel_name(self):
        self.channel_name = await self.token_manager.get_channel_name()
        print_with_time(f"Channel name set to {green(self.channel_name)}")

    async def upgraded_add_points(self, user: User, amount: int, session: database.AsyncSession):
        user = user.refresh(session)
        if amount > 0:
            user.gain += amount
        elif amount < 0:
            user.lost -= amount
        # old_last_points = user.last_points_checked
        if self.use_local_points_instead:
            points = await user.points(api=self, session=session)
            user.local_points = points + amount
            session.commit()
        else:
            await self.add_points(user.name, amount)
        user.update_last_checked_income(session=session)
        await user.total_worth(self, session=session)  # update total worth by checking it
        # print(user.last_points_checked, old_last_points)
        session.commit()

    def command(self, **kwargs):
        return commands.command(registry=self.commands, **kwargs)

    def group(self, **kwargs):
        return commands.group(registry=self.commands, **kwargs)

    @property
    def name(self):
        return self.token_manager.get_bot_account_name()

    @CachedProperty
    def currency_system(self):
        session = database.Session()
        currency_system_db = session.query(database.Settings).get('currency_system')
        if currency_system_db is not None:
            res = currency_system_db.value
        else:
            res = ''
            session.add(database.Settings(key='currency_system', value=''))
            session.commit()
        return res

    def mark_dirty(self, setting):
        if f'{setting}' in self._cache.keys():
            del self._cache[setting]

    @property
    async def tokens_ready(self):
        if 'tokens_ready' in self._cache:
            return self._cache['tokens_ready']
        if self.currency_system and self.token_manager.twitch_token_manager.token and await self.token_manager.validate_twitch_token():
            if self.currency_system == 'streamlabs' and self.streamlabs_key or \
                    self.currency_system == 'stream_elements' and self.stream_elements_key:
                self._cache['tokens_ready'] = True
                return True

            if self.currency_system == 'streamlabs_local':
                self._cache['tokens_ready'] = True
                return True
        return False

    async def stream_elements_id(self):
        return await self.token_manager.currency_system_manager.get_user_id()

    async def ping_streamlabs_local(self):
        self.send_chat_message('!connect_minigame')
        await self.request_streamlabs_local_message(f'!get_user_points {self.name}')

    async def request_streamlabs_local_message(self, message: str):
        async with self.streamlabs_local_buffer_lock:
            self.streamlabs_local_send_buffer = message
            self.streamlabs_local_send_buffer_event.set()
            await self.streamlabs_local_receive_buffer_event.wait()
            self.streamlabs_local_receive_buffer_event.clear()
            response = self.streamlabs_local_receive_buffer
        return response

    def get_and_format(self, ctx: contexts.UserContext, message_name: str, **formats):
        if message_name not in self.overlord.messages:
            default_messages = load_message_templates()
            if message_name in default_messages:
                self.overlord.messages[message_name] = default_messages[message_name]
            else:
                return ''

        return self.overlord.messages[message_name].format(stocks_alias=self.overlord.messages['stocks_alias'],
                                                           company_alias=self.overlord.messages['company_alias'],
                                                           user_name=ctx.user.name,
                                                           currency_name=self.overlord.currency_name,
                                                           stocks_limit=f'{self.overlord.max_stocks_owned:,}',
                                                           **formats)

    def load_command_names(self):
        # self.command_names = {('acquire', None): 'buy', ('my', None): 'my', ('income', 'my'): 'income'}

        session = database.Session()
        command_names = session.query(database.Settings).get('command_names')
        if command_names:
            self.command_names = BidirectionalMap(ast.literal_eval(command_names.value))
            default_command_names = load_command_names()
            for key in default_command_names:
                if key not in self.command_names or self.command_names[key] != default_command_names[key]:
                    self.command_names[key] = default_command_names[key]
        else:
            self.command_names = load_command_names()
            # command_names = database.Settings(key='command_names', value=repr(self.command_names))
            # session.add(command_names)
            # session.commit()

    async def validate_tokens(self):
        await self.token_manager.validate_tokens()

    @property
    def twitch_key(self):
        return self.token_manager.twitch_token_manager.token

    @property
    def streamlabs_key(self):
        return self.token_manager.currency_system_manager.token

    @property
    def stream_elements_key(self):
        return self.token_manager.currency_system_manager.token

    async def announce(self, message: str = '', embed: discord.Embed = None, **kwargs):
        """Announces a message on the pre-specified text channel on discord"""
        return await self.discord_manager.announce(message, embed=embed, **kwargs)


if __name__ == '__main__':
    def main():
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
        # just FYI, if you plan on testing just API alone, do it in the Overlord.py, not here


    def main2():
        loop = asyncio.get_event_loop()

        t = TokenManager()
        res_ = loop.run_until_complete(t.get_channel_name())
        print(res_)


    main2()
