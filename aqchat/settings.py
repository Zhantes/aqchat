import json
from typing import Dict, Any
import streamlit as st
from auth import has_authorized
from misc import get_data_dir
from gh import extract_repo_name

CONFIG_PATH = get_data_dir() / "config.json"
CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)

def add_missing_defaults(config: Dict[str, Any], defaults: Dict[str, Any]) -> None:
    """Recursively add missing defaults to a config dict.

    Entries are added or updated in-place. If `defaults` contains nested
    dicts, the corresponding dicts in `config` are also updated.
    
    Args
    --
        config: A dict with no, some, or all entries filled in.

        defaults: A dict containing defaults to fill in.
    """
    for key, val in defaults.items():
        if key not in config:
            config[key] = val
        elif isinstance(val, dict):
            add_missing_defaults(config[key], val)

@st.cache_resource
def get_config() -> Dict[str, Any]:
    config_defaults = {
        "repo_url": "", "gh_user": "", "gh_token": "",
        "memory": get_memory_defaults(),
        "chat": get_chat_defaults()
    }
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                config = json.load(f)
                add_missing_defaults(config, config_defaults)
                return config
        except Exception:
            pass  # fall through to defaults on error
    return config_defaults

def get_chat_defaults():
    return {"num_ctx": 2048, 
            "temperature": 0.8, 
            "repeat_last_n": 64, 
            "repeat_penalty": 1.1, 
            "top_k": 40, 
            "top_p": 0.9, 
            "min_p": 0.0}

def get_memory_defaults():
    return {"ret_strat": "mmr", 
            "k": 6, 
            "fetch_k": 20, 
            "lambda_mult": 0.5}

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
    st.header("Git Settings")

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
    st.header("Memory Settings")

    config = get_config()
    dict_options = ["mmr", "similarity"]
    options = ["MMR", "Similarity"]
    ret_strat = st.selectbox("Retrieval Strategy", options, index=dict_options.index(config["memory"]["ret_strat"]))
    current_index = options.index(ret_strat)
    k_int = st.number_input("k", 1, 10, value=int(config["memory"]["k"]))
    disable_widget = ret_strat != "MMR"
    fetch_k = st.number_input("Fetch k", 10, 100, value=int(config["memory"]["fetch_k"]) , disabled=disable_widget)
    lambda_mult = st.number_input("Lambda mult", 0.0, 1.0, value=float(config["memory"]["lambda_mult"]), disabled=disable_widget)
    saved = st.button("Save")
    if saved:
        config["memory"]["ret_strat"] = dict_options[current_index]
        config["memory"]["k"] = k_int
        config["memory"]["fetch_k"] = fetch_k
        config["memory"]["lambda_mult"] = lambda_mult
        st.success("Settings saved! Please refresh the app to fully apply changes.")
        save_config()

def chat_settings():
    st.header("Chat Settings")
    config=get_config()

    # Currently, only temperature setting is actually supported, because of the OpenAI backend layer
    # not being compatible with many settings which ollama otherwise accepts.
    # These settings are disabled in the UI.

    with st.form(key="chat_settings"):
        with st.container(border=True) as context:
            st.header("Context")
            num_ctx = st.number_input("num_ctx", 512, 131072, value=int(config["chat"]["num_ctx"]), disabled=True)

        with st.container(border=True) as generation:
            st.header("Generation")
            temperature = st.number_input("temperature", 0.0, 1.0, value=float(config["chat"]["temperature"]))
            repeat_last_n = st.number_input("repeat_last_n", -1, 512, value=int(config["chat"]["repeat_last_n"]), disabled=True)
            repeat_penalty = st.number_input("repeat_penalty", 0.0, 2.0, value=float(config["chat"]["repeat_penalty"]), disabled=True)
            top_k = st.number_input("top_k", 0, 100, value=int(config["chat"]["top_k"]), disabled=True)
            top_p = st.number_input("top_p", 0.0, 1.0, value=float(config["chat"]["top_p"]), disabled=True)
            min_p = st.number_input("min_p", 0.0, 1.0, value=float(config["chat"]["min_p"]), disabled=True)
            
        saved = st.form_submit_button("Save")
        if saved:
            config["chat"]["num_ctx"] = num_ctx
            config["chat"]["temperature"] = temperature
            config["chat"]["repeat_last_n"] = repeat_last_n
            config["chat"]["repeat_penalty"] = repeat_penalty
            config["chat"]["top_k"] = top_k
            config["chat"]["top_p"] = top_p
            config["chat"]["min_p"] = min_p
            st.success("Settings saved! Please refresh the app to fully apply changes.")
            save_config()

def settings_main():
    st.title("Settings")
    git, memory, chat = st.tabs(["Git", "Memory", "Chat"])

    with git:
        page_settings()
    with memory:
        memory_settings()
    with chat:
        chat_settings()