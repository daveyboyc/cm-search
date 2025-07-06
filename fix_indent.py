#!/usr/bin/env python3

def fix_indentation():
    file_path = 'checker/services/component_detail.py'
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Find the line with the indentation error and fix it
    lines = content.split('\n')
    fixed_lines = []
    
    in_if_block = False
    for line in lines:
        if 'if isinstance(cmu_registry_entry.raw_data, dict):' in line:
            in_if_block = True
            fixed_lines.append(line)
        elif in_if_block and 'raw_cmu_data = cmu_registry_entry.raw_data' in line:
            # Fix the indentation
            fixed_lines.append('                raw_cmu_data = cmu_registry_entry.raw_data')
            in_if_block = False
        else:
            fixed_lines.append(line)
    
    fixed_content = '\n'.join(fixed_lines)
    
    with open(file_path, 'w') as f:
        f.write(fixed_content)
    
    print(f"Fixed indentation in {file_path}")

if __name__ == "__main__":
    fix_indentation() 