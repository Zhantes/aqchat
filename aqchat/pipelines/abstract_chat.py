from typing import Dict, List, Iterator

from langchain_core.messages.base import BaseMessageChunk

from pipelines.abstract_memory import AbstractMemoryPipeline

class AbstractChatPipeline:
    """This interface represents an LLM chat pipeline which can be
    queried with a memory interface and a current message list.

    NOTE: Implementers of this class MUST be thread-safe as streamlit runs
    multiple worker threads and the pipeline for a given repo will be cached,
    meaning several users having sessions may result in concurrent accesses.
    """

    # --------------------------------------------------------------
    # PUBLIC API
    # --------------------------------------------------------------

    def query(self, memory: AbstractMemoryPipeline, messages: List[Dict[str, str]]) -> Iterator[BaseMessageChunk]:
        """Stream an answer for *messages*.

        ``messages`` must be a list of chat messages of the form
        ``[{"role": "user" | "assistant" | "system", "content": "..."}, ...]``.
        The final user message is treated as the question for retrieval.
        """
        raise NotImplementedError

    