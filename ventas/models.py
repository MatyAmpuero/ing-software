from django.db import models
from django.utils import timezone
# from django.core.validators import RegexValidator

class Proveedor(models.Model):
    nombre   = models.CharField(max_length=100, unique=True)
    contacto = models.CharField(max_length=100)
    telefono = models.CharField(max_length=20)
    email    = models.EmailField()

    def __str__(self):
        return self.nombre

class Entrada(models.Model):
    proveedor  = models.ForeignKey(Proveedor, on_delete=models.PROTECT, related_name='entradas')
    fecha      = models.DateTimeField(auto_now_add=True)
    creado_por = models.ForeignKey('auth.User', on_delete=models.PROTECT)

    def __str__(self):
        return f"Entrada #{self.pk} – {self.proveedor.nombre} ({self.fecha:%Y-%m-%d})"

class EntradaDetalle(models.Model):
    entrada    = models.ForeignKey(Entrada, on_delete=models.CASCADE, related_name='detalles')
    producto   = models.ForeignKey('Producto', on_delete=models.PROTECT)
    cantidad   = models.PositiveIntegerField()

    def __str__(self):
        return f"{self.producto.nombre}: {self.cantidad}"

class Producto(models.Model):
    nombre    = models.CharField(max_length=100, unique=True)
    precio    = models.PositiveIntegerField(verbose_name="Precio")
    stock     = models.PositiveIntegerField(default=0)
    proveedor = models.ForeignKey('Proveedor', on_delete=models.PROTECT, related_name='productos')
    activo    = models.BooleanField(default=True)

    def __str__(self):
        return self.nombre

class Venta(models.Model):
    total = models.BigIntegerField(default=0)
    usuario = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    fecha = models.DateTimeField(default=timezone.now)
    medio_pago = models.CharField(max_length=20, choices=[
        ("Crédito", "Tarjeta Crédito"),
        ("Débito", "Tarjeta Débito"),
        ("Efectivo", "Efectivo"),
    ])

    def __str__(self):
        return f'Venta {self.id} ({self.fecha:%d-%m-%Y %H:%M})'
    
class CompradorFiel(models.Model):
    nombre    = models.CharField(max_length=100)
    telefono  = models.CharField(max_length=20)
    email     = models.EmailField(blank=True)
    direccion = models.CharField(max_length=150, blank=True)
    rut       = models.CharField(max_length=15, unique=True)
    visitas   = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.nombre

class DetalleVenta(models.Model):
    venta    = models.ForeignKey(Venta, related_name='detalles', on_delete=models.CASCADE)
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    cantidad = models.PositiveIntegerField()
    precio   = models.PositiveIntegerField() # precio unitario al momento de la venta

    def subtotal(self):
        return self.precio * self.cantidad

    def __str__(self):
        return f'{self.producto.nombre} x {self.cantidad}'