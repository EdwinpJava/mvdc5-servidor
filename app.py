from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from datetime import datetime, timezone, timedelta
from functools import wraps
import os
import json
import secrets
from werkzeug.utils import secure_filename
from itsdangerous import URLSafeTimedSerializer

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'clave_segura_unisinu_2026')
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=15)

# Contraseña común para registros especiales (docente, coordinador ori, coordinador programa)
PASSWORD_REGISTRO_ESPECIAL = "Unisinu2026"

serializer = URLSafeTimedSerializer(app.secret_key)

# Configuración de Email para envío real a través de Gmail
app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 465))
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME', 'vozori39@gmail.com')
# NOTA: En un entorno de producción, NUNCA debes poner la contraseña directamente en el código.
# Esto se hace aquí temporalmente para que puedas probar la funcionalidad.
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD', 'ezxi xdeb akwo kwua')
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER', 'vozori39@gmail.com')

import smtplib
import ssl
import threading
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage

def enviar_email(asunto, destinatario, cuerpo_html, cuerpo_texto="", adjuntos_cid=None):
    """
    Función helper para enviar correos electrónicos usando SSL directo.
    destinatario puede ser un string (un correo) o una lista de strings (varios correos).
    """
    mail_username = app.config.get('MAIL_USERNAME')
    mail_password = app.config.get('MAIL_PASSWORD')
    
    if not mail_username or not mail_password:
        print("NOTA: Email no enviado realmente. Faltan credenciales SMTP (MAIL_USERNAME / MAIL_PASSWORD).")
        return False
        
    try:
        # Forzar el uso del puerto 587 y STARTTLS que es más compatible con Gmail actual
        context = ssl.create_default_context()
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls(context=context)
            server.login(mail_username, mail_password)
            
            destinatarios_lista = destinatario if isinstance(destinatario, list) else [destinatario]
            
            for dest in destinatarios_lista:
                # Crear un mensaje nuevo por cada destinatario para evitar que vean los correos de los demás
                msg = MIMEMultipart('related')
                msg['From'] = f"Movilidad del Conocimiento Unisinú <{app.config.get('MAIL_DEFAULT_SENDER')}>"
                msg['To'] = dest
                msg['Subject'] = asunto
                
                # Encabezados adicionales críticos para que correos institucionales y Microsoft no reboten
                msg['Reply-To'] = app.config.get('MAIL_DEFAULT_SENDER')
                msg['MIME-Version'] = '1.0'
                msg['X-Priority'] = '3' # Normal
                msg['X-Mailer'] = 'Python SMTP'
                
                msg_alt = MIMEMultipart('alternative')
                msg.attach(msg_alt)
                
                # Attach parts into message container
                part1 = MIMEText(cuerpo_texto if cuerpo_texto else "Por favor visualice este correo en un cliente que soporte HTML.", 'plain')
                part2 = MIMEText(cuerpo_html, 'html')
                
                msg_alt.attach(part1)
                msg_alt.attach(part2)
                
                if adjuntos_cid:
                    for adj in adjuntos_cid:
                        try:
                            with open(adj['path'], 'rb') as f:
                                img_data = f.read()
                            image = MIMEImage(img_data)
                            image.add_header('Content-ID', f"<{adj['cid']}>")
                            image.add_header('Content-Disposition', 'inline', filename=os.path.basename(adj['path']))
                            msg.attach(image)
                        except Exception as e:
                            print(f"Error adjuntando imagen CID: {e}")
                
                server.send_message(msg)
            
        print(f"Correo enviado exitosamente a {len(destinatarios_lista)} destinatario(s)")
        return True
    except smtplib.SMTPAuthenticationError as e:
        print(f"ERROR GRAVE: Falló la autenticación SMTP con Google. La contraseña de aplicación es incorrecta o Google está bloqueando el acceso: {e}")
        return False
    except Exception as e:
        print(f"Error general enviando email: {e}")
        return False

# Configuración de carga de archivos
UPLOAD_FOLDER = os.path.join(app.root_path, 'static', 'uploads', 'postulaciones')
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'xls', 'xlsx', 'zip', 'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # Límite de 10MB por archivo

def allowed_file(filename):
    if not '.' in filename:
        return False
    ext = filename.rsplit('.', 1)[1].lower()
    # Doble verificación: extensión y que no sea un ejecutable peligroso
    return ext in ALLOWED_EXTENSIONS and ext not in {'exe', 'bat', 'sh', 'php', 'js'}

import uuid
def secure_custom_filename(filename):
    ext = filename.rsplit('.', 1)[1].lower()
    return f"{uuid.uuid4().hex}.{ext}"

import unicodedata
import re

def normalize_text(text):
    if not text:
        return ""
    text = unicodedata.normalize('NFD', text).encode('ascii', 'ignore').decode('utf-8')
    return text.lower().strip()

def validar_password(password):
    """
    Valida que una contraseña cumpla con los parámetros de seguridad:
    - Al menos 8 caracteres
    - Al menos una letra mayúscula
    - Al menos una letra minúscula
    - Al menos un número
    - Al menos un carácter especial
    """
    if len(password) < 8:
        return False, "La contraseña debe tener al menos 8 caracteres."
    if not re.search(r"[A-Z]", password):
        return False, "La contraseña debe contener al menos una letra mayúscula."
    if not re.search(r"[a-z]", password):
        return False, "La contraseña debe contener al menos una letra minúscula."
    if not re.search(r"\d", password):
        return False, "La contraseña debe contener al menos un número."
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        return False, "La contraseña debe contener al menos un carácter especial (!@#$%^&*...)."
    return True, ""

def es_programa_medicina(programa):
    nombre = normalize_text(programa.nombre)
    tipo = normalize_text(programa.tipo)
    return (
        'internado rotatorio' in nombre or 'internado rotatorio' in tipo or
        'postgrado medico' in nombre or 'postgrado medico' in tipo or
        'medico quirurgico' in nombre or 'medico quirurgico' in tipo or
        'medico quirurjico' in nombre or 'medico quirurjico' in tipo
    )

def es_estudiante_medicina(carrera):
    if not carrera:
        return False
    return 'medicina' in normalize_text(carrera)

# Configuración de base de datos
basedir = os.path.abspath(os.path.dirname(__file__))

# Configuración para MySQL/MariaDB
# Para usar MySQL, configura las variables de entorno:
# DB_TYPE=mysql
# DB_HOST=localhost
# DB_PORT=3306
# DB_USER=tu_usuario
# DB_PASSWORD=tu_contraseña
# DB_NAME=unisinu

db_type = os.environ.get('DB_TYPE', 'sqlite')

if db_type == 'mysql':
    db_host = os.environ.get('DB_HOST', 'localhost')
    db_port = os.environ.get('DB_PORT', '3306')
    db_user = os.environ.get('DB_USER', 'root')
    db_password = os.environ.get('DB_PASSWORD', '')
    db_name = os.environ.get('DB_NAME', 'unisinu')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'mysql+pymysql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}'
else:
    # Por defecto, usa SQLite
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///' + os.path.join(basedir, 'instance', 'unisinu.db'))

if app.config['SQLALCHEMY_DATABASE_URI'].startswith("postgres://"):
    app.config['SQLALCHEMY_DATABASE_URI'] = app.config['SQLALCHEMY_DATABASE_URI'].replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# Opcional: Aumentar el pool de conexiones para mejor rendimiento con múltiples usuarios (solo para MySQL/PostgreSQL)
if 'mysql' in app.config['SQLALCHEMY_DATABASE_URI'] or 'postgresql' in app.config['SQLALCHEMY_DATABASE_URI']:
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_size': 20,
        'max_overflow': 40,
        'pool_timeout': 30,
        'pool_recycle': 3600
    }

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

# --- DECORADORES ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Debe iniciar sesión para acceder a esta página.", "error")
            return redirect(url_for('inicio'))
        return f(*args, **kwargs)
    return decorated_function

def coordinador_ori_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'rol' not in session or session['rol'] != 'coordinador_ori':
            flash("Acceso restringido. Se requieren permisos de Coordinador ORI.", "error")
            return redirect(url_for('inicio'))
        return f(*args, **kwargs)
    return decorated_function

def coordinador_area_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'rol' not in session or session['rol'] != 'coordinador_area':
            flash("Acceso restringido. Se requieren permisos de Coordinador de Area.", "error")
            return redirect(url_for('inicio'))
        return f(*args, **kwargs)
    return decorated_function

def superadmin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'rol' not in session or session['rol'] != 'superadmin':
            flash("Acceso restringido al Administrador del Sistema.", "error")
            return redirect(url_for('inicio'))
        return f(*args, **kwargs)
    return decorated_function

def estudiante_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Si está logueado, debe ser estudiante
        if 'rol' in session and session['rol'] != 'estudiante':
            flash("Acceso restringido. Esta página es exclusiva para estudiantes.", "error")
            return redirect(url_for('inicio'))
        return f(*args, **kwargs)
    return decorated_function

def docente_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Si está logueado, debe ser docente
        if 'rol' in session and session['rol'] != 'docente':
            flash("Acceso restringido. Esta página es exclusiva para docentes.", "error")
            return redirect(url_for('inicio'))
        return f(*args, **kwargs)
    return decorated_function

def estudiante_o_docente_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Si está logueado, debe ser estudiante, docente o coordinador_area
        if 'rol' in session and session['rol'] not in ['estudiante', 'docente', 'coordinador_area']:
            flash("Acceso restringido. Los coordinadores no pueden acceder a los programas.", "error")
            return redirect(url_for('inicio'))
        # Para ver programas y detalle, si no está logueado permitimos que vea la info general
        # pero las acciones de postular ya tienen su propio @login_required
        return f(*args, **kwargs)
    return decorated_function

# --- MODELOS DE LA BASE DE DATOS ---
class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    rol = db.Column(db.String(20), nullable=False, default='estudiante')
    # Campos Académicos
    universidad = db.Column(db.String(100), nullable=True)
    carrera = db.Column(db.String(100), nullable=True)
    semestre = db.Column(db.Integer, nullable=True)
    fecha_registro = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    foto_perfil = db.Column(db.String(255), nullable=True) # Ruta de la foto de perfil
    
    # --- Nuevos campos de verificación de correo ---
    email_verificado = db.Column(db.Boolean, default=False, nullable=False)
    token_verificacion = db.Column(db.String(100), nullable=True)
    
    # Relaciones
    postulaciones = db.relationship('Postulacion', backref='estudiante', lazy=True)

class Programa(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.Text, nullable=False)
    requisitos = db.Column(db.Text, nullable=True)
    fecha_inicio = db.Column(db.DateTime, nullable=True)
    fecha_fin = db.Column(db.DateTime, nullable=True)
    tipo = db.Column(db.String(50), nullable=False) # Beca, Intercambio, Pasantía
    dirigido_a = db.Column(db.String(50), nullable=False, default='movilidad estudiantes') # movilidad estudiantes o movilidad docentes
    imagen_url = db.Column(db.String(255), nullable=True)
    formulario_json = db.Column(db.Text, nullable=True) # Estructura del formulario dinámico
    # Relaciones
    postulaciones = db.relationship('Postulacion', backref='programa', lazy=True)

class Postulacion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    programa_id = db.Column(db.Integer, db.ForeignKey('programa.id'), nullable=False)
    fecha_postulacion = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    estado = db.Column(db.String(50), nullable=False, default='pendiente_ori') # pendiente_ori, espera_ori, rechazado_ori, candidato, aprobado_jefe, rechazado_jefe
    comentarios = db.Column(db.Text, nullable=True) # Observaciones del Coordinador ORI
    observacion_jefe = db.Column(db.Text, nullable=True) # Observaciones del Coordinador de Area
    carta_jefe_url = db.Column(db.String(255), nullable=True) # Carta subida por el Coordinador de Area
    carta_ori_1_url = db.Column(db.String(255), nullable=True) # Carta 1 subida por el Coordinador ORI
    carta_ori_2_url = db.Column(db.String(255), nullable=True) # Carta 2 subida por el Coordinador ORI
    datos_formulario_json = db.Column(db.Text, nullable=True) # Respuestas del formulario
    archivos_json = db.Column(db.Text, nullable=True) # Rutas de archivos subidos

class MensajeContacto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    tipo_usuario = db.Column(db.String(50), nullable=True)
    asunto = db.Column(db.String(200), nullable=False)
    mensaje = db.Column(db.Text, nullable=False)
    fecha = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

class Noticia(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(200), nullable=True)
    contenido = db.Column(db.Text, nullable=False) # HTML content from Quill
    imagen_url = db.Column(db.String(255), nullable=True)
    fecha = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    autor_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    
    autor = db.relationship('Usuario', backref=db.backref('noticias', lazy=True))

class MensajeChat(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    remitente_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    receptor_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=True) # NULL para chat grupal/general
    mensaje = db.Column(db.Text, nullable=True)
    archivo_url = db.Column(db.String(255), nullable=True)
    archivo_tipo = db.Column(db.String(20), nullable=True) # image, video, document
    archivo_nombre = db.Column(db.String(100), nullable=True)
    fecha = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    remitente = db.relationship('Usuario', foreign_keys=[remitente_id], backref=db.backref('mensajes_enviados', lazy=True))
    receptor = db.relationship('Usuario', foreign_keys=[receptor_id], backref=db.backref('mensajes_recibidos', lazy=True))
# Crear la base de datos al iniciar (si no existe)
with app.app_context():
    db.create_all()

@app.route("/admin_master/usuarios")
@superadmin_required
def superadmin_dashboard():
    # El Super Admin puede ver a TODOS los usuarios excepto a sí mismo
    usuarios = Usuario.query.filter(Usuario.id != session.get('user_id')).all()
    return render_template("superadmin_usuarios.html", usuarios=usuarios, nombre=session.get("nombre"))

@app.route("/admin_master/usuarios/eliminar/<int:id>", methods=["POST"])
@superadmin_required
def superadmin_eliminar_usuario(id):
    if id == session.get('user_id'):
        flash("No puedes eliminar tu propia cuenta de Super Admin.", "error")
        return redirect(url_for('superadmin_dashboard'))
        
    usuario = Usuario.query.get_or_404(id)
    try:
        # Eliminar postulaciones y noticias asociadas
        for postulacion in usuario.postulaciones:
            db.session.delete(postulacion)
        for noticia in usuario.noticias:
            db.session.delete(noticia)
            
        # Eliminar mensajes de chat asociados (remitente o receptor)
        for msg in usuario.mensajes_enviados:
            db.session.delete(msg)
        for msg in usuario.mensajes_recibidos:
            db.session.delete(msg)
            
        nombre = usuario.nombre
        db.session.delete(usuario)
        db.session.commit()
        flash(f"Usuario {nombre} eliminado correctamente.", "success")
    except Exception as e:
        db.session.rollback()
        print(f"Error al eliminar usuario: {e}")
        flash("Error al eliminar el usuario.", "error")
    return redirect(url_for('superadmin_dashboard'))

@app.route("/registro-superadmin-oculto", methods=["GET", "POST"])
def registro_superadmin():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        
        if not email or not password:
            flash("Correo y contraseña son obligatorios.", "error")
            return redirect(url_for('registro_superadmin'))
            
        if Usuario.query.filter_by(email=email).first():
            flash("El correo ya está registrado.", "error")
            return redirect(url_for('registro_superadmin'))
            
        es_segura, mensaje_error = validar_password(password)
        if not es_segura:
            flash(mensaje_error, "error")
            return redirect(url_for('registro_superadmin'))
            
        try:
            hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
            nuevo_admin = Usuario(
                nombre="Administrador Sistema",
                email=email,
                password=hashed_password,
                rol="superadmin",
                universidad="N/A",
                carrera="N/A"
            )
            db.session.add(nuevo_admin)
            db.session.commit()
            
            flash("SuperAdmin registrado exitosamente. Ahora puedes iniciar sesión con tu correo y contraseña.", "success")
            return redirect(url_for('inicio'))
        except Exception as e:
            db.session.rollback()
            print(f"Error al registrar admin: {e}")
            flash("Error al registrar el SuperAdmin.", "error")
            
    return render_template("registro_superadmin.html", nombre=session.get("nombre"))

# --- RUTAS EXISTENTES ---
@app.route("/")
def inicio():
    noticias = Noticia.query.order_by(Noticia.fecha.desc()).limit(5).all()
    if 'user_id' in session:
        if session.get("rol") == 'coordinador_ori':
            return redirect(url_for('coordinador_dashboard'))
        elif session.get("rol") == 'coordinador_area':
            return redirect(url_for('jefe_dashboard'))
        else:
            return redirect(url_for('dashboard'))
            
    auto_open_register = session.pop('open_register_modal', False)
    return render_template("index.html", noticias=noticias, register_role="estudiante", auto_open_register=auto_open_register)

@app.route("/validar-registro-especial", methods=["POST"])
def validar_registro_especial():
    password_input = request.form.get("password_registro_especial")
    rol = request.form.get("rol")
    
    if password_input == PASSWORD_REGISTRO_ESPECIAL:
        session['acceso_registro_especial'] = True
        session['rol_registro_especial'] = rol
        if rol == 'docente':
            return redirect(url_for('registro_docente'))
        elif rol == 'coordinador_ori':
            return redirect(url_for('registro_ori'))
        elif rol == 'coordinador_area':
            return redirect(url_for('registro_coordinador'))
        else:
            return redirect(url_for('inicio'))
    else:
        flash("Contraseña incorrecta para este tipo de registro.", "error")
        return redirect(url_for('inicio'))

@app.route("/registro-docente")
def registro_docente():
    if not session.get('acceso_registro_especial') or session.get('rol_registro_especial') != 'docente':
        flash("Debes ingresar la contraseña de acceso para registrarte como docente.", "error")
        return redirect(url_for('inicio'))
    noticias = Noticia.query.order_by(Noticia.fecha.desc()).limit(5).all()
    if 'user_id' in session:
        return redirect(url_for('inicio'))
    auto_open_register = session.pop('open_register_modal', True)
    return render_template("index.html", noticias=noticias, register_role="docente", auto_open_register=auto_open_register)

@app.route("/registro-ori")
def registro_ori():
    if not session.get('acceso_registro_especial') or session.get('rol_registro_especial') != 'coordinador_ori':
        flash("Debes ingresar la contraseña de acceso para registrarte como coordinador ORI.", "error")
        return redirect(url_for('inicio'))
    noticias = Noticia.query.order_by(Noticia.fecha.desc()).limit(5).all()
    if 'user_id' in session:
        return redirect(url_for('inicio'))
    auto_open_register = session.pop('open_register_modal', True)
    return render_template("index.html", noticias=noticias, register_role="coordinador_ori", auto_open_register=auto_open_register)

@app.route("/registro-coordinador")
def registro_coordinador():
    if not session.get('acceso_registro_especial') or session.get('rol_registro_especial') != 'coordinador_area':
        flash("Debes ingresar la contraseña de acceso para registrarte como coordinador de programa.", "error")
        return redirect(url_for('inicio'))
    noticias = Noticia.query.order_by(Noticia.fecha.desc()).limit(5).all()
    if 'user_id' in session:
        return redirect(url_for('inicio'))
    auto_open_register = session.pop('open_register_modal', True)
    return render_template("index.html", noticias=noticias, register_role="coordinador_area", auto_open_register=auto_open_register)

@app.route("/noticias")
def noticias_publicas():
    todas_noticias = Noticia.query.order_by(Noticia.fecha.desc()).all()
    return render_template("noticias.html", noticias=todas_noticias, nombre=session.get("nombre"))

@app.route("/dashboard")
@login_required
def dashboard():
    usuario = Usuario.query.get(session["user_id"])
    if not usuario:
        session.clear()
        flash("La sesión ha expirado o el usuario no existe. Inicie sesión nuevamente.", "error")
        return redirect(url_for('inicio'))
        
    postulaciones_recientes = Postulacion.query.filter_by(usuario_id=usuario.id).order_by(Postulacion.fecha_postulacion.desc()).limit(3).all() # type: ignore
    
    if usuario.rol == 'estudiante':
        todos_programas = Programa.query.filter_by(dirigido_a='movilidad estudiantes').all()
    elif usuario.rol in ['docente', 'coordinador_area']:
        todos_programas = Programa.query.filter_by(dirigido_a='movilidad docentes').all()
    else:
        todos_programas = Programa.query.all()
        
    # Filtrar programas exclusivos de medicina
    if not es_estudiante_medicina(usuario.carrera) and usuario.rol != 'coordinador_ori':
        todos_programas = [p for p in todos_programas if not es_programa_medicina(p)]
        
    programas_disponibles = todos_programas[:3]
    
    return render_template("dashboard.html", 
                    usuario=usuario, 
                    postulaciones=postulaciones_recientes,
                    programas=programas_disponibles,
                    nombre=session.get("nombre"))

@app.route("/investigadores")
def investigadores():
    return render_template("investigadores.html", nombre=session.get("nombre"))

@app.route("/divulgacion")
def divulgacion():
    return render_template("divulgacion.html", nombre=session.get("nombre"))

@app.route("/estudiantes")
@estudiante_required
def estudiantes():
    return render_template("estudiantes.html", nombre=session.get("nombre"))

@app.route("/docentes")
@docente_required
def docentes():
    return render_template("docentes.html", nombre=session.get("nombre"))

# --- NUEVAS RUTAS (DE INTERÉS) ---
@app.route("/contacto")
def contacto():
    return render_template("contacto.html", nombre=session.get("nombre"))

@app.route("/sitios-interes")
def sitios_interes():
    return render_template("sitios_interes.html", nombre=session.get("nombre"))

@app.route("/recuperar-datos", methods=["GET", "POST"])
def recuperar_datos():
    if request.method == "POST":
        email = request.form.get("email_recuperar")
        nombre = request.form.get("nombre_recuperar")
        captcha_answer = request.form.get("captcha_answer")
        captcha_expected = session.get("captcha_result")
        
        # Validar el CAPTCHA
        if not captcha_answer or not captcha_expected or str(captcha_answer) != str(captcha_expected):
            flash("El resultado de la validación antispam es incorrecto. Inténtelo de nuevo.", "error")
            return redirect(url_for("recuperar_datos"))
            
        # Limpiar el CAPTCHA para que no se reutilice
        session.pop("captcha_result", None)
        
        usuario = None
        if email:
            usuario = Usuario.query.filter_by(email=email).first()
        elif nombre:
            usuario = Usuario.query.filter_by(nombre=nombre).first()
        
        if usuario:
            # Funcionalidad integrada: se restablece la contraseña temporalmente y se envía por correo
            import string
            import random
            
            # Generar contraseña temporal de 10 caracteres segura
            caracteres = string.ascii_letters + string.digits + "!@#$%"
            # Asegurar que cumple con los requisitos de la política de seguridad
            password_temporal = (
                random.choice(string.ascii_uppercase) +
                random.choice(string.ascii_lowercase) +
                random.choice(string.digits) +
                random.choice("!@#$%") +
                ''.join(random.choice(caracteres) for _ in range(6))
            )
            # Mezclar la contraseña para que no siga un patrón predecible
            temp_list = list(password_temporal)
            random.shuffle(temp_list)
            password_temporal = ''.join(temp_list)
            
            # Cifrar y guardar
            hashed_password = bcrypt.generate_password_hash(password_temporal).decode('utf-8')
            usuario.password = hashed_password
            
            try:
                db.session.commit()
                
                # Intentar enviar email si hay correo configurado
                asunto = "Restablecimiento de Contraseña - Movilidad del Conocimiento"
                
                html_correo = f"""
                <html>
                <body style="font-family: Arial, sans-serif; padding: 20px; color: #333;">
                    <div style="max-width: 600px; margin: 0 auto; background-color: #f9f9f9; padding: 30px; border-radius: 10px; border-top: 5px solid #b30000;">
                        <h2 style="color: #b30000; text-align: center;">Recuperación de Contraseña</h2>
                        <p>Hola {usuario.nombre},</p>
                        <p>Has solicitado restablecer tu contraseña en la plataforma de Movilidad del Conocimiento.</p>
                        <div style="background-color: #fff; padding: 15px; border-radius: 5px; text-align: center; margin: 20px 0; border: 1px dashed #ccc;">
                            <p style="margin: 0; font-size: 14px; color: #666;">Tu nueva contraseña temporal es:</p>
                            <h3 style="margin: 10px 0 0 0; color: #b30000; letter-spacing: 2px; font-family: monospace;">{password_temporal}</h3>
                        </div>
                        <p style="font-size: 14px;"><strong>Importante:</strong> Por tu seguridad, te recomendamos cambiar esta contraseña inmediatamente después de iniciar sesión accediendo a la sección "Mi Perfil".</p>
                        <hr style="border: 1px solid #eee; margin: 20px 0;">
                        <p style="font-size: 12px; color: #999; text-align: center;">Si no solicitaste este cambio, contacta al soporte técnico.</p>
                    </div>
                </body>
                </html>
                """
                texto_correo = f"Hola {usuario.nombre},\n\nTu contraseña ha sido restablecida. Tu nueva contraseña temporal es: {password_temporal}\n\nPor favor, cámbiala al iniciar sesión en tu perfil."
                
                # Enviar correo de manera síncrona o asíncrona
                enviar_email(asunto, usuario.email, html_correo, texto_correo)
                
            except Exception as e:
                db.session.rollback()
                print(f"Error al restablecer contraseña: {e}")
                
        # Por seguridad, siempre mostramos el mismo mensaje, exista o no el usuario.
        success_message = "Si los datos ingresados coinciden con un usuario registrado, se ha enviado una contraseña de acceso inmediato a su correo electrónico."
        return render_template("recuperar.html", success_message=success_message, nombre=session.get("nombre"))
        
    # GET request - Generate new math CAPTCHA
    import random
    num1 = random.randint(1, 10)
    num2 = random.randint(1, 10)
    session["captcha_result"] = num1 + num2
    captcha_text = f"¿Cuánto es {num1} + {num2}?"
        
    return render_template("recuperar.html", nombre=session.get("nombre"), captcha_text=captcha_text)

@app.route("/quienes-somos")
def quienes_somos():
    return render_template("quienes_somos.html", nombre=session.get("nombre"))

@app.route("/privacidad")
def privacidad():
    return render_template("privacidad.html", nombre=session.get("nombre"))

@app.route("/equipo-editorial", methods=["GET", "POST"])
def equipo_editorial():
    # Contraseña requerida para acceder
    PASSWORD_EDITORIAL = "Unisinu2024"
    
    if request.method == "POST":
        password_input = request.form.get("password")
        if password_input == PASSWORD_EDITORIAL:
            session['acceso_editorial'] = True
            return render_template("equipo_editorial.html", nombre=session.get("nombre"))
        else:
            flash("Contraseña incorrecta para acceder al equipo editorial.", "error")
            return render_template("login_editorial.html", nombre=session.get("nombre"))
            
    # Si ya tiene acceso en la sesión
    if session.get('acceso_editorial'):
        return render_template("equipo_editorial.html", nombre=session.get("nombre"))
        
    # Mostrar formulario de contraseña
    return render_template("login_editorial.html", nombre=session.get("nombre"))

# --- RUTAS DE LÓGICA CON BASE DE DATOS ---
@app.route("/login", methods=["POST"])
def login():
    email = request.form.get("email")
    password = request.form.get("password")
    
    if not email or not password:
        flash("Por favor, ingrese todos los campos.", "error")
        return redirect(request.referrer or url_for("inicio"))
    
    usuario = Usuario.query.filter_by(email=email).first()
    
    try:
        if usuario and bcrypt.check_password_hash(usuario.password, password):
            
            # --- Validar si el correo está verificado antes de dejarlo entrar ---
            # Excluimos al superadmin de esta validación porque se crea manualmente
            if usuario.rol != 'superadmin' and not usuario.email_verificado:
                flash("Por favor, verifica tu correo electrónico antes de iniciar sesión. Revisa tu bandeja de entrada.", "warning")
                return redirect(request.referrer or url_for("inicio"))
                
            # Guardamos el ID del usuario como un string o entero según lo manejes, pero de forma consistente
            session.permanent = True
            session["user_id"] = usuario.id
            session["nombre"] = usuario.nombre.split(" ")[0] if usuario.nombre else "Usuario"
            session["rol"] = usuario.rol
            session["foto_perfil"] = usuario.foto_perfil
            
            flash("Bienvenido de nuevo, " + session["nombre"], "success")
            
            if session["rol"] == 'coordinador_ori':
                return redirect(url_for("coordinador_dashboard"))
            elif session["rol"] == 'coordinador_area':
                return redirect(url_for("jefe_dashboard"))
            elif session["rol"] == 'superadmin':
                return redirect(url_for("superadmin_dashboard"))
            else:
                return redirect(url_for("dashboard"))
        else:
            flash("Correo o contraseña incorrectos", "error")
    except Exception as e:
        print(f"Error en login: {e}")
        flash("Ocurrió un error al intentar iniciar sesión.", "error")
        
    return redirect(request.referrer or url_for("inicio"))

@app.route("/registro", methods=["POST"])
def registro():
    nombre = request.form.get("nombre_reg")
    email = request.form.get("email_reg")
    password = request.form.get("password_reg")
    rol = request.form.get("role")
    universidad = request.form.get("universidad")
    carrera = request.form.get("carrera")
    
    if rol == 'coordinador_ori':
        universidad = 'Universidad Del Sinú'
        carrera = 'Ori'
    
    if not nombre or not email or not password:
        flash("Todos los campos obligatorios deben ser completados.", "error")
        session['open_register_modal'] = True
        return redirect(request.referrer or url_for("inicio"))

    # Validar formato de correo básico (opcional, ya que HTML5 lo hace, pero bueno para seguridad)
    if not "@" in email or not "." in email:
        flash("Por favor, ingrese un correo electrónico válido.", "error")
        session['open_register_modal'] = True
        return redirect(request.referrer or url_for("inicio"))
        
    # Validar seguridad de contraseña
    es_segura, mensaje_error = validar_password(password)
    if not es_segura:
        flash(mensaje_error, "error")
        session['open_register_modal'] = True
        return redirect(request.referrer or url_for("inicio"))
    
    # Verificar si el usuario ya existe
    if Usuario.query.filter_by(email=email).first():
        flash("El correo ya está registrado", "error")
        session['open_register_modal'] = True
        return redirect(request.referrer or url_for("inicio"))
    
    try:
        # Cifrar contraseña antes de guardar
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        
        # Generar un token único aleatorio
        token_verificacion = secrets.token_urlsafe(32)
        
        # Crear usuario y guardarlo inmediatamente en la BD con estado no verificado
        nuevo_usuario = Usuario(
            nombre=nombre,
            email=email,
            password=hashed_password,
            rol=rol,
            universidad=universidad,
            carrera=carrera,
            email_verificado=False,
            token_verificacion=token_verificacion
        )
        
        db.session.add(nuevo_usuario)
        db.session.commit()
        
        enlace_confirmacion = url_for('verificar_email', token=token_verificacion, _external=True)
        
        # Enviar email de confirmación
        asunto = "Verifica tu correo - Movilidad del Conocimiento"
        # Usamos formato HTML y texto plano para mejorar la reputación del correo
        cuerpo_html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; padding: 20px; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; background-color: #f9f9f9; padding: 30px; border-radius: 10px; border-top: 5px solid #b30000;">
                <h2 style="color: #b30000; text-align: center;">¡Bienvenido a Movilidad del Conocimiento!</h2>
                <p>Hola <strong>{nombre}</strong>,</p>
                <p>Gracias por registrarte en nuestra plataforma de la Universidad del Sinú. Para activar tu cuenta y acceder a todas las funcionalidades, necesitamos verificar tu dirección de correo electrónico.</p>
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{enlace_confirmacion}" target="movilidad_ventana" style="background-color: #b30000; color: white; padding: 12px 25px; text-decoration: none; border-radius: 5px; font-weight: bold; display: inline-block;">Verificar mi cuenta ahora</a>
                </div>
                <p style="font-size: 13px; color: #666;">Si el botón no funciona, copia y pega el siguiente enlace en tu navegador:</p>
                <p style="font-size: 13px; color: #0056b3; word-break: break-all;">{enlace_confirmacion}</p>
                <hr style="border: 1px solid #eee; margin: 20px 0;">
                <p style="font-size: 12px; color: #999; text-align: center;">Si no solicitaste este registro, puedes ignorar este mensaje de forma segura.</p>
            </div>
        </body>
        </html>
        """
        cuerpo_texto = f"Hola {nombre},\n\nGracias por registrarte en nuestra plataforma.\n\nPara activar tu cuenta y poder iniciar sesión, por favor haz clic en el siguiente enlace de verificación:\n\n{enlace_confirmacion}\n\nSi no solicitaste este registro, puedes ignorar este mensaje.\n\nSaludos,\nEquipo de Movilidad del Conocimiento"
        
        # Enviar correo real
        enviado = enviar_email(asunto, email, cuerpo_html, cuerpo_texto)
        
        if enviado:
            flash("Registro exitoso. Se ha enviado un enlace de verificación a tu correo para activar la cuenta. Por favor, revisa también tu carpeta de Spam.", "success")
        else:
            # Fallback forzado en caso de que Google bloquee por exceso de envíos en corto tiempo
            flash(f"Registro casi completo. Hubo un bloqueo de seguridad enviando el correo. Para tu entrega, haz clic aquí para validar: <a href='{enlace_confirmacion}' style='color: #fff; text-decoration: underline; font-weight: bold;'>VALIDAR CORREO AHORA</a>", "warning")
            
    except Exception as e:
        db.session.rollback()
        print(f"Error al procesar registro: {e}")
        flash("Error al procesar el registro. Por favor intente más tarde.", "error")
        
    return redirect(url_for("inicio"))

@app.route("/verificar/<token>")
def verificar_email(token):
    # Buscar el usuario por el token en la base de datos
    usuario = Usuario.query.filter_by(token_verificacion=token).first()
    
    if not usuario:
        flash("El enlace de verificación es inválido o la cuenta ya ha sido verificada.", "error")
        return redirect(url_for('inicio'))
        
    try:
        # Marcar como verificado y eliminar el token
        usuario.email_verificado = True
        usuario.token_verificacion = None
        db.session.commit()
        
        flash("¡Tu correo ha sido verificado exitosamente! Ya puedes iniciar sesión.", "success")
    except Exception as e:
        db.session.rollback()
        print(f"Error al verificar correo: {e}")
        flash("Ocurrió un error al verificar tu cuenta. Por favor, intenta de nuevo.", "error")
        
    return redirect(url_for('inicio'))

@app.route("/perfil", methods=["GET", "POST"])
@login_required
def perfil():
    usuario = Usuario.query.get(session["user_id"])
    if not usuario:
        session.clear()
        flash("La sesión ha expirado o el usuario no existe. Inicie sesión nuevamente.", "error")
        return redirect(url_for('inicio'))
        
    if request.method == "POST":
        password_actual = request.form.get("password_actual")
        nueva_password = request.form.get("nueva_password")
        confirmar_password = request.form.get("confirmar_password")
        
        if password_actual or nueva_password or confirmar_password:
            if not (password_actual and nueva_password and confirmar_password):
                flash("Para cambiar la contraseña debe llenar todos los campos de contraseña.", "error")
            elif nueva_password != confirmar_password:
                flash("La nueva contraseña y la confirmación no coinciden.", "error")
            elif not bcrypt.check_password_hash(usuario.password, password_actual):
                flash("La contraseña actual es incorrecta.", "error")
            elif password_actual == nueva_password:
                flash("La nueva contraseña no puede ser igual a la actual.", "error")
            else:
                es_segura, mensaje_error = validar_password(nueva_password)
                if not es_segura:
                    flash(mensaje_error, "error")
                else:
                    usuario.password = bcrypt.generate_password_hash(nueva_password).decode('utf-8')
                    try:
                        db.session.commit()
                        flash("Contraseña actualizada correctamente.", "success")
                        
                        # --- NOTIFICACIÓN POR CORREO DE CAMBIO DE CONTRASEÑA ---
                        try:
                            asunto_pwd = "Tu contraseña ha sido cambiada - Movilidad del Conocimiento"
                            enlace_inicio = url_for('inicio', _external=True)
                            
                            html_pwd = f"""
                            <html>
                            <body style="font-family: Arial, sans-serif; padding: 20px; color: #333;">
                                <div style="max-width: 600px; margin: 0 auto; background-color: #f9f9f9; padding: 30px; border-radius: 10px; border-top: 5px solid #b30000;">
                                    <h2 style="color: #b30000; text-align: center;">Seguridad de tu Cuenta</h2>
                                    <p>Hola <strong>{usuario.nombre}</strong>,</p>
                                    <p>Te informamos que la contraseña de tu cuenta en <strong>Movilidad del Conocimiento</strong> ha sido cambiada recientemente desde la plataforma.</p>
                                    <div style="background-color: #fff; padding: 15px; border-radius: 5px; border-left: 4px solid #b30000; margin: 20px 0;">
                                        <p style="margin: 0; font-size: 14px;"><strong>Fecha y Hora:</strong> {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
                                    </div>
                                    <p>Si fuiste tú quien realizó este cambio, puedes ignorar este mensaje de forma segura.</p>
                                    <p style="color: #d9534f; font-weight: bold;">¿No reconoces esta actividad?</p>
                                    <p>Si no cambiaste tu contraseña, te recomendamos intentar restablecerla de inmediato o ponerte en contacto con el soporte técnico de la plataforma.</p>
                                    <div style="text-align: center; margin-top: 25px;">
                                        <a href="{enlace_inicio}" target="movilidad_ventana" style="background-color: #b30000; color: white; padding: 12px 25px; text-decoration: none; border-radius: 5px; font-weight: bold;">Ir a la Plataforma</a>
                                    </div>
                                    <hr style="border: 1px solid #eee; margin: 20px 0;">
                                    <p style="font-size: 12px; color: #999; text-align: center;">Este es un aviso automático de seguridad.</p>
                                </div>
                            </body>
                            </html>
                            """
                            texto_pwd = f"Hola {usuario.nombre},\n\nTe informamos que tu contraseña ha sido cambiada recientemente en la plataforma de Movilidad del Conocimiento.\n\nSi no realizaste este cambio, por favor contacta al soporte técnico de inmediato.\n\nSaludos,\nEquipo de Movilidad"
                            
                            # Enviar de forma asíncrona para no ralentizar la respuesta al usuario
                            import threading
                            threading.Thread(target=enviar_email, args=(asunto_pwd, usuario.email, html_pwd, texto_pwd)).start()
                        except Exception as e_mail:
                            print(f"Error al enviar notificación de cambio de contraseña: {e_mail}")
                            
                    except Exception as e:
                        db.session.rollback()
                        print(f"Error al actualizar contraseña: {e}")
                        flash("Error al actualizar la contraseña.", "error")
        else:
            flash("No se detectó ningún cambio de contraseña.", "info")
            
        return redirect(url_for("perfil"))
        
    postulaciones = Postulacion.query.filter_by(usuario_id=usuario.id).all() # type: ignore
    return render_template("perfil.html", usuario=usuario, nombre=session.get("nombre"), postulaciones=postulaciones)

@app.route("/perfil/subir_foto", methods=["POST"])
@login_required
def subir_foto_perfil():
    usuario = Usuario.query.get(session["user_id"])
    if not usuario:
        return redirect(url_for('inicio'))
        
    foto_base64 = request.form.get('foto_perfil_base64')
    if not foto_base64:
        flash("No se recibió ninguna imagen.", "error")
        return redirect(url_for('perfil'))
        
    import base64
    import uuid
    try:
        # El formato de la cadena base64 es "data:image/jpeg;base64,/9j/4AAQSk..."
        header, encoded = foto_base64.split(",", 1)
        
        # Determinar la extensión
        ext = "jpg"
        if "png" in header:
            ext = "png"
            
        # Generar nombre de archivo único
        filename = f"perfil_{usuario.id}_{uuid.uuid4().hex[:8]}.{ext}"
        perfil_dir = os.path.join(app.root_path, 'static', 'uploads', 'perfiles')
        os.makedirs(perfil_dir, exist_ok=True)
        filepath = os.path.join(perfil_dir, filename)
        
        # Guardar archivo
        with open(filepath, "wb") as fh:
            fh.write(base64.b64decode(encoded))
            
        # Corregir la ruta a 'uploads/perfiles/filename' (sin barra inicial para evitar problemas con url_for)
        # La carpeta real en el sistema de archivos es static/uploads/perfiles
        usuario.foto_perfil = f'uploads/perfiles/{filename}'
        
        try:
            db.session.commit()
            # Actualizar session
            session['foto_perfil'] = usuario.foto_perfil
            flash("Foto de perfil actualizada correctamente.", "success")
        except:
            db.session.rollback()
            flash("Error al actualizar la foto de perfil en la base de datos.", "error")
            
    except Exception as e:
        print(f"Error procesando la imagen: {e}")
        flash("Error al procesar la imagen enviada.", "error")
        
    return redirect(url_for('perfil'))

@app.route("/perfil/eliminar_foto", methods=["POST"])
@login_required
def eliminar_foto_perfil():
    usuario = Usuario.query.get(session["user_id"])
    if not usuario:
        return redirect(url_for('inicio'))
        
    if usuario.foto_perfil:
        try:
            # Opcional: Eliminar el archivo físico si lo deseas
            # filepath = os.path.join(app.root_path, 'static', usuario.foto_perfil)
            # if os.path.exists(filepath):
            #     os.remove(filepath)
                
            usuario.foto_perfil = None
            db.session.commit()
            
            if 'foto_perfil' in session:
                del session['foto_perfil']
                
            flash("Foto de perfil eliminada correctamente.", "success")
        except Exception as e:
            db.session.rollback()
            print(f"Error al eliminar foto: {e}")
            flash("Error al eliminar la foto de perfil.", "error")
            
    return redirect(url_for('perfil'))

@app.route("/programas")
@estudiante_o_docente_required
def programas():
    rol = session.get('rol')
    carrera = session.get('carrera', '').lower()
    
    if rol == 'estudiante':
        lista_programas = Programa.query.filter_by(dirigido_a='movilidad estudiantes').all()
    elif rol in ['docente', 'coordinador_area']:
        lista_programas = Programa.query.filter_by(dirigido_a='movilidad docentes').all()
    else:
        lista_programas = Programa.query.all()
        
    # Filtrar programas exclusivos de medicina si el usuario NO es de medicina
    if not es_estudiante_medicina(session.get('carrera')) and rol != 'coordinador_ori':
        lista_programas = [p for p in lista_programas if not es_programa_medicina(p)]
    
    return render_template("programas.html", programas=lista_programas, nombre=session.get("nombre"), now=datetime.now())

@app.route("/programa/<int:id>")
@estudiante_o_docente_required
def detalle_programa(id):
    programa = Programa.query.get_or_404(id)
    
    # Check if the user's role is allowed to view this program
    rol = session.get('rol')
    carrera = session.get('carrera', '').lower()
    
    if rol == 'estudiante' and programa.dirigido_a != 'movilidad estudiantes':
        flash("Este programa es exclusivo para docentes.", "error")
        return redirect(url_for('programas'))
    elif rol in ['docente', 'coordinador_area'] and programa.dirigido_a != 'movilidad docentes':
        flash("Este programa es exclusivo para estudiantes.", "error")
        return redirect(url_for('programas'))
        
    # Verificar si es programa exclusivo de medicina
    if es_programa_medicina(programa) and not es_estudiante_medicina(session.get('carrera')) and rol != 'coordinador_ori':
        flash("Este programa es exclusivo para estudiantes de la carrera de Medicina.", "error")
        return redirect(url_for('programas'))
        
    ya_postulado = False
    if 'user_id' in session:
        ya_postulado = Postulacion.query.filter_by(usuario_id=session['user_id'], programa_id=id).first() is not None
    return render_template("detalle_programa.html", programa=programa, ya_postulado=ya_postulado, nombre=session.get("nombre"), now=datetime.now())

@app.route("/postular/<int:id>", methods=["POST"])
@login_required
def postular(id):
    usuario = Usuario.query.get(session["user_id"])
    if not usuario:
        session.clear()
        flash("La sesión ha expirado o el usuario no existe. Inicie sesión nuevamente.", "error")
        return redirect(url_for('inicio'))
        
    programa = Programa.query.get_or_404(id)
    
    if usuario.rol == 'estudiante' and programa.dirigido_a != 'movilidad estudiantes':
        flash("No puedes postularte a un programa de docentes.", "error")
        return redirect(url_for('programas'))
    elif usuario.rol in ['docente', 'coordinador_area'] and programa.dirigido_a != 'movilidad docentes':
        flash("No puedes postularte a un programa de estudiantes.", "error")
        return redirect(url_for('programas'))
        
    # Verificar si es programa exclusivo de medicina
    if es_programa_medicina(programa) and not es_estudiante_medicina(usuario.carrera):
        flash("Este programa es exclusivo para estudiantes de la carrera de Medicina.", "error")
        return redirect(url_for('programas'))
    
    # Verificar si el programa está cerrado (fecha límite)
    if programa.fecha_fin and datetime.now() > programa.fecha_fin:
        flash("Lo sentimos, el periodo de postulación para este programa ha finalizado.", "error")
        return redirect(url_for('detalle_programa', id=id))
    
    # Verificar si ya está postulado
    if Postulacion.query.filter_by(usuario_id=usuario.id, programa_id=id).first():
        flash("Ya te has postulado a este programa.", "error")
        return redirect(url_for('detalle_programa', id=id))
    
    # Procesar campos dinámicos
    datos_formulario = {}
    archivos_postulacion = {}
    
    if programa.formulario_json:
        try:
            campos = json.loads(programa.formulario_json)
            for campo in campos:
                campo_id = f"field_{campo['id']}"
                
                if campo['type'] == 'file':
                    if campo_id in request.files:
                        file = request.files[campo_id]
                        if file and file.filename != '' and allowed_file(file.filename):
                            filename = secure_filename(f"{usuario.id}_{id}_{campo['id']}_{file.filename}")
                            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                            file.save(file_path)
                            archivos_postulacion[campo['label']] = url_for('static', filename=f'uploads/postulaciones/{filename}')
                        elif campo.get('required'):
                            flash(f"El archivo '{campo['label']}' es obligatorio.", "error")
                            return redirect(url_for('detalle_programa', id=id))
                elif campo['type'] == 'image':
                    file_key = f"{campo_id}_file"
                    url_key = f"{campo_id}_url"
                    
                    imagen_valor = None
                    
                    # Check for file
                    if file_key in request.files:
                        file = request.files[file_key]
                        if file and file.filename != '' and allowed_file(file.filename):
                            filename = secure_filename(f"{usuario.id}_{id}_{campo['id']}_{file.filename}")
                            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                            file.save(file_path)
                            imagen_valor = url_for('static', filename=f'uploads/postulaciones/{filename}')
                            archivos_postulacion[campo['label']] = imagen_valor
                    
                    # If no file, check for URL
                    if not imagen_valor:
                        url_valor = request.form.get(url_key)
                        if url_valor:
                            imagen_valor = url_valor
                            datos_formulario[campo['label']] = url_valor
                    
                    if not imagen_valor and campo.get('required'):
                        flash(f"Debe proporcionar una imagen para '{campo['label']}' (archivo o URL).", "error")
                        return redirect(url_for('detalle_programa', id=id))
                    
                    if imagen_valor:
                        datos_formulario[campo['label']] = imagen_valor
                else:
                    if campo['type'] == 'checkbox':
                        valores = request.form.getlist(campo_id)
                        datos_formulario[campo['label']] = ", ".join(valores)
                        if not valores and campo.get('required'):
                            flash(f"El campo '{campo['label']}' es obligatorio.", "error")
                            return redirect(url_for('detalle_programa', id=id))
                    else:
                        valor = request.form.get(campo_id)
                        if not valor and campo.get('required'):
                            flash(f"El campo '{campo['label']}' es obligatorio.", "error")
                            return redirect(url_for('detalle_programa', id=id))
                        datos_formulario[campo['label']] = valor
        except Exception as e:
            print(f"Error procesando formulario dinámico: {e}")
            flash("Error al procesar el formulario. Intente de nuevo.", "error")
            return redirect(url_for('detalle_programa', id=id))

    nueva_postulacion = Postulacion(
        usuario_id=usuario.id, # type: ignore
        programa_id=id, # type: ignore
        datos_formulario_json=json.dumps(datos_formulario), # type: ignore
        archivos_json=json.dumps(archivos_postulacion) # type: ignore
    )
    
    try:
        db.session.add(nueva_postulacion)
        db.session.commit()
        flash("Tu postulación ha sido enviada con éxito.", "success")
        
        # --- NOTIFICAR A COORDINADORES ORI SOBRE NUEVA POSTULACIÓN ---
        coordinadores_ori = Usuario.query.filter_by(rol='coordinador_ori').all()
        
        for coord in coordinadores_ori:
            if coord.email:
                nombre_coord = coord.nombre.split()[0].capitalize()
                asunto_ori = f"Nueva Postulación: {programa.nombre}"
                html_ori = f"""
                <html>
                <body style="font-family: Arial, sans-serif; padding: 20px; color: #333;">
                    <div style="max-width: 600px; margin: 0 auto; background-color: #f9f9f9; padding: 30px; border-radius: 10px; border-top: 5px solid #b30000;">
                        <h2 style="color: #b30000; text-align: center;">Nueva Postulación Recibida</h2>
                        <p>Hola <strong>{nombre_coord}</strong>,</p>
                        <p>Tienes un nuevo postulado: <strong>{usuario.nombre}</strong> (Carrera: {usuario.carrera}) para el programa <strong>{programa.nombre}</strong>.</p>
                        <p style="font-size: 14px;">Inicia sesión en el panel de administración para revisar los documentos y gestionar la postulación.</p>
                        <div style="text-align: center; margin-top: 25px;">
                            <a href="{url_for('inicio', _external=True)}" target="movilidad_ventana" style="background-color: #b30000; color: white; padding: 12px 25px; text-decoration: none; border-radius: 5px; font-weight: bold;">Revisar Postulación</a>
                        </div>
                    </div>
                </body>
                </html>
                """
                texto_ori = f"Hola {nombre_coord}, tienes un nuevo postulado: {usuario.nombre} para el programa {programa.nombre}.\n\nInicia sesión en la plataforma para revisarlo."
                
                import threading
                def enviar_notif_ori_individual(app_context, dest, asunto, html, texto):
                    with app_context:
                        enviar_email(asunto, dest, html, texto)
                
                threading.Thread(target=enviar_notif_ori_individual, args=(app.app_context(), coord.email, asunto_ori, html_ori, texto_ori)).start()
            
    except Exception as e:
        db.session.rollback()
        print(f"Error guardando postulación: {e}")
        flash("Hubo un error al procesar tu postulación.", "error")
        
    return redirect(url_for('perfil'))

@app.route("/editar_postulacion/<int:id>", methods=["GET", "POST"])
@login_required
def editar_postulacion(id):
    usuario = Usuario.query.get(session["user_id"])
    if not usuario:
        session.clear()
        return redirect(url_for('inicio'))
        
    postulacion = Postulacion.query.get_or_404(id)
    if postulacion.usuario_id != usuario.id:
        flash("No tienes permiso para editar esta postulación.", "error")
        return redirect(url_for('perfil'))
        
    programa = postulacion.programa
    
    if request.method == "POST":
        datos_formulario = {}
        if programa.formulario_json:
            try:
                campos = json.loads(programa.formulario_json)
                for campo in campos:
                    field_id = f"field_{campo.get('id', '')}"
                    if campo.get('type') == 'image':
                        method = campo.get('options', 'both')
                        if method in ['both', 'file'] and field_id + '_file' in request.files and request.files[field_id + '_file'].filename != '':
                            file = request.files[field_id + '_file']
                            if file and allowed_file(file.filename):
                                filename = secure_filename(f"img_{usuario.id}_{file.filename}")
                                file_path = os.path.join(app.config['UPLOAD_FOLDER'], 'postulaciones', filename)
                                file.save(file_path)
                                datos_formulario[campo.get('label')] = url_for('uploaded_file', filename=f"postulaciones/{filename}")
                        elif method in ['both', 'url'] and request.form.get(field_id + '_url'):
                            datos_formulario[campo.get('label')] = request.form.get(field_id + '_url')
                    elif campo.get('type') == 'file':
                        # Archivos del formulario
                        if field_id in request.files and request.files[field_id].filename != '':
                            file = request.files[field_id]
                            if file and allowed_file(file.filename):
                                filename = secure_filename(f"file_{usuario.id}_{file.filename}")
                                file_path = os.path.join(app.config['UPLOAD_FOLDER'], 'postulaciones', filename)
                                file.save(file_path)
                                datos_formulario[campo.get('label')] = url_for('uploaded_file', filename=f"postulaciones/{filename}")
                    else:
                        valor = request.form.get(field_id)
                        if valor:
                            datos_formulario[campo.get('label')] = valor
            except Exception as e:
                print(f"Error procesando actualización de formulario: {e}")
                
        # Mantener datos anteriores si no se subieron nuevos archivos
        datos_antiguos = {}
        try:
            datos_antiguos = json.loads(postulacion.datos_formulario_json or '{}')
        except:
            pass
        for key, val in datos_antiguos.items():
            if key not in datos_formulario:
                datos_formulario[key] = val

        postulacion.datos_formulario_json = json.dumps(datos_formulario)
        postulacion.estado = 'pendiente_ori'  # Se reinicia el estado a revisión
        
        try:
            db.session.commit()
            flash("Tu postulación ha sido actualizada con éxito y enviada a revisión.", "success")
        except Exception as e:
            db.session.rollback()
            print(f"Error guardando actualización: {e}")
            flash("Hubo un error al procesar tu actualización.", "error")
            
        return redirect(url_for('perfil'))
        
    return render_template("detalle_programa.html", programa=programa, editando_postulacion=postulacion, nombre=session.get("nombre"), now=datetime.now())

# --- RUTAS DE COORDINADOR ORI ---
@app.route("/coordinador")
@coordinador_ori_required
def coordinador_dashboard():
    usuario = Usuario.query.get(session["user_id"])
    if not usuario:
        session.clear()
        flash("La sesión ha expirado o el usuario no existe. Inicie sesión nuevamente.", "error")
        return redirect(url_for('inicio'))
        
    total_usuarios = Usuario.query.count()
    total_programas = Programa.query.count()
    total_postulaciones = Postulacion.query.count()
    postulaciones_estudiantes = Postulacion.query.join(Usuario).filter(Usuario.rol == 'estudiante').order_by(Postulacion.fecha_postulacion.desc()).limit(10).all()
    postulaciones_docentes = Postulacion.query.join(Usuario).filter(Usuario.rol.in_(['docente', 'coordinador_area'])).order_by(Postulacion.fecha_postulacion.desc()).limit(10).all()
    
    return render_template("admin/dashboard.html", 
            total_usuarios=total_usuarios,
            total_programas=total_programas,
            total_postulaciones=total_postulaciones,
            postulaciones_estudiantes=postulaciones_estudiantes,
            postulaciones_docentes=postulaciones_docentes,
            nombre=session.get("nombre"))

@app.route("/coordinador/postulaciones")
@coordinador_ori_required
def coordinador_postulaciones():
    postulaciones_estudiantes = Postulacion.query.join(Usuario).filter(Usuario.rol == 'estudiante').order_by(Postulacion.fecha_postulacion.desc()).all()
    postulaciones_docentes = Postulacion.query.join(Usuario).filter(Usuario.rol.in_(['docente', 'coordinador_area'])).order_by(Postulacion.fecha_postulacion.desc()).all()
    return render_template("admin/postulaciones.html", postulaciones_estudiantes=postulaciones_estudiantes, postulaciones_docentes=postulaciones_docentes, nombre=session.get("nombre"))

@app.route("/coordinador/postulaciones/exportar/<string:tipo>")
@coordinador_ori_required
def exportar_postulaciones_excel(tipo):
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment
    from flask import send_file
    import io
    from datetime import datetime
    
    # Crear el libro de trabajo
    wb = Workbook()
    ws = wb.active
    ws.title = "Postulaciones"
    
    # Obtener las postulaciones según el tipo
    if tipo == "estudiantes":
        postulaciones = Postulacion.query.join(Usuario).filter(Usuario.rol == 'estudiante').order_by(Postulacion.fecha_postulacion.desc()).all()
        titulo = "Postulaciones de Estudiantes"
    else:
        postulaciones = Postulacion.query.join(Usuario).filter(Usuario.rol.in_(['docente', 'coordinador_area'])).order_by(Postulacion.fecha_postulacion.desc()).all()
        titulo = "Postulaciones de Docentes/Admin"
    
    # Estilos para encabezados
    encabezado_fill = PatternFill(start_color="1a2a3a", end_color="1a2a3a", fill_type="solid")
    encabezado_font = Font(bold=True, color="FFFFFF", size=12)
    encabezado_alignment = Alignment(horizontal="center", vertical="center")
    
    # Agregar encabezados
    encabezados = ["Nombre", "Email", "Programa", "Universidad", "Carrera", "Fecha Postulación", "Estado"]
    ws.append(encabezados)
    
    # Aplicar estilos a los encabezados
    for col_num, _ in enumerate(encabezados, 1):
        cell = ws.cell(row=1, column=col_num)
        cell.fill = encabezado_fill
        cell.font = encabezado_font
        cell.alignment = encabezado_alignment
    
    # Agregar datos de las postulaciones
    for postu in postulaciones:
        usuario = postu.estudiante
        fila = [
            usuario.nombre,
            usuario.email,
            postu.programa.nombre,
            usuario.universidad or "N/A",
            usuario.carrera or "N/A",
            postu.fecha_postulacion.strftime("%d/%m/%Y"),
            postu.estado.replace("_ori", "").replace("_jefe", "").replace("_", " ").upper()
        ]
        ws.append(fila)
    
    # Ajustar el ancho de las columnas
    for col in ws.columns:
        max_length = 0
        column = col[0].column_letter
        for cell in col:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass
        adjusted_width = min(max_length + 2, 50)
        ws.column_dimensions[column].width = adjusted_width
    
    # Guardar el libro en memoria
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    
    # Nombre del archivo
    fecha_actual = datetime.now().strftime("%Y%m%d_%H%M%S")
    nombre_archivo = f"{titulo.replace(' ', '_')}_{fecha_actual}.xlsx"
    
    # Enviar el archivo para descarga
    return send_file(
        output,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name=nombre_archivo
    )

@app.route("/coordinador/postulacion/<int:id>/estado", methods=["POST"])
@coordinador_ori_required
def coordinador_cambiar_estado_postulacion(id):
    postulacion = Postulacion.query.get_or_404(id)
    es_docente = postulacion.estudiante.rol in ['docente', 'coordinador_area']
    
    # Si el estado ya fue actualizado por el jefe o es un docente aprobado, el coordinador solo puede subir cartas
    # EXCEPCIÓN: Si es docente, el coordinador ORI SIEMPRE puede actualizar el estado.
    if not es_docente and postulacion.estado in ['aprobado_jefe', 'rechazado_jefe', 'aprobado_ori']:
        # Manejar carga de cartas ORI para estudiantes
        cartas_subidas = 0
        if 'carta_ori_1' in request.files:
            file1 = request.files['carta_ori_1']
            if file1 and file1.filename != '' and allowed_file(file1.filename):
                filename1 = secure_filename(f"carta_ori1_{postulacion.id}_{file1.filename}")
                file1.save(os.path.join(app.config['UPLOAD_FOLDER'], filename1))
                postulacion.carta_ori_1_url = url_for('static', filename=f'uploads/postulaciones/{filename1}')
                cartas_subidas += 1
                
        if 'carta_ori_2' in request.files:
            file2 = request.files['carta_ori_2']
            if file2 and file2.filename != '' and allowed_file(file2.filename):
                filename2 = secure_filename(f"carta_ori2_{postulacion.id}_{file2.filename}")
                file2.save(os.path.join(app.config['UPLOAD_FOLDER'], filename2))
                postulacion.carta_ori_2_url = url_for('static', filename=f'uploads/postulaciones/{filename2}')
                cartas_subidas += 1
        
        if cartas_subidas > 0:
            try:
                db.session.commit()
                flash(f"Se han subido {cartas_subidas} carta(s) para {postulacion.estudiante.nombre}", "success")
                
                # --- ENVÍO DE NOTIFICACIÓN DE CARTAS ---
                asunto_notif = f"Nuevos Documentos: {postulacion.programa.nombre}"
                html_notif = f"""
                <html>
                <body style="font-family: Arial, sans-serif; padding: 20px; color: #333;">
                    <div style="max-width: 600px; margin: 0 auto; background-color: #f9f9f9; padding: 30px; border-radius: 10px; border-top: 5px solid #b30000;">
                        <h2 style="color: #b30000; text-align: center;">Nuevos Documentos Disponibles</h2>
                        <p>Hola {postulacion.estudiante.nombre},</p>
                        <p>La Coordinación ORI ha subido {cartas_subidas} nueva(s) carta(s) a tu postulación para el programa <strong>{postulacion.programa.nombre}</strong>.</p>
                        <p style="font-size: 14px;">Inicia sesión en la plataforma y ve a tu perfil para descargar los documentos.</p>
                    </div>
                </body>
                </html>
                """
                texto_notif = f"Hola {postulacion.estudiante.nombre},\n\nLa Coordinación ORI ha subido {cartas_subidas} nueva(s) carta(s) a tu postulación.\n\nInicia sesión en la plataforma para ver los documentos."
                
                import threading
                def enviar_notificacion_doc(app_context, dest, asunto, html, texto):
                    with app_context:
                        enviar_email(asunto, dest, html, texto)
                
                hilo = threading.Thread(target=enviar_notificacion_doc, args=(app.app_context(), postulacion.estudiante.email, asunto_notif, html_notif, texto_notif))
                hilo.start()
                
            except Exception as e:
                db.session.rollback()
                print(f"Error al guardar cartas y notificar: {e}")
                flash("Error al guardar las cartas.", "error")
        else:
            flash("No se seleccionaron archivos válidos para subir.", "warning")
            
        return redirect(url_for('coordinador_postulaciones'))

    # Para docentes que ya están aprobados, primero manejar la carta si se envió
    if es_docente and postulacion.estado == 'aprobado_ori':
        if 'carta_ori_1' in request.files:
            file1 = request.files['carta_ori_1']
            if file1 and file1.filename != '' and allowed_file(file1.filename):
                filename1 = secure_filename(f"carta_ori1_{postulacion.id}_{file1.filename}")
                file1.save(os.path.join(app.config['UPLOAD_FOLDER'], filename1))
                postulacion.carta_ori_1_url = url_for('static', filename=f'uploads/postulaciones/{filename1}')
                try:
                    db.session.commit()
                    flash(f"Carta de aprobación subida para {postulacion.estudiante.nombre}", "success")
                    
                    # --- ENVÍO DE NOTIFICACIÓN DE CARTA DOCENTE ---
                    asunto_notif = f"Aprobación Final: {postulacion.programa.nombre}"
                    html_notif = f"""
                    <html>
                    <body style="font-family: Arial, sans-serif; padding: 20px; color: #333;">
                        <div style="max-width: 600px; margin: 0 auto; background-color: #f9f9f9; padding: 30px; border-radius: 10px; border-top: 5px solid #b30000;">
                            <h2 style="color: #b30000; text-align: center;">Aprobación de Movilidad</h2>
                            <p>Hola {postulacion.estudiante.nombre},</p>
                            <p>La Coordinación ORI ha subido la carta de aprobación para tu programa de movilidad: <strong>{postulacion.programa.nombre}</strong>.</p>
                            <p style="font-size: 14px;">Inicia sesión en la plataforma y ve a tu perfil para descargar el documento.</p>
                        </div>
                    </body>
                    </html>
                    """
                    texto_notif = f"Hola {postulacion.estudiante.nombre},\n\nLa Coordinación ORI ha subido la carta de aprobación a tu postulación.\n\nInicia sesión en la plataforma para ver los documentos."
                    
                    import threading
                    def enviar_notificacion_doc_docente(app_context, dest, asunto, html, texto):
                        with app_context:
                            enviar_email(asunto, dest, html, texto)
                    
                    hilo = threading.Thread(target=enviar_notificacion_doc_docente, args=(app.app_context(), postulacion.estudiante.email, asunto_notif, html_notif, texto_notif))
                    hilo.start()
                    
                except Exception as e:
                    db.session.rollback()
                    print(f"Error guardando carta docente y notificar: {e}")
                    flash("Error al guardar la carta.", "error")

    # Flujo normal de cambio de estado (Aplica para estudiantes en estados tempranos y docentes SIEMPRE)
    nuevo_estado = request.form.get("estado")
    comentarios = request.form.get("comentarios")
    
    if nuevo_estado and nuevo_estado in ['espera_ori', 'rechazado_ori', 'candidato', 'aprobado_ori']:
        postulacion.estado = nuevo_estado
        
        if nuevo_estado in ['candidato', 'aprobado_ori']:
            postulacion.comentarios = None
        elif comentarios is not None:
            postulacion.comentarios = comentarios
            
        try:
            db.session.commit()
            flash(f"Postulación de {postulacion.estudiante.nombre} marcada como {nuevo_estado.replace('_ori', '').upper()}", "success")
            
            # --- ENVÍO DE NOTIFICACIÓN DE ESTADO ---
            asunto_notif = f"Actualización de Postulación: {postulacion.programa.nombre}"
            estado_legible = nuevo_estado.replace('_ori', '').upper().replace('_', ' ')
            
            texto_obs = f"<p><strong>Observaciones:</strong> {postulacion.comentarios}</p>" if postulacion.comentarios else ""
            
            html_notif = f"""
            <html>
            <body style="font-family: Arial, sans-serif; padding: 20px; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; background-color: #f9f9f9; padding: 30px; border-radius: 10px; border-top: 5px solid #b30000;">
                    <h2 style="color: #b30000; text-align: center;">Actualización de Estado</h2>
                    <p>Hola {postulacion.estudiante.nombre},</p>
                    <p>Tu postulación al programa <strong>{postulacion.programa.nombre}</strong> ha sido actualizada por la Coordinación ORI.</p>
                    <div style="background-color: #fff; padding: 15px; border-radius: 5px; border-left: 4px solid #b30000; margin: 20px 0;">
                        <p style="margin: 0; font-size: 16px;"><strong>Nuevo Estado:</strong> {estado_legible}</p>
                        {texto_obs}
                    </div>
                    <p style="font-size: 14px;">Inicia sesión en la plataforma para ver más detalles.</p>
                </div>
            </body>
            </html>
            """
            texto_notif = f"Hola {postulacion.estudiante.nombre},\n\nTu postulación al programa {postulacion.programa.nombre} ha cambiado a estado: {estado_legible}.\n\nInicia sesión para más detalles."
            
            import threading
            def enviar_notificacion_estado(app_context, dest, asunto, html, texto):
                with app_context:
                    enviar_email(asunto, dest, html, texto)
            
            hilo = threading.Thread(target=enviar_notificacion_estado, args=(app.app_context(), postulacion.estudiante.email, asunto_notif, html_notif, texto_notif))
            hilo.start()

            # --- NOTIFICAR AL C.A (COORDINADOR DE PROGRAMA) CUANDO PASA A REVISIÓN ---
            if nuevo_estado == 'candidato' and postulacion.estudiante.rol == 'estudiante':
                carrera_estudiante = postulacion.estudiante.carrera
                jefes_programa = Usuario.query.filter_by(rol='coordinador_area', carrera=carrera_estudiante).all()
                
                for jefe in jefes_programa:
                    if jefe.email:
                        nombre_jefe = jefe.nombre.split()[0].capitalize()
                        asunto_ca = f"Nuevo Candidato por Revisar: {postulacion.estudiante.nombre.title()}"
                        
                        html_ca = f"""
                        <html>
                        <body style="font-family: Arial, sans-serif; padding: 20px; color: #333;">
                            <div style="max-width: 600px; margin: 0 auto; background-color: #f9f9f9; padding: 30px; border-radius: 10px; border-top: 5px solid #b30000;">
                                <h2 style="color: #b30000; text-align: center;">Candidato Pendiente de Revisión</h2>
                                <p>Hola <strong>{nombre_jefe}</strong>,</p>
                                <p>Tienes un nuevo postulado: <strong>{postulacion.estudiante.nombre.title()}</strong> (Carrera: {carrera_estudiante}) para el programa <strong>{postulacion.programa.nombre}</strong>.</p>
                                <div style="background-color: #fff; padding: 15px; border-radius: 5px; border-left: 4px solid #b30000; margin: 20px 0;">
                                    <p style="margin: 0; font-size: 16px;"><strong>Estado Actual:</strong> EN REVISIÓN (CANDIDATO)</p>
                                    <p style="margin-top: 10px; font-size: 14px; color: #555;">El estudiante ha sido validado por ORI y ahora requiere tu evaluación técnica en el panel de C.A.</p>
                                </div>
                                <div style="text-align: center; margin-top: 25px;">
                                    <a href="{url_for('inicio', _external=True)}" target="movilidad_ventana" style="background-color: #b30000; color: white; padding: 12px 25px; text-decoration: none; border-radius: 5px; font-weight: bold;">Ir al Panel de C.A</a>
                                </div>
                            </div>
                        </body>
                        </html>
                        """
                        texto_ca = f"Hola {nombre_jefe}, tienes un nuevo postulado: {postulacion.estudiante.nombre.title()} para el programa {postulacion.programa.nombre}. Inicia sesión en tu panel de C.A para evaluarlo."
                        
                        threading.Thread(target=enviar_notificacion_estado, args=(app.app_context(), jefe.email, asunto_ca, html_ca, texto_ca)).start()
            
        except Exception as e:
            db.session.rollback()
            print(f"Error al actualizar estado y notificar: {e}")
            flash("Error al actualizar el estado.", "error")
    return redirect(url_for('coordinador_postulaciones'))

@app.route("/coordinador/postulacion/eliminar/<int:id>", methods=["POST"])
@coordinador_ori_required
def coordinador_eliminar_postulacion(id):
    postulacion = Postulacion.query.get_or_404(id)
    nombre_estudiante = postulacion.estudiante.nombre
    try:
        db.session.delete(postulacion)
        db.session.commit()
        flash(f"La postulación de {nombre_estudiante} ha sido eliminada.", "success")
    except Exception as e:
        db.session.rollback()
        flash("Error al eliminar la postulación.", "error")
        print(f"Error eliminando postulacion: {e}")
    return redirect(url_for('coordinador_postulaciones'))

@app.route("/coordinador/programas")
@coordinador_ori_required
def admin_programas():
    programas = Programa.query.all()
    return render_template("admin/programas.html", programas=programas, nombre=session.get("nombre"))

# --- GESTIÓN DE NOTICIAS ORI ---
@app.route("/coordinador/noticias")
@coordinador_ori_required
def admin_noticias():
    noticias = Noticia.query.order_by(Noticia.fecha.desc()).all()
    return render_template("admin/noticias.html", noticias=noticias, nombre=session.get("nombre"))

@app.route("/coordinador/noticia/nueva", methods=["GET", "POST"])
@coordinador_ori_required
def admin_nueva_noticia():
    if request.method == "POST":
        contenido = request.form.get("contenido") # Contenido HTML de Quill
        
        # Extraer título del contenido (primeros 50 caracteres sin tags)
        import re
        texto_limpio = re.sub('<[^<]+?>', '', contenido or '')
        titulo = (texto_limpio[:50] + '...') if len(texto_limpio) > 50 else texto_limpio
        
        imagen_url = None
        if 'imagen_archivo' in request.files:
            file = request.files['imagen_archivo']
            if file and file.filename != '' and allowed_file(file.filename):
                filename = secure_filename(f"news_{datetime.now().timestamp()}_{file.filename}")
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                imagen_url = url_for('static', filename=f'uploads/postulaciones/{filename}')
        
        nueva_noticia = Noticia(
            titulo=titulo, # type: ignore
            contenido=contenido, # type: ignore
            imagen_url=imagen_url, # type: ignore
            autor_id=session['user_id'] # type: ignore
        )
        
        try:
            db.session.add(nueva_noticia)
            db.session.commit()
            
            # Enviar correo a todos los usuarios de forma asíncrona
            from threading import Thread
            
            def enviar_notificacion_noticia(asunto, correos, html, texto):
                with app.app_context():
                    enviar_email(asunto, correos, html, texto)
            
            try:
                todos_usuarios = Usuario.query.with_entities(Usuario.email).all()
                correos = [u.email for u in todos_usuarios if u.email]
                
                if correos:
                    asunto_correo = f"Nueva Noticia: {titulo}"
                    enlace_plataforma = url_for('inicio', _external=True)
                    
                    cuerpo_html = f"""
                    <html>
                    <body style="font-family: Arial, sans-serif; padding: 20px; color: #333;">
                        <div style="max-width: 600px; margin: 0 auto; background-color: #f9f9f9; padding: 30px; border-radius: 10px; border-top: 5px solid #b30000;">
                            <h2 style="color: #b30000; text-align: center;">Nueva Noticia en Movilidad del Conocimiento</h2>
                            <p>Hola,</p>
                            <p>Se ha publicado una nueva noticia en la plataforma:</p>
                            <div style="background-color: #fff; padding: 15px; border-radius: 5px; margin: 20px 0; border: 1px solid #ddd;">
                                <h3 style="margin-top: 0; color: #333;">{titulo}</h3>
                                <p style="color: #555; font-size: 14px;">{texto_limpio[:200]}...</p>
                            </div>
                            <div style="text-align: center; margin: 30px 0;">
                                <a href="{enlace_plataforma}" target="movilidad_ventana" style="background-color: #b30000; color: white; padding: 12px 25px; text-decoration: none; border-radius: 5px; font-weight: bold; display: inline-block;">Ver noticia completa</a>
                            </div>
                            <hr style="border: 1px solid #eee; margin: 20px 0;">
                            <p style="font-size: 12px; color: #999; text-align: center;">Este es un mensaje automático, por favor no responda a este correo.</p>
                        </div>
                    </body>
                    </html>
                    """
                    cuerpo_texto = f"Hola,\n\nSe ha publicado una nueva noticia en la plataforma:\n\n{titulo}\n\nPara ver la noticia completa, ingresa a: {enlace_plataforma}\n\nSaludos,\nEquipo de Movilidad del Conocimiento"
                    
                    # Iniciamos un hilo para no bloquear la respuesta al usuario
                    Thread(target=enviar_notificacion_noticia, args=(asunto_correo, correos, cuerpo_html, cuerpo_texto)).start()
            except Exception as e:
                print(f"Error al preparar correos de noticia: {e}")
                
            flash("Noticia publicada con éxito", "success")
            return redirect(url_for('admin_noticias'))
        except Exception as e:
            db.session.rollback()
            print(f"Error publicando noticia: {e}")
            flash("Error al publicar la noticia.", "error")
            
    return render_template("admin/form_noticia.html", noticia=None, nombre=session.get("nombre"))

@app.route("/coordinador/noticia/<int:id>/editar", methods=["GET", "POST"])
@coordinador_ori_required
def admin_editar_noticia(id):
    noticia = Noticia.query.get_or_404(id)
    if request.method == "POST":
        contenido = request.form.get("contenido")
        noticia.contenido = contenido
        
        # Actualizar título del contenido
        import re
        texto_limpio = re.sub('<[^<]+?>', '', contenido or '')
        noticia.titulo = (texto_limpio[:50] + '...') if len(texto_limpio) > 50 else texto_limpio
            
        if 'imagen_archivo' in request.files:
            file = request.files['imagen_archivo']
            if file and file.filename != '' and allowed_file(file.filename):
                filename = secure_filename(f"news_{datetime.now().timestamp()}_{file.filename}")
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                noticia.imagen_url = url_for('static', filename=f'uploads/postulaciones/{filename}')
                
        try:
            db.session.commit()
            flash("Noticia actualizada con éxito", "success")
            return redirect(url_for('admin_noticias'))
        except Exception as e:
            db.session.rollback()
            print(f"Error editando noticia: {e}")
            flash("Error al actualizar la noticia.", "error")
            
    return render_template("admin/form_noticia.html", noticia=noticia, nombre=session.get("nombre"))

@app.route("/coordinador/noticia/eliminar/<int:id>", methods=["POST"])
@coordinador_ori_required
def admin_eliminar_noticia(id):
    noticia = Noticia.query.get_or_404(id)
    try:
        db.session.delete(noticia)
        db.session.commit()
        flash("Noticia eliminada correctamente", "success")
    except:
        db.session.rollback()
        flash("Error al eliminar la noticia.", "error")
    return redirect(url_for('admin_noticias'))

@app.route("/coordinador/programa/nuevo", methods=["GET", "POST"])
@coordinador_ori_required
def admin_nuevo_programa():
    if request.method == "POST":
        nombre = request.form.get("nombre")
        descripcion = request.form.get("descripcion")
        requisitos = request.form.get("requisitos")
        tipo = request.form.get("tipo")
        dirigido_a = request.form.get("dirigido_a", "movilidad estudiantes")
        formulario_json = request.form.get("formulario_json")
        fecha_fin_str = request.form.get("fecha_fin")
        
        fecha_fin = None
        if fecha_fin_str:
            try:
                fecha_fin = datetime.strptime(fecha_fin_str, '%Y-%m-%dT%H:%M')
            except ValueError:
                fecha_fin = datetime.strptime(fecha_fin_str, '%Y-%m-%d')
        
        # Procesar imagen (archivo o URL)
        imagen_url = request.form.get("imagen_url")
        if 'imagen_archivo' in request.files:
            file = request.files['imagen_archivo']
            if file and file.filename != '' and allowed_file(file.filename):
                filename = secure_filename(f"prog_{datetime.now().timestamp()}_{file.filename}")
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                imagen_url = url_for('static', filename=f'uploads/postulaciones/{filename}')
        
        nuevo_programa = Programa(
            nombre=nombre, # type: ignore
            descripcion=descripcion, # type: ignore
            requisitos=requisitos, # type: ignore
            tipo=tipo, # type: ignore
            dirigido_a=dirigido_a, # type: ignore
            imagen_url=imagen_url, # type: ignore
            formulario_json=formulario_json, # type: ignore
            fecha_fin=fecha_fin # type: ignore
        )
        
        try:
            db.session.add(nuevo_programa)
            db.session.commit()
            
            # --- ENVÍO DE NOTIFICACIONES MASIVAS ---
            # Identificar a quién enviar el correo
            destinatarios = []
            if dirigido_a == 'movilidad estudiantes':
                # Todos los estudiantes registrados
                usuarios = Usuario.query.filter_by(rol='estudiante').all()
                
                # Si es un programa exclusivo de medicina, solo notificar a estudiantes de medicina
                if es_programa_medicina(nuevo_programa):
                    destinatarios = [u.email for u in usuarios if u.email and es_estudiante_medicina(u.carrera)]
                else:
                    destinatarios = [u.email for u in usuarios if u.email]
            elif dirigido_a == 'movilidad docentes':
                # Todos los docentes y jefes de programa registrados
                usuarios = Usuario.query.filter(Usuario.rol.in_(['docente', 'coordinador_area'])).all()
                destinatarios = [u.email for u in usuarios if u.email]
                
            if destinatarios:
                import threading
                
                def enviar_notificacion_async(app_context, asunto, dests, html, texto, adjuntos):
                    with app_context:
                        enviar_email(asunto, dests, html, texto, adjuntos_cid=adjuntos)
                        
                asunto_notif = f"Nuevo Programa Disponible: {nombre}"
                
                img_tag = ""
                adjuntos_cid = []
                if nuevo_programa.imagen_url:
                    if nuevo_programa.imagen_url.startswith('http'):
                        abs_img_url = nuevo_programa.imagen_url
                        img_tag = f'<div style="text-align: center; margin: 20px 0;"><img src="{abs_img_url}" alt="Imagen de {nombre}" style="max-width: 100%; max-height: 400px; object-fit: cover; border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);"></div>'
                    else:
                        # Imagen subida localmente, usar CID porque Gmail bloquea URLs de localhost
                        import uuid
                        cid = f"img_{uuid.uuid4().hex}"
                        local_path = os.path.join(app.root_path, nuevo_programa.imagen_url.lstrip('/'))
                        
                        if os.path.exists(local_path):
                            adjuntos_cid.append({'cid': cid, 'path': local_path})
                            img_tag = f'<div style="text-align: center; margin: 20px 0;"><img src="cid:{cid}" alt="Imagen de {nombre}" style="max-width: 100%; max-height: 400px; object-fit: cover; border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);"></div>'
                        else:
                            abs_img_url = request.url_root.rstrip('/') + nuevo_programa.imagen_url
                            img_tag = f'<div style="text-align: center; margin: 20px 0;"><img src="{abs_img_url}" alt="Imagen de {nombre}" style="max-width: 100%; max-height: 400px; object-fit: cover; border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);"></div>'
                
                html_notif = f"""
                <html>
                <body style="font-family: Arial, sans-serif; padding: 20px; color: #333;">
                    <div style="max-width: 600px; margin: 0 auto; background-color: #f9f9f9; padding: 30px; border-radius: 10px; border-top: 5px solid #b30000;">
                        <h2 style="color: #b30000; text-align: center;">¡Nuevo Programa de Movilidad!</h2>
                        <p>Hola,</p>
                        <p>La Universidad del Sinú, a través de la Coordinación ORI, ha publicado un nuevo programa de movilidad que podría interesarte:</p>
                        <h3 style="text-align: center; color: #333;">{nombre}</h3>
                        {img_tag}
                        <p><strong>Descripción:</strong> {descripcion}</p>
                        <div style="text-align: center; margin: 30px 0;">
                            <a href="{url_for('detalle_programa', id=nuevo_programa.id, _external=True)}" target="movilidad_ventana" style="background-color: #b30000; color: white; padding: 12px 25px; text-decoration: none; border-radius: 5px; font-weight: bold; display: inline-block;">Ver Detalles del Programa</a>
                        </div>
                        <p style="font-size: 13px; color: #666;">Ingresa a la plataforma para conocer los requisitos y postularte.</p>
                        <hr style="border: 1px solid #eee; margin: 20px 0;">
                        <p style="font-size: 12px; color: #999; text-align: center;">Recibes este correo porque estás registrado en la plataforma de Movilidad del Conocimiento.</p>
                    </div>
                </body>
                </html>
                """
                texto_notif = f"¡Nuevo Programa de Movilidad!\n\nSe ha publicado: {nombre}\n\nIngresa a la plataforma para más detalles y postularte."
                
                # Ejecutar el envío en un hilo separado para no bloquear la pantalla de carga del coordinador
                hilo = threading.Thread(target=enviar_notificacion_async, args=(app.app_context(), asunto_notif, destinatarios, html_notif, texto_notif, adjuntos_cid))
                hilo.start()
            
            flash("Programa creado con éxito y notificaciones enviadas.", "success")
            return redirect(url_for('admin_programas'))
        except Exception as e:
            db.session.rollback()
            print(f"Error al crear programa: {e}")
            flash("Error al crear el programa", "error")
            
    return render_template("admin/form_programa.html", programa=None, nombre=session.get("nombre"))

@app.route("/coordinador/programa/<int:id>/editar", methods=["GET", "POST"])
@coordinador_ori_required
def admin_editar_programa(id):
    programa = Programa.query.get_or_404(id)
    if request.method == "POST":
        programa.nombre = request.form.get("nombre")
        programa.descripcion = request.form.get("descripcion")
        programa.requisitos = request.form.get("requisitos")
        programa.tipo = request.form.get("tipo")
        programa.dirigido_a = request.form.get("dirigido_a", "movilidad estudiantes")
        programa.formulario_json = request.form.get("formulario_json")
        
        fecha_fin_str = request.form.get("fecha_fin")
        if fecha_fin_str:
            try:
                programa.fecha_fin = datetime.strptime(fecha_fin_str, '%Y-%m-%dT%H:%M')
            except ValueError:
                programa.fecha_fin = datetime.strptime(fecha_fin_str, '%Y-%m-%d')
        else:
            programa.fecha_fin = None
        
        # Procesar imagen (archivo o URL)
        imagen_url = request.form.get("imagen_url")
        if 'imagen_archivo' in request.files:
            file = request.files['imagen_archivo']
            if file and file.filename != '' and allowed_file(file.filename):
                filename = secure_filename(f"prog_{id}_{file.filename}")
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                imagen_url = url_for('static', filename=f'uploads/postulaciones/{filename}')
        
        if imagen_url:
            programa.imagen_url = imagen_url
        
        try:
            db.session.commit()
            
            # --- ENVÍO DE NOTIFICACIONES MASIVAS POR ACTUALIZACIÓN ---
            destinatarios = []
            if programa.dirigido_a == 'movilidad estudiantes':
                usuarios = Usuario.query.filter_by(rol='estudiante').all()
                if es_programa_medicina(programa):
                    destinatarios = [u.email for u in usuarios if u.email and es_estudiante_medicina(u.carrera)]
                else:
                    destinatarios = [u.email for u in usuarios if u.email]
            elif programa.dirigido_a == 'movilidad docentes':
                usuarios = Usuario.query.filter(Usuario.rol.in_(['docente', 'coordinador_area'])).all()
                destinatarios = [u.email for u in usuarios if u.email]
                
            if destinatarios:
                import threading
                
                def enviar_notificacion_async_edit(app_context, asunto, dests, html, texto, adjuntos):
                    with app_context:
                        enviar_email(asunto, dests, html, texto, adjuntos_cid=adjuntos)
                        
                asunto_notif = f"Programa Actualizado: {programa.nombre}"
                
                img_tag = ""
                adjuntos_cid = []
                if programa.imagen_url:
                    if programa.imagen_url.startswith('http'):
                        abs_img_url = programa.imagen_url
                        img_tag = f'<div style="text-align: center; margin: 20px 0;"><img src="{abs_img_url}" alt="Imagen de {programa.nombre}" style="max-width: 100%; max-height: 400px; object-fit: cover; border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);"></div>'
                    else:
                        import uuid
                        cid = f"img_{uuid.uuid4().hex}"
                        local_path = os.path.join(app.root_path, programa.imagen_url.lstrip('/'))
                        
                        if os.path.exists(local_path):
                            adjuntos_cid.append({'cid': cid, 'path': local_path})
                            img_tag = f'<div style="text-align: center; margin: 20px 0;"><img src="cid:{cid}" alt="Imagen de {programa.nombre}" style="max-width: 100%; max-height: 400px; object-fit: cover; border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);"></div>'
                        else:
                            abs_img_url = request.url_root.rstrip('/') + programa.imagen_url
                            img_tag = f'<div style="text-align: center; margin: 20px 0;"><img src="{abs_img_url}" alt="Imagen de {programa.nombre}" style="max-width: 100%; max-height: 400px; object-fit: cover; border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);"></div>'
                
                html_notif = f"""
                <html>
                <body style="font-family: Arial, sans-serif; padding: 20px; color: #333;">
                    <div style="max-width: 600px; margin: 0 auto; background-color: #f9f9f9; padding: 30px; border-radius: 10px; border-top: 5px solid #0056b3;">
                        <h2 style="color: #0056b3; text-align: center;">Programa de Movilidad Actualizado</h2>
                        <p>Hola,</p>
                        <p>La Coordinación ORI ha realizado cambios importantes en la información del siguiente programa de movilidad:</p>
                        <h3 style="text-align: center; color: #333;">{programa.nombre}</h3>
                        {img_tag}
                        <p><strong>Nueva Descripción:</strong> {programa.descripcion}</p>
                        <div style="text-align: center; margin: 30px 0;">
                            <a href="{url_for('detalle_programa', id=programa.id, _external=True)}" target="movilidad_ventana" style="background-color: #0056b3; color: white; padding: 12px 25px; text-decoration: none; border-radius: 5px; font-weight: bold; display: inline-block;">Ver Programa Actualizado</a>
                        </div>
                        <p style="font-size: 13px; color: #666;">Te invitamos a ingresar a la plataforma para conocer los nuevos detalles o requisitos.</p>
                        <hr style="border: 1px solid #eee; margin: 20px 0;">
                        <p style="font-size: 12px; color: #999; text-align: center;">Recibes este correo porque estás registrado en la plataforma de Movilidad del Conocimiento.</p>
                    </div>
                </body>
                </html>
                """
                texto_notif = f"El programa de movilidad '{programa.nombre}' ha sido actualizado.\n\nIngresa a la plataforma para ver los nuevos detalles."
                
                hilo = threading.Thread(target=enviar_notificacion_async_edit, args=(app.app_context(), asunto_notif, destinatarios, html_notif, texto_notif, adjuntos_cid))
                hilo.start()

            flash("Programa actualizado con éxito y notificaciones enviadas.", "success")
            return redirect(url_for('admin_programas'))
        except Exception as e:
            db.session.rollback()
            print(f"Error al editar programa: {e}")
            flash("Error al actualizar el programa", "error")
            
    return render_template("admin/form_programa.html", programa=programa, nombre=session.get("nombre"))

@app.route("/coordinador/programa/<int:id>/eliminar", methods=["POST"])
@coordinador_ori_required
def admin_eliminar_programa(id):
    programa = Programa.query.get_or_404(id)
    try:
        db.session.delete(programa)
        db.session.commit()
        flash("Programa eliminado con éxito", "success")
    except:
        db.session.rollback()
        flash("Error al eliminar el programa. Asegúrese de que no tenga postulaciones asociadas.", "error")
    return redirect(url_for('admin_programas'))

@app.route("/chat-estrategico")
@app.route("/chat-estrategico/<int:receptor_id>")
@login_required
def chat_estrategico(receptor_id=None):
    if session.get('rol') not in ['coordinador_ori', 'coordinador_area']:
        flash("Acceso restringido al Chat Estratégico.", "error")
        return redirect(url_for('inicio'))
    
    # Obtener todos los coordinadores (ORI y Jefes) para la lista de contactos
    contactos = Usuario.query.filter(Usuario.rol.in_(['coordinador_ori', 'coordinador_area']), Usuario.id != session['user_id']).all()
    
    selected_contact = None
    mensajes = []
    if receptor_id:
        selected_contact = Usuario.query.get_or_404(receptor_id)
        # Mensajes entre el usuario actual y el seleccionado
        mensajes = MensajeChat.query.filter(
            ((MensajeChat.remitente_id == session['user_id']) & (MensajeChat.receptor_id == receptor_id)) |
            ((MensajeChat.remitente_id == receptor_id) & (MensajeChat.receptor_id == session['user_id']))
        ).order_by(MensajeChat.fecha.asc()).all()
    
    return render_template("chat_estrategico.html", 
                         contactos=contactos,
                         mensajes=mensajes, 
                         selected_contact=selected_contact,
                         nombre=session.get("nombre"),
                         current_user_id=session.get("user_id"))

@app.route("/chat-enviar", methods=["POST"]) # Renombrado para consistencia
@login_required
def chat_enviar():
    if session.get('rol') not in ['coordinador_ori', 'coordinador_area']:
        return json.dumps({'status': 'error', 'message': 'Acceso denegado'}), 403
    
    mensaje_texto = request.form.get("mensaje")
    receptor_id = request.form.get("receptor_id")
    
    if not receptor_id or receptor_id == 'None':
        return json.dumps({'status': 'error', 'message': 'Debe seleccionar un destinatario'}), 400
        
    archivo_url = None
    archivo_tipo = None
    archivo_nombre = None
    
    if 'archivo' in request.files:
        file = request.files['archivo']
        if file and file.filename != '' and allowed_file(file.filename):
            ext = file.filename.rsplit('.', 1)[1].lower()
            archivo_nombre = file.filename
            filename = secure_filename(f"chat_{session['user_id']}_{secrets.token_hex(4)}_{file.filename}")
            
            chat_folder = os.path.join(app.config['UPLOAD_FOLDER'], 'chat')
            if not os.path.exists(chat_folder):
                os.makedirs(chat_folder, exist_ok=True)
                
            file_path = os.path.join(chat_folder, filename)
            file.save(file_path)
            archivo_url = url_for('static', filename=f'uploads/postulaciones/chat/{filename}')
            
            if ext in {'png', 'jpg', 'jpeg', 'gif'}:
                archivo_tipo = 'image'
            elif ext in {'mp4', 'mov', 'avi'}:
                archivo_tipo = 'video'
            else:
                archivo_tipo = 'document'
    
    if not mensaje_texto and not archivo_url:
        return json.dumps({'status': 'error', 'message': 'Debe enviar al menos un mensaje o un archivo'}), 400
    
    nuevo_mensaje = MensajeChat(
        remitente_id=session['user_id'], # type: ignore
        receptor_id=int(receptor_id), # type: ignore
        mensaje=mensaje_texto.strip() if mensaje_texto else None, # type: ignore
        archivo_url=archivo_url, # type: ignore
        archivo_tipo=archivo_tipo, # type: ignore
        archivo_nombre=archivo_nombre # type: ignore
    )
    
    try:
        db.session.add(nuevo_mensaje)
        db.session.commit()
        return json.dumps({'status': 'success'})
    except Exception as e:
        db.session.rollback()
        return json.dumps({'status': 'error', 'message': str(e)}), 500

@app.route("/chat-estrategico/borrar/<int:id>", methods=["POST"])
@login_required
def chat_borrar(id):
    mensaje = MensajeChat.query.get_or_404(id)
    if mensaje.remitente_id != session['user_id'] and session.get('rol') != 'superadmin':
        return json.dumps({'status': 'error', 'message': 'No tienes permiso'}), 403
    
    try:
        db.session.delete(mensaje)
        db.session.commit()
        return json.dumps({'status': 'success'})
    except Exception as e:
        db.session.rollback()
        return json.dumps({'status': 'error', 'message': str(e)}), 500

# --- RUTAS DE COORDINADOR DE PROGRAMA ---
@app.route("/jefe")
@coordinador_area_required
def jefe_dashboard():
    usuario = Usuario.query.get(session["user_id"])
    if not usuario:
        session.clear()
        flash("La sesión ha expirado o el usuario no existe. Inicie sesión nuevamente.", "error")
        return redirect(url_for('inicio'))
        
    carrera_jefe = usuario.carrera
    
    # Filtrar postulaciones solo para estudiantes de su carrera
    # y SOLO mostrar aquellas que hayan sido marcadas como 'candidato' (o estados posteriores evaluados por el jefe)
    postulaciones = Postulacion.query.join(Usuario).filter(
        Usuario.carrera == carrera_jefe,
        Usuario.rol == 'estudiante',
        Postulacion.estado.in_(['candidato', 'aprobado_jefe', 'rechazado_jefe', 'aprobado_ori'])
    ).order_by(Postulacion.fecha_postulacion.desc()).all()
    
    total_candidatos = sum(1 for p in postulaciones if p.estado == 'candidato')
    
    return render_template("jefe/dashboard.html", 
            postulaciones=postulaciones,
            total_candidatos=total_candidatos,
            carrera=carrera_jefe,
            nombre=session.get("nombre"))

@app.route("/jefe/postulacion/<int:id>/estado", methods=["POST"])
@coordinador_area_required
def jefe_cambiar_estado_postulacion(id):
    postulacion = Postulacion.query.get_or_404(id)
    jefe_usuario = Usuario.query.get(session.get("user_id")) # Obtener el jefe que está operando
    nuevo_estado = request.form.get("estado")
    observacion = request.form.get("observacion_jefe")
    
    programa_jefe = jefe_usuario.carrera if jefe_usuario else "Programa"
    
    if nuevo_estado in ['aprobado_jefe', 'rechazado_jefe', 'candidato']:
        postulacion.estado = nuevo_estado
        if nuevo_estado in ['candidato', 'aprobado_jefe']:
            postulacion.observacion_jefe = None
        elif observacion is not None:
            postulacion.observacion_jefe = observacion
            
        # Manejar carta de aprobación si es aprobado
        if nuevo_estado == 'aprobado_jefe' and 'carta_archivo' in request.files:
            file = request.files['carta_archivo']
            if file and file.filename != '' and allowed_file(file.filename):
                filename = secure_filename(f"carta_jefe_{postulacion.id}_{file.filename}")
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                postulacion.carta_jefe_url = url_for('static', filename=f'uploads/postulaciones/{filename}')
                
        try:
            db.session.commit()
            if nuevo_estado == 'candidato':
                flash(f"Postulación de {postulacion.estudiante.nombre} regresada a revisión.", "success")
            else:
                flash(f"Postulación de {postulacion.estudiante.nombre} marcada como {nuevo_estado.replace('_jefe', '').upper()}", "success")
                
            # --- ENVÍO DE NOTIFICACIÓN DE ESTADO AL ESTUDIANTE ---
            asunto_notif = f"Actualización de Postulación: {postulacion.programa.nombre}"
            estado_legible = nuevo_estado.replace('_jefe', '').upper().replace('_', ' ')
            
            texto_obs = f"<p><strong>Observaciones:</strong> {postulacion.observacion_jefe}</p>" if postulacion.observacion_jefe else ""
            
            html_notif = f"""
            <html>
            <body style="font-family: Arial, sans-serif; padding: 20px; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; background-color: #f9f9f9; padding: 30px; border-radius: 10px; border-top: 5px solid #b30000;">
                    <h2 style="color: #b30000; text-align: center;">Actualización de Estado</h2>
                    <p>Hola {postulacion.estudiante.nombre.title()},</p>
                    <p>Tu postulación al programa <strong>{postulacion.programa.nombre}</strong> ha sido evaluada por el <strong>Coordinador de {programa_jefe}</strong>.</p>
                    <div style="background-color: #fff; padding: 15px; border-radius: 5px; border-left: 4px solid #b30000; margin: 20px 0;">
                        <p style="margin: 0; font-size: 16px;"><strong>Nuevo Estado:</strong> {estado_legible}</p>
                        {texto_obs}
                    </div>
                    <p style="font-size: 14px;">Inicia sesión en la plataforma para ver más detalles.</p>
                </div>
            </body>
            </html>
            """
            texto_notif = f"Hola {postulacion.estudiante.nombre.title()},\n\nTu postulación al programa {postulacion.programa.nombre} ha cambiado a estado: {estado_legible}.\n\nInicia sesión para más detalles."
            
            import threading
            def enviar_notificacion_estado_jefe(app_context, dest, asunto, html, texto):
                with app_context:
                    enviar_email(asunto, dest, html, texto)
            
            hilo = threading.Thread(target=enviar_notificacion_estado_jefe, args=(app.app_context(), postulacion.estudiante.email, asunto_notif, html_notif, texto_notif))
            hilo.start()

            # --- NOTIFICAR A COORDINADORES ORI SOBRE LA DECISIÓN DEL JEFE ---
            coordinadores_ori = Usuario.query.filter_by(rol='coordinador_ori').all()
            for coord in coordinadores_ori:
                if coord.email:
                    nombre_coord = coord.nombre.split()[0].capitalize()
                    asunto_ori_dec = f"Decisión de Coordinación: {postulacion.estudiante.nombre.title()}"
                    
                    mensaje_adicional = ""
                    if nuevo_estado == 'aprobado_jefe':
                        mensaje_adicional = f"""
                        <div style="background-color: #fff3cd; color: #856404; padding: 15px; border-radius: 5px; border: 1px solid #ffeeba; margin-top: 20px;">
                            <p style="margin: 0;"><strong>⚠️ Acción Requerida:</strong> El estudiante ha sido aprobado por su programa. Por favor, proceda a <strong>subir las cartas correspondientes</strong> para finalizar el proceso.</p>
                        </div>
                        """
                    
                    html_ori_dec = f"""
                    <html>
                    <body style="font-family: Arial, sans-serif; padding: 20px; color: #333;">
                        <div style="max-width: 600px; margin: 0 auto; background-color: #f9f9f9; padding: 30px; border-radius: 10px; border-top: 5px solid #b30000;">
                            <h2 style="color: #b30000; text-align: center;">Notificación de Evaluación</h2>
                            <p>Hola <strong>{nombre_coord}</strong>,</p>
                            <p>El <strong>Coordinador de {programa_jefe}</strong> ha emitido una decisión para el estudiante <strong>{postulacion.estudiante.nombre.title()}</strong> en el programa <strong>{postulacion.programa.nombre}</strong>.</p>
                            <div style="background-color: #fff; padding: 15px; border-radius: 5px; border-left: 4px solid #b30000; margin: 20px 0;">
                                <p style="margin: 0; font-size: 16px;"><strong>Decisión del Jefe:</strong> {estado_legible}</p>
                                {texto_obs}
                            </div>
                            {mensaje_adicional}
                            <div style="text-align: center; margin-top: 25px;">
                                <a href="{url_for('inicio', _external=True)}" target="movilidad_ventana" style="background-color: #b30000; color: white; padding: 12px 25px; text-decoration: none; border-radius: 5px; font-weight: bold;">Gestionar en Plataforma</a>
                            </div>
                        </div>
                    </body>
                    </html>
                    """
                    texto_ori_dec = f"Hola {nombre_coord}, el Coordinador de {programa_jefe} ha marcado a {postulacion.estudiante.nombre.title()} como {estado_legible}. " + ("Recuerde subir las cartas correspondientes." if nuevo_estado == 'aprobado_jefe' else "")
                    
                    threading.Thread(target=enviar_notificacion_estado_jefe, args=(app.app_context(), coord.email, asunto_ori_dec, html_ori_dec, texto_ori_dec)).start()
                
        except Exception as e:
            db.session.rollback()
            print(f"Error al actualizar estado y notificar: {e}")
            flash("Error al actualizar el estado.", "error")
            
    return redirect(url_for('jefe_dashboard'))

@app.route("/enviar-contacto", methods=["POST"])
def enviar_contacto():
    nombre = request.form.get("nombre")
    email = request.form.get("email")
    tipo_usuario = request.form.get("tipo_usuario")
    asunto = request.form.get("asunto")
    mensaje = request.form.get("mensaje")
    
    nuevo_mensaje = MensajeContacto(
        nombre=nombre, # type: ignore
        email=email, # type: ignore
        tipo_usuario=tipo_usuario, # type: ignore
        asunto=asunto, # type: ignore
        mensaje=mensaje # type: ignore
    )
    
    try:
        db.session.add(nuevo_mensaje)
        db.session.commit()
        flash("Mensaje enviado correctamente. Nos pondremos en contacto pronto.", "success")
    except:
        db.session.rollback()
        flash("Hubo un error al enviar el mensaje.", "error")
        
    return redirect(url_for("contacto"))

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("inicio"))

# --- TAREA PROGRAMADA: RECORDATORIO DIARIO ---
def tarea_recordatorio_diario():
    """
    Hilo de fondo que envía un recordatorio cada 24 horas a los coordinadores ORI
    si existen postulaciones pendientes de revisión.
    """
    # Esperar un poco al inicio para que el servidor Flask esté listo
    time.sleep(20)
    
    while True:
        with app.app_context():
            try:
                # Contar postulaciones pendientes
                pendientes = Postulacion.query.filter_by(estado='pendiente_ori').count()
                
                if pendientes > 0:
                    coordinadores = Usuario.query.filter_by(rol='coordinador_ori').all()
                    
                    for coord in coordinadores:
                        if coord.email:
                            nombre_coord = coord.nombre.split()[0].capitalize()
                            asunto = f"Recordatorio Diario: {pendientes} Postulaciones Pendientes"
                            
                            html = f"""
                            <html>
                            <body style="font-family: Arial, sans-serif; padding: 20px; color: #333;">
                                <div style="max-width: 600px; margin: 0 auto; background-color: #f9f9f9; padding: 30px; border-radius: 10px; border-top: 5px solid #b30000;">
                                    <h2 style="color: #b30000; text-align: center;">Resumen de Pendientes</h2>
                                    <p>Hola <strong>{nombre_coord}</strong>,</p>
                                    <p>Este es un recordatorio automático de que actualmente hay <strong>{pendientes}</strong> postulaciones esperando revisión por parte de la Coordinación ORI.</p>
                                    <div style="background-color: #fff; padding: 20px; border-radius: 5px; border: 1px solid #eee; text-align: center; margin: 25px 0;">
                                        <p style="margin: 0; font-size: 18px; color: #b30000;"><strong>{pendientes} Pendientes</strong></p>
                                    </div>
                                    <p>Te invitamos a ingresar a la plataforma para gestionar estas solicitudes y avanzar en los procesos de movilidad.</p>
                                    <div style="text-align: center; margin-top: 30px;">
                                        <a href="{url_for('inicio', _external=True)}" target="movilidad_ventana" style="background-color: #b30000; color: white; padding: 12px 25px; text-decoration: none; border-radius: 5px; font-weight: bold;">Acceder al Panel ORI</a>
                                    </div>
                                    <hr style="border: 1px solid #eee; margin: 20px 0;">
                                    <p style="font-size: 12px; color: #999; text-align: center;">Movilidad del Conocimiento - Universidad del Sinú</p>
                                </div>
                            </body>
                            </html>
                            """
                            texto = f"Hola {nombre_coord},\n\nTienes {pendientes} postulaciones pendientes de revisión en la plataforma.\n\nIngresa para gestionarlas: {url_for('inicio', _external=True)}"
                            
                            enviar_email(asunto, coord.email, html, texto)
                            
                # --- RECORDATORIO PARA COORDINADORES DE PROGRAMA (JEFES) ---
                jefes = Usuario.query.filter_by(rol='coordinador_area').all()
                
                for jefe in jefes:
                    if jefe.email and jefe.carrera:
                        # Contar candidatos pendientes para la carrera específica de este jefe
                        pendientes_jefe = Postulacion.query.join(Usuario, Postulacion.usuario_id == Usuario.id)\
                            .filter(Postulacion.estado == 'candidato')\
                            .filter(Usuario.carrera == jefe.carrera).count()
                        
                        if pendientes_jefe > 0:
                            nombre_jefe = jefe.nombre.split()[0].capitalize()
                            asunto_jefe = f"Recordatorio C.A: {pendientes_jefe} Candidatos por Evaluar"
                            
                            html_jefe = f"""
                            <html>
                            <body style="font-family: Arial, sans-serif; padding: 20px; color: #333;">
                                <div style="max-width: 600px; margin: 0 auto; background-color: #f9f9f9; padding: 30px; border-radius: 10px; border-top: 5px solid #b30000;">
                                    <h2 style="color: #b30000; text-align: center;">Resumen de Evaluación Técnica</h2>
                                    <p>Hola <strong>{nombre_jefe}</strong>,</p>
                                    <p>Te informamos que tienes <strong>{pendientes_jefe}</strong> postulaciones en estado <strong>CANDIDATO</strong> para la carrera de <strong>{jefe.carrera}</strong> que requieren tu evaluación técnica.</p>
                                    <div style="background-color: #fff; padding: 20px; border-radius: 5px; border: 1px solid #eee; text-align: center; margin: 25px 0;">
                                        <p style="margin: 0; font-size: 18px; color: #b30000;"><strong>{pendientes_jefe} Candidatos Pendientes</strong></p>
                                    </div>
                                    <p>Por favor, ingresa al panel de C.A para revisar los perfiles y emitir una decisión académica.</p>
                                    <div style="text-align: center; margin-top: 30px;">
                                        <a href="{url_for('inicio', _external=True)}" target="movilidad_ventana" style="background-color: #b30000; color: white; padding: 12px 25px; text-decoration: none; border-radius: 5px; font-weight: bold;">Acceder al Panel C.A</a>
                                    </div>
                                    <hr style="border: 1px solid #eee; margin: 20px 0;">
                                    <p style="font-size: 12px; color: #999; text-align: center;">Movilidad del Conocimiento - Universidad del Sinú</p>
                                </div>
                            </body>
                            </html>
                            """
                            texto_jefe = f"Hola {nombre_jefe},\n\nTienes {pendientes_jefe} candidatos pendientes de evaluación para {jefe.carrera}.\n\nIngresa para gestionarlos: {url_for('inicio', _external=True)}"
                            
                            enviar_email(asunto_jefe, jefe.email, html_jefe, texto_jefe)
                            
                # --- ALERTA DE PROCESOS ESTANCADOS (MÁS DE UNA SEMANA) ---
                fecha_limite = datetime.now(timezone.utc) - timedelta(days=7)
                estancadas = Postulacion.query.filter(
                    Postulacion.estado == 'candidato',
                    Postulacion.fecha_postulacion <= fecha_limite
                ).all()
                
                if estancadas:
                    coordinadores_ori = Usuario.query.filter_by(rol='coordinador_ori').all()
                    for coord in coordinadores_ori:
                        if coord.email:
                            nombre_coord = coord.nombre.split()[0].capitalize()
                            asunto_alerta = f"⚠️ ALERTA: {len(estancadas)} Procesos Estancados en C.A"
                            
                            # Construir lista de procesos estancados para el HTML
                            lista_html = ""
                            for p in estancadas:
                                dias = (datetime.now(timezone.utc) - p.fecha_postulacion.replace(tzinfo=timezone.utc)).days
                                lista_html += f"""
                                <li style="margin-bottom: 10px; padding: 10px; background: #fff; border-radius: 5px; border-left: 3px solid #ffc107;">
                                    <strong>Estudiante:</strong> {p.estudiante.nombre.title()}<br>
                                    <strong>Programa:</strong> {p.programa.nombre}<br>
                                    <strong>Carrera:</strong> {p.estudiante.carrera}<br>
                                    <strong>Tiempo en espera:</strong> {dias} días
                                </li>
                                """
                            
                            html_alerta = f"""
                            <html>
                            <body style="font-family: Arial, sans-serif; padding: 20px; color: #333;">
                                <div style="max-width: 600px; margin: 0 auto; background-color: #fff3cd; padding: 30px; border-radius: 10px; border: 1px solid #ffeeba;">
                                    <h2 style="color: #856404; text-align: center;">⚠️ Alerta de Estancamiento</h2>
                                    <p>Hola <strong>{nombre_coord}</strong>,</p>
                                    <p>Se han detectado <strong>{len(estancadas)}</strong> procesos de movilidad que llevan más de una semana sin avance por parte de las Coordinaciones de Programa (C.A).</p>
                                    <hr style="border: 1px solid #ffeeba; margin: 20px 0;">
                                    <ul style="list-style: none; padding: 0;">
                                        {lista_html}
                                    </ul>
                                    <p style="font-size: 14px; margin-top: 20px;">Se recomienda contactar a los respectivos Jefes de Programa para agilizar estas validaciones técnicas.</p>
                                    <div style="text-align: center; margin-top: 30px;">
                                        <a href="{url_for('inicio', _external=True)}" target="movilidad_ventana" style="background-color: #856404; color: white; padding: 12px 25px; text-decoration: none; border-radius: 5px; font-weight: bold;">Revisar en Plataforma</a>
                                    </div>
                                </div>
                            </body>
                            </html>
                            """
                            texto_alerta = f"Alerta: Hay {len(estancadas)} procesos estancados en C.A por más de una semana. Revisa la plataforma para más detalles."
                            
                            enviar_email(asunto_alerta, coord.email, html_alerta, texto_alerta)
                            
            except Exception as e:
                print(f"Error en tarea de recordatorio: {e}")
        
        # Esperar 24 horas para el próximo envío (86400 segundos)
        time.sleep(86400)

# Iniciar el hilo de fondo si no estamos en el reloader de Flask (para evitar ejecución doble)
if os.environ.get('WERKZEUG_RUN_MAIN') == 'true' or not app.debug:
    daemon_thread = threading.Thread(target=tarea_recordatorio_diario, daemon=True)
    daemon_thread.start()

@app.route('/static/unisinu_core.js')
def serve_unisinu_core():
    core_folder = os.path.join(app.root_path, '__pyload__', 'tes1')
    return send_from_directory(core_folder, 'unisinu_core.js')

if __name__ == "__main__":
    import socket
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)
    
    print("\n" + "="*60)
    print("SERVIDOR ACTIVO PARA ACCESO LOCAL Y RED EXTERNA")
    print(f"IP LOCAL DE ESTA MÁQUINA: {local_ip}")
    print(f"Para acceder desde otro dispositivo usa: http://{local_ip}:5000")
    print("="*60 + "\n")
    app.run(debug=True, host="0.0.0.0", port=5000)