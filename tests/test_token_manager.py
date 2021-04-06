import aiounittest

from aioresponses import aioresponses
import asyncio

from tests.test_database import AbstractAsyncTestDatabase
from token_manager import TokenManager
from database import Settings
from utils import CurrencySystem


class AbstractTokenManagerTestCase(AbstractAsyncTestDatabase):
    GENERIC_TOKEN = "hfd0mnw1k23mm918w31lxoyr2a6bh2"
    token_name = ''

    def setUp(self) -> None:
        super(AbstractTokenManagerTestCase, self).setUp()
        self.token_manager = TokenManager()

    def _add_token(self, token_name, token_value):
        self.session.add(Settings(key=token_name, value=token_value))
        self.session.commit()
        return token_value

    def add_token(self, token_value):
        return self._add_token(token_name=self.token_name, token_value=token_value)

    def tearDown(self) -> None:
        self.session.close()


class TwitchTokenManagerTestCase(AbstractTokenManagerTestCase):
    TWITCH_VALIDATE_URL_ENDPOINT = 'https://id.twitch.tv/oauth2/validate'
    TWITCH_REFRESH_URL_ENDPOINT = 'https://razbi.funcity.org/stocks-chat-minigame/twitch/refresh_token'
    token_name = 'twitch_key'

    @staticmethod
    def generate_fake_validate_details(user_id=None, login=None, expires_in=None):
        return {'user_id': user_id if user_id else 123,
                'login': login if login else 'razbi',
                'expires_in': expires_in if expires_in else 30_000}

    async def test_twitch_token_non_existent(self):
        self.assertFalse(await self.token_manager.validate_twitch_token())

    async def test_invalid_or_non_refresh_able_twitch_token(self):
        fake_token = self.add_token(self.GENERIC_TOKEN)
        self.token_manager.twitch_token_manager.load_token()
        with aioresponses() as m:
            for i in range(2):
                m.get(self.TWITCH_VALIDATE_URL_ENDPOINT, status=401)
            m.get(f'{self.TWITCH_REFRESH_URL_ENDPOINT}?access_token={fake_token}', status=500, payload={'code': 'invalid token'})

            self.assertFalse(await self.token_manager.validate_twitch_token())
        await asyncio.sleep(.2)

    async def test_expired_refresh_able_twitch_token(self):
        fake_token = self.add_token(self.GENERIC_TOKEN)
        self.token_manager.twitch_token_manager.load_token()
        with aioresponses() as m:
            for status_code in (401, 200):
                m.get(self.TWITCH_VALIDATE_URL_ENDPOINT, status=status_code, payload=self.generate_fake_validate_details())
            m.get(f'{self.TWITCH_REFRESH_URL_ENDPOINT}?access_token={fake_token}', status=200, payload=dict(access_token='fake new access token'))
            self.assertTrue(await self.token_manager.validate_twitch_token())

    async def test_almost_expired_refresh_able_twitch_token(self):
        fake_token = self.add_token(self.GENERIC_TOKEN)
        self.token_manager.twitch_token_manager.load_token()
        with aioresponses() as m:
            m.get(self.TWITCH_VALIDATE_URL_ENDPOINT, status=200, payload=self.generate_fake_validate_details(expires_in=120))
            m.get(f'{self.TWITCH_REFRESH_URL_ENDPOINT}?access_token={fake_token}', status=200, payload=dict(access_token='fake new access token'))
            m.get(self.TWITCH_VALIDATE_URL_ENDPOINT, status=200, payload=self.generate_fake_validate_details())
            self.assertTrue(await self.token_manager.validate_twitch_token())

    async def test_saving_attributes_from_twitch_validate(self):
        self.add_token('fake_token')
        self.token_manager.twitch_token_manager.load_token()
        with aioresponses() as m:
            fake_details_payload = self.generate_fake_validate_details()
            m.get(self.TWITCH_VALIDATE_URL_ENDPOINT, status=200, payload=fake_details_payload)
            await self.token_manager.validate_twitch_token()
            for saved_attr, needs_save_attr in self.token_manager.twitch_token_manager.attrs_to_save_from_validate.items():
                self.assertEqual(getattr(self.token_manager.twitch_token_manager, saved_attr), fake_details_payload.get(needs_save_attr))


class StreamElementsTokenManagerTestCase(AbstractTokenManagerTestCase):
    STREAM_ELEMENTS_VALIDATE_URL_ENDPOINT = 'https://api.streamelements.com/oauth2/validate'
    STREAM_ELEMENTS_REFRESH_URL_ENDPOINT = 'https://razbi.funcity.org/stocks-chat-minigame/stream_elements/refresh_token'
    token_name = 'stream_elements_key'

    @staticmethod
    def generate_fake_validate_details(channel_id=None, expires_in=None):
        return {'channel_id': channel_id if channel_id else 123,
                'expires_in': expires_in if expires_in else 2_628_000}

    def setUp(self) -> None:
        super(StreamElementsTokenManagerTestCase, self).setUp()
        self.token_manager.set_currency_system(CurrencySystem.STREAM_ELEMENTS)

    def load_token(self):
        self.token_manager.currency_system_manager.load_token()

    async def test_stream_elements_token_non_existent(self):
        self.assertFalse(await self.token_manager.validate_currency_system())

    async def test_invalid_or_non_refresh_able_stream_elements_token(self):
        fake_token = self.add_token(self.GENERIC_TOKEN)
        self.load_token()
        with aioresponses() as m:
            for i in range(2):
                m.get(self.STREAM_ELEMENTS_VALIDATE_URL_ENDPOINT, status=401)
            m.get(f'{self.STREAM_ELEMENTS_REFRESH_URL_ENDPOINT}?access_token={fake_token}', status=500, payload={'code': 'invalid token'})

            self.assertFalse(await self.token_manager.validate_currency_system())

    async def test_expired_refresh_able_stream_elements_token(self):
        fake_token = self.add_token(self.GENERIC_TOKEN)
        self.load_token()
        with aioresponses() as m:
            for status_code in (401, 200):
                m.get(self.STREAM_ELEMENTS_VALIDATE_URL_ENDPOINT, status=status_code, payload=self.generate_fake_validate_details())
            m.get(f'{self.STREAM_ELEMENTS_REFRESH_URL_ENDPOINT}?access_token={fake_token}', status=200, payload=dict(access_token='fake new access token'))
            self.assertTrue(await self.token_manager.validate_currency_system())

    async def test_almost_expired_refresh_able_stream_elements_token(self):
        fake_token = self.add_token(self.GENERIC_TOKEN)
        self.load_token()
        with aioresponses() as m:
            m.get(self.STREAM_ELEMENTS_VALIDATE_URL_ENDPOINT, status=200, payload=self.generate_fake_validate_details(expires_in=120))
            m.get(f'{self.STREAM_ELEMENTS_REFRESH_URL_ENDPOINT}?access_token={fake_token}', status=200, payload=dict(access_token='fake new access token'))
            m.get(self.STREAM_ELEMENTS_VALIDATE_URL_ENDPOINT, status=200, payload=self.generate_fake_validate_details())
            self.assertTrue(await self.token_manager.validate_currency_system())

    async def test_saving_attributes_from_stream_elements_validate(self):
        self.add_token('fake_token')
        self.load_token()
        with aioresponses() as m:
            fake_details_payload = self.generate_fake_validate_details()
            m.get(self.STREAM_ELEMENTS_VALIDATE_URL_ENDPOINT, status=200, payload=fake_details_payload)
            await self.token_manager.validate_currency_system()
            for saved_attr, needs_save_attr in self.token_manager.currency_system_manager.attrs_to_save_from_validate.items():
                self.assertEqual(getattr(self.token_manager.currency_system_manager, saved_attr), fake_details_payload.get(needs_save_attr))


class StreamlabsTokenManagerTestCase(AbstractTokenManagerTestCase):
    STREAMLABS_VALIDATE_URL_ENDPOINTS = 'https://streamlabs.com/api/v1.0/user'
    token_name = 'streamlabs_key'

    def setUp(self) -> None:
        super(StreamlabsTokenManagerTestCase, self).setUp()
        self.token_manager.set_currency_system(CurrencySystem.STREAMLABS)

    def load_token(self):
        self.token_manager.currency_system_manager.load_token()

    @staticmethod
    def generate_fake_validate_details(user_id=None, display_name=None):
        return {
            "twitch": {
                'id': user_id if user_id else 123,
                'display_name': display_name if display_name else "Razbi"
            }
        }

    async def test_valid_streamlabs_token(self):
        fake_token = self.add_token("fake_valid_token")
        self.load_token()
        with aioresponses() as m:
            m.get(f'{self.STREAMLABS_VALIDATE_URL_ENDPOINTS}?access_token={fake_token}', status=200, payload=self.generate_fake_validate_details())
            self.assertTrue(await self.token_manager.validate_currency_system())

    async def test_invalid_streamlabs_token(self):
        fake_token = self.add_token("fake_invalid_token")
        self.load_token()
        with aioresponses() as m:
            m.get(f'{self.STREAMLABS_VALIDATE_URL_ENDPOINTS}?access_token={fake_token}', status=401, payload=self.generate_fake_validate_details())
            self.assertFalse(await self.token_manager.validate_currency_system())

    async def test_saving_attributes_from_streamlabs_validate(self):
        fake_token = self.add_token('fake_token')
        self.load_token()
        fake_details_payload = self.generate_fake_validate_details()
        with aioresponses() as m:
            m.get(f'{self.STREAMLABS_VALIDATE_URL_ENDPOINTS}?access_token={fake_token}', status=200, payload=fake_details_payload)
            await self.token_manager.validate_currency_system()
            self.assertTrue(self.token_manager.currency_system_manager.display_name, fake_details_payload.get('twitch').get('display_name'))


if __name__ == '__main__':
    aiounittest.async_test()
