# Generated by Django 5.1.6 on 2025-02-15 12:31

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tenants', '0004_tenant_has_first_buy_promo'),
        ('whatsapp', '0009_whatsappcontact_last_detected_language'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='whatsappcontact',
            name='tenant',
        ),
        migrations.AddField(
            model_name='whatsappcontact',
            name='tenants',
            field=models.ManyToManyField(related_name='whatsapp_contacts', to='tenants.tenant', verbose_name='Tenants'),
        ),
    ]
