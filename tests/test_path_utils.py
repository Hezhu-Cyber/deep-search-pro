import os

import pytest

from utils.path_utils import resolve_path


@pytest.fixture
def session(tmp_path):
    d = tmp_path / "output" / "session_123"
    d.mkdir(parents=True)
    return d


def test_no_session_resolves_relative_to_cwd(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "sub").mkdir()
    assert resolve_path("sub/test.md") == str((tmp_path / "sub" / "test.md").resolve())


def test_relative_joined_into_session(session):
    assert resolve_path("sub1/sub2/test.md", str(session)) == str(
        session / "sub1" / "sub2" / "test.md"
    )


def test_workspace_prefix_cleaned_into_session(session):
    assert resolve_path("/workspace/report.md", str(session)) == str(session / "report.md")


@pytest.mark.skipif(os.name != "nt", reason="仅 Windows 将无盘符绝对路径视为相对路径")
def test_unix_abs_without_drive_joined_into_session(session):
    assert resolve_path("/sub/test.md", str(session)) == str(session / "sub" / "test.md")


def test_abs_inside_session_kept(session):
    target = session / "sub" / "report.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("x", encoding="utf-8")
    assert resolve_path(str(target), str(session)) == str(target.resolve())


def test_abs_outside_session_kept(tmp_path, session):
    outside = tmp_path / "other" / "file.md"
    outside.parent.mkdir(parents=True, exist_ok=True)
    outside.write_text("x", encoding="utf-8")
    assert resolve_path(str(outside), str(session)) == str(outside.resolve())


def test_nested_session_prefix_corrected(session):
    nested = session / "session_123" / "report.md"
    nested.parent.mkdir(parents=True, exist_ok=True)
    nested.write_text("x", encoding="utf-8")
    assert resolve_path(str(nested), str(session)) == str(session / "report.md")


def test_relative_with_session_name_uses_basename(session):
    assert resolve_path("session_123/report.md", str(session)) == str(session / "report.md")


def test_relative_with_output_prefix_uses_basename(session):
    assert resolve_path("output/report.md", str(session)) == str(session / "report.md")


def test_updated_path_resolved_under_cwd(tmp_path, monkeypatch, session):
    monkeypatch.chdir(tmp_path)
    result = resolve_path("abc/updated/upload/file.pdf", str(session))
    assert result == str((tmp_path / "updated" / "upload" / "file.pdf").resolve())