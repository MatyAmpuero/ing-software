from django.urls import path
from django.shortcuts import get_object_or_404, redirect
from ventas.models import Producto
from django.contrib.auth.views import LogoutView
from django.contrib.auth.decorators import login_required
from .views import (
    HomeView, custom_login,
    dashboard_bodeguero, dashboard_cajero, dashboard_jefe,
    ProductoList, ProductoCreate, ProductoUpdate, ProductoDelete,
    VentaList, VentaCreate,
    usuario_list, UsuarioCreateView, UsuarioUpdateView, UsuarioDeleteView,
    activate_account,
    go_to_register,
    register, custom_login, desactivar_producto, 
    dashboard_bodeguero, dashboard_cajero,
)

urlpatterns = [
    #PAGINA DE BIENVENIDA
    path("", HomeView.as_view(), name="home"),

    #LOGIN LOGOUT
    path("login/", custom_login, name="login"),
    path("logout/", LogoutView.as_view(next_page="home"), name="logout"),

    #DASHBOARD POR ROL
    path("bodega/dashboard/", dashboard_bodeguero, name="dashboard_bodeguero"),
    path("cajero/dashboard/", dashboard_cajero,   name="dashboard_cajero"),
    path("jefe/dashboard/", dashboard_jefe, name="dashboard_jefe"),

    #CRUD PRODUCTOS
    path("productos/",       ProductoList.as_view(),   name="productos_list"),
    path("productos/nuevo/", ProductoCreate.as_view(), name="producto_create"),
    path("productos/<int:pk>/editar/", ProductoUpdate.as_view(), name="producto_update"),
    path("productos/<int:pk>/borrar/",  ProductoDelete.as_view(), name="producto_delete"),
    path('productos/<int:pk>/desactivar/', desactivar_producto, name='desactivar_producto'),

    #CRUD USUARIOS
    path("jefe/usuarios/",             usuario_list,            name="usuario_list"),
    path("jefe/usuarios/nuevo/",       UsuarioCreateView.as_view(), name="usuario_create"),
    path("jefe/usuarios/<int:pk>/editar/", UsuarioUpdateView.as_view(), name="usuario_update"),
    path("jefe/usuarios/<int:pk>/borrar/",  UsuarioDeleteView.as_view(), name="usuario_delete"),

    #CRUD VENTAS
    path('ventas/', VentaList.as_view(), name='ventas_list'),
    path('ventas/nueva/', VentaCreate.as_view(), name='venta_create'),

    # Registro de usuarios
    path("register/", register, name="register"),
    path("go-to-register", go_to_register, name="go_to_register"),
    

    #Activar cuenta
    path('activate/<uidb64>/<token>/', activate_account, name='activate_account'),
]

@login_required
def desactivar_producto(request, pk):
    producto = get_object_or_404(Producto, pk=pk)
    producto.activo = False
    producto.save()
    return redirect('producto_list')