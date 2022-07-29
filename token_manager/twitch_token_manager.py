__all__ = ["TwitchTokenManager"]

import aiohttp

from .abstract_token_manager import AbstractTokenManager

from datetime import timedelta


class TwitchTokenManager(AbstractTokenManager):
    token_db_name = 'twitch_key'
    token_name = 'Twitch'
    client_id = 'q4nn0g7b07xfo6g1lwhp911spgutps'
    validate_url_endpoint = 'https://id.twitch.tv/oauth2/validate'
    refresh_url_endpoint = 'https://razbi.funcity.org/stocks-chat-minigame/twitch/refresh_token'
    get_user_url_endpoint = 'https://api.twitch.tv/helix/users'
    attrs_to_save_from_validate = {'display_name': 'login', 'user_id': 'user_id'}
    refresh_before_expires = timedelta(minutes=30)

    def get_channel_name(self):
        if self.display_name:
            return self.display_name
        else:
            raise ValueError("Tried fetching channel name before it was available")

    async def id_to_username(self, user_id: str):
        headers = {'Authorization': f'Bearer {self.token}', 'Client-Id': self.client_id}
        async with aiohttp.ClientSession() as session:
            async with session.get(url=f'{self.get_user_url_endpoint}?id={user_id}', headers=headers) as res:
                if res.status == 200:
                    res_json = await res.json()
                    return res_json["data"][0].get("display_name", None)
                elif res.status == 500:
                    print("Streamelements servers are down. The program cannot recover from this state")
                else:
                    print(f"Unhandled status code: {res.status} | {res.content}")

    async def username_to_id(self, username: str):
        headers = {'Authorization': f'Bearer {self.token}', 'Client-Id': self.client_id}
        async with aiohttp.ClientSession() as session:
            async with session.get(url=f'{self.get_user_url_endpoint}?login={username}', headers=headers) as res:
                if res.status == 200:
                    res_json = await res.json()
                    return res_json["data"][0].get("id", None)
                elif res.status == 500:
                    print("Streamelements servers are down. The program cannot recover from this state")
                else:
                    print(f"Unhandled status code: {res.status} | {res.content}")
