"""
Servicio de envío de correos electrónicos con SendGrid
"""
import os
import threading
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from config import Config


def send_email_async(destinatario, asunto, cuerpo_html):
    """
    Envía un correo de forma asíncrona para no bloquear la aplicación.
    
    Args:
        destinatario: email del destinatario
        asunto: asunto del correo
        cuerpo_html: contenido HTML del correo
    """
    def _send():
        try:
            print(f"[MAIL] send_email_async to={destinatario} subject={asunto}", flush=True)
            if not destinatario or '@' not in destinatario:
                print(f"[WARN] Email destinatario invalido: {destinatario}", flush=True)
                return

            # Obtener API key de SendGrid
            sendgrid_api_key = os.getenv('SENDGRID_API_KEY')
            if not sendgrid_api_key:
                print("[WARN] SENDGRID_API_KEY no configurado en las variables de entorno", flush=True)
                print("[WARN] Agrega la variable SENDGRID_API_KEY en Render", flush=True)
                return
            
            # Email del remitente (usa un email verificado en SendGrid)
            from_email = os.getenv('SENDGRID_FROM_EMAIL', 'noreply@lalavanderia.com')
            
            # Crear mensaje
            message = Mail(
                from_email=from_email,
                to_emails=destinatario,
                subject=asunto,
                html_content=cuerpo_html
            )
            
            # Enviar
            sg = SendGridAPIClient(sendgrid_api_key)
            response = sg.send(message)
            
            if response.status_code in [200, 201, 202]:
                print(f"[OK] Correo enviado a {destinatario}: {asunto}", flush=True)
            else:
                print(f"[ERROR] SendGrid response: {response.status_code}", flush=True)
                
        except Exception as e:
            print(f"[ERROR] Enviando correo a {destinatario}: {e}", flush=True)
    
    # Ejecutar en thread separado
    thread = threading.Thread(target=_send)
    thread.daemon = False
    thread.start()
