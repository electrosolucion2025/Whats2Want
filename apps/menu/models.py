import uuid
from django.db import models
from apps.tenants.models import Tenant

# Modelo de Alérgenos
class Allergen(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, null=True, blank=True, verbose_name="Empresa")
    name = models.CharField(max_length=50, verbose_name="Nombre del alérgeno")  # 🟢 Obligatorio
    description = models.TextField(blank=True, null=True, verbose_name="Descripción")
    icon = models.ImageField(upload_to='allergens/', blank=True, null=True, verbose_name="Ícono del alérgeno")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Alérgeno"
        verbose_name_plural = "Alérgenos"

# Tabla intermedia para Productos y Alérgenos
class ProductAllergen(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, null=True, blank=True, verbose_name="Empresa")
    product = models.ForeignKey('Product', on_delete=models.CASCADE, verbose_name="Producto")
    allergen = models.ForeignKey(Allergen, on_delete=models.CASCADE, verbose_name="Alérgeno")

    class Meta:
        unique_together = ('tenant', 'product', 'allergen')
        verbose_name = "Relación Producto-Alérgeno"
        verbose_name_plural = "Relaciones Productos-Alérgenos"

# Modelo de Categorías
class Category(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, null=True, blank=True, verbose_name="Empresa")
    name = models.CharField(max_length=100, verbose_name="Nombre de la categoría")  # 🟢 Obligatorio
    description = models.TextField(blank=True, null=True, verbose_name="Descripción")
    image = models.ImageField(upload_to='categories/', blank=True, null=True, verbose_name="Imagen")
    order = models.PositiveIntegerField(default=1, verbose_name="Orden de aparición")  # 🔹 Ahora inicia en 1
    is_active = models.BooleanField(default=True, verbose_name="¿Activo?")
    print_zones = models.ManyToManyField('printers.PrinterZone', blank=True, verbose_name="Zonas de impresión")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de creación")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Última actualización")

    def save(self, *args, **kwargs):
        """
        Antes de guardar, si `order` es 1 (valor por defecto), asigna el siguiente número disponible.
        """
        if not self.order or self.order == 1:  # 🔹 Si no tiene orden o es 1, asignar el siguiente disponible
            last_order = Category.objects.filter(tenant=self.tenant).aggregate(models.Max("order"))["order__max"] or 0
            self.order = last_order + 1  # 🔹 Asignar el siguiente número secuencial

        super().save(*args, **kwargs)

    @classmethod
    def get_total_categories(cls, tenant=None):
        """
        Devuelve el total de categorías activas, opcionalmente filtrando por `tenant`.
        """
        if tenant:
            return cls.objects.filter(is_active=True, tenant=tenant).count()
        return cls.objects.filter(is_active=True).count()

    def __str__(self):
        return f"{self.order}. {self.name}"

    class Meta:
        verbose_name = "Categoría"
        verbose_name_plural = "Categorías"
        ordering = ["order"]  # 🔹 Asegura que siempre se ordenen correctamente

# Modelo de Extras
class Extra(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, null=True, blank=True, verbose_name="Empresa")
    name = models.CharField(max_length=100, verbose_name="Nombre del extra")  # 🟢 Obligatorio
    description = models.TextField(blank=True, null=True, verbose_name="Descripción")
    price = models.DecimalField(max_digits=6, decimal_places=2, verbose_name="Precio")
    available = models.BooleanField(default=True, verbose_name="¿Disponible?")
    allergens = models.ManyToManyField(Allergen, through='ExtraAllergen', blank=True, verbose_name="Alérgenos")
    is_default = models.BooleanField(default=False, verbose_name="¿Seleccionado por defecto?")
    max_quantity = models.PositiveIntegerField(null=True, blank=True, verbose_name="Cantidad máxima")
    image = models.ImageField(upload_to='extras/', blank=True, null=True, verbose_name="Imagen")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de creación")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Última actualización")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Extra"
        verbose_name_plural = "Extras"

# Tabla intermedia para Extras y Alérgenos
class ExtraAllergen(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, null=True, blank=True, verbose_name="Empresa")
    extra = models.ForeignKey(Extra, on_delete=models.CASCADE, verbose_name="Extra")
    allergen = models.ForeignKey(Allergen, on_delete=models.CASCADE, verbose_name="Alérgeno")

    class Meta:
        unique_together = ('tenant', 'extra', 'allergen')
        verbose_name = "Relación Extra-Alérgeno"
        verbose_name_plural = "Relaciones Extras-Alérgenos"

# Tabla intermedia para Productos y Extras
class ProductExtra(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, null=True, blank=True, verbose_name="Empresa")
    product = models.ForeignKey('Product', on_delete=models.CASCADE, verbose_name="Producto")
    extra = models.ForeignKey(Extra, on_delete=models.CASCADE, verbose_name="Extra")

    class Meta:
        unique_together = ('tenant', 'product', 'extra')
        verbose_name = "Relación Producto-Extra"
        verbose_name_plural = "Relaciones Productos-Extras"

# Modelo de Productos
class Product(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, null=True, blank=True, verbose_name="Empresa")
    category = models.ForeignKey(Category, related_name='products', on_delete=models.CASCADE, verbose_name="Categoría")
    name = models.CharField(max_length=100, verbose_name="Nombre del producto")  # 🟢 Obligatorio
    description = models.TextField(blank=True, null=True, verbose_name="Descripción")
    price = models.DecimalField(max_digits=6, decimal_places=2, verbose_name="Precio")
    ingredients = models.TextField(verbose_name="Ingredientes")  # 🟢 Obligatorio
    allergens = models.ManyToManyField(Allergen, through='ProductAllergen', blank=True, verbose_name="Alérgenos")
    extras = models.ManyToManyField(Extra, through='ProductExtra', blank=True, verbose_name="Extras")
    image = models.ImageField(upload_to='products/', blank=True, null=True, verbose_name="Imagen")
    available = models.BooleanField(default=True, verbose_name="¿Disponible?")
    is_special = models.BooleanField(default=False, verbose_name="¿Especial?")
    preparation_time = models.PositiveIntegerField(null=True, blank=True, verbose_name="Tiempo de preparación (min)")
    spicy_level = models.PositiveIntegerField(null=True, blank=True, verbose_name="Nivel de picante (0-5)")
    stock = models.PositiveIntegerField(null=True, blank=True, verbose_name="Stock disponible")
    calories = models.PositiveIntegerField(null=True, blank=True, verbose_name="Calorías")

    # ✅ Booleanos con opción de ser NULL
    is_vegetarian = models.BooleanField(null=True, blank=True, verbose_name="¿Vegetariano?")
    is_vegan = models.BooleanField(null=True, blank=True, verbose_name="¿Vegano?")
    gluten_free = models.BooleanField(null=True, blank=True, verbose_name="¿Sin gluten?")

    print_zones = models.ManyToManyField('printers.PrinterZone', blank=True, verbose_name="Zonas de impresión")

    tags = models.CharField(max_length=255, blank=True, null=True, verbose_name="Etiquetas")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de creación")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Última actualización")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Producto"
        verbose_name_plural = "Productos"
