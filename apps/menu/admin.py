import json

from django.contrib import admin, messages
from django.shortcuts import render, redirect
from django.urls import path
from django import forms
from django.utils.html import format_html

from apps.menu.models import (
    Product, Category, Allergen, Extra, ProductAllergen, ProductExtra, ExtraAllergen
)
from apps.tenants.models import Tenant

# 📌 **Formulario para importar Menú desde JSON**
class MenuUploadForm(forms.Form):
    tenant = forms.ModelChoiceField(
        queryset=Tenant.objects.all(),
        label="Selecciona un Tenant",
        required=True
    )
    json_file = forms.FileField(label="Sube un archivo JSON")

# 📌 **Inline para manejar los alérgenos dentro de Productos**
class ProductAllergenInline(admin.TabularInline):  # También puede ser `StackedInline`
    model = ProductAllergen
    extra = 1  # Muestra 1 campo vacío por defecto para agregar más
    autocomplete_fields = ["allergen"]  # Mejora la búsqueda

# 📌 **Inline para manejar los extras dentro de Productos**
class ProductExtraInline(admin.TabularInline):
    model = ProductExtra
    extra = 1
    autocomplete_fields = ["extra"]

# 📌 **Admin de Productos**
@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "price", "available", "created_at")
    search_fields = ("name", "category__name")
    list_filter = ("category", "available", "created_at")
    ordering = ("-created_at",)
    list_editable = ("price", "available")

    # 📌 Agregamos los inlines para alérgenos y extras
    inlines = [ProductAllergenInline, ProductExtraInline]

    fieldsets = (
        ("Información General", {"fields": ("name", "description", "category", "image")}),
        ("Detalles del Producto", {"fields": ("price", "ingredients", "calories", "spicy_level", "preparation_time")}),
        ("Atributos Especiales", {"fields": ("is_vegetarian", "is_vegan", "gluten_free", "is_special")}),
        ("Stock y Disponibilidad", {"fields": ("stock", "available")}),
        ("Opciones de Impresión", {"fields": ("print_zones",)}),
        ("Tiempos", {"fields": ("created_at", "updated_at")}),
    )

    readonly_fields = ("created_at", "updated_at")  # 🔒 Evitar edición de fechas

# 📌 **Admin de Categorías con Importación de Menú**
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "tenant", "is_active", "created_at")
    list_filter = ("tenant", "is_active", "created_at")
    search_fields = ("name",)
    ordering = ("-created_at",)

    def get_urls(self):
        """
        Agrega la URL personalizada para la importación del menú.
        """
        urls = super().get_urls()
        custom_urls = [
            path("import-menu/", self.admin_site.admin_view(self.import_menu_view), name="import_menu"),
        ]
        return custom_urls + urls
    
    def changelist_view(self, request, extra_context=None):
        """
        Agrega el botón "📥 Importar Menú" en la lista de categorías.
        """
        extra_context = extra_context or {}
        extra_context["import_menu_url"] = "/admin/menu/category/import-menu/"  # ✅ URL Absoluta Correcta
        return super().changelist_view(request, extra_context=extra_context)


    def import_menu_view(self, request):
        """
        Vista personalizada para importar menús desde un archivo JSON.
        """
        if request.method == "POST":
            form = MenuUploadForm(request.POST, request.FILES)
            if form.is_valid():
                tenant = form.cleaned_data["tenant"]
                json_file = request.FILES["json_file"]

                try:
                    data = json.load(json_file)
                    self.process_menu_upload(data, tenant)
                    messages.success(request, f"✅ Menú importado exitosamente para {tenant.name}.")
                    return redirect("admin:menu_category_changelist")
                except Exception as e:
                    messages.error(request, f"❌ Error al procesar el archivo JSON: {e}")
        else:
            form = MenuUploadForm()

        context = {
            "form": form,
            "title": "Importar Menú desde JSON"
        }
        return render(request, "admin/import_menu.html", context)

    def process_menu_upload(self, data, tenant):
        """
        Procesa el archivo JSON y carga el menú en la base de datos.
        """
        for category_data in data.get("categories", []):
            category, _ = Category.objects.get_or_create(
                name=category_data["name"],
                tenant=tenant
            )

            for item in category_data.get("items", []):
                product, _ = Product.objects.get_or_create(
                    name=item["name"],
                    tenant=tenant,
                    defaults={
                        "category": category,
                        "description": item.get("description", ""),
                        "ingredients": ", ".join(item.get("ingredients", [])),
                        "price": item.get("price", 0),
                        "available": item.get("available", True)
                    }
                )
                
    def import_menu_button(self):
        """
        Genera un botón en la vista de lista para importar el menú.
        """
        return format_html(
            '<div style="margin-bottom: 15px;">'
            '<a class="button" href="{}" style="background: #007bff; color: white; padding: 8px 12px; text-decoration: none; border-radius: 4px;">📥 Importar Menú</a>'
            "</div>",
            "import-menu/"
        )
        
    import_menu_button.allow_tags = True
    import_menu_button.short_description = "Importar Menú"

# 📌 **Admin de Alérgenos**
@admin.register(Allergen)
class AllergenAdmin(admin.ModelAdmin):
    list_display = ("name", "description")
    search_fields = ("name",)
    ordering = ("name",)


# 📌 **Admin de Extras**
@admin.register(Extra)
class ExtraAdmin(admin.ModelAdmin):
    list_display = ("name", "price", "available", "is_default", "max_quantity", "created_at")
    search_fields = ("name",)
    list_filter = ("available", "is_default")
    list_editable = ("price", "available", "is_default", "max_quantity")
    ordering = ("-created_at",)


# 📌 **Registra las Tablas Intermedias**
admin.site.register(ProductAllergen)
admin.site.register(ProductExtra)
admin.site.register(ExtraAllergen)
