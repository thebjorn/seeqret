"""Unit tests for seeqret.slack.padding.

The padding format is the wire-compatibility anchor between the Python
and JavaScript implementations, so these tests pin exact sizes and
reject off-by-one errors.
"""

import pytest

from seeqret.slack.padding import (
    DEFAULT_BUCKET,
    pad_to_bucket,
    unpad_from_bucket,
)


def test_round_trip_empty():
    padded = pad_to_bucket(b'')
    assert len(padded) == DEFAULT_BUCKET
    assert unpad_from_bucket(padded) == b''


def test_round_trip_short():
    payload = b'hello slack'
    padded = pad_to_bucket(payload)
    assert len(padded) == DEFAULT_BUCKET
    assert unpad_from_bucket(padded) == payload


def test_pads_to_next_bucket_medium():
    payload = b'\xAB' * 5000
    padded = pad_to_bucket(payload)
    # 4 + 5000 = 5004 -> next multiple of 4096 is 8192
    assert len(padded) == 8192
    assert unpad_from_bucket(padded) == payload


def test_round_trip_exact_bucket_fill():
    # Choose N so that 4 + N is a multiple of 4096
    N = 4096 * 2 - 4
    payload = b'\x11' * N
    padded = pad_to_bucket(payload)
    assert len(padded) == 4096 * 2
    assert unpad_from_bucket(padded) == payload


def test_rejects_truncated_blob():
    with pytest.raises(ValueError):
        unpad_from_bucket(b'\x00\x01\x02')


def test_rejects_absurd_length_prefix():
    bad = b'\x00\x0f\x42\x40' + b'\x00' * 96  # claims ~1MB payload
    with pytest.raises(ValueError):
        unpad_from_bucket(bad)


def test_custom_bucket_size():
    padded = pad_to_bucket(b'x', bucket=64)
    assert len(padded) == 64
    assert unpad_from_bucket(padded) == b'x'
