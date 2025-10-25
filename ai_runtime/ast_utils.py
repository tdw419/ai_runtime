"""
AST Utilities for safe code modification.

This module provides functions for parsing, manipulating, and unparsing Python
code using the Abstract Syntax Tree (AST) module. This allows for more
robust and structured code modifications than simple text replacement.
"""
import ast

class FunctionDefVisitor(ast.NodeVisitor):
    """A visitor to find function definitions in an AST."""
    def __init__(self):
        self.functions = {}

    def visit_FunctionDef(self, node):
        self.functions[node.name] = node
        self.generic_visit(node)

def parse_code(source_code: str) -> ast.AST:
    """Safely parse source code into an AST tree."""
    return ast.parse(source_code)

def unparse_code(tree: ast.AST) -> str:
    """Unparse an AST tree back into source code."""
    return ast.unparse(tree)

def add_function(source_code: str, new_function_def: ast.FunctionDef) -> str:
    """
    Adds a function to the source code. If a function with the same name
    exists, it is replaced.

    Args:
        source_code: The original source code.
        new_function_def: The AST node of the function to add/replace.

    Returns:
        The modified source code.
    """
    tree = parse_code(source_code)

    # Check if the function already exists
    visitor = FunctionDefVisitor()
    visitor.visit(tree)

    if new_function_def.name in visitor.functions:
        # Replace existing function
        new_body = []
        for node in tree.body:
            if isinstance(node, ast.FunctionDef) and node.name == new_function_def.name:
                new_body.append(new_function_def)
            else:
                new_body.append(node)
        tree.body = new_body
    else:
        # Add new function to the end of the file
        tree.body.append(new_function_def)

    return unparse_code(tree)

def add_import(source_code: str, module_name: str, alias: str = None) -> str:
    """
    Adds an import statement to the source code if it doesn't already exist.

    Args:
        source_code: The original source code.
        module_name: The name of the module to import.
        alias: An optional alias for the import.

    Returns:
        The modified source code.
    """
    tree = parse_code(source_code)

    # Check if import already exists
    for node in tree.body:
        if isinstance(node, ast.Import):
            for name in node.names:
                if name.name == module_name:
                    return source_code # Already imported
        if isinstance(node, ast.ImportFrom):
            if node.module == module_name:
                return source_code # Already imported from

    # Create the new import node
    import_node = ast.Import(names=[ast.alias(name=module_name, asname=alias)])

    # Insert the import at the top of the file
    tree.body.insert(0, import_node)

    return unparse_code(tree)
