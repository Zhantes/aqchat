import re
from typing import Any, Tuple
import streamlit as st
import settings
from langchain_core.messages import ToolMessage, AIMessageChunk
from gh import GitHubRepo
from pipelines import AbstractChatPipeline, AbstractMemoryPipeline
from auth import has_authorized
from eng import get_repo, update_repo, get_chat_pipeline, get_memory_pipeline

def get_chat_model():
    "Get an instance of the chat model"
    repo: GitHubRepo = st.session_state["gh"]
    chat: AbstractChatPipeline = get_chat_pipeline(repo.repo_name)
    return lambda messages: chat.query(messages)


# ---------- message UI ----------
# 
# Below functions are used for displaying messages already saved
# in the message history.

def _strip_tags(txt: str, tag: str) -> str:
    """Remove <think> wrapper. For display inside expander."""
    return txt.replace(f"<{tag}>", "").replace(f"</{tag}>", "")

def _show_thought(thought: str):
    """Render one hidden-reasoning block in a collapsible expander."""
    if thought.strip():
        with st.expander("Thinking complete!"):
            st.markdown(_strip_tags(thought, "think"))

def _show_tool(result: str):
    """Render a tool-call result in its own expander."""
    if result.strip():
        with st.expander("Tool result"):
            st.code(_strip_tags(result, "toolresult"), language=None) # render as plain monospace text

def _show_response(response: str):
    response = response.rstrip()
    if response:
        st.markdown(response)

def _display_assistant(raw: str):
    """Show stored assistant msg with each <think>...</think> collapsed."""
    parts = re.split(r"(<(?:think|toolresult)>.*?</(?:think|toolresult)>)", raw, flags=re.DOTALL)
    for part in parts:
        if part.startswith("<think>"):
            _show_thought(part)
        elif part.startswith("<toolresult>"):
            _show_tool(part)
        else:
            _show_response(part)

def display_messages():
    for msg in st.session_state["messages"]:
        if msg["role"] == "system":
            continue
        with st.chat_message(msg["role"]):
            if msg["role"] == "assistant":
                _display_assistant(msg["content"])
            else:
                st.markdown(msg["content"])

# ---------- response stream ----------
# 
# Below functions are used for receiving and displaying the streaming
# response after the latest sent message by the user.

def render_stream(stream) -> str:
    """
    Consume the model's streaming output and update the UI live.

    Returns the *full* assistant message to store in chat history:
       <think>...</think>
       <toolresult>...</toolresult>
       <think>...</think>
       FINAL ANSWER
    """

    def _receive_think(think_start: str) -> Tuple[str, Any]:
        think_block = think_start
        display_block = think_block

        start_think = "<think>" in think_start
        if start_think:
            display_block = think_block.split("<think>")[1]

        end_think = False
        chunk = None

        with st.status("Thinking...", expanded=False) as spinner:
            thought_area = st.empty()

            while start_think and not end_think:
                thought_area.markdown(display_block)

                next_chunk = next(stream, None)

                if next_chunk is None or not isinstance(next_chunk, AIMessageChunk):
                    # unexpected
                    break

                content = next_chunk.content
                think_block += content

                end_think = "</think>" in content

                if end_think:
                    content = content.split("</think>")[0]

                display_block += content
            
            if end_think:
                spinner.update(label="Thinking complete!", state="complete", expanded=False)
            else:
                # broke out of the loop due to end of stream, or an unexpected chunk type
                spinner.update(label="Thinking cancelled!", state="complete", expanded=False)

        return think_block, chunk

    def _receive_tool(tool_body: str) -> Tuple[str, Any]:
        with st.status("Using Tool...", expanded=False) as spinner:
            st.code(tool_body, language=None)
            spinner.update(label="Tool Result", state="complete", expanded=False)
        return "<toolresult>" + tool_body + "</toolresult>", None
    
    def _receive_response(response_start: str) -> Tuple[str, Any]:
        response_block = response_start
        end_response = False
        response_area = st.empty()
        chunk = None

        while not end_response:
            response_area.markdown(response_block)

            chunk = next(stream, None)

            if chunk is None or not isinstance(chunk, AIMessageChunk):
                end_response = True
            else:
                response_block += chunk.content

        if not response_block.rstrip():
            # If the response block does not actually
            # contain any whitespace characters, then 
            # we simply reset the area to empty
            # so that we don't end up displaying a markdown
            # block with one/a few whitespace characters.
            response_area.empty()

        return response_block, chunk

    blocks = []
    final_response = ""
    next_chunk = None

    while True:
        if next_chunk:
            # If there was a next chunk returned from one of the receiver methods,
            # we need to use it here instead of fetching from the iterator (otherwise
            # we would end up skipping over a chunk)
            chunk = next_chunk
            next_chunk = None
        else:
            chunk = next(stream, None)

        if chunk is None:
            break
        
        if isinstance(chunk, ToolMessage):
            block, next_chunk = _receive_tool(chunk.content)
            blocks.append(block)
        elif isinstance(chunk, AIMessageChunk) and chunk.content:
            if "<think>" in chunk.content:
                block, next_chunk = _receive_think(chunk.content)
                blocks.append(block)
            else:
                block, next_chunk = _receive_response(chunk.content)
                block = block.rstrip()
                if block:
                    final_response += block

    blocks.append(final_response)
    
    return "\n".join(blocks)

def process_input():
    user_text = st.chat_input("Message", key="user_input")
    if not user_text or not user_text.strip():
        return

    # show user bubble
    st.session_state["messages"].append({"role": "user", "content": user_text})
    with st.chat_message("user"):
        st.markdown(user_text)

    # stream assistant reply
    with st.chat_message("assistant"):
        chat_model = get_chat_model()
        stream = chat_model(st.session_state["messages"])
        full_msg = render_stream(stream)

    # save assistant reply
    st.session_state["messages"].append(
        {"role": "assistant", "content": full_msg}
    )


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

        # we don't do anything with the pipeline here, but getting an instance here will load and cache
        # it on first page load, if we don't do this then the page will lag when the user clicks
        # on Chat tab instead
        pipeline: AbstractMemoryPipeline = get_memory_pipeline(repo.repo_name)

        update_repo(repo)
        st.session_state["gh"] = repo
        st.session_state["initialized"] = True
    
    if "messages" not in st.session_state:
        st.session_state["messages"] = []

    display_messages()
    process_input()
    