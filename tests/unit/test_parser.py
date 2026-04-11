"""
Unit tests for parser implementations (Python, TypeScript/JavaScript).
"""

import pytest
import tempfile
from pathlib import Path

from arcnical.parse.parser import SymbolType, ParseResult
from arcnical.parse.python_parser import PythonParser
from arcnical.parse.typescript_parser import TypeScriptParser


class TestPythonParser:
    """Tests for Python parser."""
    
    @pytest.fixture
    def parser(self):
        """Create parser instance."""
        return PythonParser()
    
    def test_simple_function(self, parser):
        """Test parsing simple function."""
        code = """
def hello():
    pass
"""
        result = parser.parse_content(code, "test.py")
        
        assert len(result.symbols) >= 2  # file + function
        assert result.total_files == 1
        assert 'python' in result.language_breakdown
    
    def test_simple_class(self, parser):
        """Test parsing simple class."""
        code = """
class MyClass:
    def method(self):
        pass
"""
        result = parser.parse_content(code, "test.py")
        
        assert len(result.symbols) >= 3  # file + class + method
        assert any(s.type == SymbolType.CLASS for s in result.symbols)
    
    def test_nested_class(self, parser):
        """Test parsing nested classes."""
        code = """
class Outer:
    class Inner:
        pass
"""
        result = parser.parse_content(code, "test.py")
        
        # Should have file + outer class + inner class
        assert len(result.symbols) >= 3
        classes = [s for s in result.symbols if s.type == SymbolType.CLASS]
        assert len(classes) >= 2
    
    def test_imports(self, parser):
        """Test parsing imports."""
        code = """
import os
from pathlib import Path
from typing import List, Dict
"""
        result = parser.parse_content(code, "test.py")
        
        assert len(result.imports) >= 3
    
    def test_function_calls(self, parser):
        """Test parsing function calls."""
        code = """
def caller():
    helper()
    other.method()
"""
        result = parser.parse_content(code, "test.py")
        
        # Should detect calls
        assert len(result.calls) >= 1
    
    def test_async_function(self, parser):
        """Test parsing async functions."""
        code = """
async def async_func():
    pass
"""
        result = parser.parse_content(code, "test.py")
        
        # Find async function
        async_funcs = [s for s in result.symbols if s.is_async]
        assert len(async_funcs) >= 1
    
    def test_decorated_function(self, parser):
        """Test parsing decorated functions."""
        code = """
@decorator
def decorated():
    pass
"""
        result = parser.parse_content(code, "test.py")
        
        # Should mark as decorated
        funcs = [s for s in result.symbols if s.type == SymbolType.FUNCTION]
        assert len(funcs) >= 1
    
    def test_parse_error_handling(self, parser):
        """Test handling of parse errors."""
        code = "def broken syntax here"
        result = parser.parse_content(code, "test.py")
        
        # Should not crash, but may have errors
        assert isinstance(result, ParseResult)


class TestTypeScriptParser:
    """Tests for TypeScript parser."""
    
    @pytest.fixture
    def parser(self):
        """Create parser instance."""
        try:
            return TypeScriptParser(is_typescript=True)
        except ImportError:
            pytest.skip("tree-sitter-typescript not installed")
    
    def test_simple_class(self, parser):
        """Test parsing TypeScript class."""
        code = """
class MyClass {
    method() {
        return "hello";
    }
}
"""
        result = parser.parse_content(code, "test.ts")
        
        assert len(result.symbols) >= 2  # file + class
        assert 'typescript' in result.language_breakdown
    
    def test_function_declaration(self, parser):
        """Test parsing function declaration."""
        code = """
function myFunction() {
    return 42;
}
"""
        result = parser.parse_content(code, "test.ts")
        
        assert len(result.symbols) >= 2  # file + function
    
    def test_arrow_function(self, parser):
        """Test parsing arrow functions."""
        code = """
const callback = () => {
    return "hello";
};
"""
        result = parser.parse_content(code, "test.ts")
        
        # Should parse without error
        assert isinstance(result, ParseResult)
    
    def test_imports(self, parser):
        """Test parsing imports."""
        code = """
import { Component } from '@angular/core';
import * as React from 'react';
"""
        result = parser.parse_content(code, "test.ts")
        
        assert len(result.imports) >= 1
    
    def test_async_function(self, parser):
        """Test parsing async functions."""
        code = """
async function fetchData() {
    return await fetch('/api');
}
"""
        result = parser.parse_content(code, "test.ts")
        
        # Should detect async
        assert any(s.is_async for s in result.symbols if s.type == SymbolType.FUNCTION)


class TestParserIntegration:
    """Integration tests for parsers."""
    
    def test_parse_real_file(self):
        """Test parsing an actual Python file."""
        python_parser = PythonParser()
        
        # Use arcnical/parse/parser.py itself as test file
        result = python_parser.parse_file("arcnical/parse/parser.py")
        
        # Should successfully parse
        assert result.total_files == 1
        assert len(result.symbols) > 0
        assert result.language_breakdown.get('python', 0) > 0
        assert len(result.unparsed_files) == 0
    
    def test_combined_parse_result(self):
        """Test merging multiple parse results."""
        parser = PythonParser()
        
        result1 = parser.parse_content("""
def func1():
    pass
""", "file1.py")
        
        result2 = parser.parse_content("""
def func2():
    pass
""", "file2.py")
        
        merged = result1.merge(result2)
        
        assert merged.total_files == 2
        assert len(merged.symbols) == 4  # 2 files + 2 functions
