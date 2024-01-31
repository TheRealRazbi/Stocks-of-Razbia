__all__ = ["AbstractTokenManager", "ServersDownException"]

import json
import time
from abc import ABC, abstractmethod

import aiohttp

import database
from utils import print_with_time
from datetime import timedelta
import gettext


class ServersDownException(Exception):
    pass


class AbstractTokenManager(ABC):
    refresh_url_endpoint: str = NotImplemented
    validate_url_endpoint: str = NotImplemented
    token_name: str = NotImplemented
    token_db_name: str = NotImplemented
    attrs_to_save_from_validate = {}  # {<attr_in_class>: <attr_from_validation_request>}
    refresh_before_expires: timedelta = NotImplemented

    def __init__(self):
        self.token = None
        self.display_name = None
        self.expires_at = 0
        for attr_name, _ in self.attrs_to_save_from_validate.items():
            setattr(self, attr_name, None)

        if self.token_db_name:
            self.load_token()

    def load_token(self):
        session = database.Session()

        token_db = session.query(database.Settings).get(self.token_db_name)
        if token_db:
            self.token = token_db.value
        session.close()

    def save_token(self):
        if self.token is None:
            return
        session = database.Session()

        token_db = session.query(database.Settings).get(self.token_db_name)
        if token_db:
            token_db.value = self.token
        else:
            session.add(database.Settings(key=self.token_db_name, value=self.token))
        session.commit()

    def delete_token(self):
        session = database.Session()

        token_db = session.query(database.Settings).get(self.token_db_name)
        if token_db:
            session.delete(token_db)
            session.commit()
            self.token = None

    @staticmethod
    def generate_expires_in_text_str(expires_in: timedelta):
        return f"{expires_in.days} {gettext.ngettext('day', 'days', expires_in.days)}" if expires_in.days \
            else f"{expires_in.seconds // 3600} {gettext.ngettext('hour', 'hours', expires_in.seconds // 3600)}" if expires_in >= timedelta(
            hours=3) else f"{expires_in.seconds // 60} {gettext.ngettext('minute', 'minutes', expires_in.seconds // 60)}"

    async def validate_token(self):
        if not self.token:
            self.load_token()
            if not self.token:
                print_with_time(f"{self.token_name} Token wasn't generated yet...", "magenta")
                return False

        if time.time() < self.expires_at:
            # print_with_time(f"Returning cached result available for {self.generate_expires_in_text_str(abs(timedelta(seconds=time.time() - self.expires_at)))}", "green")
            return True

        headers = {'Authorization': f'OAuth {self.token}'}
        async with aiohttp.ClientSession() as session:
            async with session.get(url=self.validate_url_endpoint, headers=headers) as res:
                if res.status == 200:
                    res_json = await res.json()
                    for name_in_class, name_in_request in self.attrs_to_save_from_validate.items():
                        setattr(self, name_in_class, res_json.get(name_in_request))

                    expires_in = timedelta(seconds=res_json.get('expires_in'))
                    self.expires_at = time.time() + expires_in.total_seconds() - self.refresh_before_expires.total_seconds()
                    expires_in_str = self.generate_expires_in_text_str(expires_in=expires_in)
                    print_with_time(f"{self.token_name} Token validated. Token expires in {expires_in_str}.",
                                    "green")
                    if expires_in <= self.refresh_before_expires:
                        print_with_time(
                            f'{expires_in_str} till {self.token_name} Token expires. Refreshing the Token...',
                            "yellow")
                        await self.refresh_token()
                    return True
                elif res.status == 401:
                    print_with_time(f"{self.token_name} Token validation failed. Refreshing Token whenever possible...",
                                    "red")
                    refresh_result = await self.refresh_token()
                    if refresh_result == "invalid token":
                        return False
                    return await self.validate_token()
                else:
                    raise ValueError(
                        f"A response code appeared that Razbi didn't handle when validating a {self.token_name} Token, maybe tell him? Response Code: {res.status}")

    async def refresh_token(self):
        if self.token is None:
            print_with_time(f"Tried refreshing {self.token_name} Token... but there was no token in the first place",
                            "red")
            return
        querystring = {'access_token': self.token}
        async with aiohttp.ClientSession() as session_:
            async with session_.get(url=self.refresh_url_endpoint, params=querystring) as res:
                if res.status == 200:
                    res_json = json.loads(await res.text())

                    self.token = res_json.get('access_token')
                    self.save_token()

                    print_with_time(f"{self.token_name} Token refreshed successfully.", 'green')

                elif res.status == 500:
                    error_message = await res.text()
                    if error_message:
                        try:
                            error_code = json.loads(error_message).get('code')
                        except json.decoder.JSONDecodeError:
                            raise ValueError(
                                f"Error message while refreshing the {self.token_name} token {error_message}")
                        else:
                            if error_code == 'invalid token':
                                print_with_time(
                                    f"Tried refreshing the {self.token_name} Token, but it's no longer valid, please generate a new one on the home page of the web interface",
                                    "red")
                                self.delete_token()
                                return 'invalid token'
                    raise ValueError(
                        f"Tried refreshing the {self.token_name} Token, but the server is down or smth, please tell Razbi about this. P.S.: This is an unrecoverable error")
                else:
                    raise ValueError(f'Unhandled status code when refreshing the {self.token_name} Token. TELL RAZBI',
                                     res.status)

    def __repr__(self):
        return f"{self.__class__.__name__}: {self.token_name=}"

    @abstractmethod
    def get_channel_name(self):
        raise NotImplemented
