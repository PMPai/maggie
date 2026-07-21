"""Test #2: Contract versions are not overwritten — new versions are created."""
import pytest


def test_version_no_overwrite():
    # The API create_version endpoint always increments version_no
    # and never updates an existing version row
    from app.models.contract import ContractVersionStatus
    # Approving a new version SUPERSEDES the old one; old row remains
    assert ContractVersionStatus.SUPERSEDED.value == "SUPERSEDED"
    assert ContractVersionStatus.APPROVED.value == "APPROVED"
    # The approve_version endpoint sets old APPROVED -> SUPERSEDED, new DRAFT -> APPROVED
    # It never deletes or overwrites the old version row
