"""
Identificar rutas faltantes entre original y MVC
"""
import re

# Leer original
with open('app_original_backup.py', 'r', encoding='utf-8') as f:
    original = f.read()

# Extraer TODAS las rutas del original con sus métodos
rutas_original = re.findall(r'@app\.route\([\'"]([^\'"]+)[\'"](?:,\s*methods=\[[^\]]+\])?\)\s*\ndef\s+(\w+)\(', original)

print("="*80)
print("RUTAS EN app_original_backup.py")
print("="*80)
print(f"\nTotal: {len(rutas_original)} rutas\n")

rutas_dict_original = {}
for ruta, func in rutas_original:
    rutas_dict_original[ruta] = func
    print(f"  {ruta:<50} → {func}()")

# Leer MVC
archivos_mvc = ['routes/auth.py', 'routes/cliente.py', 'routes/admin.py', 'routes/api.py', 'routes/utils.py']
rutas_mvc_dict = {}

print("\n" + "="*80)
print("RUTAS EN ARCHIVOS MVC")
print("="*80)

for archivo in archivos_mvc:
    with open(archivo, 'r', encoding='utf-8') as f:
        contenido = f.read()
        rutas = re.findall(r'@bp\.route\([\'"]([^\'"]+)[\'"](?:,\s*methods=\[[^\]]+\])?\)\s*\ndef\s+(\w+)\(', contenido)
        
        print(f"\n{archivo}:")
        for ruta, func in rutas:
            rutas_mvc_dict[ruta] = func
            print(f"  {ruta:<50} → {func}()")

# Comparar
print("\n" + "="*80)
print("ANÁLISIS DE DIFERENCIAS")
print("="*80)

rutas_faltantes = set(rutas_dict_original.keys()) - set(rutas_mvc_dict.keys())
rutas_extra = set(rutas_mvc_dict.keys()) - set(rutas_dict_original.keys())

if rutas_faltantes:
    print(f"\n❌ RUTAS DEL ORIGINAL QUE FALTAN EN MVC ({len(rutas_faltantes)}):")
    for ruta in sorted(rutas_faltantes):
        func = rutas_dict_original[ruta]
        print(f"  • {ruta:<50} → {func}()")
else:
    print("\n✅ Todas las rutas del original están en MVC")

if rutas_extra:
    print(f"\n⚠️ RUTAS EN MVC QUE NO ESTÁN EN ORIGINAL ({len(rutas_extra)}):")
    for ruta in sorted(rutas_extra):
        func = rutas_mvc_dict[ruta]
        print(f"  • {ruta:<50} → {func}()")

# Rutas comunes
rutas_comunes = set(rutas_dict_original.keys()) & set(rutas_mvc_dict.keys())
print(f"\n✓ RUTAS COMUNES: {len(rutas_comunes)}/{len(rutas_dict_original)}")

print("\n" + "="*80)
