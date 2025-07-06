#!/usr/bin/env python

# Fix apps.py
print("Fixing apps.py...")
with open('checker/apps.py', 'r') as f:
    content = f.read()

# Fix the indentation for import logging line
fixed_content = content.replace("def perform_startup_checks():\n        import logging", 
                               "def perform_startup_checks():\n                import logging")

with open('checker/apps.py', 'w') as f:
    f.write(fixed_content)
print("✅ Fixed indentation in apps.py")

# Fix company_search.py
print("Fixing company_search.py...")
with open('checker/services/company_search.py', 'r') as f:
    content = f.read()

# Fix indentation for page = 1 after except block
content = content.replace("    except (ValueError, TypeError):\n    page = 1", 
                         "    except (ValueError, TypeError):\n        page = 1")

# Fix indentation for context.update(extra_context)
content = content.replace("    # Add extra context and return\n                context.update(extra_context)\n    context.update(extra_context)",
                         "    # Add extra context and return\n    context.update(extra_context)")

# Fix indentation issues in _organize_year_data function
content = content.replace("            if year and auction:\n        if year not in year_auctions:", 
                         "            if year and auction:\n                if year not in year_auctions:")

content = content.replace("            year_auctions[year] = {}", 
                         "                    year_auctions[year] = {}")

content = content.replace("                if auction not in year_auctions[year]:\n            year_auctions[year][auction] = True", 
                         "                if auction not in year_auctions[year]:\n                    year_auctions[year][auction] = True")

content = content.replace("                    logger.debug", 
                         "                    logger.debug")

# Fix indentation for else block
content = content.replace("            else:", "    else:")

with open('checker/services/company_search.py', 'w') as f:
    f.write(content)
print("✅ Fixed indentation in company_search.py")

print("Verifying fixes...")
import py_compile
try:
    py_compile.compile('checker/apps.py')
    print("✅ apps.py compiles successfully")
except Exception as e:
    print(f"❌ apps.py still has issues: {e}")

try:
    py_compile.compile('checker/services/company_search.py')
    print("✅ company_search.py compiles successfully")
except Exception as e:
    print(f"❌ company_search.py still has issues: {e}") 