"""
Python parser using tree-sitter for extracting code symbols.

Extracts:
- Classes, functions, methods, variables
- Import statements (import X, from X import Y)
- Function calls and method calls
"""

import os
from typing import List, Dict, Tuple, Optional, Set
from pathlib import Path

try:
    from tree_sitter import Language, Parser
    from tree_sitter_python import language as python_language
    TREE_SITTER_AVAILABLE = True
except ImportError:
    TREE_SITTER_AVAILABLE = False

from arcnical.parse.parser import (
    BaseLanguageParser, ParseResult, Symbol, SymbolType, Import, Call
)


class PythonParser(BaseLanguageParser):
    """Parser for Python source code using tree-sitter."""
    
    def __init__(self):
        """Initialize the Python parser."""
        super().__init__("python")
        
        if not TREE_SITTER_AVAILABLE:
            raise ImportError(
                "tree-sitter libraries not installed. "
                "Run: pip install tree-sitter tree-sitter-python"
            )
        
        self.parser = Parser(Language(python_language()))
    
    def parse_file(self, filepath: str) -> ParseResult:
        """Parse a Python file and extract symbols."""
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            return self.parse_content(content, filepath)
        except Exception as e:
            result = ParseResult()
            result.unparsed_files.append(filepath)
            result.parse_errors[filepath] = str(e)
            result.total_files = 1
            return result
    
    def parse_content(self, content: str, filepath: str) -> ParseResult:
        """Parse Python content and extract symbols."""
        result = ParseResult()
        result.total_files = 1
        result.language_breakdown['python'] = 1
        
        try:
            tree = self.parser.parse(content.encode('utf-8'))
            root = tree.root_node
            
            # Extract symbols, imports, and calls
            self._extract_symbols(content, filepath, root, result)
            self._extract_imports(content, filepath, root, result)
            self._extract_calls(content, filepath, root, result)
            
        except Exception as e:
            result.unparsed_files.append(filepath)
            result.parse_errors[filepath] = str(e)
        
        return result
    
    def _extract_symbols(self, content: str, filepath: str, node, result: ParseResult):
        """Extract class and function definitions."""
        module_name = self._get_module_name(filepath)
        
        # Add file as a symbol
        lines = content.split('\n')
        file_symbol = Symbol(
            file=filepath,
            type=SymbolType.FILE,
            name=Path(filepath).name,
            qualified_name=module_name,
            lineno=1,
            end_lineno=len(lines),
            language="python"
        )
        result.symbols.append(file_symbol)
        
        # Extract classes and functions
        self._walk_symbols(
            content, filepath, node, module_name, None, result
        )
    
    def _walk_symbols(
        self,
        content: str,
        filepath: str,
        node,
        module_name: str,
        parent_qualified_name: Optional[str],
        result: ParseResult,
        depth: int = 0,
        is_decorated: bool = False
    ):
        """Recursively walk the tree and extract symbols."""

        if node.type == 'decorated_definition':
            # Find the inner function_definition or class_definition
            for child in node.children:
                if child.type in ('function_definition', 'class_definition'):
                    self._walk_symbols(
                        content, filepath, child,
                        module_name, parent_qualified_name, result, depth,
                        is_decorated=True
                    )
            return

        if node.type == 'class_definition':
            class_name = self._get_node_name(node)
            if class_name:
                qualified = self._build_qualified_name(parent_qualified_name, class_name)
                symbol = Symbol(
                    file=filepath,
                    type=SymbolType.CLASS,
                    name=class_name,
                    qualified_name=qualified,
                    lineno=node.start_point[0] + 1,
                    end_lineno=node.end_point[0] + 1,
                    parent_qualified_name=parent_qualified_name,
                    language="python",
                    is_decorated=is_decorated
                )
                result.symbols.append(symbol)

                # Extract methods and nested classes from class body
                for child in node.children:
                    if child.type == 'block':
                        for member_node in child.children:
                            if member_node.type in ('function_definition', 'class_definition', 'decorated_definition'):
                                self._walk_symbols(
                                    content, filepath, member_node,
                                    module_name, qualified, result, depth + 1
                                )

        elif node.type == 'function_definition':
            func_name = self._get_node_name(node)
            if func_name:
                qualified = self._build_qualified_name(parent_qualified_name, func_name)

                is_async = any(child.type == 'async' for child in node.children)

                symbol = Symbol(
                    file=filepath,
                    type=SymbolType.METHOD if parent_qualified_name else SymbolType.FUNCTION,
                    name=func_name,
                    qualified_name=qualified,
                    lineno=node.start_point[0] + 1,
                    end_lineno=node.end_point[0] + 1,
                    parent_qualified_name=parent_qualified_name,
                    language="python",
                    is_async=is_async,
                    is_decorated=is_decorated
                )
                result.symbols.append(symbol)

        # Recurse into top-level children
        for child in node.children:
            if child.type in ('class_definition', 'function_definition', 'decorated_definition'):
                self._walk_symbols(
                    content, filepath, child,
                    module_name, parent_qualified_name, result, depth
                )
    
    def _extract_imports(self, content: str, filepath: str, node, result: ParseResult):
        """Extract import statements."""
        module_name = self._get_module_name(filepath)
        
        self._find_imports(content, filepath, node, module_name, result)
    
    def _find_imports(self, content: str, filepath: str, node, module_name: str, result: ParseResult):
        """Recursively find import statements."""
        
        if node.type == 'import_statement':
            # import x, import x.y, import x as y
            for child in node.children:
                if child.type == 'dotted_name' or child.type == 'identifier':
                    target = self._get_node_text(content, child).strip()
                    import_obj = Import(
                        source_file=filepath,
                        source_module=module_name,
                        target_module=target,
                        import_type='import',
                        lineno=node.start_point[0] + 1,
                        language='python'
                    )
                    result.imports.append(import_obj)
        
        elif node.type == 'import_from_statement':
            # from x import y, from . import y, from ..x import y
            target_module = None
            target_names = []
            past_import_keyword = False

            # Find the module being imported from
            for child in node.children:
                if child.text in (b'import', 'import'):
                    past_import_keyword = True
                    continue
                if not past_import_keyword:
                    if child.type in ('dotted_name', 'relative_import'):
                        target_module = self._get_node_text(content, child).strip()
                else:
                    if child.type in ('import_alias', 'identifier', 'dotted_name'):
                        target_names.append(self._get_node_text(content, child).strip())
                    elif child.text in (b'*', '*'):
                        target_names.append('*')

            if target_module or target_names:
                is_relative = any(
                    child.text in (b'.', b'..', '.', '..')
                    for child in node.children
                )
                
                if target_names:
                    for name in target_names:
                        if name:
                            import_obj = Import(
                                source_file=filepath,
                                source_module=module_name,
                                target_module=target_module or '.',
                                target_name=name,
                                import_type='from',
                                lineno=node.start_point[0] + 1,
                                is_relative=is_relative,
                                language='python'
                            )
                            result.imports.append(import_obj)
        
        # Recurse
        for child in node.children:
            self._find_imports(content, filepath, child, module_name, result)
    
    def _extract_calls(self, content: str, filepath: str, node, result: ParseResult):
        """Extract function and method calls."""
        self._find_calls(content, filepath, node, None, result)
    
    def _find_calls(
        self, 
        content: str, 
        filepath: str, 
        node, 
        current_function: Optional[str],
        result: ParseResult
    ):
        """Recursively find function calls."""
        
        # Track current function context
        if node.type == 'function_definition':
            current_function = self._get_node_name(node)
        
        # Find call expressions
        if node.type == 'call' and current_function:
            # Get the function being called
            for child in node.children:
                if child.type in ('identifier', 'attribute'):
                    called_name = self._get_node_text(content, child).strip()
                    if called_name:
                        call_obj = Call(
                            caller_file=filepath,
                            caller_qualified_name=current_function,
                            called_qualified_name=called_name,
                            lineno=node.start_point[0] + 1,
                            language='python'
                        )
                        result.calls.append(call_obj)
                    break
        
        # Recurse
        for child in node.children:
            self._find_calls(content, filepath, child, current_function, result)
    
    def _get_node_name(self, node) -> Optional[str]:
        """Get the name of a class or function."""
        for child in node.children:
            if child.type == 'identifier':
                return child.text.decode('utf-8')
        return None
    
    def _get_node_text(self, content: str, node) -> str:
        """Get text content of a node."""
        try:
            start = node.start_byte
            end = node.end_byte
            return content[start:end]
        except:
            return ""
    
    def _get_module_name(self, filepath: str) -> str:
        """Convert filepath to module name."""
        path = Path(filepath)
        
        # Remove .py extension
        if path.suffix == '.py':
            path = path.with_suffix('')
        
        # Convert path to module notation
        parts = path.parts
        # Filter out common non-module directories
        filtered = []
        skip_next = False
        
        for part in parts:
            if part in ('src', 'lib', 'arcnical'):
                skip_next = False
                continue
            if not skip_next:
                filtered.append(part.replace('-', '_'))
        
        return '.'.join(filtered) if filtered else 'unknown'
    
    def _build_qualified_name(self, parent: Optional[str], name: str) -> str:
        """Build qualified name from parent and name."""
        if parent:
            return f"{parent}.{name}"
        return name
    
    def _has_decorators(self, node) -> bool:
        """Check if node has decorators."""
        prev_sibling = node.prev_sibling
        while prev_sibling:
            if prev_sibling.type == 'decorator':
                return True
            if prev_sibling.type in ('newline', 'indent'):
                prev_sibling = prev_sibling.prev_sibling
            else:
                break
        return False
