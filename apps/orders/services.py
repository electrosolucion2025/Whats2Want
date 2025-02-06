import uuid
from decimal import Decimal

from apps.orders.models import Order, OrderItem
from apps.menu.models import Product, Extra
from apps.payments.services import generate_payment_link
from apps.whatsapp.utils import send_whatsapp_message

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

                try:
                    extra = Extra.objects.get(name__iexact=extra_name, tenant=session.tenant)
                    extras_list.append({"name": extra.name, "price": float(extra_price)})
                except Extra.DoesNotExist:
                    print(f"❌ Extra no encontrado: {extra_name}", flush=True)
                    continue

            order_item = OrderItem.objects.create(
                tenant=session.tenant,
                order=order,
                product=product,
                quantity=quantity,
                price=unit_price or product.price,
                exclusions=", ".join(exclusions),
                special_instructions=special_instructions,
                extras=extras_list,
                discount=item_discount,
                tax_amount=item_tax
            )

            total_price += order_item.final_price

        order.total_price = Decimal(total_price - order.discount + order.tax_amount).quantize(Decimal("0.01"))
        order.save()

        print("✅ Pedido guardado correctamente en la base de datos.", flush=True)
        
        # 📦 PASO 4: Preparar el link de pago
        payment_link = generate_payment_link(order)
        
        # 📩 PASO 5: Enviar el link al usuario por WhatsApp
        message = (
            f"🔗 Para pagar, haz clic aquí: {payment_link}\n"
            f"📌 Una vez completado el pago, recibirás la confirmación. 😊"
        )
        
        send_whatsapp_message(session.phone_number, message, tenant=session.tenant)
        print(f"✉️ Mensaje enviado al usuario: {message}", flush=True)

    except Exception as e:
        print(f"❌ Error al guardar el pedido: {e}", flush=True)
