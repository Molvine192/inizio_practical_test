import json
import pytest
from fastapi.testclient import TestClient
import app as app_module

ORIG_FETCH_RESULTS = app_module.fetch_results

client = TestClient(app_module.app)

FAKE_RESULTS = {
    "results": [
        {"rank": 1, "title": "Alpha", "url": "https://a.example/", "snippet": "A"},
        {"rank": 2, "title": "Beta",  "url": "https://b.example/", "snippet": "B"},
    ]
}

@pytest.fixture(autouse=True)
def patch_fetch_results(monkeypatch):
    async def fake_fetch_results(query: str):
        return FAKE_RESULTS
    monkeypatch.setattr(app_module, "fetch_results", fake_fetch_results)

def test_search_endpoint_returns_results():
    r = client.post("/search", json={"query": "test"})
    assert r.status_code == 200
    data = r.json()
    assert "results" in data
    assert len(data["results"]) == 2
    assert set(data["results"][0].keys()) == {"rank", "title", "url", "snippet"}
    assert data["results"][0]["rank"] == 1

def test_download_json_returns_file():
    r = client.post("/download/json", json={"query": "test"})
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/json")
    assert "attachment; filename=results.json" in r.headers.get("content-disposition", "").lower()

    arr = json.loads(r.content.decode("utf-8"))
    assert isinstance(arr, list)
    assert len(arr) == 2
    assert arr[0]["title"] == "Alpha"

def test_download_csv_returns_file_with_header_and_two_rows():
    r = client.post("/download/csv", json={"query": "test"})
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    assert "attachment; filename=results.csv" in r.headers.get("content-disposition", "").lower()

    lines = r.content.decode("utf-8").strip().splitlines()
    assert lines[0].strip() == "rank,title,url,snippet"
    assert len(lines) == 3  # header + 2 rows

def test_search_validation_empty_query_422():
    r = client.post("/search", json={"query": ""})
    assert r.status_code == 422
    body = r.json()
    assert body["detail"][0]["type"].startswith("string_too_short")

# 5) Пустая выдача: JSON и CSV
def test_empty_results_json_and_csv(monkeypatch):
    async def empty_results(query: str):
        return {"results": []}
    monkeypatch.setattr(app_module, "fetch_results", empty_results)

    # JSON
    rj = client.post("/download/json", json={"query": "anything"})
    assert rj.status_code == 200
    arr = json.loads(rj.content.decode("utf-8"))
    assert isinstance(arr, list)
    assert len(arr) == 0

    # CSV
    rc = client.post("/download/csv", json={"query": "anything"})
    assert rc.status_code == 200
    lines = rc.content.decode("utf-8").strip().splitlines()
    assert lines[0].strip() == "rank,title,url,snippet"
    assert len(lines) == 1  # только заголовок

# 6) CSV экранирование (запятая и перенос строки внутри полей)
def test_csv_escaping_of_commas_and_newlines(monkeypatch):
    tricky = {
        "results": [
            {
                "rank": 1,
                "title": "Hello, world\nNew line",
                "url": "https://example.com/a,b",
                "snippet": "line1\nline2"
            }
        ]
    }
    async def tricky_results(query: str):
        return tricky
    monkeypatch.setattr(app_module, "fetch_results", tricky_results)

    r = client.post("/download/csv", json={"query": "x"})
    assert r.status_code == 200
    text = r.content.decode("utf-8")
    lines = text.strip().splitlines()
    assert lines[0].strip() == "rank,title,url,snippet"
    assert '"Hello, world\nNew line"' in text or '"Hello, world\r\nNew line"' in text
    assert '"https://example.com/a,b"' in text

# 7) Fail-safe при ошибке провайдера (напр. HTTP ошибка) → пустой список
def test_provider_failure_returns_empty_results(monkeypatch):
    import httpx

    monkeypatch.setattr(app_module, "fetch_results", ORIG_FETCH_RESULTS)

    async def fake_get(self, *args, **kwargs):
        raise httpx.HTTPError("boom")

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

    r = client.post("/search", json={"query": "test"})
    assert r.status_code == 200
    data = r.json()
    assert "results" in data and data["results"] == []