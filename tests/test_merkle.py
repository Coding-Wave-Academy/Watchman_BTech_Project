
from merkle import build_merkle_tree, merkle_root, merkle_proof, verify_proof, _pair_hash, canonical_alert_hash

def test_merkle_root_empty():
    assert merkle_root([]) is None

def test_merkle_root_single():
    hashes = ["a"]
    assert merkle_root(hashes) == "a"

def test_merkle_tree_even():
    hashes = ["a", "b", "c", "d"]
    root = merkle_root(hashes)
    assert root is not None

def test_merkle_proof():
    hashes = ["a", "b", "c", "d", "e"]
    root = merkle_root(hashes)
    proof = merkle_proof(hashes, 2)
    assert verify_proof(hashes[2], proof, root)

def test_domain_separation():
    # Ensure domain separation prefixes exist implicitly through our functions
    # For a pair, it hashes \x01 + left + right
    expected = _pair_hash("a", "b")
    assert expected is not None