# Generated by Django 5.2.1 on 2025-06-25 00:22

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ventas', '0002_proveedor_entrada_entradadetalle'),
    ]

    operations = [
        migrations.AlterField(
            model_name='proveedor',
            name='contacto',
            field=models.CharField(max_length=100),
        ),
        migrations.AlterField(
            model_name='proveedor',
            name='email',
            field=models.EmailField(max_length=254),
        ),
        migrations.AlterField(
            model_name='proveedor',
            name='telefono',
            field=models.CharField(max_length=20),
        ),
    ]
