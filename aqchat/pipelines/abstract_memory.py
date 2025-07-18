import os
from typing import List, Dict, Any
from abc import ABC, abstractmethod

from langchain_core.documents import Document

class AbstractMemoryPipeline(ABC):
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

    @abstractmethod
    def ingest(self, repo_path: str | os.PathLike) -> None:
        """Walk *repo_path*, index eligible files, and build the retrieval chain."""
        pass

    @abstractmethod  
    def update_files(self, *file_paths: str | os.PathLike) -> None:
        """(Re)-index *file_paths* that were modified since the last ingest."""
        pass

    @abstractmethod
    def clear(self) -> None:
        """Clear *in-memory* state - keep the persisted DB intact."""
        pass

    @abstractmethod
    def has_vector_db(self) -> bool:
        """Return True if there is a loaded vector store present."""
        pass

    @abstractmethod
    def clear_vector_db(self) -> None:
        """Delete the persisted database on disk and reset state."""
        pass

    @abstractmethod    
    def ready_for_retrieval(self) -> bool:
        """Returns True if the pipeline is ready to be used."""
        pass

    @abstractmethod
    def invoke(self, input: str) -> List[Document]:
        """Invoke the memory retriever and return the resulting documents."""
        pass
    
    def set_retrieval_settings(self, retrieval_settings: Dict[str, Any]) -> None:
        """Update retrieval settings.
        
        Retrieval settings MUST be a dict of the form:

        ```
        {
            "ret_strat": "mmr", "k": 6, "fetch_k": 20, "lambda_mult": 0.5
        }
        ```

        OR:
        ```
        {
            "ret_strat": "similarity", "k": 4
        }
        ```
        """
        with self.lock:
            self.retrieval_settings = retrieval_settings
            self._build_chain()