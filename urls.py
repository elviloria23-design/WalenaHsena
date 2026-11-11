from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from .views import (
    home, 
    crear_cuenta, 
    catalogo_habitaciones, 
    hotel_view, 
    planes_view, 
    desayunos_view, 
    contactanos_view, 
    login_view, 
    cerrar_sesion,
    reservar_habitacion,
    gerente_dashboard,
    gerente_habitaciones,
    gerente_reservas,
    gerente_pagos,
    gerente_huespedes,
    gerente_reportes,
    gerente_configuracion,
    gerente_tipos,
    gerente_servicios,
    verificar_codigo,
    gerente_eliminar_servicio,
    solicitar_recuperacion,
    verificar_codigo_pass,
    cambiar_password_final,
    mis_reservas,
    cancelar_reserva,
    editar_habitacion,
    eliminar_habitacion,
    eliminar_tipo_habitacion,
    cambiar_estado_staff,
    completar_datos_huesped,
    reserva_exitosa,
    enviar_correo_reserva,
    panel_recepcion,
    cambiar_estado_reserva_recepcion
)

urlpatterns = [

    path('', home, name='home'),
    path('habitaciones/', catalogo_habitaciones, name='catalogo_habitaciones'),
    path('crearCuenta/', crear_cuenta, name='crear_cuenta'),
    path('hotel/', hotel_view, name='hotel'),
    path('planes/', planes_view, name='planes'),
    path('desayunos/', desayunos_view, name='desayunos'),
    path('contactanos/', contactanos_view, name='contactanos'),

    path('login/', login_view, name='login'),
    path('logout/', cerrar_sesion, name='logout'),
    path('verificar-codigo/', verificar_codigo, name='verificar_codigo'),

    path('reservar/<int:habitacion_id>/', reservar_habitacion, name='reservar_habitacion'),
    path('reserva/datos/<int:habitacion_id>/', completar_datos_huesped, name='completar_datos_huesped'),
    path('reserva/exitosa/<int:reserva_id>/', reserva_exitosa, name='reserva_exitosa'),
    path('reserva/enviar-correo/<int:reserva_id>/', enviar_correo_reserva, name='enviar_correo_reserva'),

    path('reserva/cancelar/<int:reserva_id>/', cancelar_reserva, name='cancelar_reserva'),
    path('mis-reservas/', mis_reservas, name='mis_reservas'),

    path('gerente/dashboard/', gerente_dashboard, name='gerente_dashboard'),

    path('gerente/habitaciones/', gerente_habitaciones, name='gerente_habitaciones'),
    path('gerente/habitacion/editar/<int:habitacion_id>/', editar_habitacion, name='editar_habitacion'),
    path('gerente/habitacion/eliminar/<int:habitacion_id>/', eliminar_habitacion, name='eliminar_habitacion'),

    path('gerente/reservas/', gerente_reservas, name='gerente_reservas'),
    path('gerente/pagos/', gerente_pagos, name='gerente_pagos'),

    path('gerente/huespedes/', gerente_huespedes, name='gerente_huespedes'),
    path('gerente/huespedes/staff/<int:user_id>/', cambiar_estado_staff, name='cambiar_estado_staff'),

    path('gerente/reportes/', gerente_reportes, name='gerente_reportes'),
    path('gerente/configuracion/', gerente_configuracion, name='gerente_configuracion'),

    path('gerente/tipos/', gerente_tipos, name='gerente_tipos'),
    path('tipo-habitacion/eliminar/<int:pk>/', eliminar_tipo_habitacion, name='eliminar_tipo_habitacion'),

    path('gerente/servicios/', gerente_servicios, name='gerente_servicios'),
    path('gerente/servicios/eliminar/<int:pk>/', gerente_eliminar_servicio, name='gerente_eliminar_servicio'),

    path('recuperar/paso-1/', solicitar_recuperacion, name='solicitar_recuperacion'),
    path('recuperar/paso-2/', verificar_codigo_pass, name='verificar_codigo_pass'),
    path('recuperar/paso-3/', cambiar_password_final, name='cambiar_password_final'),

    path('recepcion/', panel_recepcion, name='panel_recepcion'),
    path('recepcion/crear-reserva/', panel_recepcion, name='crear_reserva_recepcion'),
    path('recepcion/disponibilidad/', panel_recepcion, name='consultar_disponibilidad'),
    path('recepcion/gestionar-reservas/', panel_recepcion, name='gestionar_reservas'),
    path('recepcion/check-in/', panel_recepcion, name='lista_checkin'),
    path('recepcion/check-out/', panel_recepcion, name='lista_checkout'),
    path('recepcion/pagos/', panel_recepcion, name='gestion_pagos'),
    path('recepcion/check-in/<int:pk>/', panel_recepcion, name='registrar_checkin'),
    path('recepcion/reserva/<int:reserva_id>/cambiar/<str:nuevo_estado>/', cambiar_estado_reserva_recepcion, name='cambiar_estado_recepcion'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)