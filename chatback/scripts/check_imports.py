#!/usr/bin/env python3
import ast
import os
from pathlib import Path
from collections import defaultdict

def find_imports(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        try:
            tree = ast.parse(f.read())
        except SyntaxError:
            print(f"Syntax error in {file_path}")
            return set()
    
    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for name in node.names:
                imports.add(name.name.split('.')[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.add(node.module.split('.')[0])
    return imports

def main():
    # Get the project root directory
    project_root = Path(__file__).parent.parent
    
    # Find all Python files
    python_files = list(project_root.rglob('*.py'))
    
    # Collect all imports
    all_imports = set()
    for file_path in python_files:
        imports = find_imports(file_path)
        all_imports.update(imports)
    
    # Print results
    print("\nFound imports:")
    for imp in sorted(all_imports):
        print(f"- {imp}")
    
    # Compare with pyproject.toml dependencies
    print("\nChecking against pyproject.toml dependencies...")
    with open(project_root / 'pyproject.toml', 'r') as f:
        content = f.read()
    
    # Extract dependencies from pyproject.toml
    dependencies = set()
    for line in content.split('\n'):
        if '=' in line and not line.startswith('['):
            dep = line.split('=')[0].strip().strip('"').strip("'")
            if dep and not dep.startswith('#'):
                dependencies.add(dep)
    
    print("\nPotentially unused dependencies in pyproject.toml:")
    for dep in sorted(dependencies):
        if dep not in all_imports and not any(dep in imp for imp in all_imports):
            print(f"- {dep}")

if __name__ == '__main__':
    main() 