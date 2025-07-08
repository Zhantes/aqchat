import os
import streamlit as st
from gh import extract_repo_name, GitHubRepo
import settings
from pipelines import AbstractChatPipeline, AbstractMemoryPipeline, OllamaChatPipeline, CodeMemoryPipeline, TestingChatPipeline
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
def get_memory_pipeline(repo_name: str) -> AbstractMemoryPipeline:
    print(f"[pipeline] making memory pipeline for {repo_name}")

    data_dir = get_data_dir()

    pipeline_setting = os.environ.get('USE_CHAT_PIPELINE', "TESTING")

    # If Ollama is specified, then we will call the ollama server
    # for embeddings using the specified embedding model.
    if pipeline_setting == "OLLAMA":
        ollama_url = os.environ.get('OLLAMA_URL', "http://localhost:11434")
        print(f"[pipeline] using embedding from ollama server on {ollama_url}")

        ollama_embedding_model = os.environ.get('OLLAMA_EMBEDDING_MODEL', "unclemusclez/jina-embeddings-v2-base-code")
        print(f"[pipeline] using embedding model {ollama_embedding_model}")
    else:
        ollama_url = None
        ollama_embedding_model = None
        print("[pipeline] no ollama server set; using default embedding model")

    memory = CodeMemoryPipeline(
        persist_directory=data_dir / f"chroma/{repo_name}",
        ollama_url=ollama_url,
        ollama_embedding_model=ollama_embedding_model
    )

    # If the pipeline didn't load the vector store from disk,
    # then we need to process the repo for the first time.
    if not memory.has_vector_db():
        memory.ingest(data_dir / f"repos/{repo_name}")

    return memory

def get_chat_pipeline(repo_name: str) -> AbstractChatPipeline:
    chat_pipeline = st.session_state.get("chat_pipeline")
    if chat_pipeline:
        print(f"[pipeline] acquired existing chat pipeline for {repo_name}")
        return chat_pipeline

    print(f"[pipeline] making chat pipeline for {repo_name}")

    memory = get_memory_pipeline(repo_name)

    pipeline_setting = os.environ.get('USE_CHAT_PIPELINE', "TESTING")

    # If Ollama is specified in the USE_CHAT_PIPELINE environment
    # variable, then initialize the ollama chat pipeline.

    # Otherwise (as in, by default) initialize the testing pipeline.
    # In a development environment, this allows us to test
    # the server without depending on an LLM server.
    if pipeline_setting == "OLLAMA":
        ollama_url = os.environ.get('OLLAMA_URL', "http://localhost:11434")
        print(f"[pipeline] connecting to ollama server on {ollama_url}")

        ollama_model = os.environ.get('OLLAMA_MODEL', "qwen3:32B")
        print(f"[pipeline] using model {ollama_model}")

        chat_pipeline = OllamaChatPipeline(
            memory=memory,
            ollama_url=ollama_url,
            ollama_model=ollama_model,
        )
    else:
        chat_pipeline = TestingChatPipeline(memory=memory)
    
    st.session_state["chat_pipeline"] = chat_pipeline
    return chat_pipeline

def update_repo(repo: GitHubRepo):
    print(f"[repo,pipeline] syncing {repo.remote_url}")
    repo_name: str = extract_repo_name(repo.remote_url)

    memory: AbstractMemoryPipeline = get_memory_pipeline(repo_name)

    cb = lambda path: memory.update_files(path)
    callbacks = {
        "added": [cb],
        "removed": [cb],
        "modified": [cb],
    }

    repo.pull(callbacks)