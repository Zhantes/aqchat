import os
from typing import List

from langchain_core.documents import Document

class AbstractMemoryPipeline:
    """This interface represents a pipeline for indexing
    and maintaining a database over some kind of file system which
    backs memory retrieval.

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

    def clear(self) -> None:
        """Clear *in-memory* state - keep the persisted DB intact."""
        raise NotImplementedError

    def has_vector_db(self) -> bool:
        """Return True if there is a loaded vector store present."""
        raise NotImplementedError

    def clear_vector_db(self) -> None:
        """Delete the persisted database on disk and reset state."""
        raise NotImplementedError
    
    def ready_for_retrieval(self) -> bool:
        """Returns True if the pipeline is ready to be used."""
        raise NotImplementedError

    def invoke(self, input: str) -> List[Document]:
        """Invoke the memory retriever and return the resulting documents."""
        raise NotImplementedError
    