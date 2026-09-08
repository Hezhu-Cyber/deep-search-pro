import asyncio
import shutil
import uuid
from pathlib import Path

from fastapi.testclient import TestClient

import api.server as server


def test_home_returns_frontend():
    with TestClient(server.app) as client:
        response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_task_returns_started(monkeypatch):
    async def noop(query, session_id):  # noqa: ANN001
        return None

    monkeypatch.setattr(server, "run_deep_agent", noop)
    captured = []
    monkeypatch.setattr(
        server.asyncio,
        "create_task",
        lambda coro, *args, **kwargs: (captured.append(coro), coro)[1],
    )
    with TestClient(server.app) as client:
        response = client.post("/api/task", json={"query": "测试一下", "thread_id": "t1"})
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "started"
    assert body["thread_id"] == "t1"
    assert len(captured) == 1
    asyncio.run(captured[0])


def test_upload_sanitizes_filename():
    tid = f"test-{uuid.uuid4().hex[:8]}"
    session_dir = server.updated_dir / f"session_{tid}"
    try:
        with TestClient(server.app) as client:
            response = client.post(
                "/api/upload",
                data={"thread_id": tid},
                files=[("files", ("../evil.txt", b"hello", "text/plain"))],
            )
        assert response.status_code == 200
        body = response.json()
        assert body["files"] == ["evil.txt"]
        assert (session_dir / "evil.txt").exists()
    finally:
        shutil.rmtree(session_dir, ignore_errors=True)


def test_download_rejects_outside_output_dir(tmp_path):
    outside = tmp_path / "secret.md"
    outside.write_text("x", encoding="utf-8")
    with TestClient(server.app) as client:
        response = client.get("/api/download", params={"path": str(outside)})
    assert response.status_code == 200
    assert "error" in response.json()


def test_list_files_rejects_outside_output_dir():
    with TestClient(server.app) as client:
        response = client.get("/api/files", params={"path": str(Path.cwd())})
    assert "error" in response.json()


def test_list_files_within_output_ok():
    session_path = server.output_dir / "session_listtest"
    session_path.mkdir(parents=True, exist_ok=True)
    (session_path / "a.md").write_text("hi", encoding="utf-8")
    try:
        with TestClient(server.app) as client:
            response = client.get("/api/files", params={"path": str(session_path)})
        assert response.status_code == 200
        names = [f["name"] for f in response.json()["files"]]
        assert "a.md" in names
    finally:
        shutil.rmtree(session_path, ignore_errors=True)