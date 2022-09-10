__all__ = ('FakeAPI',)

import asyncio
from typing import Dict, Union

import discord
from loguru import logger

import commands
import contexts
import database
from bot_commands import register_commands
from customizable_stuff import load_command_names, load_message_templates
from database import User
from message_manager import create_twitch_messenger
from simulations.user import BaseUser


def create_discord_messenger():
    async def send_message(*args, **kwargs):
        if 'embed' in kwargs:
            embed = kwargs.pop('embed')
            logger.debug(f"Discord Message Embed: {embed.title} {embed.fields}")

        if args or kwargs:
            logger.debug(f"Discord Message: {args}, {kwargs}")

    return send_message


class FakeAPI:
    def __init__(self, overlord):
        self.overlord = overlord
        self.use_local_points_instead = True
        self.commands: Dict[str, Union[commands.Command, commands.Group]] = {}
        self.command_names = load_command_names()
        self.command_lock = asyncio.Lock()
        # noinspection PyTypeChecker
        register_commands(self)

    @classmethod
    def send_chat_message(cls, message):
        logger.debug("Sent message on chat", f"{message}")

    @classmethod
    async def announce(cls, message: str = None, embed: discord.Embed = None):
        if message:
            logger.debug(f'Announced {message}')
        if embed:
            logger.debug(f'Sent embed: {embed.title=}, {embed.fields=}')

    async def run_command(self, text_without_prefix, session, user: BaseUser = None,
                          discord_message: discord.Message = None):
        async with self.command_lock:
            text_without_prefix = text_without_prefix.lower()
            old_command_name, *args = text_without_prefix.split()
            command_name = self.command_names.get((old_command_name, None), old_command_name)
            command_name, _, group_name = command_name.partition(" ")
            if group_name:
                args.insert(0, group_name)
            if command_name in self.commands:
                ctx = await self.create_context(session, user=user,
                                                discord_message=discord_message)
                command = self.commands[command_name]
                try:
                    # if not command.available_on_twitch and not ctx.discord_message:
                    #     await ctx.send_message("This command can only be ran in Discord. discord.gg/swavy")  # this is the discord of the person I am updating the bot for
                    #     print_with_time(f"Command {command} not available on twitch chat")
                    #     return
                    await command.run_command(ctx, *args)
                    # noinspection PyTypeChecker
                except commands.BadArgumentCount as e:
                    await ctx.send_message(f'@{ctx.user.name} Usage: {e.usage(name=old_command_name)}')
                except commands.ProperArgumentNotProvided as e:
                    if e.arg_name in command.specific_arg_usage:
                        await ctx.send_message(command.specific_arg_usage[e.arg_name])

                except commands.CommandError as e:
                    await ctx.send_message(e.msg)

    async def create_context(self, session, user: BaseUser = None,
                             discord_message: discord.Message = None):
        if discord_message is None:
            send_message = create_twitch_messenger(self)
        else:
            send_message = create_discord_messenger()

        return contexts.UserContext(user=user.db_user, api=self, session=session, discord_message=discord_message,
                                    send_message=send_message)

    def command(self, **kwargs):
        return commands.command(registry=self.commands, **kwargs)

    def group(self, **kwargs):
        return commands.group(registry=self.commands, **kwargs)

    async def upgraded_add_points(self, user: User, amount: int, session: database.AsyncSession):
        user = await user.refresh(session)
        if amount > 0:
            user.gain += amount
        elif amount < 0:
            user.lost -= amount
        # old_last_points = user.last_points_checked
        points = await user.points(api=self, session=session)
        user.local_points = points + amount
        await session.commit()

        await user.update_last_checked_income(session=session)
        await user.total_worth(self, session=session)  # update total worth by checking it
        # print(user.last_points_checked, old_last_points)
        await session.commit()

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
