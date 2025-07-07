import json
from typing import Dict, Any
import streamlit as st
from auth import has_authorized
from misc import get_data_dir
from gh import extract_repo_name

CONFIG_PATH = get_data_dir() / "config.json"
CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)

@st.cache_resource
def get_config() -> Dict[str, Any]:
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass  # fall through to defaults on error
    return {"repo_url": "", "gh_user": "", "gh_token": ""}

def save_config():
    """Persist configuration atomically."""
    config = get_config()
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = CONFIG_PATH.with_suffix(".tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(config, f)
    tmp_path.replace(CONFIG_PATH)

def has_config() -> bool:
    config = get_config()

    # we don't require token to be present, in case
    # user has supplied a public repo
    config_reqs = [
        "repo_url" in config,
        "gh_user" in config
    ]

    if not all(config_reqs):
        return False
    
    format_reqs = [
        len(config["repo_url"]) != 0,
        len(config["gh_user"]) != 0
    ]
    
    if not all(format_reqs):
        return False
    
    return True

def page_settings():
    st.title("Settings")

    if not has_authorized():
        st.error("You must login with your PIN passcode before you can access this page.")
        return

    config = get_config()
    with st.form(key="settings_form"):
        repo_url = st.text_input("Repository URL :red[*]", value=config.get("repo_url", ""))
        gh_user = st.text_input("Your Github Username :red[*]", value=config.get("gh_user", ""))
        gh_token = st.text_input("Github PAT", help="Personal Access Token, only required for private repositories.", value=config.get("gh_token", ""), type="password") # TODO: Find a way to align help tooltip so it's closer to label. Also add instructions on how to find the PAT, I couldn't make the tooltip multi-line.
        saved = st.form_submit_button("Save")
        if saved:
            if repo_url and gh_user:
                try:
                    extract_repo_name(repo_url)
                except:
                    st.error("Invalid repository URL, please verify the URL and try again.")
                else:
                    config["repo_url"] = repo_url
                    config["gh_user"] = gh_user
                    config["gh_token"] = gh_token
                    st.success("Settings saved! Please refresh the app to fully apply changes.")
                    save_config()
            else:
                st.error("Please fill all required fields.")

def memory_settings():
    st.title("Memory Settings")

    ret_strat = st.selectbox("Retrieval Strategy", ["MMR", "Similarity"])
    k_int = st.number_input("k", 1, 10, 6)
    disable_widget = ret_strat != "MMR"
    fetch_k = st.number_input("Fetch k", 10, 100, 20, disabled=disable_widget)
    lambda_mult = st.number_input("Lambda mult", 0.0, 1.0, 0.5, disabled=disable_widget)