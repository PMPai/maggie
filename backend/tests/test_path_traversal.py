import pytest
from app.services.file_service import PathTraversalException, _resolve_safe_path
from app.models.document import StorageRoot


def test_path_traversal_rejected():
    root = StorageRoot.__new__(StorageRoot)
    root.base_path = "/data/archive"
    with pytest.raises(PathTraversalException):
        _resolve_safe_path(root, "../../../etc/passwd")


def test_path_traversal_double_dot_rejected():
    root = StorageRoot.__new__(StorageRoot)
    root.base_path = "/data/archive"
    with pytest.raises(PathTraversalException):
        _resolve_safe_path(root, "project/../../etc/shadow")


def test_normal_path_accepted():
    root = StorageRoot.__new__(StorageRoot)
    root.base_path = "/data/archive"
    path = _resolve_safe_path(root, "org1/proj25-032/contracts/file.pdf")
    assert str(path).startswith("/data/archive")
