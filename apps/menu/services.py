from apps.menu.models import Category, Product, Extra, Allergen

def get_menu_data(tenant):
    menu_data = []
    
    # 🔹 Obtener el total de categorías activas utilizando el método de clase
    total_categories = Category.get_total_categories(tenant)

    # 🔹 Filtrar categorías activas y ordenarlas correctamente
    categories = Category.objects.filter(tenant=tenant, is_active=True).order_by("order")
    
    for category in categories:
        category_data = {
            "category": category.name,
            "order": category.order,
            "total_categories": total_categories,  # 🔹 Se obtiene desde el método de clase
            "items": []
        }

        # 🔹 Obtener productos activos de la categoría
        products = Product.objects.filter(category=category, tenant=tenant, available=True)
        
        for product in products:
            # 🔹 Obtener extras relacionados con el producto
            extras = Extra.objects.filter(productextra__product=product, available=True)
            
            # 🔹 Obtener alérgenos relacionados con el producto
            allergens = Allergen.objects.filter(productallergen__product=product)

            product_data = {
                "name": product.name,
                "description": product.description,
                "price": product.price,
                "available": product.available,
                "extras": [{"name": extra.name, "price": extra.price, "available": extra.available} for extra in extras],
                "allergens": [allergen.name for allergen in allergens]
            }
            
            category_data["items"].append(product_data)

        menu_data.append(category_data)

    return {"menu": menu_data}
