from unittest import TestCase, mock

from refresh_service.session_encryption_tools import SessionEncryption
from refresh_service.database import RedisDataBase


def test_encrypt_session_vars():
    suite = SessionEncryption("test")
    session_vars = {"session": {"var": "iables"}}
    enc_string = suite.encrypt_session_vars(session_vars)

    assert isinstance(enc_string, str)
    assert len(enc_string) == 120


def test_decrypt_session_variables():
    suite = SessionEncryption("test")
    enc_string = (
        "gAAAAABp-0WcmQWLTVS1g9iVswsGEE1qXPv6ofT72yxtRryMlJFvZAuIJOCMUfQ2OAZDsXIMtV0mHbQr6D_1vjTg3FtivzuS4Zcb50EZHpLv7K22wOkj6qs="
    )
    decrypted_vars = suite.decrypt_session_variables(enc_string)

    assert decrypted_vars == {"session": {"var": "iables"}}


@mock.patch("refresh_service.database.RedisDataBase.__init__", return_value=None)
def test_get_session_token(mock_redis):
    database_instance = RedisDataBase()
    mock_redis = mock.Mock()
    mock_redis.hgetall.return_value = {"enc_object": "abc", "refresh_url": "some_url"}
    database_instance.redis_instance = mock_redis

    token_details = database_instance.get_session_token("usr", "service")
    assert token_details == ("abc", "some_url")
