from app.services.file_service import compute_sha256_bytes


def test_hash_deterministic():
    data = b"test content for hashing"
    h1 = compute_sha256_bytes(data)
    h2 = compute_sha256_bytes(data)
    assert h1 == h2
    assert len(h1) == 64


def test_hash_differs_for_different_content():
    h1 = compute_sha256_bytes(b"content A")
    h2 = compute_sha256_bytes(b"content B")
    assert h1 != h2
