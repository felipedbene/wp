#!/usr/bin/env python
"""
Fix for wordpress_xmlrpc library to work with Python 3.10+
This script patches the wordpress_xmlrpc/base.py file to use collections.abc.Iterable
instead of collections.Iterable which was removed in Python 3.10
"""

import os
import sys
import site

def fix_wordpress_xmlrpc():
    # Find the site-packages directory
    site_packages = site.getsitepackages()[0]
    
    # Path to the file that needs to be fixed
    file_path = os.path.join(site_packages, 'wordpress_xmlrpc', 'base.py')
    
    if not os.path.exists(file_path):
        print(f"Error: Could not find {file_path}")
        return False
    
    # Read the file
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Check if the file already uses collections.abc
    if 'from collections import abc as collections' in content:
        print("File already patched.")
        return True
    
    # Replace the import statement
    content = content.replace(
        'from collections import Iterable', 
        'from collections.abc import Iterable'
    )
    
    # Also fix any other direct imports from collections
    content = content.replace(
        'import collections', 
        'import collections.abc as collections'
    )
    
    # Write the modified content back to the file
    try:
        with open(file_path, 'w') as f:
            f.write(content)
        print(f"Successfully patched {file_path}")
        return True
    except Exception as e:
        print(f"Error writing to {file_path}: {e}")
        return False

if __name__ == "__main__":
    if fix_wordpress_xmlrpc():
        print("Patch applied successfully!")
    else:
        print("Failed to apply patch.")
