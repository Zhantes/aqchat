import os
from typing import Dict, List, Iterator

from langchain_core.messages.base import BaseMessageChunk

class AbstractChatPipeline:
    """This interface represents an LLM chat pipeline which indexes
    and maintains a database over some kind of file system.

    NOTE: Implementers of this class MUST be thread-safe as streamlit runs
    multiple worker threads and the pipeline for a given repo will be cached,
    meaning several users having sessions may result in concurrent accesses.
    """

    # --------------------------------------------------------------
    # PUBLIC API
    # --------------------------------------------------------------

    def ingest(self, repo_path: str | os.PathLike) -> None:
        """Walk *repo_path*, index eligible files, and build the retrieval chain."""
        raise NotImplementedError

    def update_files(self, *file_paths: str | os.PathLike) -> None:
        """(Re)-index *file_paths* that were modified since the last ingest."""
        raise NotImplementedError

    def query(self, messages: List[Dict[str, str]]) -> Iterator[BaseMessageChunk]:
        """Stream an answer for *messages*.

        ``messages`` must be a list of chat messages of the form
        ``[{"role": "user" | "assistant" | "system", "content": "..."}, ...]``.
        The final user message is treated as the question for retrieval.
        """
        raise NotImplementedError

    def clear(self) -> None:
        """Clear *in-memory* state - keep the persisted DB intact."""
        raise NotImplementedError

    def has_vector_db(self) -> bool:
        """Return True if there is a loaded vector store present."""
        raise NotImplementedError

    def clear_vector_db(self) -> None:
        """Delete the persisted database on disk and reset state."""
        raise NotImplementedError

    