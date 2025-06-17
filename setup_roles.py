import os
import django

# 1) Indica dónde está tu settings.py
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pos.settings")

# 2) Inicializa Django
django.setup()

# 3) Ahora sí puedes importar modelos y permisos
from django.contrib.auth.models import Group, Permission
from ventas.models import Producto, Venta  # Ajusta si tus modelos están en otra parte

# Borra los grupos si ya existen (opcional)
Group.objects.filter(name__in=["Cajero", "Bodeguero", "Jefe"]).delete()

# Crear grupo Cajero
cajero = Group.objects.create(name="Cajero")
cajero.permissions.add(
    Permission.objects.get(codename="add_venta"),
    Permission.objects.get(codename="view_producto"),
)

# Crear grupo Bodeguero
bodeguero = Group.objects.create(name="Bodeguero")
bodeguero.permissions.add(
    Permission.objects.get(codename="add_producto"),
    Permission.objects.get(codename="change_producto"),
    Permission.objects.get(codename="view_producto"),
)

# Crear grupo Jefe con todos los permisos de producto y venta
jefe = Group.objects.create(name="Jefe")
for perm in Permission.objects.filter(content_type__model__in=["producto", "venta"]):
    jefe.permissions.add(perm)

print("✅ Grupos y permisos creados correctamente.")
