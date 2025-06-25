from django.urls import path
from django.shortcuts import get_object_or_404, redirect
from ventas.models import Producto
from django.contrib.auth.views import LogoutView
from django.contrib.auth.decorators import login_required
from .views import (
    HomeView, custom_login,
    dashboard_bodeguero, dashboard_cajero, dashboard_jefe,
    entrada_stock,
    ProveedorListView, ProveedorCreateView, ProveedorUpdateView, ProveedorDeleteView,
    ProductoList, ProductoCreate, ProductoUpdate, ProductoDelete,
    CompradorFielListView, CompradorFielCreateView, CompradorFielUpdateView, CompradorFielDeleteView,
    VentaList, VentaCreate, reportes_ventas, reset_ventas,
    usuario_list, UsuarioCreateView, UsuarioUpdateView, UsuarioDeleteView,
    activate_account,
    go_to_register, register, desactivar_producto,
    export_sales_excel,
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

    #CRUD PROVEEDORES
    path('bodega/proveedores/', ProveedorListView.as_view(),   name='proveedores_list'),
    path('bodega/proveedores/nuevo/', ProveedorCreateView.as_view(), name='proveedor_create'),
    path('bodega/proveedores/<int:pk>/editar/', ProveedorUpdateView.as_view(), name='proveedor_update'),
    path('bodega/proveedores/<int:pk>/borrar/', ProveedorDeleteView.as_view(), name='proveedor_delete'),
    #STOCK
    path('bodega/entrada/', entrada_stock, name='entrada_stock'),

    #CRUD USUARIOS
    path("jefe/usuarios/",             usuario_list,            name="usuario_list"),
    path("jefe/usuarios/nuevo/",       UsuarioCreateView.as_view(), name="usuario_create"),
    path("jefe/usuarios/<int:pk>/editar/", UsuarioUpdateView.as_view(), name="usuario_update"),
    path("jefe/usuarios/<int:pk>/borrar/",  UsuarioDeleteView.as_view(), name="usuario_delete"),

    #CRUD COMPRADORES FIELES
    path('compradores-fieles/', CompradorFielListView.as_view(), name='compradores_fieles_list'),
    path('compradores-fieles/nuevo/', CompradorFielCreateView.as_view(), name='comprador_fiel_create'),
    path('compradores-fieles/<int:pk>/editar/', CompradorFielUpdateView.as_view(), name='comprador_fiel_update'),
    path('compradores-fieles/<int:pk>/borrar/', CompradorFielDeleteView.as_view(), name='comprador_fiel_delete'),

    #CRUD VENTAS
    path('ventas/', VentaList.as_view(), name='ventas_list'),
    path('ventas/nueva/', VentaCreate.as_view(), name='venta_create'),
    path("jefe/reportes/", reportes_ventas, name="reportes_ventas"),
    path("jefe/reset_ventas/",  reset_ventas,    name="reset_ventas"),

    # Registro de usuarios
    path("register/", register, name="register"),
    path("go-to-register", go_to_register, name="go_to_register"),
    
    #Activar cuenta
    path('activate/<uidb64>/<token>/', activate_account, name='activate_account'),

    #Reportes a excel
    path("jefe/reportes/exportar_excel/", export_sales_excel, name="exportar_excel"),
]