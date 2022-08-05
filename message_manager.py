import discord
from discord import Message
from termcolor import colored


def create_discord_messenger(og_message: Message):
    async def send_message(message: str = None, embed: discord.Embed = None, no_reply=True, **kwargs):
        if message is None and embed is None and kwargs is {}:
            return
        if message:
            message = f'{message}'
            if message.startswith("@"):
                old_name, _, _ = message.partition(" ")
                message = message.replace(old_name, f'<@{og_message.author.id}>')
            message = message.replace("|", "│")

            print(f"{colored('Message sent:', 'cyan')} {colored(message, 'yellow')}")
        if embed:
            print(f"{colored('Embed sent:', 'cyan')} {colored(embed.title, 'yellow')}")
        if no_reply:
            msg = await og_message.channel.send(message, embed=embed, **kwargs)
        else:
            msg = await og_message.reply(message, embed=embed, **kwargs)
        return msg

    return send_message


def create_twitch_messenger(api):
    async def send_message(message: str):
        api.send_chat_message(message)

    return send_message
