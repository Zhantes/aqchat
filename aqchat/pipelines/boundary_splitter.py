import os
from typing import List, Dict, Any, Optional, Iterable
from langchain.text_splitter import TextSplitter
from langchain.docstore.document import Document
from pipelines.detectors import CodeBoundaryDetector
from langchain_text_splitters.character import RecursiveCharacterTextSplitter
from langchain_text_splitters import TextSplitter

def _get_extension_from_path(path: str):
    """
    Extracts the file extension from a file path.
    Returns None if there's no extension.
    """
    filename = os.path.basename(path)
    dot_index = filename.rfind('.')
    
    if dot_index > 0: # Excludes dotfiles like .bashrc
        return filename[dot_index:]
    return None

class CodeBoundaryTextSplitter(TextSplitter):
    """
    This class splits code files based on language-specific boundaries (classes, functions, etc.).

    When splitting text, you must provide a dict mapping file extensions (for example `.py`) to a
    CodeBoundaryDetector implementation for that language. If no boundary detector is available,
    then by default the Langchain recursive text splitter will be used.
    """
    
    def __init__(
        self,
        chunk_size: int = 4000,
        chunk_overlap: int = 200,
        length_function: callable = len,
        keep_separator: bool = True,
        add_start_index: bool = False,
        strip_whitespace: bool = True,
    ):
        """
        Initialize the CodeBoundaryTextSplitter.
        
        Args:
            boundary_detector: The boundary detector for the specific language
            chunk_size: Maximum size of each chunk
            chunk_overlap: Overlap between chunks
            length_function: Function to calculate text length
            keep_separator: Whether to keep boundary separators
            add_start_index: Whether to add start index to metadata
            strip_whitespace: Whether to strip whitespace from chunks
            default_splitter: This is used as a splitter for raw text documents,
            as well as any extensions for which there is no available boundary detector.
        """
        super().__init__(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=length_function,
            keep_separator=keep_separator,
            add_start_index=add_start_index,
            strip_whitespace=strip_whitespace,
        )
        self.default_splitter = RecursiveCharacterTextSplitter()
    
    def split_text(self, text: str, *, boundary_detector: CodeBoundaryDetector = None) -> List[str]:
        """Split text based on code boundaries."""

        # If no boundary detector was supplied for a specific language,
        # default to the Langchain text splitter. This will work fine for e.g. text,
        # markdown, etc.
        if boundary_detector is None:
            return self.default_splitter.split_text(text)

        lines = text.split('\n')
        boundaries = boundary_detector.find_boundaries(text)
        
        # Sort boundaries by start line
        boundaries.sort(key=lambda x: x[0])
        
        chunks = []
        current_pos = 0
        
        # Process each boundary
        for start_line, end_line, boundary_type, indent_level in boundaries:
            # Add any code before this boundary as a separate chunk
            if start_line > current_pos:
                pre_boundary_text = '\n'.join(lines[current_pos:start_line])
                if pre_boundary_text.strip():
                    chunks.extend(self._split_large_chunk(pre_boundary_text))
            
            # Add the boundary itself as a chunk
            boundary_text = '\n'.join(lines[start_line:end_line + 1])
            if boundary_text.strip():
                chunks.extend(self._split_large_chunk(boundary_text))
            
            current_pos = end_line + 1
        
        # Add any remaining code after the last boundary
        if current_pos < len(lines):
            remaining_text = '\n'.join(lines[current_pos:])
            if remaining_text.strip():
                chunks.extend(self._split_large_chunk(remaining_text))
        
        return [chunk for chunk in chunks if chunk.strip()]
    
    def _split_large_chunk(self, text: str) -> List[str]:
        """Split a chunk that exceeds the size limit."""
        if self._length_function(text) <= self._chunk_size:
            return [text]
        
        # If the chunk is too large, split it by lines
        lines = text.split('\n')
        chunks = []
        current_chunk = []
        current_size = 0
        
        for line in lines:
            line_size = self._length_function(line + '\n')
            
            # If adding this line would exceed the limit, save current chunk
            if current_size + line_size > self._chunk_size and current_chunk:
                chunks.append('\n'.join(current_chunk))
                current_chunk = []
                current_size = 0
            
            current_chunk.append(line)
            current_size += line_size
        
        # Add the last chunk if it has content
        if current_chunk:
            chunks.append('\n'.join(current_chunk))
        
        return chunks
    
    def create_documents(
        self, 
        texts: List[str], 
        metadatas: Optional[List[Dict[str, Any]]] = None,
        *,
        boundary_detectors: Dict[str, CodeBoundaryDetector],
        include_metadata: bool = False
    ) -> List[Document]:
        """Create Document objects from texts."""
        documents = []
        
        for i, text in enumerate(texts):
            metadata = metadatas[i] if metadatas else {}

            boundary_detector = None

            source: str = metadata.get("source")
            if source:
                # extract extension from the filename
                ext = _get_extension_from_path(source)

                if ext:
                    boundary_detector = boundary_detectors.get(ext)
            
            # Split the text. We pass the boundary detector found for
            # the file's extension, if none was found, then split_text
            # will default to the Langchain text splitter.
            chunks = self.split_text(text, boundary_detector=boundary_detector)
            
            # Create documents for each chunk
            for j, chunk in enumerate(chunks):
                doc_metadata = metadata.copy()

                if include_metadata:
                    doc_metadata.update({
                        'chunk_index': j,
                        'total_chunks': len(chunks),
                    })
                    if boundary_detector is not None:
                        doc_metadata['boundary_types'] = boundary_detector.get_boundary_types()
                    
                    if self._add_start_index:
                        doc_metadata['start_index'] = text.find(chunk)
                
                documents.append(Document(page_content=chunk, metadata=doc_metadata))
        
        return documents

    def split_documents(self,
                        documents: Iterable[Document],
                        *,
                        boundary_detectors: Dict[str, CodeBoundaryDetector],
                        include_metadata: bool = False) -> List[Document]:
        """Split documents."""
        texts, metadatas = [], []
        for doc in documents:
            texts.append(doc.page_content)
            metadatas.append(doc.metadata)
        return self.create_documents(texts,
                                     metadatas=metadatas,
                                     boundary_detectors=boundary_detectors,
                                     include_metadata=include_metadata)
    