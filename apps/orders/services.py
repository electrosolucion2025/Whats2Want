# Python standard library imports
import uuid
from decimal import Decimal

# Django imports
from django.utils import timezone

# Local imports
from apps.menu.models import Extra, Product
from apps.orders.models import Order, OrderItem
from apps.payments.models import Payment
from apps.payments.services import generate_payment_link
from apps.payments.utils import send_order_email
from apps.payments.views import process_successful_payment
from apps.vip.utils import is_vip
from apps.whatsapp.models import WhatsAppContact
from apps.whatsapp.utils import (
    send_promotion_opt_in_message,
    send_whatsapp_message,
)

def generate_order_number():
    number_generated = str(int(uuid.uuid4().int))[:12]
    print(f"🔢 Número de pedido generado: {number_generated}", flush=True)
    return number_generated  # Convierte UUID a número y toma 12 dígitos

def save_order_to_db(order_data, session):
    print(f"🔍 Guardando pedido: {order_data}", flush=True)
    try:
        order = Order.objects.create(
            tenant=session.tenant,
            phone_number=session.phone_number,
            chat_session=session.chat_session,
            table_number=order_data.get('table_number'),
            notes=order_data.get('notes', ''),
            order_number=generate_order_number(),
            status='PENDING',
            delivery_type=order_data.get('delivery_type', 'DINE_IN'),
            payment_status='PENDING',
            discount=Decimal(order_data.get('discount', 0.00)),
            tax_amount=Decimal(order_data.get('tax_amount', 0.00)),
            is_scheduled=False,
        )
        print(f"📝 Pedido creado: {order}", flush=True)

        total_price = Decimal('0.00') 

        for item in order_data.get('order_items', []):
            print(f"🍔 Procesando ítem: {item}", flush=True)
            product_name = item.get('product_name')
            quantity = item.get('quantity', 1)
            unit_price = Decimal(str(item.get('unit_price', 0.00)))
            extras_data = item.get('extras', [])
            exclusions = item.get('exclusions', [])
            special_instructions = item.get('special_instructions', '')
            item_discount = Decimal(str(item.get('discount', 0.00)))
            item_tax = Decimal(str(item.get('tax_amount', 0.00)))

            try:
                product = Product.objects.get(name__iexact=product_name, tenant=session.tenant)
            except Product.DoesNotExist:
                print(f"❌ Producto no encontrado: {product_name}", flush=True)
                continue

            extras_list = []
            for extra_data in extras_data:
                extra_name = extra_data.get('name')
                extra_price = Decimal(str(extra_data.get('price', 0.00)))

                extra = Extra.objects.filter(name__iexact=extra_name, tenant=session.tenant).first()
                
                if extra:
                    extras_list.append({"name": extra.name, "price": float(extra_price)})
                else:
                    print(f"❌ Extra no encontrado: {extra_name}", flush=True)
            
            # 🚀 Obtener el contacto del usuario para verificar si es su primera compra
            contact = WhatsAppContact.objects.filter(phone_number=session.phone_number, tenant=session.tenant).first()
            is_first_buy = contact.first_buy if contact else False

            # ✅ Solo permitir precio 0 si es la primera compra y el producto es café
            if is_first_buy:
                print(f"🎁 Aplicando promoción de café gratis para {contact.phone_number}", flush=True)
            else:
                unit_price = product.price  # ❌ Si no es la primera compra, usar el precio de la BD

            order_item = OrderItem.objects.create(
                tenant=session.tenant,
                order=order,
                product=product,
                quantity=quantity,
                price=unit_price,
                exclusions=", ".join(exclusions),
                special_instructions=special_instructions,
                extras=extras_list,
                discount=item_discount,
                tax_amount=item_tax
            )

            # ✅ Si el producto no es gratuito, sumarlo al total
            if order_item.price > 0:
                total_price += order_item.final_price

        order.total_price = Decimal(total_price - order.discount + order.tax_amount).quantize(Decimal("0.01"))
        order.save()

        print("✅ Pedido guardado correctamente en la base de datos.", flush=True)
        
        contact = WhatsAppContact.objects.get(phone_number=session.phone_number, tenant=session.tenant)
        if contact and contact.first_buy:
            contact.first_buy = False
            contact.save()
            print(f"🎉 Primera compra registrada para {contact.phone_number}. `first_buy` actualizado a False.", flush=True)
        
        # 🔍 **Verificar si el usuario es VIP**
        is_vip_user = is_vip(session.phone_number, session.tenant)

        if is_vip_user:
            print("🏆 Cliente VIP detectado. Saltando proceso de pago...", flush=True)
            
            # 🏦 **Marcar el pago como completado sin requerir transacción**
            payment = Payment.objects.create(
                tenant=order.tenant,
                order=order,
                payment_id=order.order_number,
                amount=order.total_price,
                currency="EUR",
                status="completed",  # 🏆 Pago automáticamente completado
                payment_method="VIP",
            )

            # 📝 **Actualizar el estado del pedido**
            order.payment_status = "PAID"
            order.status = "COMPLETED"
            order.save()

            # 🚪 **Cerrar la sesión del usuario VIP**
            chat_session = order.chat_session
            if chat_session:
                chat_session.is_active = False
                chat_session.ended_at = timezone.now()
                chat_session.save()
                print(f"🔒 Sesión {chat_session.id} cerrada tras el pedido VIP {order.order_number}", flush=True)

            # 🖨️ **Generar los tickets de impresión**
            process_successful_payment(order)
            print(f"🖨️ Tickets de impresión generados para el pedido VIP {order.order_number}", flush=True)

            print(f"🔍 Contenido de SESSION: {session}", flush=True)

            # 📩 **Enviar mensaje de confirmación al usuario VIP**
            confirmation_message = (
                f"🏆 ¡Gracias por tu pedido VIP! 🎉\n"
                f"📌 Pedido: {order.order_number}\n"
                f"📦 Tu pedido está en preparación. ¡Disfrútalo! 😊"
            )
            send_whatsapp_message(order.phone_number, confirmation_message, tenant=order.tenant)
            
            # 📧 Enviar correo con el ticket del pedido
            send_order_email(order)

            # 🔹 Comprobar si el usuario ya aceptó recibir promociones
            try:
                whatsapp_contact = WhatsAppContact.objects.get(phone_number=order.phone_number, tenant=order.tenant)
                if whatsapp_contact.accepts_promotions is None:
                    send_promotion_opt_in_message(whatsapp_contact.phone_number, order.tenant)
            except WhatsAppContact.DoesNotExist:
                pass

        else:
            # 📦 **Generar el link de pago normalmente**
            payment = Payment.objects.create(
                tenant=order.tenant,
                order=order,
                payment_id=order.order_number,
                amount=order.total_price,
                currency="EUR",
                status="pending",
                payment_method="Card",
            )

            # 📩 **Generar y enviar el link de pago**
            payment_link = generate_payment_link(order)
            message = (
                f"🔗 Para pagar, haz clic aquí: {payment_link}\n\n"
                f"📌 Una vez completado el pago, recibirás la confirmación. 😊"
            )
            send_whatsapp_message(session.phone_number, message, tenant=session.tenant)
            
            print(f"✉️ Mensaje enviado al usuario: {message}", flush=True)

    except Exception as e:
        print(f"❌ Error al guardar el pedido: {e}", flush=True)
