import os
import time 
import qrcode
import urllib.parse
from datetime import datetime
from collections import Counter
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash 
from flask_sqlalchemy import SQLAlchemy

# -------------------------------
# CONFIGURACIÓN APP
# -------------------------------
app = Flask(__name__)


 # Guardamos hash_clave en la DB 
app.config['SECRET_KEY'] = 'mi_clave_secreta_super_segura_12345'

# Base de datos SQLite
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///catalogo.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

print("BASE DE DATOS:", app.config['SQLALCHEMY_DATABASE_URI'])

# Inicializar SQLAlchemy
db = SQLAlchemy(app)


@app.context_processor
def carrito_global():

    return {
        'cantidad_carrito': len(
            session.get('carrito', [])
        )
    }

# --- MODELO DE USUARIO --- 
class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    username = db.Column(
        db.String(50),
        unique=True,
        nullable=False
    )

    password_hash = db.Column(
        db.String(255),
        nullable=False
    )

    rol = db.Column(
        db.String(20),
        default='usuario'
    )
with app.app_context(): 
    db.create_all() 
 
# --- RUTAS DE AUTENTICACIÓN --- 
 
@app.route('/registro', methods=['GET', 'POST'])
def registro():

    if request.method == 'POST':

        usuario = request.form.get('username')
        clave = request.form.get('password')

        hash_seguro = generate_password_hash(
            clave,
            method='scrypt'
        )

        nuevo_usuario = Usuario(
            username=usuario,
            password_hash=hash_seguro
        )

        try:
            db.session.add(nuevo_usuario)
            db.session.commit()

            flash(
                "Registro exitoso. Ahora puedes iniciar sesión.",
                "success"
            )

            return redirect(url_for('login'))

        except:
            flash(
                "Ese nombre de usuario ya existe.",
                "error"
            )

    return render_template('registro.html')



@app.route('/login', methods=['GET', 'POST'])
def login():

    if request.method == 'POST':

        usuario = request.form.get('username')
        clave = request.form.get('password')

        usuario_db = Usuario.query.filter_by(
            username=usuario
        ).first()

        if usuario_db and check_password_hash(
            usuario_db.password_hash,
            clave
        ):

            session['user_id'] = usuario_db.id
            session['username'] = usuario_db.username

            flash(
                "Inicio de sesión correcto.",
                "success"
            )

            return redirect(url_for('dashboard'))

        flash(
            "Usuario o contraseña incorrectos.",
            "error"
        )

    return render_template('login.html')



@app.route('/logout')
def logout():

    session.clear()

    flash(
        "Sesión cerrada correctamente.",
        "success"
    )

    return redirect(url_for('login'))
 
# --- RUTA PROTEGIDA (DASHBOARD) --- 

@app.route('/dashboard')
def dashboard():

    if 'user_id' not in session:

        flash(
            "Debes iniciar sesión para acceder.",
            "warning"
        )

        return redirect(url_for('login'))

    return render_template(
        'dashboard.html',
        nombre=session['username']
    )
# -------------------------------
# MODELO DE DATOS
# -------------------------------
class Producto(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    nombre = db.Column(
        db.String(100),
        nullable=False
    )

    precio = db.Column(
        db.Float,
        nullable=False
    )

    categoria = db.Column(
        db.String(50),
        nullable=True
    )

    descripcion = db.Column(
        db.Text,
        nullable=True
    )

    imagen = db.Column(
        db.String(255),
        nullable=True
    )

    def to_dict(self):

        return {
            "id": self.id,
            "nombre": self.nombre,
            "precio": self.precio,
            "categoria": self.categoria,
            "descripcion": self.descripcion,
            "imagen": self.imagen
        }


class Pedido(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    nombre = db.Column(
        db.String(100),
        nullable=False
    )

    direccion = db.Column(
        db.String(200),
        nullable=False
    )

    localidad = db.Column(
        db.String(100),
        nullable=False
    )

    forma_pago = db.Column(
        db.String(50),
        nullable=False
    )

    productos = db.Column(
        db.Text,
        nullable=False
    )

    total = db.Column(
        db.Float,
        nullable=False
    )

    fecha = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

# -------------------------------
# CREAR BASE DE DATOS
# -------------------------------
with app.app_context():
    db.create_all()


# -------------------------------
# RUTA PRINCIPAL (READ)
# -------------------------------
@app.route('/')
def index():

    productos_db = Producto.query.all()

    cantidad_carrito = len(
        session.get('carrito', [])
    )

    return render_template(
        'index.html',
        productos=productos_db,
        cantidad_carrito=cantidad_carrito
    )
# -------------------------------
# AGRAGAR CARRITO
# -------------------------------

@app.route('/agregar_carrito/<int:id>')
def agregar_carrito(id):

    if 'carrito' not in session:
        session['carrito'] = []

    carrito = session['carrito']

    carrito.append(id)

    session['carrito'] = carrito

    return redirect(url_for('index'))





@app.route('/carrito')
def carrito():

    ids = session.get('carrito', [])

    contador = Counter(ids)

    productos_carrito = []
    total = 0

    for id_producto, cantidad in contador.items():

        producto = Producto.query.get(id_producto)

        if producto:

            subtotal = producto.precio * cantidad

            productos_carrito.append({
                'producto': producto,
                'cantidad': cantidad,
                'subtotal': subtotal
            })

            total += subtotal

    return render_template(
        'carrito.html',
        productos_carrito=productos_carrito,
        total=total
    )



@app.route('/vaciar_carrito')
def vaciar_carrito():

    session['carrito'] = []

    return redirect(url_for('carrito'))




@app.route('/finalizar_pedido')
def finalizar_pedido():

    ids = session.get('carrito', [])

    contador = Counter(ids)

    mensaje = "Hola, quiero realizar este pedido:\n\n"

    total = 0

    for id_producto, cantidad in contador.items():

        producto = Producto.query.get(id_producto)

        if producto:

            subtotal = producto.precio * cantidad

            mensaje += (
                f"• {producto.nombre} x{cantidad} = "
                f"${subtotal:,.0f}\n"
            )

            total += subtotal

    mensaje += (
        f"\nTotal: ${total:,.0f}\n\n"
        "Nombre:\n"
        "Dirección:\n"
        "Localidad:\n"
        "Forma de pago:"
    )

    mensaje = mensaje.replace(",", ".")

    telefono = "5493624617222"

    url = (
        f"https://wa.me/{telefono}"
        f"?text={urllib.parse.quote(mensaje)}"
    )

    return redirect(url)



@app.route('/checkout')
def checkout():

    return render_template('checkout.html')



@app.route('/enviar_pedido', methods=['POST'])
def enviar_pedido():

    nombre = request.form['nombre']
    direccion = request.form['direccion']
    localidad = request.form['localidad']
    pago = request.form['pago']

    ids = session.get('carrito', [])

    contador = Counter(ids)

    mensaje = "Hola, quiero realizar este pedido:\n\n"

    total = 0
    productos_texto = ""

    for id_producto, cantidad in contador.items():

        producto = Producto.query.get(id_producto)

        if producto:

            subtotal = producto.precio * cantidad

            mensaje += (
                f"• {producto.nombre} x{cantidad} = "
                f"${subtotal:,.0f}\n"
            )

            productos_texto += (
                f"{producto.nombre} x{cantidad}\n"
            )

            total += subtotal

    mensaje += (
        f"\nTotal: ${total:,.0f}\n\n"
        f"Nombre: {nombre}\n"
        f"Dirección: {direccion}\n"
        f"Localidad: {localidad}\n"
        f"Forma de pago: {pago}"
    )

   # pedido = Pedido(
   #     nombre=nombre,
   #     direccion=direccion,
    #    localidad=localidad,
    #    forma_pago=pago,
    #    productos=productos_texto,
    #    total=total
    #)

    #db.session.add(pedido)
    #db.session.commit()

    mensaje = mensaje.replace(",", ".")

    telefono = "5493624617222"

    url = (
        f"https://wa.me/{telefono}"
        f"?text={urllib.parse.quote(mensaje)}"
    )

    session['carrito'] = []

    return redirect(url)
# -------------------------------
# CREATE
# -------------------------------
@app.route('/agregar', methods=['POST'])
def agregar_producto():

    nombre = request.form.get('nombre').strip()
    precio = request.form.get('precio')
    categoria = request.form.get('categoria').strip()
    descripcion = request.form.get('descripcion').strip()
    imagen = request.form.get('imagen').strip()
    if nombre and precio:

      nuevo_producto = Producto(

        nombre=nombre,
        precio=float(precio),
        categoria=categoria,
        descripcion=descripcion,
        imagen=imagen

    )

    db.session.add(nuevo_producto)
    db.session.commit()

    return redirect(url_for('index'))


# -------------------------------
# DELETE
# -------------------------------
@app.route('/borrar/<int:id>')
def eliminar_producto(id):

    if 'user_id' not in session:
      return redirect(url_for('login'))

    producto = Producto.query.get(id)

    if producto:
        db.session.delete(producto)
        db.session.commit()

    return redirect(url_for('index'))


# -------------------------------
# UPDATE
# -------------------------------
@app.route('/editar/<int:id>', methods=['POST'])
def editar_producto(id):

    producto = Producto.query.get(id)

    if producto:

        producto.nombre = request.form.get('nombre')
        producto.precio = float(request.form.get('precio'))
        producto.descripcion = request.form.get('descripcion')

        db.session.commit()

    return redirect(url_for('index'))


# -------------------------------
# API JSON
# -------------------------------
@app.route("/api/hola")
def hola_json():

    return jsonify({
        "status": "success",
        "mensaje": "Hola desde Flask 👋",
        "clase": "Diseño Web II"
    })

# -------------------------------
# API BUSCADOR
# -------------------------------
@app.route('/api/buscar')
def buscar_productos():

    query_text = request.args.get('q', '').lower()

    if not query_text:
        return jsonify([])

    resultados = Producto.query.filter(
        Producto.nombre.ilike(f'%{query_text}%')
    ).all()

    return jsonify([p.to_dict() for p in resultados])

# -------------------------------
# RUTA SERVICIOS
# -------------------------------
@app.route("/servicios")
def servicios():

    datos_servicios = [
        {"nombre": "Corte de Cabello", "precio": 25, "disponible": True},
        {"nombre": "Barba", "precio": 15, "disponible": True},
        {"nombre": "Tinte", "precio": 40, "disponible": False},
        {"nombre": "Masaje Facial", "precio": 20, "disponible": True}
    ]

    return render_template(
        "servicios.html",
        titulo="Servicios",
        servicios=datos_servicios
    )


# -------------------------------
# RUTA CONTACTO
# -------------------------------
@app.route('/contacto', methods=['GET', 'POST'])
def contacto():

    mensaje_error = None
    mensaje_exito = None

    if request.method == 'POST':

        nombre = request.form.get('nombre')
        email = request.form.get('email')
        telefono = request.form.get('telefono')
        mensaje = request.form.get('mensaje')

        # VALIDACIONES
        if not nombre or not email or not telefono:

            mensaje_error = "⚠️ Todos los campos obligatorios deben completarse"

        elif "@" not in email or "." not in email:

            mensaje_error = "📧 Email inválido"

        elif not telefono.isdigit() or len(telefono) < 7:

            mensaje_error = "📞 Teléfono inválido (solo números)"

        else:

            mensaje_exito = f"✅ ¡Gracias {nombre}! Datos recibidos correctamente"

            print(nombre, email, telefono, mensaje)

    return render_template(
        "contacto.html",
        titulo="Contacto",
        error=mensaje_error,
        exito=mensaje_exito
    )

@app.route('/generar_qr')
def generar_qr():

    os.makedirs("static/qrs", exist_ok=True)

    qr = qrcode.make("Hola Gustavo - Mi primer QR con Flask")

    ruta_archivo = "static/qrs/mi_primer_qr.png"

    qr.save(ruta_archivo)

    return f"""
    <h2>QR generado correctamente</h2>
    <img src="/static/qrs/mi_primer_qr.png" width="300">
    """

@app.route('/reserva')
def reserva():

    return render_template('reserva.html')


@app.route('/reservar', methods=['POST'])
def reservar():

    nombre = request.form.get('nombre')
    telefono = request.form.get('telefono')
    servicio = request.form.get('servicio')

    if not nombre or not telefono or not servicio:

        return "Todos los campos son obligatorios"

    ticket_id = "TKT-2026-99"

    try:

        qr_data = f"""
        Ticket: {ticket_id}
        Cliente: {nombre}
        Servicio: {servicio}
        """

        qr = qrcode.QRCode(
            version=1,
            box_size=10,
            border=4
        )

        qr.add_data(qr_data)
        qr.make(fit=True)

        img = qr.make_image(
            fill_color="black",
            back_color="white"
        )

        os.makedirs("static/qrs", exist_ok=True)

        ruta_qr = f"static/qrs/{ticket_id}.png"

        img.save(ruta_qr)

        return f"""
        <h2>Reserva registrada correctamente</h2>

        <p>Cliente: {nombre}</p>
        <p>Servicio: {servicio}</p>
        <p>Ticket: {ticket_id}</p>

        <img src="/static/qrs/{ticket_id}.png" width="300">
        """

    except Exception as e:

        return f"Error generando QR: {e}"
    

    # =====================================
# CLASE 8 - UX AVANZADA
# =====================================

@app.route('/api/reservas')
def api_reservas():

    if 'user_id' not in session:
        return jsonify([])

    time.sleep(2)

    if 'mock_reservas' not in session:
        session['mock_reservas'] = []

    return jsonify(session['mock_reservas'])


@app.route('/api/reservas/crear', methods=['POST'])
def api_crear_reserva():

    if 'user_id' not in session:
        return jsonify({"error": "No autorizado"}), 403

    time.sleep(1.5)

    import random

    servicios = [
        "Mentoría Python Avanzado",
        "Taller Flask",
        "Diseño UX"
    ]

    reserva = {
        "id": f"TKT-{random.randint(1000,9999)}",
        "servicio": random.choice(servicios),
        "estado": "Confirmado"
    }

    if 'mock_reservas' not in session:
        session['mock_reservas'] = []

    reservas = session['mock_reservas']

    reservas.append(reserva)

    session['mock_reservas'] = reservas

    return jsonify(reserva)


@app.route('/api/reservas/limpiar', methods=['POST'])
def api_limpiar():

    if 'user_id' not in session:
        return jsonify({"error": "No autorizado"}), 403

    time.sleep(1)

    session['mock_reservas'] = []

    return jsonify({"ok": True})
# -------------------------------
# EJECUCIÓN
# -------------------------------
if __name__ == "__main__":
    app.run(debug=True)
