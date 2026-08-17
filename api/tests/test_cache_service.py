import time

import pytest

from api.services import cache_service

pytestmark = pytest.mark.unit


class TestCacheService:
    def test_cache_response_and_get_cached_response(self):
        cache_service.cache_response("evaluation:1", {"score": 90})

        assert cache_service.get_cached_response("evaluation:1") == {"score": 90}

    def test_cache_miss_returns_none(self):
        assert cache_service.get_cached_response("does-not-exist") is None

    def test_clear_cache_removes_entry(self):
        cache_service.cache_response("questions:sde:junior", ["q1", "q2"])

        cache_service.clear_cache("questions:sde:junior")

        assert cache_service.get_cached_response("questions:sde:junior") is None

    def test_clear_cache_on_missing_key_does_not_raise(self):
        cache_service.clear_cache("never-existed")

    @pytest.mark.slow
    def test_ttl_expiration(self):
        cache_service.cache_response("short-lived", "value", ttl=1)
        assert cache_service.get_cached_response("short-lived") == "value"

        time.sleep(1.5)

        assert cache_service.get_cached_response("short-lived") is None
