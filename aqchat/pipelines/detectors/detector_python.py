import re
from typing import List, Tuple
from pipelines.detectors.boundary_detector import CodeBoundaryDetector

class PythonBoundaryDetector(CodeBoundaryDetector):
    """Boundary detector for Python code."""
    
    def __init__(self):
        self.class_pattern = re.compile(r'^(\s*)class\s+\w+.*?:')
        self.function_pattern = re.compile(r'^(\s*)def\s+\w+.*?:')
        self.async_function_pattern = re.compile(r'^(\s*)async\s+def\s+\w+.*?:')
    
    def find_boundaries(self, text: str) -> List[Tuple[int, int, str, int]]:
        """Find class and function boundaries in Python code."""
        lines = text.split('\n')
        boundaries = []
        
        for i, line in enumerate(lines):
            # Check for class definition
            class_match = self.class_pattern.match(line)
            if class_match:
                indent_level = len(class_match.group(1))
                end_line = self._find_block_end(lines, i, indent_level)
                boundaries.append((i, end_line, 'class', indent_level))
            
            # Check for function definition (including async)
            func_match = self.function_pattern.match(line) or self.async_function_pattern.match(line)
            if func_match:
                indent_level = len(func_match.group(1))
                end_line = self._find_block_end(lines, i, indent_level)
                boundaries.append((i, end_line, 'function', indent_level))
        
        return boundaries
    
    def _find_block_end(self, lines: List[str], start_line: int, base_indent: int) -> int:
        """Find the end of a code block based on indentation."""
        for i in range(start_line + 1, len(lines)):
            line = lines[i]
            if line.strip() == '':  # Skip empty lines
                continue
            
            # Calculate current line's indentation
            current_indent = len(line) - len(line.lstrip())
            
            # If we find a line with same or less indentation, the block has ended
            if current_indent <= base_indent:
                return i - 1
        
        # If we reach the end of file, return the last line
        return len(lines) - 1
    
    def get_boundary_types(self) -> List[str]:
        return ['class', 'function']