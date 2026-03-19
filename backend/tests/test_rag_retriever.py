"""Tests for the RAG retriever module (cosine similarity)."""

import math

from app.gateway.rag.retriever import _cosine_similarity


def test_cosine_similarity_identical_vectors() -> None:
    v = [1.0, 2.0, 3.0]
    assert abs(_cosine_similarity(v, v) - 1.0) < 1e-6


def test_cosine_similarity_orthogonal_vectors() -> None:
    a = [1.0, 0.0]
    b = [0.0, 1.0]
    assert abs(_cosine_similarity(a, b)) < 1e-6


def test_cosine_similarity_opposite_vectors() -> None:
    a = [1.0, 0.0]
    b = [-1.0, 0.0]
    assert abs(_cosine_similarity(a, b) - (-1.0)) < 1e-6


def test_cosine_similarity_different_lengths_returns_zero() -> None:
    a = [1.0, 2.0]
    b = [1.0, 2.0, 3.0]
    assert _cosine_similarity(a, b) == 0.0


def test_cosine_similarity_zero_vector_returns_zero() -> None:
    a = [0.0, 0.0, 0.0]
    b = [1.0, 2.0, 3.0]
    assert _cosine_similarity(a, b) == 0.0


def test_cosine_similarity_both_zero_vectors() -> None:
    a = [0.0, 0.0]
    b = [0.0, 0.0]
    assert _cosine_similarity(a, b) == 0.0


def test_cosine_similarity_known_value() -> None:
    a = [1.0, 2.0, 3.0]
    b = [4.0, 5.0, 6.0]
    dot = 1 * 4 + 2 * 5 + 3 * 6
    norm_a = math.sqrt(1 + 4 + 9)
    norm_b = math.sqrt(16 + 25 + 36)
    expected = dot / (norm_a * norm_b)
    assert abs(_cosine_similarity(a, b) - expected) < 1e-6


def test_cosine_similarity_negative_values() -> None:
    a = [-1.0, -2.0]
    b = [-1.0, -2.0]
    assert abs(_cosine_similarity(a, b) - 1.0) < 1e-6


def test_cosine_similarity_single_dimension() -> None:
    a = [3.0]
    b = [5.0]
    assert abs(_cosine_similarity(a, b) - 1.0) < 1e-6


def test_cosine_similarity_empty_vectors() -> None:
    assert _cosine_similarity([], []) == 0.0
