from threading import Lock
from typing import Dict, List, Sequence, Iterator

from langchain_core.messages.base import BaseMessageChunk
from langchain_community.chat_models import ChatOllama
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
        *,
        ollama_model: str = "qwen3:32B",
        ollama_url: str | None = None,
    ) -> None:
        # allocate mutex
        self.lock = Lock()

        # Connect to Ollama
        self.model = ChatOllama(model=ollama_model, base_url=ollama_url)

    def query(self, memory: AbstractMemoryPipeline, messages: List[Dict[str, str]]) -> Iterator[BaseMessageChunk]:
        """Stream an answer for *messages*.

        ``messages`` must be a list of chat messages of the form
        ``[{"role": "user" | "assistant" | "system", "content": "..."}, ...]``.
        The final user message is treated as the question for retrieval.
        """
        with self.lock:
            if not memory.ready_for_retrieval():
                raise RuntimeError("Call .ingest(<path>) before querying.")

            question = self._extract_latest_user_message(messages)
            if question is None:
                raise ValueError("No user message found in conversation history.")

            # Retrieve relevant context for the *current* question only
            docs = memory.invoke(question)
            context = "\n\n".join(d.page_content for d in docs)

            # Assemble an augmented conversation. Two system messages:
            #   1) Instructions for the assistant
            #   2) The retrieval‑augmented context
            instruct_msg = {
                "role": "system",
                "content": (
                    "You are an assistant for question-answering tasks. "
                    "Use the provided context to answer questions to the best of your ability."
                ),
            }
            context_msg = {
                "role": "system",
                "content": f"Context:\n{context}",
            }

            chat_history: Sequence[Dict[str, str]] = [instruct_msg] + messages + [context_msg]
            return self.model.stream(chat_history)
    

    def _extract_latest_user_message(self, messages: List[Dict[str, str]]) -> str | None:
        """Return the content of the *most recent* user message, or ``None``."""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                return msg.get("content", "")
        return None