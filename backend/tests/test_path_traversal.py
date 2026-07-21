import pytest
from types import SimpleNamespace
from app.services.file_service import PathTraversalException, _resolve_safe_path


def _make_root(base_path: str):
    return SimpleNamespace(base_path=base_path)


def test_path_traversal_rejected():
    root = _make_root("/data/archive")
    with pytest.raises(PathTraversalException):
        _resolve_safe_path(root, "../../../etc/passwd")


def test_path_traversal_double_dot_rejected():
    root = _make_root("/data/archive")
    with pytest.raises(PathTraversalException):
        _resolve_safe_path(root, "project/../../etc/shadow")


def test_normal_path_accepted():
    root = _make_root("/data/archive")
    path = _resolve_safe_path(root, "org1/proj25-032/contracts/file.pdf")
    assert "org1" in path.parts
    assert "proj25-032" in path.parts
    assert "contracts" in path.parts
    assert "file.pdf" in path.parts
