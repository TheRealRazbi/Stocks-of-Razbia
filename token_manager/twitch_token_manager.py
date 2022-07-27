__all__ = ["TwitchTokenManager"]

from .abstract_token_manager import AbstractTokenManager

from datetime import timedelta


class TwitchTokenManager(AbstractTokenManager):
    token_db_name = 'twitch_key'
    token_name = 'Twitch'
    validate_url_endpoint = 'https://id.twitch.tv/oauth2/validate'
    refresh_url_endpoint = 'https://razbi.funcity.org/stocks-chat-minigame/twitch/refresh_token'
    attrs_to_save_from_validate = {'display_name': 'login', 'user_id': 'user_id'}
    refresh_before_expires = timedelta(minutes=30)

    def get_channel_name(self):
        if self.display_name:
            return self.display_name
        else:
            raise ValueError("Tried fetching channel name before it was available")
