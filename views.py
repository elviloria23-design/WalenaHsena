from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from .models import usuario, reservas, pagos, Habitacion, Servicio, HotelConfig, TipoHabitacion, huespedes, NotaRecepcion, DetalleConsumo, PerfilUsuario, Plan
from .forms import ReservaForm
from django.db.models import Q, Count, Sum
from datetime import datetime
import random
from django.utils import timezone
from django.core.mail import EmailMultiAlternatives, send_mail
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.template.loader import render_to_string
from decimal import Decimal
from django.conf import settings
from django.core.mail import EmailMessage
from django.dispatch import receiver
from django.db.models.signals import post_save

import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException

configuration = sib_api_v3_sdk.Configuration()
configuration.api_key['api-key'] = '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'


# ==========================================
# CONTROL DE ROLES JERÁRQUICOS (0, 1, 2)
# ==========================================

def es_gerente(user):

    if not user.is_authenticated:
        return False
    return user.is_superuser


def es_recepcionista_o_superior(user):

    if not user.is_authenticated:
        return False
    return user.is_staff or user.is_superuser


# ==========================================
# VISTAS PÚBLICAS (Huésped / Cliente)
# ==========================================

def home(request):
    return render(request, 'inc/home.html')


def catalogo_habitaciones(request):
    habitaciones = Habitacion.objects.all()
    return render(request, 'catalogo_habitaciones.html', {'habitaciones': habitaciones})


# ==========================================
# VISTAS PRIVADAS / AUTENTICACIÓN
# ==========================================

def crear_cuenta(request):

    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        password_confirm = request.POST.get('password_confirm')

        context = {'username': username, 'email': email}

        if password != password_confirm:
            messages.error(request, 'Las contraseñas no coinciden.')
            return render(request, 'registrarse.html', context)

        if User.objects.filter(username=username).exists():
            messages.error(request, 'El nombre de usuario ya está registrado.')
            return render(request, 'registrarse.html', context)

        if User.objects.filter(email=email).exists():
            messages.error(request, 'El correo electrónico ya está registrado.')
            return render(request, 'registrarse.html', context)

        codigo_verificacion = str(random.randint(100000, 999999))

        request.session['temp_user'] = {
            'username': username,
            'email': email,
            'password': password,
            'codigo': codigo_verificacion
        }

        api_instance = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(configuration))
        sender = {"name": "Walena Hotel", "email": "elviloria23@gmail.com"}
        to = [{"email": email, "name": username}]
        
        html_content = f"""
            <div style="font-family: Arial, sans-serif; padding: 20px; color: #333;">
                <h2 style="color: #00334e;">Código de Verificación - Walena Hotel</h2>
                <hr style="border: 1px solid #f2c14e;">
                <p>Hola <strong>{username}</strong>,</p>
                <p>Tu código de verificación para completar el registro es:</p>
                <h1 style="color: #d97706; letter-spacing: 2px;">{codigo_verificacion}</h1>
                <p>Si no solicitaste esta cuenta, puedes ignorar este mensaje.</p>
            </div>
        """

        send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
            to=to,
            sender=sender,
            subject="Código de verificación para tu cuenta - Walena Hotel",
            html_content=html_content
        )

        try:
            api_instance.send_transac_email(send_smtp_email)
            messages.success(request, '¡Te hemos enviado un código de verificación a tu correo!')
            return redirect('verificar_codigo')
        except ApiException:
            messages.error(request, 'Error al enviar el correo de verificación. Inténtalo de nuevo.')

    return render(request, 'registrarse.html')


@receiver(post_save, sender=User)
def crear_perfil_usuario(sender, instance, created, **kwargs):
    if created:
        PerfilUsuario.objects.create(user=instance)

@receiver(post_save, sender=User)
def guardar_perfil_usuario(sender, instance, **kwargs):
    instance.perfil.save()


def verificar_codigo(request):
    if 'temp_user' not in request.session:
        return redirect('crear_cuenta')

    if request.method == 'POST':
        codigo_ingresado = request.POST.get('codigo')
        datos_temp = request.session['temp_user']

        if codigo_ingresado == datos_temp['codigo']:
            user = User.objects.create_user(
                username=datos_temp['username'],
                email=datos_temp['email'],
                password=datos_temp['password']
            )
            user.save()

            del request.session['temp_user']

            messages.success(request, '¡Cuenta verificada y creada con éxito! Ya puedes iniciar sesión.')
            return redirect('login')
        else:
            messages.error(request, 'El código de verificación es incorrecto.')

    return render(request, 'verificar_codigo.html')


def login_view(request):
    username_ingresado = ''
    
    if request.method == 'POST':
        username_ingresado = request.POST.get('username', '').strip()
        password_ingresado = request.POST.get('password', '').strip()
        
        user = authenticate(request, username=username_ingresado, password=password_ingresado)
        
        if user is not None:
            login(request, user)
            messages.success(request, f'¡Bienvenido de nuevo, {user.username}!')
            return redirect('home')
        else:
            messages.error(request, 'Usuario o contraseña incorrectos. Por favor, verifica tus datos.')
            
    context = {
        'username_ingresado': username_ingresado,
    }
    return render(request, 'login.html', context)


def cerrar_sesion(request):
    logout(request)
    return redirect('login')


# ==========================================
# VISTAS DEL HOTEL Y CONTACTO
# ==========================================

def hotel_view(request):
    return render(request, 'inc/hotel.html')


@login_required
def cambiar_tema_usuario(request):
    if request.method == 'POST':
        perfil, created = PerfilUsuario.objects.get_or_create(user=request.user)
        perfil.modo_oscuro = not perfil.modo_oscuro
        perfil.save()
        return JsonResponse({'status': 'success', 'modo_oscuro': perfil.modo_oscuro})
    return JsonResponse({'status': 'error'}, status=400)


def planes_view(request):
    return render(request, 'planes.html')


def desayunos_view(request):
    return render(request, 'desayunos.html')


def contactanos_view(request):
    if request.method == 'POST':
        nombre = request.POST.get('nombre')
        email_remitente = request.POST.get('email')
        telefono = request.POST.get('telefono')
        asunto_seleccionado = request.POST.get('asunto')
        mensaje_cliente = request.POST.get('mensaje')

        api_instance = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(configuration))

        sender = {"name": "Walena Hotel Contacto", "email": "elviloria23@gmail.com"}
        to = [{"email": "elviloria23@gmail.com", "name": "Administración Walena Hotel"}]

        contexto = {
            'nombre': nombre,
            'email_remitente': email_remitente,
            'telefono': telefono,
            'asunto_seleccionado': asunto_seleccionado,
            'mensaje_cliente': mensaje_cliente,
        }

        html_content = render_to_string('correo_contacto.html', contexto)

        send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
            to=to,
            sender=sender,
            subject=f"[{asunto_seleccionado}] - Mensaje de {nombre}",
            html_content=html_content,
            reply_to={"email": email_remitente, "name": nombre}
        )

        try:
            api_instance.send_transac_email(send_smtp_email)
            messages.success(request, '¡Tu mensaje ha sido enviado con éxito! Te responderemos pronto.')
            return redirect('contactanos')
        except ApiException:
            messages.error(request, 'Ocurrió un error al enviar el mensaje. Inténtalo de nuevo.')

    return render(request, 'contactanos.html')


# ==========================================
# PROCESO DE RESERVA (HUÉSPED)
# ==========================================

@login_required
def reservar_habitacion(request, habitacion_id):
    habitacion = get_object_or_404(Habitacion, id=habitacion_id)

    if request.method == 'POST':
        reserva_activa = reservas.objects.filter(
            usuario=request.user, 
            estado__in=['Pendiente', 'Confirmada']
        ).exists()

        if reserva_activa:
            messages.error(
                request, 
                "Ya cuentas con una reserva activa o pendiente. Debes cancelarla antes de solicitar una nueva."
            )
            return redirect('mis_reservas')

        checkin = request.POST.get('checkin')
        checkout = request.POST.get('checkout')
        
        adultos = int(request.POST.get('adultos', 1))
        ninos = int(request.POST.get('ninos', 0))

        try:
            fecha_in = datetime.strptime(checkin, '%Y-%m-%d')
            fecha_out = datetime.strptime(checkout, '%Y-%m-%d')
            noches = (fecha_out - fecha_in).days
            if noches < 1:
                noches = 1
        except (ValueError, TypeError):
            noches = 1

        tarifas_adultos = {
            1: 160650,
            2: 220150,
            3: 279650,
            4: 339150
        }

        precio_noche = tarifas_adultos.get(adultos, float(habitacion.precio_noche or 160650))
        precio_total = precio_noche * noches

        request.session['temp_reserva'] = {
            'checkin': checkin,
            'checkout': checkout,
            'adultos': adultos,
            'ninos': ninos,
            'precio_total': precio_total
        }
        
        request.session.modified = True

        return redirect('completar_datos_huesped', habitacion_id=habitacion.id)

    return render(request, 'reservar.html', {'habitacion': habitacion})


@login_required(login_url='/login/')
def completar_datos_huesped(request, habitacion_id):
    habitacion = get_object_or_404(Habitacion, id=habitacion_id)
    datos_temp = request.session.get('temp_reserva')

    if not datos_temp:
        return redirect('reservar_habitacion', habitacion_id=habitacion.id)

    if request.method == 'POST':
        nombre = request.POST.get('nombre')
        apellido = request.POST.get('apellido')
        cedula = request.POST.get('cedula')
        correo = request.POST.get('correo') or request.user.email
        telefono = request.POST.get('telefono')

        huespedes.objects.update_or_create(
            cedula=cedula,
            defaults={
                'nombre': nombre,
                'apellido': apellido,
                'correo': correo,
                'telefono': telefono,
            }
        )

        adultos_val = int(datos_temp.get('adultos', 1))
        ninos_val = int(datos_temp.get('ninos', 0))
        precio_final = datos_temp.get('precio_total')

        nueva_reserva = reservas.objects.create(
            usuario=request.user,
            habitacion=habitacion,
            checkin=datos_temp['checkin'],
            checkout=datos_temp['checkout'],
            adultos=adultos_val,
            ninos=ninos_val,
            precio_total=precio_final,
            correo=correo,
            nombre=nombre,
            apellido=apellido,
            cedula=cedula,
            telefono=telefono,
            estado='Pendiente'
        )

        if 'temp_reserva' in request.session:
            del request.session['temp_reserva']

        messages.success(
            request, 
            "¡Reserva registrada con éxito! Para confirmar su cupo, por favor póngase en contacto con nosotros para realizar el abono del 50%."
        )

        return redirect('reserva_exitosa', reserva_id=nueva_reserva.id)

    context = {
        'habitacion': habitacion,
        'datos_reserva': datos_temp
    }
    return render(request, 'completar_datos.html', context)


@login_required(login_url='/login/')
def reserva_exitosa(request, reserva_id):
    reserva = get_object_or_404(reservas, id=reserva_id, usuario=request.user)
    huesped = huespedes.objects.filter(correo=request.user.email).first()

    context = {
        'reserva': reserva,
        'huesped': huesped
    }
    return render(request, 'reserva_exitosa.html', context)


def enviar_correo_reserva(request, reserva_id):
    reserva = get_object_or_404(reservas, id=reserva_id)

    if not reserva.correo:
        messages.error(request, "Esta reserva no tiene un correo electrónico asociado.")
        return redirect('reserva_exitosa', reserva_id=reserva.id)

    asunto = "Comprobante y Resumen de Reserva - Walena Hotel"
    remitente = settings.DEFAULT_FROM_EMAIL
    destinatario = [reserva.correo]

    texto_plano = f"Hola {reserva.nombre} {reserva.apellido}, tu reserva en Walena Hotel ha sido registrada con éxito."

    html_contenido = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{
                font-family: Arial, sans-serif;
                background-color: #f4f6f9;
                margin: 0;
                padding: 20px;
            }}
            .email-container {{
                max-width: 600px;
                background: #ffffff;
                padding: 30px;
                border-radius: 12px;
                box-shadow: 0 4px 10px rgba(0,0,0,0.1);
                margin: auto;
            }}
            h2 {{
                color: #00334e;
                text-align: center;
                border-bottom: 2px solid #f2c14e;
                padding-bottom: 10px;
            }}
            .details-box {{
                background: #f9f9f9;
                padding: 15px 20px;
                border-radius: 8px;
                margin: 20px 0;
            }}
            .details-box ul {{
                list-style: none;
                padding: 0;
                margin: 0;
            }}
            .details-box li {{
                padding: 8px 0;
                border-bottom: 1px solid #eee;
                font-size: 14px;
                color: #333;
            }}
            .details-box li strong {{
                color: #00334e;
            }}
            .total {{
                font-size: 18px;
                color: #00334e;
                font-weight: bold;
                text-align: right;
                margin-top: 15px;
            }}
            .footer {{
                text-align: center;
                font-size: 12px;
                color: #888;
                margin-top: 30px;
            }}
        </style>
    </head>
    <body>
        <div class="email-container">
            <h2>🏨 Walena Hotel</h2>
            <p>¡Hola <strong>{reserva.nombre} {reserva.apellido}</strong>!</p>
            <p>Hemos registrado exitosamente tu solicitud de reserva. Aquí tienes los detalles:</p>
            
            <div class="details-box">
                <ul>
                    <li><strong>Habitación:</strong> #{reserva.habitacion.numero} ({reserva.habitacion.tipo})</li>
                    <li><strong>Cédula:</strong> {reserva.cedula}</li>
                    <li><strong>Teléfono:</strong> {reserva.telefono}</li>
                    <li><strong>Check-in:</strong> {reserva.checkin}</li>
                    <li><strong>Check-out:</strong> {reserva.checkout}</li>
                    <li><strong>Adultos:</strong> {reserva.adultos} | <strong>Niños:</strong> {reserva.ninos}</li>
                    <li><strong>Estado:</strong> {reserva.estado}</li>
                </ul>
                <div class="total">
                    Total a Pagar: ${reserva.precio_total}
                </div>
            </div>

            <p style="text-align: center; color: #555;">
                Para confirmar su cupo, por favor póngase en contacto con nosotros para realizar el abono del 50%.
            </p>

            <div class="footer">
                <p>© 2026 Walena Hotel. Todos los derechos reservados.</p>
            </div>
        </div>
    </body>
    </html>
    """

    try:
        msg = EmailMultiAlternatives(asunto, texto_plano, remitente, destinatario)
        msg.attach_alternative(html_contenido, "text/html")
        msg.send()
        messages.success(request, "¡Correo con diseño enviado con éxito!")
    except Exception as e:
        messages.error(request, f"No se pudo enviar el correo: {e}")

    return redirect('reserva_exitosa', reserva_id=reserva.id)


@login_required
def cancelar_reserva(request, reserva_id):
    if request.method == 'POST':
        reserva = get_object_or_404(reservas, id=reserva_id, usuario=request.user)
        
        if reserva.estado == 'Pendiente':
            reserva.estado = 'Cancelada'
            reserva.save()
            messages.success(request, "Tu reserva ha sido cancelada exitosamente.")
        else:
            messages.error(request, "Esta reserva no se puede cancelar porque ya fue procesada.")
            
    return redirect('mis_reservas')


@login_required
def mis_reservas(request):
    filtro = request.GET.get('filtro', 'activas')
    page = request.GET.get('page', 1)
    
    if filtro == 'canceladas':
        lista_reservas = reservas.objects.filter(
            usuario=request.user, 
            estado='Cancelada'
        ).order_by('-fecha_creacion')
    else:
        lista_reservas = reservas.objects.filter(
            usuario=request.user, 
            estado__in=['Pendiente', 'Pago 50%', 'Confirmada', 'Completada']
        ).order_by('-fecha_creacion')

    paginator = Paginator(lista_reservas, 3)

    try:
        reservas_paginadas = paginator.page(page)
    except PageNotAnInteger:
        reservas_paginadas = paginator.page(1)
    except EmptyPage:
        reservas_paginadas = paginator.page(paginator.num_pages)

    return render(request, 'mis_reservas.html', {'reservas': reservas_paginadas, 'filtro_actual': filtro})


# ==========================================
# PANEL DE RECEPCIÓN (Rol 1 y Rol 2)
# ==========================================

@login_required(login_url='/login/')
@user_passes_test(es_recepcionista_o_superior, login_url='/habitaciones/')
def panel_recepcion(request):
    hoy = timezone.now().date()
    busqueda = request.GET.get('q', '').strip()
    estado_filtro = request.GET.get('estado', '').strip()

    perfil_usuario, created = PerfilUsuario.objects.get_or_create(user=request.user)

    llegadas_hoy_count = reservas.objects.filter(checkin=hoy, estado__in=['Pendiente', 'Confirmada']).count()
    salidas_hoy_count = reservas.objects.filter(checkout=hoy, estado='Confirmada').count()
    habitaciones_disponibles = Habitacion.objects.filter(estado='Disponible').count()
    habitaciones_ocupadas = Habitacion.objects.filter(estado='Ocupada').count()

    reservas_list = reservas.objects.all().order_by('-id')

    if estado_filtro and estado_filtro.lower() != 'todas':
        reservas_list = reservas_list.filter(estado__iexact=estado_filtro)

    if busqueda:
        reservas_list = reservas_list.filter(
            Q(nombre__icontains=busqueda) |
            Q(apellido__icontains=busqueda) |
            Q(cedula__icontains=busqueda) |
            Q(habitacion__numero__icontains=busqueda)
        )

    paginator = Paginator(reservas_list, 10)
    page_number = request.GET.get('page')
    reservas_paginadas = paginator.get_page(page_number)

    habitaciones_list = Habitacion.objects.all().order_by('numero')
    habitaciones_disponibles_lista = Habitacion.objects.filter(estado__iexact='Disponible').order_by('numero')
    notas = NotaRecepcion.objects.all()[:15]

    context = {
        'reservas': reservas_paginadas,
        'lista_reservas': reservas_paginadas,
        'habitaciones': habitaciones_list,
        'habitaciones_disponibles_lista': habitaciones_disponibles_lista,
        'busqueda': busqueda,
        'estado_filtro': estado_filtro,
        'llegadas_hoy_count': llegadas_hoy_count,
        'salidas_hoy_count': salidas_hoy_count,
        'habitaciones_disponibles': habitaciones_disponibles,
        'habitaciones_ocupadas': habitaciones_ocupadas,
        'notas': notas,
        'hoy': hoy,
        'perfil_usuario': perfil_usuario,
    }
    return render(request, 'recepcion/recepcion_dashboard.html', context)


@login_required(login_url='/login/')
@user_passes_test(es_recepcionista_o_superior, login_url='/habitaciones/')
def reubicar_reserva(request, reserva_id):
    reserva = get_object_or_404(reservas, id=reserva_id)

    if reserva.estado.lower() != 'pendiente':
        messages.error(request, "Esta reserva ya no está pendiente, no se puede reubicar.")
        return redirect('panel_recepcion')

    if request.method == 'POST':
        nueva_habitacion_id = request.POST.get('nueva_habitacion_id')
        
        if nueva_habitacion_id:
            nueva_habitacion = get_object_or_404(Habitacion, id=nueva_habitacion_id)

            habitacion_vieja = reserva.habitacion
            habitacion_vieja.estado = 'Disponible'
            habitacion_vieja.save()

            reserva.habitacion = nueva_habitacion
            reserva.save()

            nueva_habitacion.estado = 'Ocupada'
            nueva_habitacion.save()
            
            messages.success(request, f"¡Huésped {reserva.nombre} reubicado exitosamente a la Habitación #{nueva_habitacion.numero}!")
        else:
            messages.error(request, "Debe seleccionar una nueva habitación válida.")
            
    return redirect('panel_recepcion')


@login_required(login_url='/login/')
@user_passes_test(es_recepcionista_o_superior, login_url='/habitaciones/')
def cambiar_estado_reserva_recepcion(request, reserva_id, nuevo_estado):
    reserva = get_object_or_404(reservas, id=reserva_id)
    habitacion = reserva.habitacion

    estados_validos = ['Pendiente', 'Pago 50%', 'Confirmada', 'Completada', 'Cancelada']
    if nuevo_estado not in estados_validos:
        messages.error(request, "Estado no válido.")
        return redirect('panel_recepcion')

    reserva.estado = nuevo_estado

    if nuevo_estado == 'Pago 50%':

        reserva.monto_abono_50 = reserva.precio_total * Decimal('0.50')
        reserva.save()
        messages.success(request, f"Abono del 50% (${reserva.monto_abono_50}) registrado para la reserva #{reserva.id} de {reserva.nombre}.")

    elif nuevo_estado == 'Confirmada':
        reserva.save()
        habitacion.estado = 'Ocupada'
        habitacion.save()
        messages.success(request, f"Check-In confirmado para {reserva.nombre} {reserva.apellido}. Habitación #{habitacion.numero} marcada como Ocupada.")

    elif nuevo_estado == 'Completada':
        reserva.save()
        habitacion.estado = 'Disponible'
        habitacion.save()
        messages.success(request, f"Check-Out completado para {reserva.nombre} {reserva.apellido}. Habitación #{habitacion.numero} ahora está Disponible.")

    elif nuevo_estado == 'Cancelada':
        reserva.save()
        if habitacion.estado == 'Ocupada':
            habitacion.estado = 'Disponible'
            habitacion.save()
        messages.warning(request, f"La reserva #{reserva.id} de {reserva.nombre} ha sido cancelada.")

    else:
        reserva.save()
        messages.info(request, f"Reserva #{reserva.id} actualizada a {nuevo_estado}.")

    return redirect('panel_recepcion')


@login_required(login_url='/login/')
@user_passes_test(es_recepcionista_o_superior, login_url='/habitaciones/')
def cambiar_estado_habitacion_recepcion(request, habitacion_id, nuevo_estado):
    habitacion = get_object_or_404(Habitacion, id=habitacion_id)
    estados_permitidos = ['Disponible', 'Ocupada', 'Mantenimiento']

    if nuevo_estado in estados_permitidos:
        habitacion.estado = nuevo_estado
        habitacion.save()
        messages.success(request, f"Habitación #{habitacion.numero} actualizada a: {nuevo_estado}.")
    else:
        messages.error(request, "Estado de habitación no permitido.")

    return redirect('panel_recepcion')


@login_required
def crear_nota_recepcion(request):
    if request.method == 'POST':
        mensaje = request.POST.get('mensaje', '').strip()
        importante = request.POST.get('importante') == 'on'
        if mensaje:
            NotaRecepcion.objects.create(
                autor=request.user,
                mensaje=mensaje,
                importante=importante
            )
            messages.success(request, "Recordatorio guardado en la bitácora de turno.")
    return redirect('panel_recepcion')

@login_required
def alternar_estado_nota(request, nota_id):
    nota = get_object_or_404(NotaRecepcion, id=nota_id)
    nota.resuelta = not nota.resuelta
    nota.save()
    return redirect('panel_recepcion')

@login_required
def eliminar_nota_recepcion(request, nota_id):
    nota = get_object_or_404(NotaRecepcion, id=nota_id)
    nota.delete()
    messages.info(request, "Nota eliminada de la bitácora.")
    return redirect('panel_recepcion')


@login_required(login_url='/login/')
@user_passes_test(es_recepcionista_o_superior, login_url='/habitaciones/')
def recepcion_servicios(request):
    servicios = Servicio.objects.all()
    reservas_activas = reservas.objects.filter(estado__in=['Pago 50%', 'Confirmada'])

    asignaciones = DetalleConsumo.objects.all().order_by('-id')[:20]

    context = {
        'servicios': servicios,
        'reservas_activas': reservas_activas,
        'asignaciones': asignaciones,
    }
    return render(request, 'recepcion/recepcion_servicios.html', context)

@login_required(login_url='/login/')
@user_passes_test(es_recepcionista_o_superior, login_url='/habitaciones/')
def crear_servicio(request):
    if request.method == 'POST':
        nombre = request.POST.get('nombre')
        precio = request.POST.get('precio')
        descripcion = request.POST.get('descripcion')
        
        Servicio.objects.create(nombre=nombre, precio=precio, descripcion=descripcion)
        messages.success(request, f"Servicio '{nombre}' creado exitosamente.")
        return redirect('recepcion_servicios')
        
    return redirect('recepcion_servicios')

@login_required(login_url='/login/')
@user_passes_test(es_recepcionista_o_superior, login_url='/habitaciones/')
def editar_servicio(request, servicio_id):
    servicio = get_object_or_404(Servicio, id=servicio_id)
    if request.method == 'POST':
        servicio.nombre = request.POST.get('nombre')
        servicio.precio = request.POST.get('precio')
        servicio.descripcion = request.POST.get('descripcion')
        servicio.save()
        messages.success(request, f"Servicio '{servicio.nombre}' actualizado exitosamente.")
        return redirect('recepcion_servicios')
    
    return render(request, 'recepcion/editar_servicio.html', {'servicio': servicio})

@login_required(login_url='/login/')
@user_passes_test(es_recepcionista_o_superior, login_url='/habitaciones/')
def eliminar_servicio(request, servicio_id):
    if request.method == 'POST':
        servicio = get_object_or_404(Servicio, id=servicio_id)
        nombre = servicio.nombre
        servicio.delete()
        messages.success(request, f"Servicio '{nombre}' eliminado del catálogo.")
    return redirect('recepcion_servicios')

@login_required(login_url='/login/')
@user_passes_test(es_recepcionista_o_superior, login_url='/habitaciones/')
def recepcion_servicios(request, servicio_id=None):
    servicio_editando = get_object_or_404(Servicio, id=servicio_id) if servicio_id else None
    
    if request.method == 'POST':
        nombre = request.POST.get('nombre')
        precio = request.POST.get('precio')
        descripcion = request.POST.get('descripcion')
        
        if servicio_editando:
            servicio_editando.nombre = nombre
            servicio_editando.precio = precio
            servicio_editando.descripcion = descripcion
            servicio_editando.save()
            messages.success(request, f"Servicio '{nombre}' actualizado exitosamente.")
        else:
            Servicio.objects.create(nombre=nombre, precio=precio, descripcion=descripcion)
            messages.success(request, f"Servicio '{nombre}' creado exitosamente.")
            
        return redirect('recepcion_servicios')

    servicios = Servicio.objects.all()
    context = {
        'servicios': servicios,
        'servicio_editando': servicio_editando,
    }
    return render(request, 'recepcion/recepcion_servicios.html', context)


@login_required(login_url='/login/')
@user_passes_test(es_recepcionista_o_superior, login_url='/habitaciones/')
def asignar_servicio_huesped(request):
    if request.method == 'POST':
        reserva_id = request.POST.get('reserva_id')
        servicio_id = request.POST.get('servicio_id')
        cantidad = int(request.POST.get('cantidad', 1))
        
        reserva_obj = get_object_or_404(reservas, id=reserva_id)
        servicio_obj = get_object_or_404(Servicio, id=servicio_id)

        DetalleConsumo.objects.create(
            reserva=reserva_obj,
            servicio=servicio_obj,
            cantidad=cantidad,
            precio_aplicado=servicio_obj.precio
        )
        
        messages.success(request, f"Servicio '{servicio_obj.nombre}' asignado correctamente.")
        return redirect('recepcion_servicios')
        
    return redirect('recepcion_servicios')


@login_required(login_url='/login/')
@user_passes_test(es_recepcionista_o_superior, login_url='/habitaciones/')
def procesar_checkout_y_factura(request, reserva_id):
    reserva_obj = get_object_or_404(reservas, id=reserva_id)

    reserva_obj.estado = 'Check-Out'
    reserva_obj.save()

    if hasattr(reserva_obj.habitacion, 'estado'):
        reserva_obj.habitacion.estado = 'Disponible'
        reserva_obj.habitacion.save()

    consumos = DetalleConsumo.objects.filter(reserva=reserva_obj)
    total_consumos = sum(c.cantidad * (c.precio_aplicado or c.servicio.precio) for c in consumos)

    total_hospedaje = getattr(reserva_obj, 'precio_total', 0)

    gran_total = total_hospedaje + total_consumos

    context_factura = {
        'reserva': reserva_obj,
        'consumos': consumos,
        'total_consumos': total_consumos,
        'total_hospedaje': total_hospedaje,
        'gran_total': gran_total,
    }

    if hasattr(reserva_obj, 'correo') and reserva_obj.correo:
        try:
            html_content = render_to_string('recepcion/email_factura.html', context_factura)
            email = EmailMessage(
                subject=f'Factura de Estadía - Walena Hotel (Reserva #{reserva_obj.id})',
                body=html_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[reserva_obj.correo],
            )
            email.content_subtype = 'html'
            email.send(fail_silently=True)
        except Exception as e:
            print(f"Error al enviar correo: {e}")

    return redirect('ver_factura_recepcion', reserva_id=reserva_obj.id)

@login_required(login_url='/login/')
@user_passes_test(es_recepcionista_o_superior, login_url='/habitaciones/')
def ver_factura_recepcion(request, reserva_id):
    reserva_obj = get_object_or_404(reservas, id=reserva_id)
    consumos = DetalleConsumo.objects.filter(reserva=reserva_obj)
    total_consumos = sum(c.cantidad * (c.precio_aplicado or c.servicio.precio) for c in consumos)

    total_hospedaje = getattr(reserva_obj, 'precio_total', 0)
    
    gran_total = total_hospedaje + total_consumos

    context = {
        'reserva': reserva_obj,
        'consumos': consumos,
        'total_consumos': total_consumos,
        'total_hospedaje': total_hospedaje,
        'gran_total': gran_total,
    }
    return render(request, 'recepcion/factura_solo_lectura.html', context)

@login_required(login_url='/login/')
@user_passes_test(es_recepcionista_o_superior, login_url='/habitaciones/')
def reenviar_factura_correo(request, reserva_id):
    reserva_obj = get_object_or_404(reservas, id=reserva_id)
    consumos = DetalleConsumo.objects.filter(reserva=reserva_obj)
    total_consumos = sum(c.cantidad * (c.precio_aplicado or c.servicio.precio) for c in consumos)

    total_hospedaje = getattr(reserva_obj, 'precio_total', 0)
    
    gran_total = total_hospedaje + total_consumos

    context_factura = {
        'reserva': reserva_obj,
        'consumos': consumos,
        'total_consumos': total_consumos,
        'total_hospedaje': total_hospedaje,
        'gran_total': gran_total,
    }

    if reserva_obj.correo:
        try:
            html_content = render_to_string('recepcion/email_factura.html', context_factura)
            email = EmailMessage(
                subject=f'Factura de Estadía - Walena Hotel (Reserva #{reserva_obj.id})',
                body=html_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[reserva_obj.correo],
            )
            email.content_subtype = 'html'
            email.send(fail_silently=False)
            messages.success(request, f"Correo reenviado exitosamente a {reserva_obj.correo}")
        except Exception as e:
            print("================ ERROR DE SMTP ================")
            print(e)
            print("===============================================")
            messages.error(request, f"Error al enviar el correo: {e}")
    else:
        messages.warning(request, "El huésped no tiene un correo electrónico registrado.")

    return redirect('ver_factura_recepcion', reserva_id=reserva_obj.id)

# ==========================================
# PANEL DE GERENCIA / ADMIN (Solo Rol 2)
# ==========================================

@login_required(login_url='/login/')
@user_passes_test(es_gerente, login_url='/habitaciones/')
def gerente_dashboard(request):
    hoy = timezone.now().date()

    total_habitaciones = Habitacion.objects.count()
    habitaciones_ocupadas = Habitacion.objects.filter(estado='Ocupada').count()
    habitaciones_disponibles = Habitacion.objects.filter(estado='Disponible').count()
    
    porcentaje_ocupacion = (
        int((habitaciones_ocupadas / total_habitaciones) * 100)
        if total_habitaciones > 0
        else 0
    )

    total_reservas = reservas.objects.count()

    reservas_activas = reservas.objects.filter(estado__in=['Pendiente', 'Pago 50%', 'Confirmada']).count()

    reservas_del_dia = reservas.objects.filter(checkin=hoy).count()

    ingresos_totales = pagos.objects.aggregate(total=Sum('monto'))['total'] or 0
    total_usuarios = User.objects.count()

    estado_filtro = request.GET.get('estado', '')
    busqueda = request.GET.get('q', '')

    reservas_list = reservas.objects.all().order_by('-id')

    if estado_filtro:
        reservas_list = reservas_list.filter(estado__iexact=estado_filtro)

    if busqueda:
        reservas_list = reservas_list.filter(
            Q(nombre__icontains=busqueda) | 
            Q(apellido__icontains=busqueda) | 
            Q(cedula__icontains=busqueda) | 
            Q(usuario__username__icontains=busqueda)
        )

    paginator = Paginator(reservas_list, 5)
    page_number = request.GET.get('page')
    reservas_paginadas = paginator.get_page(page_number)

    context = {
        'total_habitaciones': total_habitaciones,
        'habitaciones_ocupadas': habitaciones_ocupadas,
        'habitaciones_disponibles': habitaciones_disponibles,
        'porcentaje_ocupacion': porcentaje_ocupacion,
        'total_reservas': total_reservas,
        'reservas_activas': reservas_activas,
        'reservas_del_dia': reservas_del_dia,
        'ingresos_totales': ingresos_totales,
        'total_usuarios': total_usuarios,
        'reservas': reservas_paginadas,
        'estado_filtro': estado_filtro,
        'busqueda': busqueda,
    }

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return render(request, 'gerente/partials/tabla_reservas_ajax.html', context)

    return render(request, 'gerente/dashboard.html', context)

def planes_view(request):
    planes = Plan.objects.filter(disponible=True).order_by('id')
    return render(request, 'planes.html', {'planes': planes})

@login_required(login_url='/login/')
@user_passes_test(es_gerente, login_url='/habitaciones/')
def gerente_planes(request):
    edit_plan = None
    edit_id = request.GET.get('editar')

    if edit_id:
        try:
            edit_plan = Plan.objects.get(id=edit_id, disponible=True)
        except Plan.DoesNotExist:
            pass

    if request.method == 'POST':
        plan_id = request.POST.get('plan_id')
        nombre = request.POST.get('nombre', '').strip()
        duracion = request.POST.get('duracion', '').strip() or "Pasadía (Full Day)"
        descripcion = request.POST.get('descripcion', '').strip()
        incluye = request.POST.get('incluye', '')

        precio_str = request.POST.get('precio', '0').replace('.', '').replace(',', '.')
        try:
            precio = float(precio_str)
        except ValueError:
            precio = 0.0

        imagen = request.FILES.get('imagen')

        if plan_id:
            try:
                plan = Plan.objects.get(id=plan_id)
                plan.nombre = nombre
                plan.duracion = duracion
                plan.descripcion = descripcion
                plan.incluye = incluye
                plan.precio = precio
                if imagen:
                    plan.imagen = imagen
                plan.save()
                messages.success(request, '¡Plan actualizado exitosamente!')
            except Plan.DoesNotExist:
                messages.error(request, 'El plan no existe.')
        else:
            if nombre:
                Plan.objects.create(
                    nombre=nombre,
                    duracion=duracion,
                    descripcion=descripcion,
                    incluye=incluye,
                    precio=precio,
                    imagen=imagen,
                    disponible=True
                )
                messages.success(request, '¡Plan registrado exitosamente!')
        return redirect('gerente_planes')

    planes_list = Plan.objects.filter(disponible=True).order_by('id')
    context = {
        'planes': planes_list,
        'edit_plan': edit_plan,
    }
    return render(request, 'gerente/planes.html', context)

@login_required(login_url='/login/')
@user_passes_test(es_gerente, login_url='/habitaciones/')
def gerente_eliminar_plan(request, plan_id):
    if request.method == 'POST':
        try:
            plan = Plan.objects.get(id=plan_id)
            plan.disponible = False
            plan.save()
            messages.success(request, '¡Plan eliminado exitosamente!')
        except Plan.DoesNotExist:
            messages.error(request, 'El plan no existe.')
    return redirect('gerente_planes')


@login_required(login_url='/login/')
@user_passes_test(es_gerente, login_url='/habitaciones/')
def gerente_habitaciones(request):
    if request.method == 'POST':
        numero = request.POST.get('numero')
        piso = request.POST.get('piso')
        tipo = request.POST.get('tipo')
        cap_max = request.POST.get('cap_max')

        descripcion = request.POST.get('descripcion', '')
        
        precio_str = request.POST.get('precio_noche', '0')
        precio_limpio = precio_str.replace('.', '').replace(',', '.')
        try:
            precio_noche = float(precio_limpio)
        except ValueError:
            precio_noche = 0.0

        estado = request.POST.get('estado', 'Disponible')

        foto1 = request.FILES.get('foto1')
        foto2 = request.FILES.get('foto2')
        foto3 = request.FILES.get('foto3')
        foto4 = request.FILES.get('foto4')

        try:
            Habitacion.objects.create(
                numero=numero,
                piso=piso,
                tipo=tipo,
                cap_max=cap_max,
                precio_noche=precio_noche,
                estado=estado,
                descripcion=descripcion,
                foto1=foto1,
                foto2=foto2,
                foto3=foto3,
                foto4=foto4,
            )
            messages.success(request, '¡Habitación creada y publicada exitosamente!')
        except Exception as e:
            messages.error(request, f'Error al registrar la habitación: {e}')

        return redirect('gerente_habitaciones')

    lista_habitaciones = Habitacion.objects.all()
    return render(request, 'gerente/habitaciones.html', {'habitaciones': lista_habitaciones})


@login_required(login_url='/login/')
@user_passes_test(es_gerente, login_url='/habitaciones/')
def editar_habitacion(request, habitacion_id):
    habitacion = get_object_or_404(Habitacion, id=habitacion_id)

    if request.method == 'POST':
        habitacion.numero = request.POST.get('numero') or habitacion.numero
        habitacion.piso = request.POST.get('piso') or habitacion.piso
        habitacion.tipo = request.POST.get('tipo') or habitacion.tipo


        cap_max = request.POST.get('cap_max')
        if cap_max:
            habitacion.cap_max = cap_max
            
        precio_noche = request.POST.get('precio_noche')
        if precio_noche:
            habitacion.precio_noche = precio_noche

        if request.POST.get('estado'):
            habitacion.estado = request.POST.get('estado')

        

        if 'foto1' in request.FILES:
            habitacion.foto1 = request.FILES['foto1']
        if 'foto2' in request.FILES:
            habitacion.foto2 = request.FILES['foto2']
        if 'foto3' in request.FILES:
            habitacion.foto3 = request.FILES['foto3']
        if 'foto4' in request.FILES:
            habitacion.foto4 = request.FILES['foto4']

        habitacion.save()
        messages.success(request, f"¡Habitación N° {habitacion.numero} actualizada correctamente!")
        return redirect('gerente_habitaciones')

    return render(request, 'gerente/editar_habitacion.html', {'habitacion': habitacion})


@login_required(login_url='/login/')
@user_passes_test(es_gerente, login_url='/habitaciones/')
def eliminar_habitacion(request, habitacion_id):
    if request.method == 'POST':
        habitacion = get_object_or_404(Habitacion, id=habitacion_id)

        habitacion.estado = 'Inactiva'
        habitacion.save()

        messages.success(request, f"La habitación N° {habitacion.numero} ha sido dada de baja (estado Inactiva).")

    return redirect('gerente_habitaciones')


@login_required(login_url='/login/')
@user_passes_test(es_gerente, login_url='/habitaciones/')
def gerente_reservas(request):
    estado_filtro = request.GET.get('estado', '')
    
    if estado_filtro:
        reservas_list = reservas.objects.filter(estado=estado_filtro).order_by('-id')
    else:
        reservas_list = reservas.objects.all().order_by('-id')

    paginator = Paginator(reservas_list, 10)
    page_number = request.GET.get('page')
    reservas_paginadas = paginator.get_page(page_number)
    
    context = {
        'reservas': reservas_paginadas,
        'estado_filtro': estado_filtro,
    }
    return render(request, 'gerente/reservas.html', context)


@login_required(login_url='/login/')
@user_passes_test(es_gerente, login_url='/habitaciones/')
def gerente_pagos(request):
    lista_pagos = pagos.objects.all()
    return render(request, 'gerente/pagos.html', {'pagos': lista_pagos})


@login_required(login_url='/login/')
@user_passes_test(es_gerente, login_url='/habitaciones/')
def gerente_huespedes(request):
    query = request.GET.get('q', '')

    usuarios_list = User.objects.all().order_by('-id')

    if query:
        usuarios_list = usuarios_list.filter(
            Q(username__icontains=query) |
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(email__icontains=query)
        )

    paginator = Paginator(usuarios_list, 5)
    page_number = request.GET.get('page')
    usuarios_paginados = paginator.get_page(page_number)

    context = {
        'usuarios': usuarios_paginados,
        'query': query,
    }
    return render(request, 'gerente/huespedes.html', context)


@login_required(login_url='/login/')
@user_passes_test(es_gerente, login_url='/habitaciones/')
def cambiar_estado_staff(request, user_id):
    usuario_obj = get_object_or_404(User, id=user_id)

    if not usuario_obj.is_staff and not usuario_obj.is_superuser:
        usuario_obj.is_staff = True
        usuario_obj.is_superuser = False
        rol_texto = "Recepcionista (1)"
    elif usuario_obj.is_staff and not usuario_obj.is_superuser:
        usuario_obj.is_staff = True
        usuario_obj.is_superuser = True
        rol_texto = "Administrador (2)"
    else:
        usuario_obj.is_staff = False
        usuario_obj.is_superuser = False
        rol_texto = "Huésped (0)"

    usuario_obj.save()
    messages.success(request, f"Se actualizó el rol de {usuario_obj.username} a: {rol_texto}.")
    return redirect('gerente_huespedes')


@login_required(login_url='/login/')
@user_passes_test(es_gerente, login_url='/habitaciones/')
def gerente_reportes(request):
    fecha_inicio = request.GET.get('fecha_inicio', '')
    fecha_fin = request.GET.get('fecha_fin', '')
    estado = request.GET.get('estado', '')

    reservas_list = reservas.objects.all().order_by('-id')

    if fecha_inicio and fecha_fin:
        reservas_list = reservas_list.filter(
            fecha_creacion__range=[fecha_inicio, fecha_fin]
        )

    if estado:
        reservas_list = reservas_list.filter(estado__iexact=estado)

    reservas_activas = reservas_list.exclude(estado__iexact='Cancelada')
    total_recaudado = pagos.objects.filter(
        reservas_id__in=reservas_activas
    ).aggregate(Sum('monto'))['monto__sum'] or 0

    total_reservas = reservas_list.count()
    total_canceladas = reservas_list.filter(estado__iexact='Cancelada').count()
    total_pendientes = reservas_list.filter(estado__iexact='Pendiente').count()

    if request.method == 'POST' and 'enviar_reporte' in request.POST:
        correo_destino = request.POST.get('correo_destino')
        
        if correo_destino:
            asunto = f"Reporte de Reservas Walena Hotel ({fecha_inicio} al {fecha_fin})"

            texto_plano = (
                f"--- REPORTE FINANCIERO Y DE RESERVAS ---\n\n"
                f"Período evaluado: Desde {fecha_inicio} hasta {fecha_fin}\n"
                f"Total Recaudado Real: ${total_recaudado:,.2f}\n"
                f"Total de Reservas: {total_reservas}\n"
                f"Canceladas: {total_canceladas} | Pendientes: {total_pendientes}\n"
            )

            contexto = {
                'fecha_inicio': fecha_inicio,
                'fecha_fin': fecha_fin,
                'total_recaudado': total_recaudado,
                'total_reservas': total_reservas,
                'total_canceladas': total_canceladas,
                'total_pendientes': total_pendientes,
            }

            html_content = render_to_string('gerente/correo_reporte.html', contexto)

            api_instance = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(configuration))
            sender = {"name": "Walena Hotel Gerencia", "email": "elviloria23@gmail.com"}
            to = [{"email": correo_destino}]

            send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
                to=to,
                sender=sender,
                subject=asunto,
                html_content=html_content,
                text_content=texto_plano
            )
            
            try:
                api_instance.send_transac_email(send_smtp_email)
                messages.success(request, f"¡Reporte enviado con éxito al correo {correo_destino}!")
            except ApiException as e:
                messages.error(request, f"Error al enviar el reporte: {e}")
                
            url_destino = f"{request.path}?fecha_inicio={fecha_inicio}&fecha_fin={fecha_fin}&estado={estado}"
            return redirect(url_destino)

    paginator = Paginator(reservas_list, 5)
    page_number = request.GET.get('page')
    reservas_page = paginator.get_page(page_number)

    context = {
        'reservas': reservas_page,
        'total_recaudado': total_recaudado,
        'total_reservas': total_reservas,
        'total_canceladas': total_canceladas,
        'total_pendientes': total_pendientes,
    }
    return render(request, 'gerente/reportes.html', context)


@login_required(login_url='/login/')
@user_passes_test(es_gerente, login_url='/habitaciones/')
def gerente_configuracion(request):
    config, created = HotelConfig.objects.get_or_create(id=1)

    if request.method == 'POST':
        config.nombre = request.POST.get('nombre')
        config.municipio = request.POST.get('municipio')
        config.direccion = request.POST.get('direccion')
        config.telefono = request.POST.get('telefono')
        config.email = request.POST.get('email')
        config.save()
        
        messages.success(request, '¡La configuración se actualizó y se sincronizó en todo el sistema!')
        return redirect('gerente_configuracion')

    context = {
        'config': config,
    }
    return render(request, 'gerente/configuracion.html', context)


@login_required(login_url='/login/')
@user_passes_test(es_gerente, login_url='/habitaciones/')
def gerente_tipos(request):
    tipos = TipoHabitacion.objects.all()
    
    if request.method == 'POST':
        nombre_tipo = request.POST.get('tipo')
        if nombre_tipo:
            TipoHabitacion.objects.get_or_create(nombre=nombre_tipo)
            messages.success(request, "Tipo de habitación creado con éxito.")
            return redirect('gerente_tipos')

    return render(request, 'gerente/tipos.html', {'tipos': tipos})


@login_required(login_url='/login/')
@user_passes_test(es_gerente, login_url='/habitaciones/')
def eliminar_tipo_habitacion(request, pk):
    if request.method == 'POST':
        tipo = get_object_or_404(TipoHabitacion, pk=pk)
        tipo.delete()
        messages.success(request, "Tipo de habitación eliminado de la lista maestra.")
    return redirect('gerente_tipos')


@login_required(login_url='/login/')
@user_passes_test(es_gerente, login_url='/habitaciones/')
def gerente_servicios(request):
    edit_servicio = None
    edit_id = request.GET.get('editar')

    if edit_id:
        try:
            edit_servicio = Servicio.objects.get(id=edit_id, disponible=True)
        except Servicio.DoesNotExist:
            pass

    if request.method == 'POST':
        servicio_id = request.POST.get('servicio_id')
        nombre = request.POST.get('nombre')
        descripcion = request.POST.get('descripcion')
        precio = request.POST.get('precio')
        
        if servicio_id:
            try:
                serv = Servicio.objects.get(id=servicio_id)
                serv.nombre = nombre
                serv.descripcion = descripcion
                serv.precio = precio
                serv.save()
                messages.success(request, '¡Servicio actualizado exitosamente!')
            except Servicio.DoesNotExist:
                messages.error(request, 'El servicio no existe.')
        else:
            if nombre and precio:
                Servicio.objects.create(
                    nombre=nombre,
                    descripcion=descripcion,
                    precio=precio,
                    disponible=True
                )
                messages.success(request, '¡Servicio registrado exitosamente!')
        return redirect('gerente_servicios')

    servicios_list = Servicio.objects.filter(disponible=True).order_by('id')
    context = {
        'servicios': servicios_list,
        'edit_servicio': edit_servicio,
    }
    return render(request, 'gerente/servicios.html', context)


@login_required(login_url='/login/')
@user_passes_test(es_gerente, login_url='/habitaciones/')
def gerente_eliminar_servicio(request, servicio_id):
    if request.method == 'POST':
        try:
            serv = Servicio.objects.get(id=servicio_id)

            serv.disponible = False
            serv.save()

            messages.success(request, '¡Servicio eliminado exitosamente!')
        except Servicio.DoesNotExist:
            messages.error(request, 'El servicio no existe.')
    return redirect('gerente_servicios')


# ========================================
# RECUPERAR CUENTA
# ========================================

def solicitar_recuperacion(request):
    username_ingresado = ''
    correo_ingresado = ''
    
    if request.method == 'POST':
        username_ingresado = request.POST.get('username', '').strip()
        correo_ingresado = request.POST.get('correo', '').strip()
        
        try:
            user = User.objects.get(username__iexact=username_ingresado, email__iexact=correo_ingresado)
            codigo = str(random.randint(100000, 999999))

            request.session['reset_user_id'] = user.id
            request.session['codigo_recuperacion'] = codigo

            api_instance = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(configuration))
            sender = {"name": "Walena Hotel Soporte", "email": "elviloria23@gmail.com"}
            to = [{"email": correo_ingresado, "name": user.username}]
            
            html_content = f"""
                <div style="font-family: Arial, sans-serif; padding: 20px; color: #333;">
                    <h2 style="color: #00334e;">Recuperación de Contraseña - Walena Hotel</h2>
                    <hr style="border: 1px solid #f2c14e;">
                    <p>Hola <strong>{user.username}</strong>,</p>
                    <p>Has solicitado restablecer tu contraseña. Tu código de verificación es:</p>
                    <h1 style="color: #d97706; letter-spacing: 2px;">{codigo}</h1>
                    <p>Si no solicitaste este cambio, puedes ignorar este mensaje.</p>
                </div>
            """

            send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
                to=to,
                sender=sender,
                subject="Código de Recuperación de Contraseña - Walena Hotel",
                html_content=html_content
            )

            api_instance.send_transac_email(send_smtp_email)
            messages.success(request, '¡Código enviado con éxito a tu correo!')
            return redirect('verificar_codigo_pass')
            
        except User.DoesNotExist:
            messages.error(request, 'El usuario y/o correo ingresados no se encuentran en el sistema.')
        except ApiException as e:
            messages.error(request, f'Error al enviar el correo de recuperación: {e}')
            
    context = {
        'username_ingresado': username_ingresado,
        'correo_ingresado': correo_ingresado,
    }
    return render(request, 'auth/paso1_solicitar.html', context)


def verificar_codigo_pass(request):
    user_id = request.session.get('reset_user_id')
    codigo_guardado = request.session.get('codigo_recuperacion')
    
    if not user_id or not codigo_guardado:
        return redirect('solicitar_recuperacion')
        
    if request.method == 'POST':
        codigo_ingresado = request.POST.get('codigo', '').strip()
        
        if codigo_guardado == codigo_ingresado:
            request.session['codigo_verificado'] = True
            messages.success(request, '¡Código verificado con éxito! Ingresa tu nueva contraseña.')
            return redirect('cambiar_password_final')
        else:
            messages.error(request, 'El código de verificación es incorrecto.')
            
    return render(request, 'auth/paso2_codigo.html')


def cambiar_password_final(request):
    user_id = request.session.get('reset_user_id')
    codigo_verificado = request.session.get('codigo_verificado')
    
    if not user_id or not codigo_verificado:
        return redirect('solicitar_recuperacion')
        
    user = User.objects.get(id=user_id)

    if request.method == 'POST':
        username = request.POST.get('username')
        correo = request.POST.get('correo')
        pass1 = request.POST.get('password')
        pass2 = request.POST.get('confirm_password')
        
        if username != user.username or correo != user.email:
            messages.error(request, 'Los datos de usuario y correo no coinciden con la solicitud.')
        elif pass1 != pass2:
            messages.error(request, 'Las contraseñas ingresadas no coinciden.')
        else:
            user.set_password(pass1)
            user.save()

            request.session.pop('reset_user_id', None)
            request.session.pop('codigo_recuperacion', None)
            request.session.pop('codigo_verificado', None)
            
            messages.success(request, '¡Tu contraseña ha sido actualizada correctamente! Ya puedes iniciar sesión.')
            return redirect('login')

    context = {
        'username_val': user.username,
        'correo_val': user.email
    }
    return render(request, 'auth/paso3_cambiar.html', context)





