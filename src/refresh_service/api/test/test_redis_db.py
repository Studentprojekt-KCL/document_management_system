from unittest import TestCase, mock

from refresh_service.database import RedisDataBase, exceptions


class TestRedisDB(TestCase):

    @staticmethod
    def insert_session_side_effect(key, *_, **__) -> bool:
        if "auth" in key:
            raise exceptions.AuthenticationError
        if "conn" in key:
            raise exceptions.ConnectionError
        if "resp" in key:
            raise exceptions.ResponseError
        return True

    @mock.patch("refresh_service.database.RedisDataBase.__init__", return_value=None)
    def setUp(self, _):
        self.database_instance = RedisDataBase()
        mock_redis = mock.Mock()
        mock_redis.hset.side_effect = self.insert_session_side_effect
        self.database_instance.redis_instance = mock_redis

    def test_insert_session_token(self):
        token_details = self.database_instance.insert_session_token("user", "service", 0, "url", "abc")
        assert token_details == True

    def test_insert_session_token_auth_error(self):
        token_details = self.database_instance.insert_session_token("auth", "service", 0, "url", "abc")
        assert token_details == False

    def test_insert_session_token_conn_error(self):
        token_details = self.database_instance.insert_session_token("conn", "service", 0, "url", "abc")
        assert token_details == False

    def test_insert_session_token_response_error(self):
        token_details = self.database_instance.insert_session_token("response", "service", 0, "url", "abc")
        assert token_details == False
