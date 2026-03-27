import pytest
from app.utils import validate_imo

def test_validate_imo():
    # Valid IMO numbers (examples from the internet)
    assert validate_imo("9074729") is True # IMO 9074729
    assert validate_imo(9074729) is True # Integer input
    assert validate_imo("9606900") is True # Example from user request
    assert validate_imo("9138006") is True

    # Invalid IMO numbers
    assert validate_imo("123456") is False # Too short
    assert validate_imo("12345678") is False # Too long
    assert validate_imo("abc1234") is False # Non-digits
    assert validate_imo("9074720") is False # Wrong checksum (should be 9)
    assert validate_imo("0") is False
    assert validate_imo("") is False
