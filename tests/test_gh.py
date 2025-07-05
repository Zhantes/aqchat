import pytest
from gh import extract_repo_name

#TODO: might put these two test functions in a class, as more unit tests are added
def test_successful():
    assert extract_repo_name("https://github.com/Zhantes/aqchat") == "aqchat"
    assert extract_repo_name("https://github.com/JFarAur/aqchat") == "aqchat"
    assert extract_repo_name("https://github.com/Zhantes/Task-Tracker") == "Task-Tracker"
    assert extract_repo_name("https://github.com/Zhantes/somereponame") == "somereponame"

def test_error():
    with pytest.raises(ValueError):
        extract_repo_name("https://github.com")
        extract_repo_name("https://github.com/JFarAur")
        extract_repo_name("https://github.com/JFarAur/")
        extract_repo_name("http://github.com/JFarAur/aqchat")
        extract_repo_name("github.com/JFarAur/aqchat")
        extract_repo_name("https://google.com")