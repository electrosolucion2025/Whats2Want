import sendgrid

from django.conf import settings
from sendgrid.helpers.mail import Mail

def send_order_email(order):
    """ Envía un correo con el ticket del pedido usando SendGrid """
    # 📩 Configuración del email
    subject = f"✅ Confirmación de tu pedido #{order.order_number}"
    # to_email = "juanmacostapts@gmail.com"  # 📌 Si tienes el email real del cliente, úsalo aquí
    from_email = settings.SENDGRID_FROM_EMAIL  # 📩 Remitente del correo

    # ✨ Contenido del correo
    # ✨ Contenido del correo
    body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Confirmación de Pedido</title>
    </head>
    <body style="font-family: Arial, sans-serif; background-color: #f4f4f4; padding: 20px; margin: 0;">
        <table style="max-width: 600px; width: 100%; background-color: #ffffff; padding: 20px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1); margin: auto;">
            <tr>
                <td style="text-align: center;">
                    <h2 style="color: #333;">✅ Confirmación de Pedido</h2>
                    <p style="color: #777;">Gracias por tu pedido en <strong>{order.tenant.name}</strong></p>
                </td>
            </tr>

            <tr>
                <td style="padding: 10px 0;">
                    <p><strong>📌 Pedido:</strong> {order.order_number}</p>
                    <p><strong>📅 Fecha:</strong> {order.created_at.strftime('%d/%m/%Y')}</p>
                    <p><strong>🕒 Hora:</strong> {order.created_at.strftime('%H:%M')}</p>
                    <p><strong>📍 Mesa:</strong> {order.table_number if order.table_number else 'N/A'}</p>
                    <p><strong>📞 Cliente:</strong> {order.phone_number}</p>
                </td>
            </tr>

            <tr>
                <td>
                    <h3 style="color: #555;">🛒 Detalle del Pedido</h3>
                    <table style="width: 100%; border-collapse: collapse;">
                        <thead>
                            <tr style="background-color: #eee;">
                                <th style="text-align: left; padding: 8px;">Producto</th>
                                <th style="text-align: center; padding: 8px;">Cant.</th>
                                <th style="text-align: right; padding: 8px;">Precio</th>
                            </tr>
                        </thead>
                        <tbody>
    """

    # 🔹 Iterar sobre los productos en el pedido
    for item in order.items.all():
        extras = ', '.join([extra['name'] for extra in item.extras]) if isinstance(item.extras, list) and item.extras else "Sin extras"
        excluded = ', '.join(item.exclusions) if isinstance(item.exclusions, list) else (item.exclusions if item.exclusions else "Sin exclusiones")
        special_instructions = f"<br><small style='color: #0066cc;'>📝 {item.special_instructions}</small>" if item.special_instructions else ""

        body += f"""
            <tr>
                <td style="padding: 8px; border-bottom: 1px solid #ddd;">
                    <strong>{item.product.name}</strong> {special_instructions} <br>
                    <small style="color: #888;">➕ {extras} | ❌ {excluded}</small>
                </td>
                <td style="text-align: center; padding: 8px; border-bottom: 1px solid #ddd;">{item.quantity}</td>
                <td style="text-align: right; padding: 8px; border-bottom: 1px solid #ddd;">{item.final_price}€</td>
            </tr>
        """

    # 🔹 Subtotal y Total
    body += f"""
                        </tbody>
                    </table>
                </td>
            </tr>

            <tr>
                <td style="padding: 10px 0;">
                    <h3 style="color: #555;">💰 Resumen</h3>
                    <p><strong>Total de items en el pedido:</strong> {order.get_total_items()}</p>
                    <h2 style="color: #333;">Total: {order.payment.amount}€</h2>
                </td>
            </tr>

            <tr>
                <td style="text-align: center; padding: 20px 0;">
                    <p style="color: #777;">📦 Tu pedido está en preparación. ¡Gracias por tu compra! 😊</p>
                </td>
            </tr>
        </table>
    </body>
    </html>
    """
    
    # 📧 Crear el mensaje
    message = Mail(
        from_email=from_email,
        to_emails= [
            "juanmacostapts@gmail.com",
            "p166r@yahoo.es"
        ],
        # to_emails=to_email,
        subject=subject,
        html_content=body
    )

    try:
        # 🚀 Cliente de SendGrid
        sg = sendgrid.SendGridAPIClient(api_key=settings.SENDGRID_API_KEY)

        # ⚡ Aplicar configuraciones opcionales
        if settings.SENDGRID_SANDBOX_MODE_IN_DEBUG:
            message.mail_settings = {"sandbox_mode": {"enable": True}}

        # ✅ Enviar el correo
        response = sg.send(message)

        # 🖥️ Mostrar el correo en consola si está activado
        if settings.SENDGRID_ECHO_TO_STDOUT:
            print(f"📧 [DEBUG] Correo enviado a {to_email} - Status: {response.status_code}")
            print(f"📩 Contenido del correo:\n{body}")

        else:
            print(f"✅ Correo enviado a {to_email} - Status: {response.status_code}")

    except Exception as e:
        print(f"❌ Error enviando correo: {str(e)}")
