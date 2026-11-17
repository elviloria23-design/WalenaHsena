from django.db import models
from django.contrib.auth.models import User

class TipoHabitacion(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    
    def __str__(self):
        return self.nombre


class Habitacion(models.Model):
    numero = models.IntegerField()
    piso = models.IntegerField()
    tipo = models.CharField(max_length=100)
    cap_max = models.IntegerField()
    precio_noche = models.DecimalField(max_digits=10, decimal_places=2)
    estado = models.CharField(max_length=50, default='Disponible')

    foto1 = models.ImageField(upload_to='habitaciones/', blank=True, null=True)
    foto2 = models.ImageField(upload_to='habitaciones/', blank=True, null=True)
    foto3 = models.ImageField(upload_to='habitaciones/', blank=True, null=True)
    foto4 = models.ImageField(upload_to='habitaciones/', blank=True, null=True)

    class Meta:
        db_table = 'habitaciones'
        managed = False


class huespedes(models.Model):
    nombre = models.CharField(max_length=45)
    apellido = models.CharField(max_length=45)
    cedula = models.CharField(max_length=20)
    correo = models.CharField(max_length=45)
    telefono = models.CharField(max_length=20)
    es_corporativo = models.BooleanField(default=False)

    class Meta:
        db_table = 'huespedes'
        managed = False


class consumo(models.Model):
    reservas_id = models.IntegerField()
    servicio_id = models.IntegerField()
    cantidad = models.IntegerField()
    precio_aplicado = models.DecimalField(max_digits=10, decimal_places=2)
    fecha_registro = models.DateTimeField()

    class Meta:
        db_table = 'detalle_consumo'
        managed = False


class pagos(models.Model):
    reservas_id = models.IntegerField()
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    metodo_pago = models.CharField(max_length=45)
    tipo_pago = models.CharField(max_length=45)
    fecha_pago = models.DateTimeField()

    class Meta:
        db_table = 'pagos'
        managed = False


class reservas(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    habitacion = models.ForeignKey(Habitacion, on_delete=models.CASCADE)
    adultos = models.IntegerField()
    ninos = models.IntegerField(default=0)
    precio_total = models.DecimalField(max_digits=10, decimal_places=2)
    estado = models.CharField(max_length=50)
    checkin = models.DateField()
    checkout = models.DateField()
    monto_abono_50 = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    nombre = models.CharField(max_length=45, blank=True, null=True)
    apellido = models.CharField(max_length=45, blank=True, null=True)
    cedula = models.CharField(max_length=20, blank=True, null=True)
    correo = models.CharField(max_length=45, blank=True, null=True)
    telefono = models.CharField(max_length=20, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'reservas'


class Servicio(models.Model):
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True, null=True)
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    disponible = models.BooleanField(default=True)

    def __str__(self):
        return self.nombre


class usuario(models.Model):
    nombre = models.CharField(max_length=50)
    apellido = models.CharField(max_length=50)
    password = models.CharField(max_length=255)
    rol = models.CharField(max_length=45)
    correo = models.EmailField(unique=True, null=True, blank=True)
    codigo_recuperacion = models.CharField(max_length=6, blank=True, null=True)

    class Meta:
        db_table = 'usuario'
        managed = False


class HotelConfig(models.Model):
    nombre = models.CharField(max_length=100, default="Walena Hotel")
    municipio = models.CharField(max_length=100, default="Riohacha, La Guajira, Colombia")
    direccion = models.CharField(max_length=200, default="Calle 14b Bis # 15-05")
    telefono = models.CharField(max_length=50, default="+57 300 123 4567")
    email = models.EmailField(default="contacto@walenahotel.com")

    def __str__(self):
        return self.nombre


class NotaRecepcion(models.Model):
    autor = models.ForeignKey(User, on_delete=models.CASCADE)
    mensaje = models.TextField()
    importante = models.BooleanField(default=False)
    resuelta = models.BooleanField(default=False)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha_creacion']

    def __str__(self):
        return f"Nota de {self.autor.username} - {self.fecha_creacion.strftime('%d/%m %H:%M')}"


class DetalleConsumo(models.Model):
    reserva = models.ForeignKey(reservas, on_delete=models.CASCADE, db_column='reservas_id')
    servicio = models.ForeignKey(Servicio, on_delete=models.CASCADE, db_column='servicio_id')
    cantidad = models.IntegerField(default=1)
    precio_aplicado = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = 'detalle_consumo'


class PerfilUsuario(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil')
    modo_oscuro = models.BooleanField(default=True)

    def __str__(self):
        return f"Perfil de {self.user.username}"

