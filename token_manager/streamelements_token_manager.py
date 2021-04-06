__all__ = ["StreamElementsTokenManager"]

from .abstract_token_manager import AbstractTokenManager

from datetime import timedelta


class StreamElementsTokenManager(AbstractTokenManager):
    validate_url_endpoint = 'https://api.streamelements.com/oauth2/validate'
    refresh_url_endpoint = 'https://razbi.funcity.org/stocks-chat-minigame/stream_elements/refresh_token'
    token_db_name = 'stream_elements_key'
    token_name = 'Stream_elements'
    attrs_to_save_from_validate = {'user_id': 'channel_id'}
    refresh_before_expires = timedelta(days=30)
