from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_provider_catalog_is_available():
    response = client.get("/api/providers")
    assert response.status_code == 200
    provider_ids = {provider["id"] for provider in response.json()["providers"]}
    assert {"openai", "deepseek", "qwen", "siliconflow", "moonshot", "zhipu", "openrouter", "custom"} <= provider_ids


def test_model_test_rejects_local_network_urls_before_connecting():
    response = client.post(
        "/api/models/test",
        json={
            "provider": "custom",
            "base_url": "https://127.0.0.1/v1",
            "model": "test-model",
            "api_key": "test-only-placeholder",
        },
    )
    assert response.status_code == 200
    assert response.json()["ok"] is False
    assert "内网" in response.json()["message"]


def test_demo_generation_streams_events_without_model_credentials():
    response = client.post("/api/generate/stream", json={"topic": "Write a short book recommendation"})
    assert response.status_code == 200
    assert '"type": "meta"' in response.text
    assert '"mode": "demo"' in response.text
    assert '"type": "chunk"' in response.text
    assert '"type": "done"' in response.text
