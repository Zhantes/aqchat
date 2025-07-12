import os
from pathlib import Path
import pytest
from auth import get_passcode_pin

def test_newlinefile(monkeypatch, mocker):
    monkeypatch.setenv("PASSCODE_PIN_FILE", "/fake/path/passcode_pin")
    mocker.patch.object(Path, "read_text", return_value ="4567\n")
    pin = get_passcode_pin()
    assert pin == "4567"