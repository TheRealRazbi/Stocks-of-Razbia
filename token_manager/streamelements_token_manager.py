__all__ = ["StreamElementsTokenManager"]

import aiohttp

from .abstract_token_manager import AbstractTokenManager

from datetime import timedelta


class StreamElementsTokenManager(AbstractTokenManager):
    validate_url_endpoint = 'https://api.streamelements.com/oauth2/validate'
    refresh_url_endpoint = 'https://razbi.funcity.org/stocks-chat-minigame/stream_elements/refresh_token'
    user_info_endpoint = 'https://api.streamelements.com/kappa/v2/channels/'

    token_db_name = 'stream_elements_key'
    token_name = 'Stream_elements'
    user_id = None
    attrs_to_save_from_validate = {'user_id': 'channel_id'}
    refresh_before_expires = timedelta(days=5)

    async def get_user_id(self):
        if self.user_id is None:
            await self.validate_token()
        return self.user_id

    async def get_channel_name(self):
        if self.display_name:
            return self.display_name

        querystring = {'access_token': f'{self.token}', 'Accept': 'application/json'}
        async with aiohttp.ClientSession() as session:
            async with session.get(url=f'{self.user_info_endpoint}/{await self.get_user_id()}',
                                   params=querystring) as res:
                if res.status == 200:
                    self.display_name = (await res.json()).get('username')
                    return self.display_name
                elif res.status == 500:
                    raise ValueError("Streamelements servers are down. The program cannot recover from this state")
                else:
                    raise ValueError(f"Unhandled status code: {res.status} | {res.content}")
