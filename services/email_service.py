"""
Servicio de envío de correos electrónicos con SendGrid
"""
import base64
import os
import threading
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import (
    Mail,
    Attachment,
    FileContent,
    FileName,
    FileType,
    Disposition,
    ContentId,
)


def send_email_async(destinatario, asunto, cuerpo_html, attachments=None):
    """
    Envía un correo de forma asíncrona para no bloquear la aplicación.
    
    Args:
        destinatario: email del destinatario
        asunto: asunto del correo
        cuerpo_html: contenido HTML del correo
        attachments: lista opcional de adjuntos en formato dict
            - filename: nombre del archivo
            - content_bytes/content: contenido en bytes
            - mime_type: tipo MIME (ej: image/png)
            - disposition: attachment/inline (opcional)
            - content_id: id para inline cid: (opcional)
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

            # Adjuntar archivos opcionales (por ejemplo, código de barras del pedido)
            if attachments:
                for idx, attachment_data in enumerate(attachments, start=1):
                    try:
                        if not isinstance(attachment_data, dict):
                            print(f"[WARN] Adjunto #{idx} inválido: se esperaba un dict", flush=True)
                            continue

                        filename = attachment_data.get('filename', f'adjunto_{idx}.bin')
                        mime_type = attachment_data.get('mime_type', 'application/octet-stream')
                        disposition_value = attachment_data.get('disposition', 'attachment')
                        content_id_value = attachment_data.get('content_id')
                        content_bytes = attachment_data.get('content_bytes', attachment_data.get('content'))

                        if not content_bytes:
                            print(f"[WARN] Adjunto omitido ({filename}): contenido vacío", flush=True)
                            continue

                        if isinstance(content_bytes, str):
                            content_bytes = content_bytes.encode('utf-8')

                        encoded_content = base64.b64encode(content_bytes).decode('utf-8')

                        attachment = Attachment(
                            file_content=FileContent(encoded_content),
                            file_name=FileName(filename),
                            file_type=FileType(mime_type),
                            disposition=Disposition(disposition_value)
                        )

                        if content_id_value:
                            attachment.content_id = ContentId(content_id_value)

                        message.add_attachment(attachment)
                    except Exception as attachment_error:
                        print(f"[WARN] Error procesando adjunto #{idx}: {attachment_error}", flush=True)
            
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
