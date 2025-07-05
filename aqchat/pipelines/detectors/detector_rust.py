import re
from typing import List, Tuple
from pipelines.detectors.boundary_detector import CodeBoundaryDetector

class RustBoundaryDetector(CodeBoundaryDetector):
    """Boundary detector for Rust code."""
    
    def __init__(self):
        # Function patterns (pub/private, async, unsafe, const, etc.)
        self.function_pattern = re.compile(r'^(\s*)(?:pub\s+)?(?:async\s+)?(?:unsafe\s+)?(?:const\s+)?fn\s+\w+')
        
        # Struct patterns (pub/private, with generics)
        self.struct_pattern = re.compile(r'^(\s*)(?:pub\s+)?struct\s+\w+')
        
        # Trait patterns (pub/private, with generics)
        self.trait_pattern = re.compile(r'^(\s*)(?:pub\s+)?trait\s+\w+')
        
        # Impl patterns (with generics, trait impls)
        self.impl_pattern = re.compile(r'^(\s*)impl\s+')
    
    def find_boundaries(self, text: str) -> List[Tuple[int, int, str, int]]:
        """Find function, struct, trait, and impl boundaries in Rust code."""
        lines = text.split('\n')
        boundaries = []
        
        i = 0
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()
            
            # Skip regular comments and empty lines
            if stripped.startswith('//') and not stripped.startswith('///') and not stripped.startswith('//!') or stripped == '':
                i += 1
                continue
            
            # Check if this line starts a code item (function, struct, trait, impl)
            func_match = self.function_pattern.match(line)
            struct_match = self.struct_pattern.match(line)
            trait_match = self.trait_pattern.match(line)
            impl_match = self.impl_pattern.match(line)
            
            if func_match or struct_match or trait_match or impl_match:
                # Found a code item, now find its actual start including attributes and docs
                start_line = self._find_item_start(lines, i)
                
                # Determine the type and base indentation
                if func_match:
                    item_type = 'function'
                    indent_level = len(func_match.group(1))
                elif struct_match:
                    item_type = 'struct'
                    indent_level = len(struct_match.group(1))
                elif trait_match:
                    item_type = 'trait'
                    indent_level = len(trait_match.group(1))
                else:  # impl_match
                    item_type = 'impl'
                    indent_level = len(impl_match.group(1))
                
                # Find the end of the code block
                end_line = self._find_rust_block_end(lines, i, indent_level)
                boundaries.append((start_line, end_line, item_type, indent_level))
            
            i += 1
        
        return boundaries
    
    def _find_item_start(self, lines: List[str], item_line: int) -> int:
        """Find the actual start of a code item including attributes and doc comments."""
        start_line = item_line
        
        # Look backwards for attributes and doc comments
        for i in range(item_line - 1, -1, -1):
            line = lines[i]
            stripped = line.strip()
            
            # Check if this line is an attribute
            if stripped.startswith('#[') or stripped.startswith('#!'):
                start_line = i
                continue
            
            # Check if this line is a doc comment
            if stripped.startswith('///') or stripped.startswith('//!'):
                start_line = i
                continue
            
            # If we find an empty line, continue looking (attributes/docs can be separated)
            if stripped == '':
                continue
            
            # If we find anything else, stop looking
            break
        
        return start_line
    
    def _find_rust_block_end(self, lines: List[str], start_line: int, base_indent: int) -> int:
        """Find the end of a Rust code block using brace matching."""
        brace_count = 0
        found_opening_brace = False
        
        for i in range(start_line, len(lines)):
            line = lines[i]
            
            # Skip comments
            if line.strip().startswith('//'):
                continue
            
            # Count braces (simple approach - doesn't handle strings/comments perfectly)
            for char in line:
                if char == '{':
                    brace_count += 1
                    found_opening_brace = True
                elif char == '}':
                    brace_count -= 1
                    
                    # If we've closed all braces, we found the end
                    if found_opening_brace and brace_count == 0:
                        return i
            
            # Handle single-line items without braces (like struct declarations)
            if i == start_line and ';' in line:
                return i
        
        # If we reach the end of file, return the last line
        return len(lines) - 1
    
    def get_boundary_types(self) -> List[str]:
        return ['function', 'struct', 'trait', 'impl']