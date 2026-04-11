"""
TypeScript/JavaScript parser using tree-sitter.

Extracts classes, functions, imports, and calls from .ts and .js files.
"""

from typing import Optional, List
from pathlib import Path

try:
    from tree_sitter import Language, Parser
    from tree_sitter_typescript import language as typescript_language
    TREE_SITTER_AVAILABLE = True
except ImportError:
    TREE_SITTER_AVAILABLE = False

from arcnical.parse.parser import (
    BaseLanguageParser, ParseResult, Symbol, SymbolType, Import, Call
)


class TypeScriptParser(BaseLanguageParser):
    """Parser for TypeScript and JavaScript using tree-sitter."""
    
    def __init__(self, is_typescript: bool = True):
        """Initialize TypeScript/JavaScript parser."""
        super().__init__("typescript" if is_typescript else "javascript")
        
        if not TREE_SITTER_AVAILABLE:
            raise ImportError(
                "tree-sitter libraries not installed. "
                "Run: pip install tree-sitter tree-sitter-typescript"
            )
        
        self.is_typescript = is_typescript
        self.parser = Parser(Language(typescript_language()))
    
    def parse_file(self, filepath: str) -> ParseResult:
        """Parse a TypeScript/JavaScript file."""
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
        """Parse TypeScript/JavaScript content."""
        result = ParseResult()
        result.total_files = 1
        language_key = 'typescript' if self.is_typescript else 'javascript'
        result.language_breakdown[language_key] = 1
        
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
        
        # Add file as symbol
        lines = content.split('\n')
        file_symbol = Symbol(
            file=filepath,
            type=SymbolType.FILE,
            name=Path(filepath).name,
            qualified_name=module_name,
            lineno=1,
            end_lineno=len(lines),
            language=self.language
        )
        result.symbols.append(file_symbol)
        
        # Extract classes and functions
        self._walk_symbols(content, filepath, node, module_name, None, result)
    
    def _walk_symbols(
        self,
        content: str,
        filepath: str,
        node,
        module_name: str,
        parent_qualified_name: Optional[str],
        result: ParseResult
    ):
        """Recursively walk AST and extract symbols."""
        
        if node.type == 'class_declaration':
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
                    language=self.language
                )
                result.symbols.append(symbol)
                
                # Extract methods from class
                for child in node.children:
                    if child.type == 'class_body':
                        for method_node in child.children:
                            if method_node.type in (
                                'method_definition',
                                'function_definition',
                                'arrow_function'
                            ):
                                self._walk_symbols(
                                    content, filepath, method_node,
                                    module_name, qualified, result
                                )
        
        elif node.type in ('function_declaration', 'method_definition'):
            func_name = self._get_node_name(node)
            if func_name:
                qualified = self._build_qualified_name(parent_qualified_name, func_name)
                is_async = self._is_async(node)
                
                symbol = Symbol(
                    file=filepath,
                    type=SymbolType.METHOD if parent_qualified_name else SymbolType.FUNCTION,
                    name=func_name,
                    qualified_name=qualified,
                    lineno=node.start_point[0] + 1,
                    end_lineno=node.end_point[0] + 1,
                    parent_qualified_name=parent_qualified_name,
                    language=self.language,
                    is_async=is_async
                )
                result.symbols.append(symbol)
        
        elif node.type == 'arrow_function' and parent_qualified_name:
            # Arrow functions in class context
            func_name = self._get_arrow_function_name(node)
            if func_name:
                qualified = self._build_qualified_name(parent_qualified_name, func_name)
                symbol = Symbol(
                    file=filepath,
                    type=SymbolType.METHOD,
                    name=func_name,
                    qualified_name=qualified,
                    lineno=node.start_point[0] + 1,
                    end_lineno=node.end_point[0] + 1,
                    parent_qualified_name=parent_qualified_name,
                    language=self.language,
                    is_async=self._is_async(node)
                )
                result.symbols.append(symbol)
        
        # Recurse
        for child in node.children:
            if child.type in ('class_declaration', 'function_declaration', 'method_definition'):
                self._walk_symbols(
                    content, filepath, child,
                    module_name, parent_qualified_name, result
                )
    
    def _extract_imports(self, content: str, filepath: str, node, result: ParseResult):
        """Extract import/export statements."""
        module_name = self._get_module_name(filepath)
        self._find_imports(content, filepath, node, module_name, result)
    
    def _find_imports(self, content: str, filepath: str, node, module_name: str, result: ParseResult):
        """Recursively find import statements."""
        
        if node.type in ('import_statement', 'import_clause'):
            # import X from 'y'
            # import { X, Y } from 'z'
            source = None
            names = []
            
            for child in node.children:
                if child.type == 'string' or child.type == 'template_string':
                    source = self._extract_string_value(content, child)
                elif child.type == 'named_imports':
                    for import_child in child.children:
                        if import_child.type == 'import_specifier':
                            name = self._get_node_text(content, import_child).strip()
                            if name:
                                names.append(name)
                elif child.type == 'identifier':
                    name = child.text.decode('utf-8')
                    if name not in ('import', 'from', 'as'):
                        names.append(name)
            
            if source:
                if names:
                    for name in names:
                        import_obj = Import(
                            source_file=filepath,
                            source_module=module_name,
                            target_module=source,
                            target_name=name,
                            import_type='from',
                            lineno=node.start_point[0] + 1,
                            language=self.language
                        )
                        result.imports.append(import_obj)
                else:
                    import_obj = Import(
                        source_file=filepath,
                        source_module=module_name,
                        target_module=source,
                        import_type='import',
                        lineno=node.start_point[0] + 1,
                        language=self.language
                    )
                    result.imports.append(import_obj)
        
        # Recurse
        for child in node.children:
            self._find_imports(content, filepath, child, module_name, result)
    
    def _extract_calls(self, content: str, filepath: str, node, result: ParseResult):
        """Extract function calls."""
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
        
        # Track current function
        if node.type in ('function_declaration', 'arrow_function'):
            current_function = self._get_node_name(node) or current_function
        
        # Find call expressions
        if node.type == 'call_expression' and current_function:
            for child in node.children:
                if child.type in ('identifier', 'member_expression'):
                    called_name = self._get_node_text(content, child).strip()
                    if called_name:
                        call_obj = Call(
                            caller_file=filepath,
                            caller_qualified_name=current_function,
                            called_qualified_name=called_name,
                            lineno=node.start_point[0] + 1,
                            language=self.language
                        )
                        result.calls.append(call_obj)
                    break
        
        # Recurse
        for child in node.children:
            self._find_calls(content, filepath, child, current_function, result)
    
    def _get_node_name(self, node) -> Optional[str]:
        """Get name of function/class."""
        for child in node.children:
            if child.type == 'identifier':
                return child.text.decode('utf-8')
        return None
    
    def _get_arrow_function_name(self, node) -> Optional[str]:
        """Get name of arrow function (from variable declaration context)."""
        # Arrow functions don't have inherent names, would need parent context
        return None
    
    def _get_node_text(self, content: str, node) -> str:
        """Get text content of node."""
        try:
            start = node.start_byte
            end = node.end_byte
            return content[start:end]
        except:
            return ""
    
    def _extract_string_value(self, content: str, node) -> Optional[str]:
        """Extract string value from import statement."""
        text = self._get_node_text(content, node)
        # Remove quotes
        if text.startswith('"') or text.startswith("'"):
            return text[1:-1]
        if text.startswith('`'):
            return text[1:-1]
        return text
    
    def _get_module_name(self, filepath: str) -> str:
        """Convert filepath to module name."""
        path = Path(filepath)
        
        # Remove extension
        if path.suffix in ('.ts', '.tsx', '.js', '.jsx'):
            path = path.with_suffix('')
        
        # Convert path to module notation
        parts = path.parts
        filtered = []
        
        for part in parts:
            if part not in ('src', 'lib', 'dist'):
                filtered.append(part.replace('-', '_'))
        
        return '.'.join(filtered) if filtered else 'unknown'
    
    def _build_qualified_name(self, parent: Optional[str], name: str) -> str:
        """Build qualified name."""
        if parent:
            return f"{parent}.{name}"
        return name
    
    def _is_async(self, node) -> bool:
        """Check if function is async."""
        for child in node.children:
            if child.type == 'async':
                return True
            if child.text == b'async':
                return True
        return False
