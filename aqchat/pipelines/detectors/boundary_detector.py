from abc import ABC, abstractmethod
from typing import List, Tuple

class CodeBoundaryDetector(ABC):
    """Abstract base class for detecting code boundaries in different languages."""
    
    @abstractmethod
    def find_boundaries(self, text: str) -> List[Tuple[int, int, str, int]]:
        """
        Find boundaries in the code text.
        
        Returns:
            List of tuples: (start_line, end_line, boundary_type, indent_level)
        """
        pass
    
    @abstractmethod
    def get_boundary_types(self) -> List[str]:
        """Return list of boundary types this detector can identify."""
        pass