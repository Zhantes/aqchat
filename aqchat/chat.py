import re
import os
from typing import Dict
import streamlit as st
import settings
from gh import extract_repo_name, GitHubRepo
from pipelines.abstract_pipeline import AbstractChatPipeline
from pipelines.chat_rag_pipeline import ChatRAGPipeline
from auth import has_authorized
from misc import get_data_dir

@st.cache_resource
def get_repo(repo_url: str, gh_user: str) -> GitHubRepo:
    print(f"[repo] initializing {repo_url} as {gh_user}")
    config = settings.get_config()
    repo_name = extract_repo_name(repo_url)

    return GitHubRepo(
        repo_url,
        get_data_dir() / "repos" / repo_name,
        username=gh_user,
        token=config["gh_token"]
    )

@st.cache_resource
def get_pipeline(repo_name: str) -> AbstractChatPipeline:
    print(f"[pipeline] making pipeline for {repo_name}")

    ollama_url = os.environ.get('OLLAMA_URL', "http://localhost:11434")
    print(f"[pipeline] connecting to ollama server on {ollama_url}")

    ollama_model = os.environ.get('OLLAMA_MODEL', "qwen3:32B")
    print(f"[pipeline] using model {ollama_model}")

    data_dir = get_data_dir()

    pipeline = ChatRAGPipeline(
        ollama_url=ollama_url,
        persist_directory=data_dir / f"chroma/{repo_name}"
    )

    # If the pipeline didn't load the vector store from disk,
    # then we need to process the repo for the first time.
    if not pipeline.has_vector_db():
        pipeline.ingest(data_dir / f"repos/{repo_name}")

    return pipeline

def update_repo(repo: GitHubRepo):
    print(f"[repo,pipeline] syncing {repo.remote_url}")
    repo_name: str = extract_repo_name(repo.remote_url)

    pipeline: AbstractChatPipeline = get_pipeline(repo_name)

    cb = lambda path: pipeline.update_files(path)
    callbacks = {
        "added": [cb],
        "removed": [cb],
        "modified": [cb],
    }

    repo.pull(callbacks)

def get_chat_model():
    "Get an instance of the chat model"
    repo: GitHubRepo = st.session_state["gh"]
    return lambda messages: get_pipeline(repo.repo_name).query(messages)

def format_reasoning_response(thinking_content: str):
    """Format the reasoning response for display"""
    return (
        thinking_content
        .replace("<think>", "")
        .replace("</think>", "")
    )

def display_messages():
    for msg in st.session_state["messages"]:
        with st.chat_message(msg["role"]):
            if msg["role"] == "user":
                st.markdown(msg["content"])

            elif msg["role"] == "assistant":
                pattern = r"<think>(.*?)</think>"
                match = re.search(pattern, msg["content"], re.DOTALL)
                if match:
                    thinking_content = match.group(0)
                    response_content = msg["content"].replace(thinking_content, "")
                    thinking_content = format_reasoning_response(thinking_content)
                    with st.expander("Thinking complete!"):
                        st.markdown(thinking_content)
                    st.markdown(response_content)
                else:
                    st.markdown(msg["content"])

    st.session_state["thinking_spinner"] = st.empty()

def process_input():
    """Handle user input and return a response from the chat model"""
    if user_input := st.chat_input("Message", key="user_input"):
        if len(user_input.strip()) > 0:
            st.session_state["messages"].append({"role": "user", "content": user_input})
            with st.chat_message("user"):
                display_user_message(user_input)

            with st.chat_message("assistant"):
                chat_model = get_chat_model()
                stream = chat_model(st.session_state["messages"])

                thinking_content = process_thinking_phase(stream)
                response_content = process_response_phase(stream)

                st.session_state["messages"].append(
                    {"role": "assistant", "content": thinking_content + response_content}
                )

def process_thinking_phase(stream):
    """Process the thinking phase of the chat model"""
    thinking_content = ""
    with st.status("Thinking...", expanded=False) as status:
        think_placeholder = st.empty()

        for chunk in stream:
            content = chunk.content or ""
            thinking_content += content

            if "<think>" in content:
                continue
            if "</think>" in content:
                content = content.replace("</think>", "")
                status.update(label="Thinking complete!", state="complete", expanded=False)
                break

            think_placeholder.markdown(format_reasoning_response(thinking_content))

    return thinking_content

def process_response_phase(stream):
    """Process the response phase of the chat model"""
    response_placeholder = st.empty()
    response_content = ""

    for chunk in stream:
        content = chunk.content or ""
        response_content += content
        response_placeholder.markdown(response_content)

    return response_content

def display_message(message: Dict[str, str]):
    """Display a message in the chat interface"""
    role = "user" if message["role"] == "user" else "assistant"
    with st.chat_message(role):
        if role == "assistant":
            display_assistant_message(message["content"])
        else:
            display_user_message(message["content"])
            

def display_user_message(content: str):
    pattern = r"<context>(.*?)</context>"
    match = re.search(pattern, content, re.DOTALL)
    if match:
        thinking_content = match.group(0)
        response_content = content.replace(thinking_content, "")
        st.markdown(response_content)
    else:
        st.markdown(content)


def display_assistant_message(content: str):
    """Display assistant message with thinking content if present"""
    pattern = r"<think>(.*?)</think>"
    match = re.search(pattern, content, re.DOTALL)
    if match:
        thinking_content = match.group(0)
        response_content = content.replace(thinking_content, "")
        thinking_content = format_reasoning_response(thinking_content)
        with st.expander("Thinking complete!"):
            st.markdown(thinking_content)
        st.markdown(response_content)
    else:
        st.markdown(content)

def format_reasoning_response(thinking_content: str):
    """Format the reasoning response for display"""
    return (
        thinking_content
        .replace("<think>", "")
        .replace("</think>", "")
    )

def display_chat_history():
    """Display all previous messages in the chat history."""
    for message in st.session_state["messages"]:
        if message["role"] != "system":  # Skip system messages
            display_message(message)

def page_chat():
    st.title("Chat")

    if not has_authorized():
        st.error("You must login with your PIN passcode before you can access this page.")
        return

    if not settings.has_config():
        st.error("You must configure a repository URL and provide Github credentials.")
        return
    
    initialized = st.session_state.get("initialized")
    if not initialized:
        config = settings.get_config()

        repo_url: str = config["repo_url"]
        gh_user: str = config["gh_user"]

        repo: GitHubRepo = get_repo(repo_url, gh_user)
        pipeline: AbstractChatPipeline = get_pipeline(repo.repo_name)

        update_repo(repo)
        st.session_state["gh"] = repo
        st.session_state["initialized"] = True
    
    if "messages" not in st.session_state:
        st.session_state["messages"] = []

    display_messages()
    process_input()
    