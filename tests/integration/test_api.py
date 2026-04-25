"""Integration tests for REST and WebSocket API."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from gotit.api.dependencies import _AppState
from gotit.app import create_app
from gotit.config import AppConfig
from gotit.domain.pipeline import VoicePipeline
from gotit.services.event_bus import EventBus
from gotit.services.session import SessionManager
from tests.conftest import FakeExecutor, FakeLLM, FakeSearcher, FakeSTT


@pytest.fixture
def app():
    config = AppConfig()
    application = create_app(config)

    application.state.app_state = _AppState(
        config=config,
        pipeline=VoicePipeline(
            stt=FakeSTT(),
            llm=FakeLLM(),
            searcher=FakeSearcher(),
            executor=FakeExecutor(),
            event_bus=EventBus(),
        ),
        event_bus=EventBus(),
        session=SessionManager(),
    )
    return application


@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


class TestHealthEndpoint:
    async def test_health(self, client):
        resp = await client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["version"] == "0.1.0"
        assert "uptime_s" in data


class TestConfigEndpoint:
    async def test_get_config(self, client):
        resp = await client.get("/api/config")
        assert resp.status_code == 200
        data = resp.json()
        assert "llm" in data
        assert "provider" in data["llm"]

    async def test_no_api_key_leak(self, client):
        resp = await client.get("/api/config")
        assert "api_key" not in resp.text


class TestDevicesEndpoint:
    async def test_list_devices(self, client):
        resp = await client.get("/api/devices")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        if data:
            assert "name" in data[0]
            assert "index" in data[0]


class TestHistoryEndpoint:
    async def test_empty_history(self, client):
        resp = await client.get("/api/history")
        assert resp.status_code == 200
        assert resp.json() == []
