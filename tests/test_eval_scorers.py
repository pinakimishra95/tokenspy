"""Tests for tokenspy.eval.scorers."""
from __future__ import annotations

from tokenspy.eval.scorers import (
    contains,
    exact_match,
    levenshtein_sim,
    regex_match,
)


def test_exact_match_identical():
    assert exact_match("Paris", "Paris") == 1.0


def test_exact_match_case_insensitive():
    assert exact_match("paris", "Paris") == 1.0


def test_exact_match_different():
    assert exact_match("Berlin", "Paris") == 0.0


def test_contains_hit():
    assert contains("The capital is Paris.", "Paris") == 1.0


def test_contains_miss():
    assert contains("The capital is Berlin.", "Paris") == 0.0


def test_contains_case_insensitive():
    assert contains("The capital is paris.", "Paris") == 1.0


def test_levenshtein_identical():
    assert levenshtein_sim("hello", "hello") == 1.0


def test_levenshtein_different():
    score = levenshtein_sim("hello", "world")
    assert 0.0 <= score < 1.0


def test_levenshtein_empty_strings():
    assert levenshtein_sim("", "") == 1.0


def test_regex_match_hit():
    scorer = regex_match(r"\d+")
    assert scorer("The answer is 42", "") == 1.0


def test_regex_match_miss():
    scorer = regex_match(r"\d+")
    assert scorer("No numbers here", "") == 0.0


def test_regex_match_anchored():
    scorer = regex_match(r"^Paris$")
    assert scorer("Paris", "") == 1.0
    assert scorer("Paris, France", "") == 0.0
