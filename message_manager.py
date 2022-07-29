from discord import Message
from termcolor import colored


def create_discord_messenger(og_message: Message):
    async def send_message(message: str):
        if message is None:
            return
        message = f'{message}'
        if message.startswith("@"):
            _, _, message = message.partition(" ")
        message = message.replace("|", "│")

        print(f"{colored('Message sent:', 'cyan')} {colored(message, 'yellow')}")
        await og_message.reply(message)

    return send_message


def create_twitch_messenger(api):
    async def send_message(message: str):
        api.send_chat_message(message)

    return send_message
