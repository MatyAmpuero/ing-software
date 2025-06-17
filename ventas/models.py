from django.db import models

class Producto(models.Model):
    nombre    = models.CharField(max_length=100)
    precio    = models.PositiveIntegerField(verbose_name="Precio")
    stock     = models.PositiveIntegerField(default=0)  # unidades en bodega
    activo    = models.BooleanField(default=True)

    def __str__(self):
        return self.nombre

class Venta(models.Model):
    total     = models.PositiveIntegerField(default=0)
    usuario   = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    fecha     = models.DateTimeField(auto_now_add=True)
    medio_pago = models.CharField(max_length=20, choices=[
        ("Crédito", "Tarjeta Crédito"),
        ("Débito", "Tarjeta Débito"),
        ("Efectivo", "Efectivo"),
    ])

    def __str__(self):
        return f'Venta {self.id} ({self.fecha:%d-%m-%Y %H:%M})'

class DetalleVenta(models.Model):
    venta    = models.ForeignKey(Venta, related_name='detalles', on_delete=models.CASCADE)
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    cantidad = models.PositiveIntegerField()
    precio   = models.PositiveIntegerField() # precio unitario al momento de la venta

    def subtotal(self):
        return self.precio * self.cantidad

    def __str__(self):
        return f'{self.producto.nombre} x {self.cantidad}'