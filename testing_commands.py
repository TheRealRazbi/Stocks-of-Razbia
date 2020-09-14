import contextlib

import commands
import database
import contexts
from customizable_stuff import load_message_templates


class FakeAPI:
    def __init__(self, fake_overlord, name: str, commands: dict, command_names: dict, user_points: int):
        self.overlord = fake_overlord
        self.message_sent_buffer = []
        self.name = name
        self.prefix = '!'
        self.commands = commands
        self.command_names = command_names
        self.fake_points = user_points

    def get_and_format(self, ctx, message_name: str, **formats):
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
                                                           **formats)

    def send_chat_message(self, message: str):
        self.message_sent_buffer.append(message)

    async def generate_user(self, session=None):
        name = self.name
        local_session = False
        if session is None:
            local_session = True
            session = database.Session()
        user = session.query(database.User).filter_by(name=name).first()
        if not user:
            user = database.User(name=name)
            session.add(user)
            session.commit()
        if local_session:
            session.close()
        return user

    async def create_context(self, session):
        user = await self.generate_user(session=session)
        return contexts.UserContext(user=user, api=self, session=session)

    async def handler(self, message: str):
        text: str = message
        if not text.startswith(self.prefix):
            return
        text = text[len(self.prefix):]
        old_command_name, *args = text.split()
        command_name = self.command_names.get((old_command_name, None), old_command_name)
        command_name, _, group_name = command_name.partition(" ")
        if group_name:
            args.insert(0, group_name)
        if command_name in self.commands:
            with contextlib.closing(database.Session()) as session:
                ctx = await self.create_context(session)
                try:
                    # noinspection PyTypeChecker
                    await self.commands[command_name](ctx, *args)
                except commands.BadArgumentCount as e:
                    self.send_chat_message(f'@{ctx.user.name} Usage: {self.prefix}{e.usage(name=old_command_name)}')
                except commands.CommandError as e:
                    self.send_chat_message(e.msg)

    async def upgraded_add_points(self, user: database.User, amount: int, session):
        # await self.overlord.real_overlord.api.upgraded_add_points(user=user, amount=amount, session=session)
        self.fake_points += amount


class FakeOverlord:
    def __init__(self, messages_dict: dict, command_names: dict, currency_name: str, commands: dict, name: str, real_overlord, user_points: int):
        self.api = FakeAPI(self, name=name, commands=commands, command_names=command_names, user_points=user_points)
        self.messages = messages_dict
        self.currency_name = currency_name
        self.real_overlord = real_overlord

    def return_sent_messages(self):
        res = [message for message in self.api.message_sent_buffer]
        self.api.message_sent_buffer = []
        return res






