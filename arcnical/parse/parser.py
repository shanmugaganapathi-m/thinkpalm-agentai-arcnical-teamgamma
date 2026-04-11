"""
Base parser interface for extracting code symbols from source files.

This module defines the core data structures and interfaces used by language-specific
parsers (Python, TypeScript/JavaScript) to extract symbols, imports, and calls.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum


class SymbolType(str, Enum):
    """Types of code symbols that can be extracted."""
    FILE = "file"
    MODULE = "module"
    CLASS = "class"
    FUNCTION = "function"
    METHOD = "method"
    VARIABLE = "variable"


@dataclass
class Symbol:
    """Represents a code symbol (file, class, function, etc.)."""
    
    file: str
    """Path to the file containing this symbol."""
    
    type: SymbolType
    """Type of symbol (file, module, class, function, method)."""
    
    name: str
    """Simple name of the symbol."""
    
    qualified_name: str
    """Fully qualified name (e.g., 'module.ClassName.method_name')."""
    
    lineno: int
    """Starting line number in source file."""
    
    end_lineno: Optional[int] = None
    """Ending line number in source file."""
    
    parent_qualified_name: Optional[str] = None
    """Qualified name of parent symbol (if nested)."""
    
    language: str = "python"
    """Programming language of the source file."""
    
    is_async: bool = False
    """Whether this is an async function/method."""
    
    is_decorated: bool = False
    """Whether this symbol has decorators."""
    
    metadata: Dict[str, Any] = field(default_factory=dict)
    """Additional metadata about the symbol."""
    
    def __hash__(self):
        return hash(self.qualified_name)
    
    def __eq__(self, other):
        if not isinstance(other, Symbol):
            return False
        return self.qualified_name == other.qualified_name


@dataclass
class Import:
    """Represents an import relationship between files/modules."""
    
    source_file: str
    """File that contains the import statement."""
    
    source_module: str
    """Module of the importing file."""
    
    target_module: str
    """Module being imported."""
    
    target_name: Optional[str] = None
    """Specific name being imported (if 'from X import Y')."""
    
    import_type: str = "import"
    """Type of import: 'import', 'from', 'require', 'import_star'."""
    
    lineno: int = 0
    """Line number where import occurs."""
    
    is_relative: bool = False
    """Whether this is a relative import (e.g., 'from . import')."""
    
    language: str = "python"
    """Language of the importing file."""
    
    metadata: Dict[str, Any] = field(default_factory=dict)
    """Additional metadata about the import."""
    
    def __hash__(self):
        return hash((self.source_module, self.target_module, self.target_name))


@dataclass
class Call:
    """Represents a function/method call."""
    
    caller_file: str
    """File containing the call."""
    
    caller_qualified_name: str
    """Fully qualified name of caller (function/method making the call)."""
    
    called_qualified_name: str
    """Fully qualified name of what's being called."""
    
    lineno: int = 0
    """Line number where call occurs."""
    
    language: str = "python"
    """Language of the calling file."""
    
    metadata: Dict[str, Any] = field(default_factory=dict)
    """Additional metadata about the call."""
    
    def __hash__(self):
        return hash((self.caller_qualified_name, self.called_qualified_name, self.lineno))


@dataclass
class ParseResult:
    """Result of parsing a single file or entire repository."""
    
    symbols: List[Symbol] = field(default_factory=list)
    """All symbols found (files, modules, classes, functions)."""
    
    imports: List[Import] = field(default_factory=list)
    """All import relationships found."""
    
    calls: List[Call] = field(default_factory=list)
    """All function/method calls found."""
    
    unparsed_files: List[str] = field(default_factory=list)
    """Files that failed to parse."""
    
    parse_errors: Dict[str, str] = field(default_factory=dict)
    """File path -> error message for failed parses."""
    
    language_breakdown: Dict[str, int] = field(default_factory=dict)
    """Count of files by language: {'python': 42, 'typescript': 15}."""
    
    total_files: int = 0
    """Total number of files processed."""
    
    def merge(self, other: "ParseResult") -> "ParseResult":
        """Merge another ParseResult into this one."""
        self.symbols.extend(other.symbols)
        self.imports.extend(other.imports)
        self.calls.extend(other.calls)
        self.unparsed_files.extend(other.unparsed_files)
        self.parse_errors.update(other.parse_errors)
        
        for lang, count in other.language_breakdown.items():
            self.language_breakdown[lang] = self.language_breakdown.get(lang, 0) + count
        
        self.total_files += other.total_files
        return self
    
    def summary(self) -> Dict[str, Any]:
        """Get a summary of parsing results."""
        return {
            'total_symbols': len(self.symbols),
            'total_imports': len(self.imports),
            'total_calls': len(self.calls),
            'unparsed_files_count': len(self.unparsed_files),
            'total_files_processed': self.total_files,
            'language_breakdown': self.language_breakdown,
            'parse_success_rate': (
                (self.total_files - len(self.unparsed_files)) / self.total_files * 100
                if self.total_files > 0 else 0
            ),
        }


class BaseLanguageParser:
    """Base class for language-specific parsers."""
    
    def __init__(self, language: str):
        """Initialize parser for a specific language."""
        self.language = language
    
    def parse_file(self, filepath: str) -> ParseResult:
        """
        Parse a single file and extract symbols, imports, and calls.
        
        Args:
            filepath: Path to the file to parse
            
        Returns:
            ParseResult containing extracted symbols, imports, and calls
            
        Raises:
            NotImplementedError: Subclasses must implement this method
        """
        raise NotImplementedError("Subclasses must implement parse_file()")
    
    def parse_content(self, content: str, filepath: str) -> ParseResult:
        """
        Parse file content (string) instead of reading from disk.
        
        Args:
            content: File content as string
            filepath: Virtual filepath for context
            
        Returns:
            ParseResult containing extracted symbols, imports, and calls
            
        Raises:
            NotImplementedError: Subclasses must implement this method
        """
        raise NotImplementedError("Subclasses must implement parse_content()")


class ParserFactory:
    """Factory for creating language-specific parsers."""
    
    _parsers: Dict[str, type] = {}
    
    @classmethod
    def register_parser(cls, language: str, parser_class: type):
        """Register a parser for a specific language."""
        cls._parsers[language] = parser_class
    
    @classmethod
    def get_parser(cls, language: str) -> Optional[BaseLanguageParser]:
        """Get a parser instance for the specified language."""
        parser_class = cls._parsers.get(language)
        if parser_class:
            return parser_class()
        return None
    
    @classmethod
    def get_supported_languages(cls) -> List[str]:
        """Get list of supported programming languages."""
        return list(cls._parsers.keys())
