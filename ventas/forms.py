import re
from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
# from django.forms import inlineformset_factory
from .models import Producto, Entrada, EntradaDetalle, Proveedor, CompradorFiel
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm, UserChangeForm
from django.contrib.auth.models import User

def validar_rut(rut):
    """Valida que el RUT tenga formato válido y DV correcto (Chile)."""
    rut = rut.upper().replace("-", "").replace(".", "")
    if not re.match(r'^\d{7,8}[0-9K]$', rut):
        raise ValidationError("Ingrese un RUT válido. Ej: 12345678-5")
    cuerpo = rut[:-1]
    dv = rut[-1]

    suma = 0
    multiplo = 2
    for c in reversed(cuerpo):
        suma += int(c) * multiplo
        multiplo += 1
        if multiplo > 7:
            multiplo = 2
    dv_esperado = 11 - (suma % 11)
    if dv_esperado == 11:
        dv_esperado = "0"
    elif dv_esperado == 10:
        dv_esperado = "K"
    else:
        dv_esperado = str(dv_esperado)
    if dv != dv_esperado:
        raise ValidationError("El RUT ingresado no es válido (DV incorrecto).")


class CustomRegisterForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        label='Correo electrónico',
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'correo@ejemplo.com'})
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Este correo electrónico ya está registrado.")
        return email
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.is_active = False
        if commit:
            user.save()
        return user


    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Ingresa tu usuario'
        })
        self.fields['password1'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Ingresa tu contraseña'
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Confirma tu contraseña'
        })
        # Asegúrate que los labels sean correctos
        self.fields['password1'].label = "Contraseña"
        self.fields['password2'].label = "Contraseña (confirmación)"

class LoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Ingresa tu usuario',
            'id': 'id_username'
        })
        self.fields['password'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': '••••••••',
            'id': 'id_password'
        })

# Form para CRUD de Proveedor
type_mismatch_ignore = None  # noqa: F841
class ProveedorForm(forms.ModelForm):
    # Override: Contacto como texto (nombres), sin validación numérica
    contacto = forms.CharField(
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        label="Contacto"
    )
    # Validación: solo números en teléfono
    telefono = forms.CharField(
        max_length=20,
        required=True,
        validators=[RegexValidator(r'^\d+$', message='Solo se permiten números en el teléfono.')],
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        label="Teléfono"
    )

    class Meta:
        model = Proveedor
        fields = ['nombre', 'contacto', 'telefono', 'email']
        widgets = {
            'nombre':   forms.TextInput(attrs={'class': 'form-control'}),
            'email':    forms.EmailInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'nombre':   'Nombre',
            'contacto': 'Contacto',
            'telefono': 'Teléfono',
            'email':    'Email',
        }

# Form y formset para Entrada de stock
class EntradaForm(forms.ModelForm):
    class Meta:
        model = Entrada
        fields = ['proveedor']
        widgets = {'proveedor': forms.Select(attrs={'class': 'form-select'})}

class EntradaDetalleForm(forms.ModelForm):
    class Meta:
        model = EntradaDetalle
        fields = ['producto', 'cantidad']
        widgets = {
            'producto': forms.Select(attrs={'class': 'form-select'}),
            'cantidad': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
        }

EntradaDetalleFormSet = forms.inlineformset_factory(
    Entrada, EntradaDetalle,
    form=EntradaDetalleForm,
    extra=5,
    can_delete=False
)


class ProductoForm(forms.ModelForm):
    class Meta:
        model = Producto
        fields = ['nombre', 'precio', 'stock', 'proveedor']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields['nombre'].widget.attrs['readonly'] = True

    def clean_stock(self):
        stock=self.cleaned_data['stock']
        if stock == 0:
            raise forms.ValidationError("El stock no puede ser 0. Si quieres eliminar el producto, usa la opción de eliminar.")
        return stock

    def clean_precio(self):
        precio = self.cleaned_data['precio']
        if precio <= 0:
            raise forms.ValidationError("El precio debe ser un número entero positivo mayor a cero.")
        return precio
    
#PODERES DEL JEFE
class JefeUserChangeForm(UserChangeForm):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'ejemplo@dominio.com'
        })
    )
    first_name = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    last_name = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    is_active = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    groups = forms.ModelMultipleChoiceField(
        queryset=User.groups.field.model._meta.model.objects.all(),
        required=False,
        widget=forms.SelectMultiple(attrs={'class': 'form-select'})
    )

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'groups', 'is_active')

class CompradorFielForm(forms.ModelForm):
    telefono = forms.CharField(
        max_length=20,
        required=True,
        validators=[RegexValidator(r'^\d+$', message='Sólo se permiten números en el teléfono.')],
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        label="Teléfono"
    )
    rut = forms.CharField(
        max_length=15,
        required=True,
        validators=[validar_rut],
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        label="RUT"
    )

    class Meta:
        model = CompradorFiel
        fields = ['nombre', 'telefono', 'email', 'direccion', 'rut']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'direccion': forms.TextInput(attrs={'class': 'form-control'}),
            # 'rut': forms.TextInput(attrs={'class': 'form-control'}), # opcional aquí porque ya lo definiste arriba
        }

class JefeUserCreationForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'ejemplo@dominio.com'
        })
    )

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email')
