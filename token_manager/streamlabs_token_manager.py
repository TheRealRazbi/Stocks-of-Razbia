__all__ = ["StreamlabsTokenManager"]

import aiohttp

from utils import print_with_time
from .abstract_token_manager import AbstractTokenManager


class StreamlabsTokenManager(AbstractTokenManager):
    token_db_name = 'streamlabs_key'
    token_name = 'Streamlabs'
    validate_url_endpoint = 'https://streamlabs.com/api/v1.0/user'

    async def validate_token(self):
        if not self.token:
            print_with_time(f"{self.token_name} Token wasn't generated yet...", "magenta")
            return False
        querystring = {'access_token': f'{self.token}'}
        async with aiohttp.ClientSession() as session:
            async with session.get(url=self.validate_url_endpoint, params=querystring) as res:
                if res.status == 200:
                    res_json = await res.json()
                    self.display_name = res_json.get("twitch", {}).get("name")

                    print_with_time(f"{self.token_name} Token validated.",
                                    "green")

                    return True
                elif res.status == 401:
                    print_with_time(
                        f"{self.token_name} Token validation failed. It seems to be invalid... Please generate a new one on the home page of the web interface ",
                        "red")
                    self.delete_token()
                    return False
                elif res.status >= 500:
                    raise ValueError(
                        f"Streamlabs token servers seem to be down. This is an unrecoverable error. Error code: {res.status} | Content {res.content.read()}")
                else:
                    raise ValueError(
                        f"A response code appeared that Razbi didn't handle when validating a {self.token_name} Token, maybe tell him? Response Code: {res.status}")

    async def refresh_token(self):
        raise NotImplemented

    async def get_channel_name(self):
        if self.display_name is None:
            await self.validate_token()

        return self.display_name
