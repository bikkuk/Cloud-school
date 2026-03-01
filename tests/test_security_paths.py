from pathlib import Path

import pytest

from agent_studio.agents.builder import BuilderAgent
from agent_studio.storage.project_store import ProjectStore


class DummyLLM:
    def generate(self, *args, **kwargs):
        return "{}"


def test_project_store_rejects_traversal_names(tmp_path: Path):
    store = ProjectStore(str(tmp_path / "studio_projects"))
    bad_names = ["../outside", "..", "nested/name", "nested\\name", ""]
    for name in bad_names:
        with pytest.raises(ValueError):
            store.ensure_project(name)


def test_project_store_valid_name_stays_within_root(tmp_path: Path):
    store = ProjectStore(str(tmp_path / "studio_projects"))
    project = store.ensure_project("valid_project")
    assert project.resolve().relative_to((tmp_path / "studio_projects").resolve())


def test_builder_safe_relative_path_rejects_windows_abs_and_unc():
    builder = BuilderAgent(DummyLLM())
    bad_paths = [
        r"C:\\temp\\file.txt",
        r"\\\\server\\share\\file.txt",
        r"\\server\\share\\file.txt",
        "/abs/file.txt",
        "../escape.txt",
        "sub/../escape.txt",
    ]
    for p in bad_paths:
        with pytest.raises(ValueError):
            builder._safe_relative_path(p)


def test_builder_write_files_skips_unsafe_and_writes_safe(tmp_path: Path):
    builder = BuilderAgent(DummyLLM())
    outputs = tmp_path / "outputs"
    outputs.mkdir(parents=True, exist_ok=True)

    writes, messages = builder.write_files_with_preview(
        outputs,
        [
            {"path": r"C:\\temp\\file.txt", "content": "x"},
            {"path": "ok/index.html", "content": "<h1>ok</h1>"},
        ],
        lambda *_: True,
    )

    assert len(writes) == 1
    assert writes[0]["path"] == "ok/index.html"
    assert (outputs / "ok" / "index.html").exists()
    assert any("Unsafe output path rejected" in m for m in messages)
