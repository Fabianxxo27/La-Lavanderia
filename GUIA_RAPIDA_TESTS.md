# ✅ Pruebas de Carga en Render - Guía Rápida

## 🎯 Lo que tienes LISTO para usar

Tu carpeta `tests/` contiene:

```
tests/
├── README.md                      ← Lee esto primero
├── run_tests.bat                  ← Ejecuta AQUÍ (Windows)
├── run_tests.sh                   ← Ejecuta AQUÍ (Mac/Linux)
├── locustfile_render.py           ← Test de carga simulando usuarios
├── test_velocidad_render.py       ← Mide velocidad de respuesta
└── test_resistencia_render.py     ← Carga prolongada (1 hora)
```

También tienes: `PRUEBAS_DE_ESTRES_EN_RENDER.md` (documentación completa)

---

## ⚡ Ejecución Super Rápida

### Opción 1: Script Automatizado (RECOMENDADO)

**Windows - Abre PowerShell en la carpeta del proyecto:**
```bash
tests\run_tests.bat
```

**Mac/Linux - Abre Terminal:**
```bash
bash tests/run_tests.sh
```

### Opción 2: Comando Directo

**Medir velocidad (2 minutos):**
```bash
python tests/test_velocidad_render.py
```

**Ver dashboard en vivo (5 minutos):**
```bash
locust -f tests/locustfile_render.py --users 20 --spawn-rate 2
# Abre: http://localhost:8089
```

**Carga prolongada (10 minutos):**
```bash
python tests/test_resistencia_render.py
```

---

## 🔧 IMPORTANTE: Reemplaza tu URL

**Todos los scripts usan esta URL:**
```
https://la-lavanderia.onrender.com
```

**Reemplázala con tu URL real:**

### Opción A: Editar cada archivo
Abre `test_velocidad_render.py`, `test_resistencia_render.py`, `locustfile_render.py`:

Busca:
```python
RENDER_URL = os.getenv("RENDER_URL", "https://la-lavanderia.onrender.com")
```

Reemplaza por tu URL, ej:
```python
RENDER_URL = os.getenv("RENDER_URL", "https://tu-app-nombre.onrender.com")
```

### Opción B: Variable de entorno (mejor)
```bash
# Windows PowerShell
$env:RENDER_URL = "https://tu-app-nombre.onrender.com"

# Mac/Linux
export RENDER_URL="https://tu-app-nombre.onrender.com"
```

---

## 📊 Qué esperar de cada prueba

### Test de Velocidad
```
Ruta                    | Promedio    | Estado
Homepage                |  1250ms     | ⚠ OK
Cliente Inicio          |   850ms     | ✓ RÁPIDO
```
✓ Muestra tabla con tiempos  
✓ Duración: ~2 minutos

### Test de Carga (Locust)
Dashboard interactivo en http://localhost:8089 con:
- Gráficos en tiempo real
- Líneas de usuarios conectados
- Tiempos de respuesta por ruta
- Errores detectados

✓ Excelente para demostración  
✓ Duración: configurable (default 5 min)

### Test de Resistencia
```
[+01min] OPs:   425 | Éxito:   425 | Fallos:     0 | Tasa:  100.0%
[+02min] OPs:   850 | Éxito:   850 | Fallos:     0 | Tasa:  100.0%
```
✓ Detecta memory leaks  
✓ Duración: 10 minutos (editable)

---

## 📋 Checklist de Ejecución

Para tu defensa de grado, ejecuta en este orden:

- [ ] 1. Abrir `tests/run_tests.bat` (o `.sh`)
- [ ] 2. Seleccionar opción 1 (Velocidad)
- [ ] 3. Capturar pantalla del resultado
- [ ] 4. Seleccionar opción 2 (Locust)
- [ ] 5. Abrir http://localhost:8089
- [ ] 6. Capturar pantalla del dashboard
- [ ] 7. Dejar correr 5 minutos para demostrar
- [ ] 8. Guardar resultados

**Total tiempo:** 15-20 minutos

---

## 🚨 Problemas Comunes

### "ModuleNotFoundError: No module named 'locust'"
```bash
pip install locust requests
```

### "Connection refused"
- Tu app en Render no está disponible
- Verifica que Render está activo
- Verifica la URL es correcta

### "Timeout"
- Render está lento (plan gratuito hibernación)
- Usa menos usuarios: `--users 5`

### Locust no abre dashboard
- Espera 10 segundos
- Abre manualmente: http://localhost:8089

---

## 📚 Documentación Completa

Lee `PRUEBAS_DE_ESTRES_EN_RENDER.md` para:
- Explicación detallada de cada prueba
- Interpretación de resultados
- Recomendaciones para la defensa
- Troubleshooting avanzado

---

## ✨ Pro Tips para tu Defensa

1. **Ejecuta el test de velocidad primero** (más rápido, genera confianza)
2. **Abre Locust mientras hablas** sobre la arquitectura
3. **Captura pantallazos** del dashboard en vivo
4. **Di:** "Mi app soporta 20+ usuarios simultáneos con respuesta promedio de X ms"
5. **Muestra el código** para explicar cómo funcionan los tests

---

¿Dudas? Consulta `tests/README.md` para detalles técnicos.
