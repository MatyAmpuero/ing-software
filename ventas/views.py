from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.db.models import Sum, F, FloatField, ExpressionWrapper
from django.db import transaction
from django.views.generic import TemplateView, ListView, CreateView, UpdateView, DeleteView
from django.views.decorators.cache import never_cache
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth.forms import PasswordResetForm, AuthenticationForm, UserCreationForm, UserChangeForm
from django.contrib.auth.views import PasswordResetView
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from django.utils.decorators import method_decorator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes
from django.urls import reverse
from ventas.models import Producto, Venta, DetalleVenta
from .forms import ProductoForm, CustomRegisterForm, JefeUserChangeForm, JefeUserCreationForm

# Pantalla de bienvenida
class HomeView(TemplateView):
    template_name = "ventas/home.html"

@never_cache
def custom_login(request):
    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            # Chequea grupo
            if user.groups.filter(name='Jefe').exists():
                return redirect('dashboard_jefe')
            elif user.groups.filter(name='Bodeguero').exists():
                return redirect('dashboard_bodeguero')
            elif user.groups.filter(name='Cajero').exists():
                return redirect('dashboard_cajero')
            else:
                return redirect('home')
        else:
            messages.error(request, "Usuario o contraseña incorrectos")
    else:
        form = AuthenticationForm()
    return render(request, "ventas/login.html", {"form": form})



@never_cache
@login_required(login_url='login')
@user_passes_test(lambda u: u.groups.filter(name='Bodeguero').exists(), login_url='login')
def dashboard_bodeguero(request):
    return render(request, "ventas/bodega/dashboard.html")

@never_cache
@login_required(login_url='login')
@user_passes_test(lambda u: u.groups.filter(name='Jefe').exists(), login_url='login')
def dashboard_jefe(request):
    """
    Panel de control para el Jefe:
    - KPIs: total de productos, activos, inactivos.
    - Ventas: total de ventas, ingresos totales.
    - Usuarios registrados.
    - Últimas 5 ventas.
    """
    # Total productos
    total_prod = Producto.objects.count()
    activos    = Producto.objects.filter(activo=True).count()
    inactivos  = total_prod - activos

    # Ventas y facturación
    total_ventas  = Venta.objects.count()
    ingresos      = Venta.objects.aggregate(total=Sum('total'))['total'] or 0

    # Usuarios
    total_usuarios = User.objects.count()

    # Últimas 5 ventas
    ultimas_ventas = Venta.objects.order_by('-fecha')[:5]

    context = {
        'total_prod': total_prod,
        'activos': activos,
        'inactivos': inactivos,
        'total_ventas': total_ventas,
        'ingresos': ingresos,
        'total_usuarios': total_usuarios,
        'ultimas_ventas': ultimas_ventas,
    }
    return render(request, 'ventas/jefe/dashboard.html', context)

# ventas/views.py

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.cache import never_cache
from django.contrib import messages

from ventas.models import Producto, Venta, DetalleVenta

@never_cache
@login_required(login_url='login')
@user_passes_test(lambda u: u.groups.filter(name='Cajero').exists(), login_url='login')
def dashboard_cajero(request):
    # 1) Búsqueda de productos
    termino = request.GET.get('busqueda', '').strip()
    productos = Producto.objects.filter(activo=True)
    if termino:
        productos = productos.filter(nombre__icontains=termino)

    # 2) Reconstruir carrito desde sesión
    carrito = request.session.get('carrito', {})       # claves: str(producto_id)
    carrito_items = []
    total = 0
    for pid_str, cantidad in carrito.items():
        try:
            prod = Producto.objects.get(pk=int(pid_str), activo=True)
        except Producto.DoesNotExist:
            continue
        subtotal = prod.precio * cantidad
        carrito_items.append({
            'producto': prod,
            'cantidad': cantidad,
            'subtotal': subtotal,
        })
        total += subtotal

    # 3) Anotar stock disponible en cada producto
    #    (stock real - ya en carrito)
    for p in productos:
        en_carrito = carrito.get(str(p.id), 0)
        p.stock_disponible = max(p.stock - en_carrito, 0)

    # 4) Procesar POST: eliminar, agregar, finalizar
    if request.method == "POST":
        # 4.a) Eliminar elemento del carrito
        if 'eliminar' in request.POST:
            prod_id = request.POST['eliminar']
            if prod_id in carrito:
                del carrito[prod_id]
                request.session['carrito'] = carrito
            return redirect('dashboard_cajero')

        # 4.b) Agregar al carrito
        if 'agregar' in request.POST:
            prod_id = request.POST['producto_id']
            try:
                cantidad = int(request.POST.get('cantidad', 1))
            except ValueError:
                cantidad = 1

            try:
                producto_obj = Producto.objects.get(pk=int(prod_id), activo=True)
            except Producto.DoesNotExist:
                messages.error(request, "Producto no válido.")
                return redirect('dashboard_cajero')

            ya_en_carrito = carrito.get(prod_id, 0)
            stock_disp = producto_obj.stock

            if cantidad + ya_en_carrito > stock_disp:
                restante = stock_disp - ya_en_carrito
                messages.error(
                    request,
                    f"No puedes agregar {cantidad} unidades de “{producto_obj.nombre}” porque "
                    f"ya tienes {ya_en_carrito} en el carrito y solo hay {stock_disp} en stock. "
                    f"Puedes agregar hasta {max(restante, 0)} más."
                )
                return redirect('dashboard_cajero')

            carrito[prod_id] = ya_en_carrito + cantidad
            request.session['carrito'] = carrito
            return redirect('dashboard_cajero')

        # 4.c) Finalizar venta
        if 'finalizar' in request.POST:
            medio_pago = request.POST.get('medio_pago', '').strip()
            if not carrito_items or total == 0:
                messages.error(request, "El carrito está vacío. Agrega al menos un producto antes de finalizar.")
                return redirect('dashboard_cajero')
            
            if not medio_pago:
                messages.error(request, "Selecciona un medio de pago.")
                return redirect('dashboard_cajero')

            # Crear Venta y DetalleVenta
            venta = Venta.objects.create(
                total=total,
                usuario=request.user,
                medio_pago=medio_pago
            )
            for item in carrito_items:
                DetalleVenta.objects.create(
                    venta=venta,
                    producto=item['producto'],
                    cantidad=item['cantidad'],
                    precio=item['producto'].precio
                )
                # descontar stock
                prod_obj = item['producto']
                prod_obj.stock -= item['cantidad']
                prod_obj.save()

            # vaciar carrito y mostrar éxito
            request.session['carrito'] = {}
            return render(request, 'ventas/cajero/venta_exito.html', {'venta': venta})

    # 5) Render final
    return render(request, 'ventas/cajero/dashboard.html', {
        'termino_busqueda': termino,
        'productos': productos,
        'carrito_items': carrito_items,
        'total': total,
    })

# Registro de usuarios
@never_cache
def register(request):
    # consumimos mensajes previos
    list(messages.get_messages(request))

    if request.method == "POST":
        form = CustomRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            send_activation_email(user, request)
            messages.success(request,
                "¡Usuario creado correctamente! Revisa tu correo para activar tu cuenta.",
                extra_tags='register'
            )
            return redirect("login")
        else:
            messages.error(request,
                "Por favor corrige los errores en el formulario.",
                extra_tags='register'
            )
    else:
        form = CustomRegisterForm()

    # limpiamos cualquier error de formulario arrastrado
    if request.method != "POST":
        form._errors = {}

    return render(request, "ventas/register.html", {"form": form})

def send_activation_email(user, request):
    token = default_token_generator.make_token(user)
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    activation_link = request.build_absolute_uri(
        reverse('activate_account', kwargs={'uidb64': uid, 'token': token})
    )
    subject = "Activa tu cuenta en Pumpkin's Hell"
    message = f'Hola {user.username},\n\nPara activar tu cuenta, haz clic en este enlace:\n{activation_link}\n\nSi no te registraste, puedes ignorar este correo.'
    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email])

def activate_account(request, uidb64, token):
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        user.is_active = True
        user.save()
        messages.success(request, "¡Cuenta activada! Ahora puedes iniciar sesión.")
        return redirect("login")
    else:
        messages.error(request, "El enlace de activación no es válido o ha expirado.")
        return redirect("home")
    
def go_to_register(request):
    return redirect('register')

@login_required
def dashboard_bodega(request):
    if request.user.groups.filter(name="Bodeguero").exists():
        return render(request, "bodega/dashboard.html")
    else:
        return redirect('no_autorizado')



@login_required
def ventas_pos(request):
    productos = Producto.objects.filter(activo=True)
    carrito = request.session.get('carrito', {})
    carrito_items = []
    total = 0

    # Reconstruir objetos del carrito
    for pid, cantidad in carrito.items():
        producto = Producto.objects.get(pk=pid)
        subtotal = producto.precio * cantidad
        carrito_items.append({
            'producto': producto,
            'cantidad': cantidad,
            'subtotal': subtotal,
        })
        total += subtotal

    if request.method == "POST":
        if 'agregar' in request.POST:
            prod_id = request.POST['producto_id']
            cantidad = int(request.POST['cantidad'])
            carrito[prod_id] = carrito.get(prod_id, 0) + cantidad
            request.session['carrito'] = carrito
            return redirect('ventas_pos')
        if 'finalizar' in request.POST:
            medio_pago = request.POST['medio_pago']
            # Aquí guardas la venta en BD y limpias el carrito
            venta = Venta.objects.create(total=total, usuario=request.user, medio_pago=medio_pago)
            for item in carrito_items:
                DetalleVenta.objects.create(
                    venta=venta,
                    producto=item['producto'],
                    cantidad=item['cantidad'],
                    precio=item['producto'].precio,
                )
            request.session['carrito'] = {}
            return render(request, 'ventas/venta_exito.html', {'venta': venta})

    return render(request, 'ventas/cajero/venta_pos.html', {
        'productos': productos,
        'carrito_items': carrito_items,
        'total': total,
    })

@never_cache
@login_required(login_url='login')
@user_passes_test(lambda u: u.groups.filter(name='Jefe').exists(), login_url='login')
def reportes_ventas(request):
    # Total de ventas y facturación
    total_ventas = Venta.objects.count()
    ingresos = Venta.objects.aggregate(total=Sum('total'))['total'] or 0

    # Ticket promedio
    ticket_promedio = (ingresos / total_ventas) if total_ventas else 0

    # Top 5 productos por unidades vendidas y sus ingresos
    top_products = (
        DetalleVenta.objects
        .values('producto__nombre')
        .annotate(
            unidades_vendidas=Sum('cantidad'),
            ingresos=Sum(
                ExpressionWrapper(F('cantidad') * F('precio'),
                                  output_field=FloatField())
            )
        )
        .order_by('-unidades_vendidas')[:5]
    )

    return render(request, 'ventas/jefe/reportes_ventas.html', {
        'total_ventas': total_ventas,
        'ingresos': ingresos,
        'ticket_promedio': ticket_promedio,
        'top_products': top_products,
    })


# Helper para chequear que el usuario es Jefe
def is_jefe(user):
    return user.groups.filter(name='Jefe').exists()

@login_required(login_url='login')
@user_passes_test(is_jefe, login_url='no_autorizado')
def reset_ventas(request):
    """
    Vista para que el Jefe borre todas las ventas y sus detalles.
    GET: muestra confirmación.
    POST: elimina Venta y DetalleVenta dentro de una transacción.
    """
    if request.method == 'POST':
        with transaction.atomic():
            DetalleVenta.objects.all().delete()
            Venta.objects.all().delete()
        messages.success(request, '✅ Todas las ventas han sido reseteadas.')
        return redirect('dashboard_jefe')
    return render(request, 'ventas/confirm_reset_ventas.html')

@never_cache
@login_required(login_url='login')
@user_passes_test(lambda u: u.groups.filter(name='Jefe').exists(), login_url='login')
def usuario_list(request):
    usuarios = User.objects.all()
    return render(request, 'ventas/jefe/usuario_list.html', {'usuarios': usuarios})

# CRUD Productos
@method_decorator(never_cache, name='dispatch')
class ProductoList(LoginRequiredMixin, ListView):
    model = Producto
    template_name = 'ventas/producto_list.html'
    context_object_name = 'object_list'

    def get_queryset(self):
        return Producto.objects.filter(activo=True)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['es_bodeguero'] = self.request.user.groups.filter(name='Bodeguero').exists()
        context['es_jefe'] = self.request.user.groups.filter(name='Jefe').exists()
        return context

class ProductoCreate(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = Producto
    form_class = ProductoForm
    template_name = 'ventas/producto_form.html'
    success_url = reverse_lazy('productos_list')
    permission_required = 'ventas.add_producto'

class ProductoUpdate(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = Producto
    form_class = ProductoForm
    template_name = 'ventas/producto_form.html'
    success_url = reverse_lazy('productos_list')
    permission_required = 'ventas.change_producto'

class ProductoDelete(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = Producto
    template_name = 'ventas/producto_confirm_delete.html'
    success_url = reverse_lazy('productos_list')
    permission_required = 'ventas.delete_producto'


@login_required
def desactivar_producto(request, pk):
    producto = get_object_or_404(Producto, pk=pk)
    producto.activo = False
    producto.save()
    return redirect('productos_list')

#CRUD USUARIOS
class UsuarioCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = User
    form_class = JefeUserCreationForm
    template_name = 'ventas/jefe/usuario_form.html'
    success_url = reverse_lazy('usuario_list')
    permission_required = 'auth.add_user'

class UsuarioUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = User
    form_class = JefeUserChangeForm
    template_name = 'ventas/jefe/usuario_form.html'
    success_url = reverse_lazy('usuario_list')
    permission_required = 'auth.change_user'

class UsuarioDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = User
    template_name = 'ventas/jefe/usuario_confirm_delete.html'
    success_url = reverse_lazy('usuario_list')
    permission_required = 'auth.delete_user'

# CRUD Ventas
class VentaList(LoginRequiredMixin, ListView):
    model = Venta
    template_name = 'ventas/venta_list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['es_bodeguero'] = self.request.user.groups.filter(name='Bodeguero').exists()
        context['es_jefe'] = self.request.user.groups.filter(name='Jefe').exists()
        return context

class VentaCreate(LoginRequiredMixin, CreateView):
    model = Venta
    fields = ['producto', 'cantidad']
    template_name = 'ventas/venta_form.html'
    success_url = reverse_lazy('ventas_list')

class CustomPasswordResetView(PasswordResetView):
    form_class = PasswordResetForm
    template_name = 'ventas/password_reset.html'
    email_template_name = 'registration/password_reset_email.html'
    success_url = reverse_lazy('password_reset_done')

    def form_valid(self, form):
        email = form.cleaned_data.get("email")
        if not User.objects.filter(email=email).exists():
            messages.error(self.request, "Este correo no está registrado en el sistema. Verifique el correo e intentelo más tarde.")
            return self.form_invalid(form)
        return super().form_valid(form)
