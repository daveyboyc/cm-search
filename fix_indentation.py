#!/usr/bin/env python

# Fix apps.py
with open('checker/apps.py', 'r') as f:
    lines = f.readlines()

# Fix the indentation for import logging line
lines[24] = '                import logging\n'

with open('checker/apps.py', 'w') as f:
    f.writelines(lines)
print("Fixed indentation in apps.py")

# Fix company_search.py
with open('checker/services/company_search.py', 'r') as f:
    lines = f.readlines()

# Fix indentation for page = 1 after except block
lines[64:66] = ['    except (ValueError, TypeError):\n', '        page = 1\n']

# Fix indentation for context.update(extra_context)
lines[154] = '    context.update(extra_context)\n'

# Fix indentation issues in _organize_year_data function
try:
    for i in range(1180, 1200):
        if "if year and auction:" in lines[i]:
            lines[i] = '            if year and auction:\n'
        elif "if year not in year_auctions:" in lines[i]:
            lines[i] = '                if year not in year_auctions:\n'
        elif "year_auctions[year] = {}" in lines[i]:
            lines[i] = '                    year_auctions[year] = {}\n'
        elif "if auction not in year_auctions[year]:" in lines[i]:
            lines[i] = '                if auction not in year_auctions[year]:\n'
        elif "year_auctions[year][auction] = True" in lines[i]:
            lines[i] = '                    year_auctions[year][auction] = True\n'
        elif "logger.debug" in lines[i] and "Added Auction" in lines[i]:
            lines[i] = '                    logger.debug(f"_organize_year_data: Row {idx} - Added Auction \'{auction}\' for Year \'{year}\'")\n'
except IndexError:
    print("Warning: Some lines for _organize_year_data couldn't be fixed")

# Fix indentation for else block
try:
    for i in range(1395, 1405):
        if "else:" in lines[i]:
            lines[i] = '    else:\n'
except IndexError:
    print("Warning: else block couldn't be fixed")

with open('checker/services/company_search.py', 'w') as f:
    f.writelines(lines)
print("Fixed indentation in company_search.py") 