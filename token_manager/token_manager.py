__all__ = ['TokenManager']

from utils import CurrencySystem

from .streamelements_token_manager import StreamElementsTokenManager
from .streamlabs_token_manager import StreamlabsTokenManager
from .twitch_token_manager import TwitchTokenManager


class TokenManager:
    def __init__(self, currency_system: CurrencySystem = None):
        self.twitch_token_manager = TwitchTokenManager()
        self.currency_system_manager = None

        if currency_system:
            self.set_currency_system(currency_system)

    async def validate_tokens(self) -> None:
        await self.validate_twitch_token()
        await self.validate_currency_system()

    async def validate_twitch_token(self) -> bool:
        return await self.twitch_token_manager.validate_token()

    async def validate_currency_system(self):
        if self.currency_system_manager is not None:
            return await self.currency_system_manager.validate_token()

    def set_currency_system(self, currency_system: CurrencySystem):
        if currency_system.value is CurrencySystem.STREAMLABS.value:
            self.currency_system_manager = StreamlabsTokenManager()
        elif currency_system.value is CurrencySystem.STREAM_ELEMENTS.value:
            self.currency_system_manager = StreamElementsTokenManager()
        else:
            raise ValueError("Unsupported Currency System by the TokenManager")
