import datetime, calendar, openpyxl, json
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.db.models.functions import TruncDay
from django.db.models import Sum, F, FloatField, ExpressionWrapper
from django.db import transaction
from django.views.generic import TemplateView, ListView, CreateView, UpdateView, DeleteView
from django.views.generic.edit import CreateView
from django.views.decorators.cache import never_cache
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin, UserPassesTestMixin
from django.contrib.auth.forms import PasswordResetForm, AuthenticationForm
from django.contrib.auth.views import PasswordResetView
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import login
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from django.utils.decorators import method_decorator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes
from django.utils import timezone
from django.urls import reverse
from django import forms
from ventas.models import Producto, Venta, DetalleVenta, Proveedor, CompradorFiel
from .forms import (ProductoForm, CustomRegisterForm, JefeUserChangeForm, JefeUserCreationForm, EntradaForm, 
                    EntradaDetalleFormSet, ProveedorForm, CompradorFielForm, VentaForm, DetalleVentaFormSet)


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


def es_jefe(user):
    return user.groups.filter(name='Jefe').exists()

def es_cajero(user):
    return user.groups.filter(name='Cajero').exists()

@never_cache
@login_required(login_url='login')
@user_passes_test(lambda u: u.groups.filter(name='Bodeguero').exists(), login_url='login')
def dashboard_bodeguero(request):
    return render(request, "ventas/bodega/dashboard.html")

@never_cache
@login_required(login_url='login')
@user_passes_test(lambda u: u.groups.filter(name='Jefe').exists(), login_url='login')
def dashboard_jefe(request):
    # ——— Fechas de interés ———
    hoy = timezone.now().date()
    inicio_actual = hoy.replace(day=1)

    #Umbral de stock bajo
    stock_threshold = 10

    #Query a productos activos con stock ≤ umbral
    low_stock = Producto.objects.filter(activo=True, stock__lte=stock_threshold).order_by('stock')

    # ——— KPI básicos ———
    total_prod     = Producto.objects.count()
    activos        = Producto.objects.filter(activo=True).count()
    inactivos      = total_prod - activos
    total_ventas   = Venta.objects.count()
    ingresos_tot   = Venta.objects.aggregate(total=Sum('total'))['total'] or 0
    total_usuarios = User.objects.count()

    # ——— KPI comparativo vs mes anterior ———
    # Calculamos rango mes anterior
    last_day_prev = inicio_actual - datetime.timedelta(days=1)
    inicio_prev  = last_day_prev.replace(day=1)

    # Query ventas en ambos periodos
    ventas_actual  = Venta.objects.filter(fecha__date__gte=inicio_actual, fecha__date__lte=hoy)
    ventas_prev     = Venta.objects.filter(fecha__date__gte=inicio_prev,  fecha__date__lte=last_day_prev)

    # Conteos
    cnt_actual    = ventas_actual.count()
    cnt_prev      = ventas_prev.count()
    ventas_change = (cnt_actual - cnt_prev) / cnt_prev * 100 if cnt_prev else None

    # Ingresos
    ing_actual       = ventas_actual.aggregate(t=Sum('total'))['t'] or 0
    ing_prev         = ventas_prev.aggregate(t=Sum('total'))['t'] or 0
    ingresos_change  = (ing_actual - ing_prev) / ing_prev * 100 if ing_prev else None

    #Conteo compradores fieles
    total_compradores_fieles = CompradorFiel.objects.count()

    # ——— Evolución de ingresos del mes actual ———
    ventas_mes = Venta.objects.filter(
        fecha__date__gte=inicio_actual,
        fecha__date__lte=hoy
    )
    qs_ingresos = (
        ventas_mes
        .annotate(dia=TruncDay('fecha'))
        .values('dia')
        .annotate(total=Sum('total'))
        .order_by('dia')
    )
    labels = [x['dia'].strftime('%d/%m') for x in qs_ingresos]
    data   = [float(x['total']) for x in qs_ingresos]

    # ——— Top 5 productos más vendidos ———
    top5_products = (
        DetalleVenta.objects
        .filter(
            venta__fecha__date__gte=inicio_actual,
            venta__fecha__date__lte=hoy
        )
        .values('producto__nombre')
        .annotate(unidades=Sum('cantidad'))
        .order_by('-unidades')[:5]
    )

    context = {
        #STOCK
        'low_stock': low_stock,
        'stock_threshold': stock_threshold,

        # KPI
        'total_prod':     total_prod,
        'activos':        activos,
        'inactivos':      inactivos,
        'total_ventas':   total_ventas,
        'ingresos':       ingresos_tot,
        'total_usuarios': total_usuarios,
        'cnt_actual':     cnt_actual,
        'cnt_prev':       cnt_prev,
        'ventas_change':  round(ventas_change, 1) if ventas_change is not None else None,
        'ing_actual':     ing_actual,
        'ing_prev':       ing_prev,
        'ingresos_change': round(ingresos_change, 1) if ingresos_change is not None else None,

        # Chart.js
        'income_labels': json.dumps(labels),
        'income_data':   json.dumps(data),

        # Top5
        'top5_products': top5_products,

        #Compradores fieles
        "total_compradores_fieles": total_compradores_fieles,
    }

    context['es_jefe'] = request.user.groups.filter(name='Jefe').exists()
    context['es_bodeguero'] = request.user.groups.filter(name='Bodeguero').exists()
    context['es_cajero'] = request.user.groups.filter(name='Cajero').exists()
    return render(request, 'ventas/jefe/dashboard.html', context)

def es_jefe_o_bodeguero(user):
    return user.groups.filter(name__in=['Bodeguero', 'Jefe']).exists()

@login_required(login_url='login')
@user_passes_test(es_jefe_o_bodeguero, login_url='login')
def entrada_stock(request):
    """
    Permite al bodeguero o jefe registrar entradas de stock.
    """

    # 1. Define a dónde volver según el grupo
    if request.user.groups.filter(name='Jefe').exists():
        volver_url = reverse('dashboard_jefe')
    else:
        volver_url = reverse('dashboard_bodeguero')

    if request.method == 'POST':
        form = EntradaForm(request.POST)
        formset = EntradaDetalleFormSet(request.POST)
        if form.is_valid() and formset.is_valid():
            # VALIDACIÓN: al menos un producto con cantidad
            hay_producto = False
            for detalle_form in formset:
                cleaned = detalle_form.cleaned_data
                if cleaned and not detalle_form.cleaned_data.get('DELETE', False):
                    producto = cleaned.get('producto')
                    cantidad = cleaned.get('cantidad')
                    if producto and cantidad and cantidad > 0:
                        hay_producto = True
                        break
            if not hay_producto:
                return render(request, 'ventas/bodega/entrada_stock.html', {
                    'form': form,
                    'formset': formset,
                    'volver_url': volver_url,  # <-- aquí
                    'error_no_producto': "Debes seleccionar al menos un producto y cantidad para registrar la entrada.",
                })
            # GUARDADO NORMAL
            entrada = form.save(commit=False)
            entrada.creado_por = request.user
            entrada.save()
            for detalle in formset.save(commit=False):
                detalle.entrada = entrada
                detalle.save()
                prod = detalle.producto
                prod.stock += detalle.cantidad
                prod.save()
            messages.success(request, '✔️ Stock actualizado correctamente.')
            return redirect(volver_url)  # <-- aquí también
    else:
        form = EntradaForm()
        formset = EntradaDetalleFormSet()
    return render(request, 'ventas/bodega/entrada_stock.html', {
        'form': form,
        'formset': formset,
        'volver_url': volver_url,  # <-- SIEMPRE agrega esto en cada render
    })



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
    carrito = request.session.get('carrito', {})  # claves: str(producto_id)
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

    # 3) Anotar stock disponible en cada producto (stock real - ya en carrito)
    for p in productos:
        en_carrito = carrito.get(str(p.id), 0)
        p.stock_disponible = max(p.stock - en_carrito, 0)

    # ---- PASAR DATOS PARA AUTOCOMPLETADO ----
    productos_data = [
        {
            "id": p.id,
            "nombre": p.nombre,
            "stock_disponible": p.stock_disponible,
        }
        for p in productos
    ]

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
        'productos_data': productos_data,   # <-- para el autocompletado en JS
        'productos_json': json.dumps(productos_data),
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
            rut_comprador_fiel = request.POST.get('rut_comprador_fiel', '').strip()

            # Busca comprador fiel si se ingresó RUT
            comprador_fiel = None
            if rut_comprador_fiel:
                try:
                    comprador_fiel = CompradorFiel.objects.get(rut=rut_comprador_fiel)
                    comprador_fiel.visitas += 1
                    comprador_fiel.save()
                    comprador_fiel = CompradorFiel.objects.get(rut=rut_comprador_fiel)
                except CompradorFiel.DoesNotExist:
                    comprador_fiel = None

            # Crear la venta (si tienes el campo comprador_fiel en tu modelo)
            venta_kwargs = {
                "total": total,
                "usuario": request.user,
                "medio_pago": medio_pago,
            }
            if hasattr(Venta, "comprador_fiel"):
                venta_kwargs["comprador_fiel"] = comprador_fiel
            venta = Venta.objects.create(**venta_kwargs)

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
    """
    Panel de reportes para el Jefe:
    - KPIs generales
    - Top 5 productos
    - Provee 'today' para el selector de mes en el template
    """
    # Fecha actual para el input[type=month]
    today = timezone.now()

    # 1) KPIs generales
    total_ventas    = Venta.objects.count()
    ingresos        = Venta.objects.aggregate(total=Sum('total'))['total'] or 0
    ticket_promedio = (ingresos / total_ventas) if total_ventas else 0

    # 2) Top 5 productos por unidades vendidas e ingresos
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

    context = {
        'total_ventas':    total_ventas,
        'ingresos':        ingresos,
        'ticket_promedio': ticket_promedio,
        'top_products':    top_products,
        'today':           today,   # para <input type="month">
    }
    return render(request, 'ventas/jefe/reportes_ventas.html', context)


# Helper para chequear que el usuario es Jefe
def is_jefe(user):
    return user.groups.filter(name='Jefe').exists()

#REPORTES A EXCEL
@login_required(login_url='login')
@user_passes_test(is_jefe, login_url='no_autorizado')
def export_sales_excel(request):
    """
    Genera un Excel con todas las ventas y sus detalles
    para el mes seleccionado (YYYY-MM).
    """
    # 1) Obtener mes seleccionado, default = mes actual
    month_str = request.GET.get('month', timezone.now().strftime('%Y-%m'))
    year, month = map(int, month_str.split('-'))
    first_day = datetime.date(year, month, 1)
    last_day  = datetime.date(year, month, calendar.monthrange(year, month)[1])

    # 2) Query ventas y detalles en ese rango
    ventas = Venta.objects.filter(
        fecha__date__gte=first_day,
        fecha__date__lte=last_day
    ).select_related('usuario')
    detalles = DetalleVenta.objects.filter(venta__in=ventas).select_related('producto')

    # 3) Crear workbook
    wb = openpyxl.Workbook()
    ws1 = wb.active
    ws1.title = f"Ventas {year}-{month:02d}"
    ws1.append(['ID','Fecha','Usuario','Medio Pago','Total'])
    for v in ventas:
        ws1.append([
            v.id,
            v.fecha.strftime('%Y-%m-%d %H:%M'),
            v.usuario.username,
            v.medio_pago,
            float(v.total),
        ])

    ws2 = wb.create_sheet('DetalleVentas')
    ws2.append(['ID Detalle','Venta ID','Producto','Cantidad','Precio Unitario'])
    for d in detalles:
        ws2.append([
            d.id,
            d.venta_id,
            d.producto.nombre,
            d.cantidad,
            float(d.precio),
        ])

    # 4) Devolver como attachment
    filename = f"ventas_{year}_{month:02d}.xlsx"
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    wb.save(response)
    return response

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

#CRUD provedores
def es_jefe_o_bodeguero(user):
    return user.groups.filter(name__in=['Jefe', 'Bodeguero']).exists()

decoradores_jefe_bodeguero = [
    login_required,
    user_passes_test(es_jefe_o_bodeguero, login_url='no_autorizado')
]

@method_decorator(never_cache, name='dispatch')
class ProveedorListView(LoginRequiredMixin, ListView):
    model = Proveedor
    template_name = 'ventas/bodega/proveedor_list.html'
    context_object_name = 'proveedores'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        es_bodeguero = self.request.user.groups.filter(name='Bodeguero').exists()
        es_jefe = self.request.user.groups.filter(name='Jefe').exists()
        if es_bodeguero:
            context['volver_url'] = reverse('dashboard_bodeguero')
        elif es_jefe:
            context['volver_url'] = reverse('dashboard_jefe')
        return context

@method_decorator(decoradores_jefe_bodeguero, name='dispatch')
class ProveedorCreateView(LoginRequiredMixin, CreateView):
    model = Proveedor
    form_class = ProveedorForm
    template_name = 'ventas/bodega/proveedor_form.html'
    success_url = reverse_lazy('proveedores_list')

@method_decorator(never_cache, name='dispatch')
class ProveedorUpdateView(UpdateView):
    model = Proveedor
    form_class = ProveedorForm
    template_name = 'ventas/bodega/proveedor_form.html'
    success_url = reverse_lazy('proveedores_list')

@method_decorator(never_cache, name='dispatch')
class ProveedorDeleteView(DeleteView):
    model = Proveedor
    template_name = 'ventas/bodega/proveedor_confirm_delete.html'
    success_url = reverse_lazy('proveedores_list')

#CRUD COMPRADOR FIEL
def es_jefe_o_cajero(user):
    return user.groups.filter(name__in=['Jefe', 'Cajero']).exists()

decoradores_cajero_jefe = [login_required, user_passes_test(es_jefe_o_cajero, login_url='no_autorizado')]

@method_decorator(decoradores_cajero_jefe, name='dispatch')
class CompradorFielListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = CompradorFiel
    template_name = 'ventas/comprador_fiel/list.html'

    def test_func(self):
        return self.request.user.groups.filter(name__in=["Cajero", "Jefe"]).exists()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['es_bodeguero'] = self.request.user.groups.filter(name='Bodeguero').exists()
        context['es_jefe'] = self.request.user.groups.filter(name='Jefe').exists()
        # Puedes agregar aquí otras variables que quieras pasar al template
        if context['es_bodeguero']:
            context['volver_url'] = reverse('dashboard_bodeguero')
        elif context['es_jefe']:
            context['volver_url'] = reverse('dashboard_jefe')
        return context

@method_decorator(decoradores_cajero_jefe, name='dispatch')
class CompradorFielCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = CompradorFiel
    form_class = CompradorFielForm
    template_name = 'ventas/comprador_fiel/form.html'
    success_url = reverse_lazy('compradores_fieles_list')

    def test_func(self):
        return self.request.user.groups.filter(name__in=["Cajero", "Jefe"]).exists()

@method_decorator(decoradores_cajero_jefe, name='dispatch')
class CompradorFielUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = CompradorFiel
    form_class = CompradorFielForm
    template_name = 'ventas/comprador_fiel/form.html'
    success_url = reverse_lazy('compradores_fieles_list')

    def test_func(self):
        return self.request.user.groups.filter(name__in=["Cajero", "Jefe"]).exists()

@method_decorator(decoradores_cajero_jefe, name='dispatch')
class CompradorFielDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = CompradorFiel
    template_name = 'ventas/comprador_fiel/confirm_delete.html'
    success_url = reverse_lazy('compradores_fieles_list')

    def test_func(self):
        return self.request.user.groups.filter(name__in=["Cajero", "Jefe"]).exists()

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
        # Aquí agregas la url de volver:
        if context['es_bodeguero']:
            context['volver_url'] = reverse('dashboard_bodeguero')
        elif context['es_jefe']:
            context['volver_url'] = reverse('dashboard_jefe')
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
    context_object_name = 'ventas'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['es_bodeguero'] = self.request.user.groups.filter(name='Bodeguero').exists()
        context['es_jefe'] = self.request.user.groups.filter(name='Jefe').exists()
        return context

class VentaUpdateView(UpdateView):
    model = Venta
    fields = ['total', 'medio_pago', 'fecha']  # O los campos que necesites
    template_name = 'ventas/venta_form.html'   # O el que tú uses
    success_url = reverse_lazy('ventas_list')

class VentaDeleteView(DeleteView):
    model = Venta
    template_name = 'ventas/venta_confirm_delete.html'  # O el que tú uses
    success_url = reverse_lazy('ventas_list')

def editar_venta(request, pk):
    venta = get_object_or_404(Venta, pk=pk)
    if request.method == "POST":
        formset = DetalleVentaFormSet(request.POST, instance=venta)
        if formset.is_valid():
            formset.save()
            # Si quieres recalcular el total aquí, hazlo:
            venta.total = sum([f.cleaned_data['cantidad'] * f.cleaned_data['precio'] for f in formset.forms if f.cleaned_data and not f.cleaned_data.get('DELETE', False)])
            venta.save()
            return redirect('ventas_list')
    else:
        formset = DetalleVentaFormSet(instance=venta)
    return render(request, 'ventas/editar_venta.html', {'venta': venta, 'formset': formset})


class VentaCreate(LoginRequiredMixin, CreateView):
    model = Venta
    fields = ['total', 'medio_pago', 'fecha']
    template_name = 'ventas/venta_form.html'
    success_url = reverse_lazy('ventas_list')

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        # Si es jefe, campo fecha editable
        if self.request.user.groups.filter(name='Jefe').exists():
            form.fields['fecha'].required = True
            form.fields['fecha'].widget.input_type = 'datetime-local'
            form.fields['fecha'].initial = timezone.now().strftime('%Y-%m-%dT%H:%M')
        else:
            # Para cajero, ocultar fecha
            form.fields['fecha'].widget = forms.HiddenInput()
            form.fields['fecha'].initial = timezone.now()
        return form

    def form_valid(self, form):
        form.instance.usuario = self.request.user
        # Si NO es jefe, fuerza la fecha a ahora
        if not self.request.user.groups.filter(name='Jefe').exists():
            form.instance.fecha = timezone.now()
        return super().form_valid(form)
    
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect
from .forms import VentaForm, DetalleVentaFormSet

@login_required
@user_passes_test(lambda u: u.groups.filter(name='Jefe').exists())
def venta_create(request):
    if request.method == 'POST':
        form = VentaForm(request.POST)
        formset = DetalleVentaFormSet(request.POST)
        if form.is_valid() and formset.is_valid():
            venta = form.save(commit=False)
            venta.usuario = request.user
            # Calcular total sumando detalles
            total = 0
            for detalle in formset:
                if detalle.cleaned_data and not detalle.cleaned_data.get('DELETE', False):
                    total += detalle.cleaned_data['cantidad'] * detalle.cleaned_data['precio']
            venta.total = total
            venta.save()
            formset.instance = venta
            formset.save()
            return redirect('ventas_list')
    else:
        form = VentaForm()
        formset = DetalleVentaFormSet()
    return render(request, 'ventas/venta_form.html', {'form': form, 'formset': formset, 'venta': None})


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
