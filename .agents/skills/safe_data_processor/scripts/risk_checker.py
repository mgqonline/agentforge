import ast
import sys

DANGEROUS_CALLS = {
    'os': ['system', 'remove', 'rmdir', 'removedirs', 'rename', 'replace'],
    'shutil': ['rmtree', 'move', 'copy'],
    'subprocess': ['run', 'Popen', 'call', 'check_call', 'check_output']
}

def check_file(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            code = f.read()
    except Exception as e:
        print(f"Error reading file {filepath}: {e}")
        sys.exit(1)

    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        print(f"Syntax error in {filepath}: {e}")
        sys.exit(1)

    warnings = []
    
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute):
                if isinstance(node.func.value, ast.Name):
                    module_name = node.func.value.id
                    func_name = node.func.attr
                    if module_name in DANGEROUS_CALLS and func_name in DANGEROUS_CALLS[module_name]:
                        warnings.append(f"Line {node.lineno}: Found potentially dangerous call '{module_name}.{func_name}'")
            elif isinstance(node.func, ast.Name):
                func_name = node.func.id
                for mod, funcs in DANGEROUS_CALLS.items():
                    if func_name in funcs:
                        warnings.append(f"Line {node.lineno}: Found potentially dangerous call '{func_name}' (possibly from {mod})")

    if warnings:
        print("⚠️  RISK DETECTED:")
        for w in warnings:
            print(" - " + w)
        sys.exit(1)
    else:
        print("✅ No obvious dangerous calls detected.")
        sys.exit(0)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python risk_checker.py <filepath>")
        sys.exit(1)
    check_file(sys.argv[1])
