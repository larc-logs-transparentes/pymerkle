"""
Tests verification of Merkle-proofs
"""

import pytest
import os
import json

from pymerkle.hashing import HASH_TYPES
from pymerkle.exceptions import InvalidMerkleProof
from pymerkle import MerkleTree, MerkleVerifier
from tests.conftest import ENCODINGS


# Merkle-proof verification

def test_verify_proof_with_commitment():
    tree = MerkleTree(*[f'{i}-th record' for i in range(666)])
    proof = tree.generate_audit_proof(tree.hash('100-th record'), commit=True)
    commitment = proof.header['commitment']
    v = MerkleVerifier()
    assert v.verify_proof(proof) is v.verify_proof(proof, commitment)


# Trees setup


MAX_LENGTH = 4

trees = []
for raw_bytes in (True, False):
    for security in (True, False):
        for length in range(1, MAX_LENGTH + 1):
            for hash_type in HASH_TYPES:
                for encoding in ENCODINGS:
                    trees.append(
                        MerkleTree(
                            *['%d-th record' % i for i in range(length)],
                            hash_type=hash_type,
                            encoding=encoding,
                            security=security
                        )
                    )


# Audit proof verification

__false_audit_proofs = []
true_audit_proofs = []

for tree in trees:

    __false_audit_proofs.append(
        (
            tree,
            tree.generate_audit_proof(b'anything that has not been recorded')
        )
    )

    for index in range(0, tree.length):
        true_audit_proofs.append(
            (
                tree,
                tree.generate_audit_proof(tree.hash('%d-th record' % index))
            )
        )


@pytest.mark.parametrize("tree, proof", __false_audit_proofs)
def test_false_audit_verify_proof(tree, proof):
    v = MerkleVerifier()
    assert not v.verify_proof(proof, tree.root_hash)


@pytest.mark.parametrize("tree, proof", true_audit_proofs)
def test_true_audit_verify_proof(tree, proof):
    v = MerkleVerifier()
    assert v.verify_proof(proof, tree.root_hash)


# Consistency proof verification

trees_and_subtrees = []

for tree in trees:
    for sublength in range(1, tree.length + 1):

        trees_and_subtrees.append(
            (
                tree,
                MerkleTree(
                    *['%d-th record' % _ for _ in range(sublength)],
                    hash_type=tree.hash_type,
                    encoding=tree.encoding,
                    raw_bytes=tree.raw_bytes,
                    security=tree.security
                )
            )
        )

__false_consistency_proofs = []
true_consistency_proofs = []

for (tree, subtree) in trees_and_subtrees:

    __false_consistency_proofs.append(
        (
            tree,
            tree.generate_consistency_proof(b'anything except for the right hash')
        )
    )

    true_consistency_proofs.append(
        (
            tree,
            tree.generate_consistency_proof(subtree.root_hash)
        )
    )


@pytest.mark.parametrize("tree, consistency_proof", __false_consistency_proofs)
def test_false_consistency_verify_proof(tree, consistency_proof):
    v = MerkleVerifier()
    assert not v.verify_proof(consistency_proof, tree.root_hash)


@pytest.mark.parametrize("tree, consistency_proof", true_consistency_proofs)
def test_true_consistency_verify_proof(tree, consistency_proof):
    v = MerkleVerifier()
    assert v.verify_proof(consistency_proof, tree.root_hash)


# MerkleVerifier object

# test KeyError in verifier construction

missing_configs = [
    {
        'encoding': 0, 'raw_bytes': 0, 'security': 0,   # missing hash_type
    },
    {
        'hash_type': 0, 'raw_bytes': 0, 'security': 0,   # missing encoding
    },
    {
        'hash_type': 0, 'encoding': 0, 'security': 0,   # missing raw_bytes
    },
    {
        'hash_type': 0, 'encoding': 0, 'raw_bytes': 0,  # missing security
    },
]


@pytest.mark.parametrize('config', missing_configs)
def test_verifier_construction_error(config):
    with pytest.raises(KeyError):
        MerkleVerifier(config)


# Test verifier main exception

@pytest.mark.parametrize('tree, proof', __false_audit_proofs[:10])
def test_verifier_with_false_proofs(tree, proof):
    verifier = MerkleVerifier(proof.get_verification_params())
    with pytest.raises(InvalidMerkleProof):
        verifier.run(proof, tree.root_hash)
