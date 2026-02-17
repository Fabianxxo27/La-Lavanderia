"""
WSGI entry point para producción
Usado por: waitress-serve wsgi:app
o: gunicorn wsgi:app
"""
from app import app

if __name__ == '__main__':
    # Solo para desarrollo local
    app.run(debug=True, host='127.0.0.1', port=5000)
