import pytest
from gh import extract_repo_name

def test_successful_nogit():
    assert extract_repo_name("https://github.com/Zhantes/aqchat") == "aqchat"

def test_successful_git():
    assert extract_repo_name("https://github.com/Zhantes/aqchat.git") == "aqchat"

def test_successful_ssh():
    assert extract_repo_name("git@github.com:JFarAur/aqchat.git") == "aqchat"

def test_successful_nohttps():
    assert extract_repo_name("github.com/Zhantes/aqchat") == "aqchat"

def test_error_nouser_norepo():
    with pytest.raises(ValueError):
        extract_repo_name("https://github.com")

def test_error_norepo():
    with pytest.raises(ValueError):
        extract_repo_name("https://github.com/JFarAur")

def test_error_notgithub():
    with pytest.raises(ValueError):
        extract_repo_name("https://google.com")