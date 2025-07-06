#!/usr/bin/env python
import re

print("Creating fixed versions of the files...")

# Fix apps.py
with open('checker/apps.py', 'r') as f:
    content = f.read()

# Fix the indentation for import logging line
fixed_content = content.replace("def perform_startup_checks():\n        import logging", 
                               "def perform_startup_checks():\n                import logging")

with open('checker/apps.py.fixed', 'w') as f:
    f.write(fixed_content)
print("✅ Created checker/apps.py.fixed")

# Create a modified version of company_search.py with corrected indentation
with open('checker/services/company_search.py', 'r') as f:
    lines = f.readlines()

# Fix page = 1 indentation
for i in range(len(lines)):
    if i < len(lines) - 1 and "except (ValueError, TypeError):" in lines[i] and "page = 1" in lines[i+1] and not lines[i+1].startswith("        "):
        lines[i+1] = "        page = 1\n"

# Remove duplicate context.update(extra_context)
for i in range(len(lines)):
    if "# Add extra context and return" in lines[i]:
        # Check the next few lines for duplicate context.update
        j = i + 1
        found_updates = 0
        while j < min(i + 5, len(lines)):
            if "context.update(extra_context)" in lines[j]:
                found_updates += 1
                if found_updates > 1:  # Keep only the first one
                    lines[j] = ""  # Remove duplicate line
            j += 1

# Fix the indentation for "else:" statements not in try blocks
for i in range(len(lines)):
    if re.match(r'^(\s*)else:', lines[i]) and i > 0:
        # Check if this else is part of an if statement
        prev_indent = None
        for j in range(i-1, max(0, i-20), -1):
            if re.match(r'^(\s*)if\s+', lines[j]):
                prev_indent = re.match(r'^(\s*)', lines[j]).group(1)
                break
        
        if prev_indent is not None:
            lines[i] = prev_indent + "else:\n"

# Write the corrected file
with open('checker/services/company_search.py.fixed', 'w') as f:
    f.writelines(lines)
print("✅ Created checker/services/company_search.py.fixed")

print("\nVerifying fixes...\n")

import py_compile
import os

try:
    py_compile.compile('checker/apps.py.fixed')
    print("✅ apps.py.fixed compiles successfully")
except Exception as e:
    print(f"❌ apps.py.fixed still has issues: {e}")

try:
    py_compile.compile('checker/services/company_search.py.fixed')
    print("✅ company_search.py.fixed compiles successfully")
except Exception as e:
    print(f"❌ company_search.py.fixed still has issues: {e}")

print("\nApplying the fixed files...")

# If files compile, replace the originals
if os.path.exists('checker/apps.py.fixed'):
    try:
        py_compile.compile('checker/apps.py.fixed')
        os.rename('checker/apps.py.fixed', 'checker/apps.py')
        print("✅ Successfully replaced checker/apps.py with fixed version")
    except Exception:
        print("❌ Fixed apps.py had issues, not replacing original")

if os.path.exists('checker/services/company_search.py.fixed'):
    try:
        py_compile.compile('checker/services/company_search.py.fixed')
        os.rename('checker/services/company_search.py.fixed', 'checker/services/company_search.py')
        print("✅ Successfully replaced checker/services/company_search.py with fixed version")
    except Exception:
        print("❌ Fixed company_search.py had issues, not replacing original") 