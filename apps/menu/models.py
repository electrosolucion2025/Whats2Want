import uuid

from django.db import models
from apps.tenants.models import Tenant

# Modelo de Alérgenos
class Allergen(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, null=True, blank=True) # Relación con el inquilino
    name = models.CharField(max_length=50)
    description = models.TextField(blank=True, null=True)
    icon = models.ImageField(upload_to='allergens/', blank=True, null=True)

    def __str__(self):
        return self.name

# Tabla intermedia para Productos y Alérgenos
class ProductAllergen(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, null=True, blank=True) # Relación con el inquilino
    product = models.ForeignKey('Product', on_delete=models.CASCADE)
    allergen = models.ForeignKey(Allergen, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('tenant', 'product', 'allergen')

# Modelo de Categorías
class Category(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, null=True, blank=True) # Relación con el inquilino
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    image = models.ImageField(upload_to='categories/', blank=True, null=True)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

# Modelo de Extras
class Extra(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, null=True, blank=True) # Relación con el inquilino
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    price = models.DecimalField(max_digits=6, decimal_places=2)
    available = models.BooleanField(default=True)
    allergens = models.ManyToManyField(Allergen, through='ExtraAllergen', blank=True)
    is_default = models.BooleanField(default=False)
    max_quantity = models.PositiveIntegerField(null=True, blank=True)
    image = models.ImageField(upload_to='extras/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

# Tabla intermedia para Extras y Alérgenos
class ExtraAllergen(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, null=True, blank=True) # Relación con el inquilino
    extra = models.ForeignKey(Extra, on_delete=models.CASCADE)
    allergen = models.ForeignKey(Allergen, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('tenant', 'extra', 'allergen')

# Tabla intermedia para Productos y Extras
class ProductExtra(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, null=True, blank=True) # Relación con el inquilino
    product = models.ForeignKey('Product', on_delete=models.CASCADE)
    extra = models.ForeignKey(Extra, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('tenant', 'product', 'extra')

# Modelo de Productos
class Product(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, null=True, blank=True)
    category = models.ForeignKey(Category, related_name='products', on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    price = models.DecimalField(max_digits=6, decimal_places=2)
    ingredients = models.TextField()
    allergens = models.ManyToManyField(Allergen, through='ProductAllergen', blank=True)
    extras = models.ManyToManyField(Extra, through='ProductExtra', blank=True)
    image = models.ImageField(upload_to='products/', blank=True, null=True)
    available = models.BooleanField(default=True)
    is_special = models.BooleanField(default=False)
    preparation_time = models.PositiveIntegerField(null=True, blank=True)
    spicy_level = models.PositiveIntegerField(null=True, blank=True)
    stock = models.PositiveIntegerField(null=True, blank=True)
    calories = models.PositiveIntegerField(null=True, blank=True)
    
    # ✅ Booleanos con opción de ser NULL
    is_vegetarian = models.BooleanField(null=True, blank=True)  
    is_vegan = models.BooleanField(null=True, blank=True)
    gluten_free = models.BooleanField(null=True, blank=True)
    
    print_zones = models.ManyToManyField('printers.PrinterZone', blank=True)

    tags = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
