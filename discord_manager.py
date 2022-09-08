import asyncio
from typing import Optional, Any, Dict

import aiohttp
import discord
from discord import app_commands
from termcolor import colored

from database import User, AsyncSession, select, get_object_by_kwargs
from utils import print_with_time, green
import traceback


class DiscordManager(discord.Client):
    def __init__(self, api, **kwargs):
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        super(DiscordManager, self).__init__(intents=intents, **kwargs)
        from API import API
        api: API
        self.api = api
        self.prefix = '!'
        self.CHECK_TWITCH_URL = 'https://razbi.vineyard.haus/stocks-chat-minigame/discord_user'
        self.TWITCH_LINK_ACCOUNT_URL = 'https://razbi.vineyard.haus/stocks-chat-minigame/discord_login'
        self.announce_channel: [discord.TextChannel, Optional[None]] = None
        self.cached_usernames: Dict[int: discord.User] = {}
        self.ready = asyncio.Event()

    async def on_ready(self):
        self.announce_channel = self.api.discord_manager.get_channel(1001891464621592668)
        print_with_time(f'Discord Bot connected as {green(self.user)}')
        await self.change_presence(activity=discord.Game(name="!stocks for commands"))
        self.ready.set()

    async def announce(self, message, embed: discord.Embed = None, **kwargs):
        await self.ready.wait()
        message = message.replace("|", "┇")
        if message:
            print(f"{colored('Message sent:', 'cyan')} {colored(message, 'yellow')}")
        if embed:
            print(f"{colored('Embed sent:', 'cyan')} {colored(embed.title, 'yellow')}")
        return await self.announce_channel.send(message, embed=embed, **kwargs)

    async def on_error(self, event_method: str, /, *args: Any, **kwargs: Any) -> None:
        traceback.print_exc()

    async def on_message(self, message: discord.Message):
        if not message.content.startswith(self.prefix) or message.author == self.user:
            return
        text_without_prefix = message.content[len(self.prefix):]
        if text_without_prefix == '':
            return

        discord_id = message.author.id
        # async with aclosing(AsyncSession()) as session:
        session = AsyncSession()
        twitch_id = await self.ensure_user_has_twitch(discord_id=f'{discord_id}', session=session)
        await session.close()

        if twitch_id:
            twitch_id: str
            for index, text in enumerate(text_without_prefix.split('\n')):
                if index > 0:
                    text = text[1:]
                await self.api.run_command(text_without_prefix=text, user_id=twitch_id,
                                           discord_message=message)
        else:
            await message.reply(f"Please link your twitch account: <{self.TWITCH_LINK_ACCOUNT_URL}>")

    async def ensure_user_has_twitch(self, discord_id: str, session: AsyncSession) -> [str, False]:
        user_1 = await get_object_by_kwargs(User, session=session, discord_id=discord_id)
        if user_1 is None:
            print(f"User with {discord_id=} not found by discord_id")
            if twitch_id := await self.user_has_twitch(discord_id=discord_id):
                if user := await get_object_by_kwargs(User, session, id=twitch_id):
                    # print(user)
                    user.discord_id = discord_id
                    user_id = user.id
                    # print(type(discord_id))
                    await session.commit()
                    # print(f"Set discord user {discord_id} the {twitch_id} twitch id successfully.")
                    return user_id
                else:
                    user = await self.api.generate_user(user_id=twitch_id, discord_id=discord_id, session=session)
                    user_id = user.id
                    return user_id
        else:
            return user_1.id
        return False

    async def user_has_twitch(self, discord_id: [str, int]) -> [str, None]:
        async with aiohttp.ClientSession() as session:
            async with session.get(url=self.CHECK_TWITCH_URL, params={'discord_id': discord_id}) as res:
                if res.status == 200:
                    return (await res.json())['id']
                elif res.status == 404:
                    return False
                elif res.status == 500:
                    print("Streamelements servers are down. The program cannot recover from this state")
                else:
                    print(f"Unhandled status code: {res.status} | {res.content}")

    async def start(self, *args, **kwargs):
        await self.api.started.wait()
        return await super(DiscordManager, self).start(*args, **kwargs)

    def get_user(self, id: int, /) -> Optional[User]:
        if id in self.cached_usernames:
            return self.cached_usernames[id]
        return super(DiscordManager, self).get_user(id)


if __name__ == '__main__':
    async def main(loop):
        from API import API

        d = DiscordManager(API(loop=loop))
        await d.api.validate_tokens()
        session = AsyncSession()

        # print(res.discord_id)
        await session.close()
        # api_key = os.getenv("DISCORD_API_KEY")
        # await d.start(f'{api_key}')


    async def main2(loop):
        import asyncio
        import database

        session = AsyncSession()
        try:
            # res = await get_object_by_kwargs(User, session, discord_id='')
            # print(res)
            query = select(database.Shares).where(database.Shares.user_id == '')
            query = await session.execute(query)
            print(query.scalars().all())

        finally:
            await session.close()

    async def main3(loop):  # TODO: look up discord guilds and how they work
        from API import API

        client = DiscordManager(api=API(loop=loop))
        tree = app_commands.CommandTree(client=client)


    loop = asyncio.get_event_loop()
    loop.run_until_complete(main(loop))