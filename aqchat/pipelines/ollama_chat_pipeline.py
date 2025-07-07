from threading import Lock
from typing import Dict, List, Sequence, Iterator

from langchain_core.tools import tool
from langchain_core.messages.base import BaseMessageChunk
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from pipelines.abstract_chat import AbstractChatPipeline
from pipelines.abstract_memory import AbstractMemoryPipeline

class OllamaChatPipeline(AbstractChatPipeline):
    """Chat implementation using ollama server.

    NOTE: This class MUST be thread-safe as streamlit runs multiple worker threads
    and the pipeline for a given repo will be cached, meaning several users
    having sessions may result in concurrent accesses.
    """

    # --------------------------------------------------------------
    # INITIALISATION
    # --------------------------------------------------------------

    def __init__(
        self,
        memory: AbstractMemoryPipeline = None,
        *,
        ollama_model: str = "qwen3:32B",
        ollama_url: str | None = None,
    ) -> None:
        # allocate mutex
        self.lock = Lock()

        # Connect to Ollama
        # ChatOllama does not support tool calling unfortunately.
        # However, ollama provides an OpenAI-compatible API wrapper, so we can use
        # ChatOpenAI, which *does* work with tool calling.
        self.model = ChatOpenAI(model=ollama_model, base_url=ollama_url + "/v1", api_key="ollama")

        self.tools = []
        self.memory = memory

        if memory:
            @tool
            def search(query: str) -> str:
                """Search the codebase with a natural-language query."""
                docs = self.memory.invoke(query)
                return "\n\n".join([f"{doc.metadata}\n{doc.page_content}" for doc in docs])
        
            self.tools.append(search)

        system_message = "You are an assistant for question-answering tasks in a codebase."

        self.agent_executor = create_react_agent(self.model, self.tools, prompt=system_message)

    def query(self, messages: List[Dict[str, str]]) -> Iterator[BaseMessageChunk]:
        """Stream an answer for *messages*.

        ``messages`` must be a list of chat messages of the form
        ``[{"role": "user" | "assistant" | "system", "content": "..."}, ...]``.
        """
        with self.lock:
            if self.memory and not self.memory.ready_for_retrieval():
                raise RuntimeError("Call .ingest(<path>) before querying.")
            
            # When we call agent executor's stream, the response is a stream of tuples, where the first
            # item in the tuple is an AIMessageChunk. chat UI code is expecting a stream of AIMessageChunk objects,
            # so we need an iterator that transforms the output into the correct form.
            def transform_first_element(iterator):
                for item in iterator:
                    yield item[0]
            
            streaming_response = self.agent_executor.stream({"messages": messages}, stream_mode="messages")

            return transform_first_element(streaming_response)

    def _extract_latest_user_message(self, messages: List[Dict[str, str]]) -> str | None:
        """Return the content of the *most recent* user message, or ``None``."""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                return msg.get("content", "")
        return None