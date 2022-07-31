import discord
from discord import Message
from termcolor import colored


def create_discord_messenger(og_message: Message):
    async def send_message(message: str = None, embed: discord.Embed = None, no_reply=True):
        if message is None and embed is None:
            return
        if message:
            message = f'{message}'
            if message.startswith("@"):
                _, _, message = message.partition(" ")
                message = f'<@{og_message.author.id}> ' + message
            message = message.replace("|", "│")

            print(f"{colored('Message sent:', 'cyan')} {colored(message, 'yellow')}")
        if embed:
            print(f"{colored('Embed sent:', 'cyan')} {colored(embed.title, 'yellow')}")
        if no_reply:
            await og_message.channel.send(message, embed=embed)
        else:
            await og_message.reply(message, embed=embed)

    return send_message


def create_twitch_messenger(api):
    async def send_message(message: str):
        api.send_chat_message(message)

    return send_message
