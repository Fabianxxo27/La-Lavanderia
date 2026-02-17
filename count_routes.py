import re

files = ['routes/auth.py', 'routes/cliente.py', 'routes/admin.py', 'routes/api.py', 'routes/utils.py']
total = 0

for f in files:
    with open(f, 'r', encoding='utf-8') as file:
        content = file.read()
        routes = re.findall(r"@bp\.route\(['\"](.+?)['\"]", content)
        print(f'\n{f}: {len(routes)} rutas')
        for r in routes[:5]:
            print(f'  - {r}')
        if len(routes) > 5:
            print(f'  ... +{len(routes)-5} más')
        total += len(routes)

print(f'\n{"="*50}')
print(f'✅ TOTAL: {total} rutas en blueprints MVC')
