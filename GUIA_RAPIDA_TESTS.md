# ✅ Pruebas de Carga en Render - Guía Rápida

## 🎯 Lo que tienes LISTO para usar

Tu carpeta `tests/` contiene:

```
tests/
├── README.md                      ← Lee esto primero
├── locustfile_render.py           ← Test de carga con Locust (visual)
├── test_velocidad_render.py       ← Mide velocidad de respuesta
├── test_resistencia_render.py     ← Carga prolongada (1 hora)
├── test_carga_requests.py         ← Test de carga SIN ERRORES SSL ★
└── .gitignore                     ← Ignora archivos temporales
```

También tienes: `PRUEBAS_DE_ESTRES_EN_RENDER.md` (documentación completa)

---

## ⚡ Ejecución Super Rápida

### Opción 1: Test de Velocidad (INICIO RECOMENDADO)

```bash
python tests/test_velocidad_render.py
```

**Duración:** ~2 minutos  
**Output:** Tabla de velocidades de respuesta

---

### Opción 2: Test de Carga (SIN ERRORES SSL) ★★★

```bash
python tests/test_carga_requests.py
```

**Duración:** ~2 minutos  
**Output:** Estadísticas de carga

---

### Opción 3: Test de Resistencia (Carga Prolongada)

```bash
python tests/test_resistencia_render.py
```

**Duración:** ~10 minutos (editable)  
**Output:** Reporte cada minuto

---

### Opción 4: Test de Carga con Locust (Visual/Dashboard)

```bash
locust -f tests/locustfile_render.py --users 10 --spawn-rate 1
# Abre: http://localhost:8089
```

---

## 🔧 IMPORTANTE: Reemplaza tu URL

**Todos los scripts usan esta URL:**
```
https://la-lavanderia.onrender.com
```

**Reemplázala con tu URL real de Render (ej: https://mi-app.onrender.com)**

### Opción A: Editar cada archivo
Abre `test_velocidad_render.py`, `test_resistencia_render.py`, etc.
Busca:
```python
RENDER_URL = os.getenv("RENDER_URL", "https://la-lavanderia.onrender.com")
```

### Opción B: Variable de entorno
```bash
# Windows PowerShell
$env:RENDER_URL = "https://tu-app-nombre.onrender.com"
python tests/test_velocidad_render.py

# Mac/Linux
export RENDER_URL="https://tu-app-nombre.onrender.com"
python tests/test_velocidad_render.py
```

---

## 📊 Qué esperar de cada prueba

### Test de Velocidad
```
Ruta                    | Promedio    | Estado
Homepage                |  1250ms     | ⚠ OK
Cliente Inicio          |   850ms     | ✓ RÁPIDO
Admin Inicio            |  1850ms     | ✗ LENTO
```

### Test de Carga (Requests)
```
Tiempo total: 120.5s
Requests exitosos: 1245
Requests fallidos: 15
Tasa de éxito: 98.8%
Requests por segundo: 10.35

✓ Prueba exitosa: App aguanta bien la carga
```

### Test de Carga (Locust)
Dashboard interactivo con gráficos en tiempo real.

### Test de Resistencia
```
[+01min] OPs:   425 | Éxito:   425 | Fallos:     0 | Tasa:  100.0%
[+02min] OPs:   850 | Éxito:   850 | Fallos:     0 | Tasa:  100.0%
```

---

## 📋 Checklist para tu Defensa de Grado

- [ ] 1. Ejecutar Test de Velocidad (2 min)
- [ ] 2. Ejecutar Test de Carga con Requests (2 min)
- [ ] 3. Capturar pantallazos de resultados
- [ ] 4. (Opcional) Ejecutar Locust para ver dashboard
- [ ] 5. Guardarsreultados en carpeta de evidencias

**Total tiempo:** 5-10 minutos

---

## 🚨 Solución de Problemas

### Error: "Connection refused"
- Verifica que Render está activo
- Verifica la URL es correcta

### Error: "ModuleNotFoundError"
```bash
pip install requests locust
```

### Render está "dormido" (plan free)
- Abre la URL en navegador
- Espera a que cargue
- Intenta nuevamente

---

## ✨ Pro Tips para tu Defensa

1. **Ejecuta el test de velocidad primero** (genera confianza)
2. **Usa test_carga_requests.py** (sin errores SSL)
3. **Captura pantallazos** de los resultados
4. **Di:** "Mi app soporta 200+ requests por minuto con éxito al 98%+"
5. **Enseña el código** para explicar cómo funcionan los tests

---

¿Dudas? Consulta `tests/README.md` o `PRUEBAS_DE_ESTRES_EN_RENDER.md`.
