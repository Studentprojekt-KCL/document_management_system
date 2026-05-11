from unittest import TestCase, mock

from refresh_service.token_refresh import insert_session


@mock.patch("refresh_service.token_refresh.SessionEncryption", return_value=None)
@mock.patch("refresh_service.token_refresh.RedisDataBase", return_value=None)
def test_insert_session(_, __):
    mock_redis_data_base = mock.Mock()
    mock_session_enc = mock.Mock()

    mock_redis_data_base.insert_session_token.return_value = True
    mock_session_enc.encrypt_session_vars.return_value = "enc_value"

    assert insert_session("user", "service", "refresh_url", {"session": "vars"}) == True
