# Generated by Django 5.1.6 on 2025-02-12 18:39

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tenants', '0003_alter_tenant_email'),
    ]

    operations = [
        migrations.AddField(
            model_name='tenant',
            name='has_first_buy_promo',
            field=models.BooleanField(default=False, verbose_name='Promoción de primera compra activa'),
        ),
    ]
