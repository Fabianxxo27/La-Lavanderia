@echo off
cd /d "c:\Users\fabia\Downloads\Proyecto de Grado La Lavanderia\GitHub\La-Lavanderia"
git add render.yaml app.py
git commit -m "FIX: Configuracion Render - usar waitress-serve en produccion"
git push origin main
echo Done!
pause
