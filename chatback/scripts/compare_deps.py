#!/usr/bin/env python3
import re
from pathlib import Path

def parse_pipreqs_output(output):
    # Extract package names from pipreqs output
    packages = set()
    for line in output.split('\n'):
        if '==' in line:
            pkg = line.split('==')[0].strip()
            packages.add(pkg.lower().replace('-', '_'))
    return packages

def parse_pyproject_toml():
    # Read pyproject.toml
    with open('pyproject.toml', 'r') as f:
        content = f.read()
    
    # Extract dependencies
    dependencies = set()
    in_deps = False
    for line in content.split('\n'):
        if 'dependencies = [' in line:
            in_deps = True
            continue
        if in_deps and ']' in line:
            in_deps = False
            continue
        if in_deps and '=' in line:
            # Extract package name before the version
            pkg = line.split('>=')[0].strip().strip('"').strip("'")
            if pkg and not pkg.startswith('#'):
                dependencies.add(pkg.lower().replace('-', '_'))
    
    return dependencies

def main():
    # Read pipreqs output from a file
    with open('pipreqs_output.txt', 'r') as f:
        pipreqs_output = f.read()
    
    # Get packages from both sources
    pipreqs_packages = parse_pipreqs_output(pipreqs_output)
    pyproject_packages = parse_pyproject_toml()
    
    # Find potentially unused packages
    unused = pyproject_packages - pipreqs_packages
    
    print("\nPotentially unused packages in pyproject.toml:")
    for pkg in sorted(unused):
        print(f"- {pkg}")
    
    print("\nPackages found by pipreqs but not in pyproject.toml:")
    missing = pipreqs_packages - pyproject_packages
    for pkg in sorted(missing):
        print(f"- {pkg}")

if __name__ == '__main__':
    main() 