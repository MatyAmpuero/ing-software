from django.contrib import admin
from .models import Producto, Venta

@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ('nombre','precio','stock')

@admin.register(Venta)
class VentaAdmin(admin.ModelAdmin):
    list_display = ['id', 'usuario', 'total', 'medio_pago', 'fecha', 'detalle_productos']

    def detalle_productos(self, obj):
        return ", ".join([
            f"{d.producto.nombre} x{d.cantidad}" for d in obj.detalles.all()
        ])
    detalle_productos.short_description = "Productos"
