__all__ = ['TokenManager']

from typing import Optional

from utils import CurrencySystem

from .streamelements_token_manager import StreamElementsTokenManager
from .streamlabs_token_manager import StreamlabsTokenManager
from .twitch_token_manager import TwitchTokenManager


class TokenManager:
    def __init__(self, currency_system: CurrencySystem = None):
        self.twitch_token_manager = TwitchTokenManager()
        self.currency_system_manager: Optional[StreamlabsTokenManager, StreamlabsTokenManager] = None

        if currency_system:
            self.set_currency_system(currency_system)

    async def validate_tokens(self) -> None:
        return await self.validate_twitch_token() and await self.validate_currency_system()

    async def validate_twitch_token(self) -> bool:
        return await self.twitch_token_manager.validate_token()

    async def validate_currency_system(self):
        if self.currency_system_manager is not None:
            return await self.currency_system_manager.validate_token()

    def load_twitch_token(self):
        self.twitch_token_manager.load_token()

    def load_currency_system_token(self):
        self.currency_system_manager.load_token()

    def set_currency_system(self, currency_system: CurrencySystem):
        if currency_system.value is CurrencySystem.STREAMLABS.value:
            self.currency_system_manager = StreamlabsTokenManager()
        elif currency_system.value is CurrencySystem.STREAM_ELEMENTS.value:
            self.currency_system_manager = StreamElementsTokenManager()
        else:
            raise ValueError("Unsupported Currency System by the TokenManager")

    @property
    async def tokens_ready(self):
        return await self.validate_tokens()

    async def get_channel_name(self):
        if self.currency_system_manager is None:
            raise ValueError("No currency system selected but tried fetching channel name")
        channel_name = await self.currency_system_manager.get_channel_name()
        if channel_name is None:
            raise ValueError("Channel Name not found. Tell Razbi about it")

        return channel_name

    def get_bot_account_name(self):
        bot_name = self.twitch_token_manager.get_channel_name()
        if bot_name is None:
            raise ValueError("Bot Name not found. Tell Razbi about it")

        return bot_name
