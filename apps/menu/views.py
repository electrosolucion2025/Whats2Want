from django.http import JsonResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
import json
from apps.tenants.models import Tenant
from .models import Category, Product, Extra, Allergen, ProductAllergen, ExtraAllergen, ProductExtra

@method_decorator(csrf_exempt, name='dispatch')
class MenuUploadView(View):
    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
            tenant_id = data.get('tenant_id')

            # Verificar si el tenant existe
            try:
                tenant = Tenant.objects.get(id=tenant_id)
            except Tenant.DoesNotExist:
                return JsonResponse({'error': 'Tenant no encontrado'}, status=404)

            for category_data in data.get('categories', []):
                category, _ = Category.objects.get_or_create(
                    name=category_data['name'],
                    tenant=tenant
                )

                for item in category_data.get('items', []):
                    price_data = item.get('price', 0)

                    # Si el precio es un diccionario (ej: {"half": 2.5, "full": 4.5})
                    if isinstance(price_data, dict):
                        for size, price in price_data.items():
                            product_name = f"{item['name']} ({size.capitalize()})"
                            product, _ = Product.objects.get_or_create(
                                name=product_name,
                                tenant=tenant,
                                defaults={
                                    'category': category,
                                    'description': item.get('description', ''),
                                    'ingredients': ", ".join(item.get('ingredients', [])),
                                    'price': price,
                                    'available': item.get('available', True)
                                }
                            )
                            process_allergens_and_extras(item, product, tenant)

                    # Si el precio es un número normal
                    else:
                        product, _ = Product.objects.get_or_create(
                            name=item['name'],
                            tenant=tenant,
                            defaults={
                                'category': category,
                                'description': item.get('description', ''),
                                'ingredients': ", ".join(item.get('ingredients', [])),
                                'price': price_data,
                                'available': item.get('available', True)
                            }
                        )
                        process_allergens_and_extras(item, product, tenant)

            return JsonResponse({'status': 'Menu uploaded successfully'}, status=201)

        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

def process_allergens_and_extras(item, product, tenant):
    # Procesar alérgenos y guardar en ProductAllergen
    for allergen_name in item.get('allergens', []):
        allergen, _ = Allergen.objects.get_or_create(name=allergen_name, tenant=tenant)
        ProductAllergen.objects.get_or_create(product=product, allergen=allergen, tenant=tenant)

    # Procesar extras y guardar en ProductExtra y ExtraAllergen
    for extra_data in item.get('extras', []):
        extra, _ = Extra.objects.get_or_create(
            name=extra_data['name'],
            tenant=tenant,
            defaults={
                'price': extra_data.get('price', 0),
                'available': extra_data.get('available', True)
            }
        )
        ProductExtra.objects.get_or_create(product=product, extra=extra, tenant=tenant)

        # Si el extra tiene alérgenos
        for allergen_name in extra_data.get('allergens', []):
            allergen, _ = Allergen.objects.get_or_create(name=allergen_name, tenant=tenant)
            ExtraAllergen.objects.get_or_create(extra=extra, allergen=allergen, tenant=tenant)
