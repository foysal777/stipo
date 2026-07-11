import os

out = []
migrations_dir = 'app/migrations'
for f in sorted(os.listdir(migrations_dir)):
    if f.endswith('.py'):
        path = os.path.join(migrations_dir, f)
        try:
            with open(path, 'r', encoding='utf-8') as file:
                for i, line in enumerate(file, 1):
                    if 'predefinedscholarship_sv' in line.lower():
                        out.append(f"{f}:{i}: {line.strip()}")
        except Exception as e:
            out.append(f"Error reading {f}: {e}")

with open('migration_search.txt', 'w', encoding='utf-8') as out_file:
    out_file.write('\n'.join(out))
