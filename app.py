from flask import Flask, render_template, request, redirect, url_for, flash, make_response, jsonify
from models.orm_models import Database, Alumno, Grado, Municipio, Asunto, Ticket, Login, Cargo
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy import func
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from io import BytesIO
import qrcode
from sqlalchemy.orm import joinedload

app = Flask(__name__)
app.secret_key = 'juannumbres12'  # Clave secreta para los mensajes flash y otras funcionalidades de seguridad
db = Database()  # Instancia de la base de datos

# Nueva ruta para el menú inicial
@app.route('/menu_inicial', methods=['GET'])
def menu_inicial():
    return render_template('menu_inicial.html')

# Modificar la ruta raíz para que redirija al menú inicial
@app.route('/')
def root():
    return redirect(url_for('menu_inicial'))

# Ruta principal para el menú de opciones
@app.route('/menu_alumno', methods=['GET'])
def menu_alumno():
    return render_template('menu_alumno.html')

# Página para el registro de alumnos
@app.route('/registrar_alumno', methods=['GET'])
def index():
    session = db.get_session()

    grados = session.query(Grado).all()  # Obtener todos los grados
    municipios = session.query(Municipio).all()  # Obtener todos los municipios
    asuntos = session.query(Asunto).all()  # Obtener todos los asuntos

    session.close()
    return render_template('register_alumno.html', grados=grados, municipios=municipios, asuntos=asuntos)

# Verificar si el alumno ya está registrado
@app.route('/check_alumno', methods=['POST'])
def check_alumno():
    session = db.get_session()

    # Cambiar request.json a request.form
    nombre = request.form.get('nombre')
    primerApe = request.form.get('primerApe')
    segundoApe = request.form.get('segundoApe', '')

    # Verificar que los datos no sean None
    if not nombre or not primerApe:
        flash("Nombre y Primer Apellido son obligatorios.", "error")
        session.close()
        return redirect(url_for('index'))

    # Buscar si el alumno ya está registrado
    alumno_existente = session.query(Alumno).filter(
        Alumno.nombre == nombre,
        Alumno.primerApe == primerApe,
        Alumno.segundoApe == segundoApe
    ).first()

    if alumno_existente:
        # Obtener la información del ticket asociado al alumno
        ticket_existente = session.query(Ticket).filter_by(idAlumno=alumno_existente.idAlumno).first()

        if ticket_existente:
            mensaje = f"El alumno {alumno_existente.nombre} {alumno_existente.primerApe} {alumno_existente.segundoApe} ya está registrado con el ticket número {ticket_existente.ordTicket}."
        else:
            mensaje = f"El alumno {alumno_existente.nombre} {alumno_existente.primerApe} {alumno_existente.segundoApe} ya está registrado, pero no tiene ticket asignado."

        session.close()
        return jsonify({'exists': True, 'message': mensaje}), 200
    else:
        session.close()
        return jsonify({'exists': False}), 200

# Ruta para registrar al alumno
@app.route('/register_alumno', methods=['POST'])
def register_alumno():
    session = db.get_session()

    nombre = request.form['nombre']
    primerApe = request.form['primerApe']
    segundoApe = request.form.get('segundoApe', '')
    telefono = request.form['telefono']
    correo = request.form['correo']
    curp = request.form['curp']  # Captura del campo CURP
    idGrado = request.form['idGrado']
    idMunicipio = request.form['idMunicipio']
    idAsunto = request.form['idAsunto']

    # Validaciones del lado del servidor
    if not nombre or not primerApe or not telefono or not correo or not curp or not idGrado or not idMunicipio or not idAsunto:
        flash("Todos los campos obligatorios deben ser completados.", "error")
        return redirect(url_for('index'))

    try:
        # Verificar si el alumno ya está registrado en el servidor
        alumno_existente = session.query(Alumno).filter_by(
            nombre=nombre,
            primerApe=primerApe,
            segundoApe=segundoApe
        ).first()

        if alumno_existente:
            flash(f"Error: El alumno con nombre '{nombre} {primerApe} {segundoApe}' ya está registrado.", "error")
            return redirect(url_for('index'))

        # Crear un nuevo alumno si no está duplicado
        nuevo_alumno = Alumno(
            nombre=nombre,
            primerApe=primerApe,
            segundoApe=segundoApe,
            telefono=telefono,
            correo=correo,
            curp=curp,  # Agregar CURP en el registro
            idGrado=idGrado,
            idMunicipio=idMunicipio,
            idAsunto=idAsunto
        )
        session.add(nuevo_alumno)
        session.commit()

        # Obtener el ID del nuevo alumno
        alumno_id = nuevo_alumno.idAlumno

        # Asignar el turno basado en el municipio seleccionado
        max_turno = session.query(func.max(Ticket.ordTicket)).filter(Ticket.idMunicipio == idMunicipio).scalar() or 0
        nuevo_turno = max_turno + 1

        # Crear un nuevo ticket
        nuevo_ticket = Ticket(
            ordTicket=nuevo_turno,
            idMunicipio=idMunicipio,
            idAlumno=alumno_id,
            idAsunto=idAsunto,
            fecha=func.now(),
            idestatus=1  # Estado inicial de "Pendiente"
        )
        session.add(nuevo_ticket)
        session.commit()

        # Flash message and redirect to generate PDF
        flash('Alumno registrado exitosamente. Se generará el PDF con el ticket.', 'success')
        return redirect(url_for('generar_pdf', alumno_id=alumno_id))

    except IntegrityError:
        session.rollback()
        flash("Error: Este registro ya existe en la base de datos. No se puede duplicar la clave primaria.", "error")
        return redirect(url_for('index'))

    except SQLAlchemyError as e:
        session.rollback()
        app.logger.error(f"Error al registrar el alumno o ticket: {e}")
        flash("Error al registrar el alumno. Por favor, inténtelo de nuevo.", "error")
        return redirect(url_for('index'))

    finally:
        session.close()

# Ruta para generar el PDF con QR
@app.route('/generar_pdf/<int:alumno_id>')
def generar_pdf(alumno_id):
    session = db.get_session()

    # Obtener los datos del alumno
    alumno = session.query(Alumno).filter_by(idAlumno=alumno_id).first()
    ticket = session.query(Ticket).filter_by(idAlumno=alumno_id).first()

    # Si el alumno o el ticket no existen, redirigir al índice
    if not alumno or not ticket:
        flash("Error: Alumno o ticket no encontrado.", "error")
        session.close()
        return redirect(url_for('index'))

    # Crear un buffer en memoria para el PDF
    buffer = BytesIO()

    # Crear el PDF en el buffer
    pdf = canvas.Canvas(buffer, pagesize=letter)
    pdf.setFont("Helvetica", 12)

    # Añadir contenido al PDF
    pdf.drawString(100, 750, f"Ticket de Registro para: {alumno.nombre} {alumno.primerApe} {alumno.segundoApe}")
    pdf.drawString(100, 730, f"Teléfono: {alumno.telefono}")
    pdf.drawString(100, 710, f"Correo: {alumno.correo}")
    pdf.drawString(100, 690, f"CURP: {alumno.curp if alumno.curp else 'No disponible'}")
    pdf.drawString(100, 670, f"Grado: {alumno.idGrado}")
    pdf.drawString(100, 650, f"Municipio: {alumno.idMunicipio}")
    pdf.drawString(100, 630, f"Asunto: {alumno.idAsunto}")
    pdf.drawString(100, 610, f"Número de Ticket: {ticket.ordTicket}")

    # Generar el código QR con la CURP del alumno
    qr_code_img = generate_qr_code(alumno.curp)

    # Añadir el código QR al PDF
    pdf.drawImage(ImageReader(qr_code_img), 400, 600, 100, 100)  # Posición y tamaño del QR en el PDF

    pdf.showPage()
    pdf.save()

    # Mover el buffer al principio para que pueda ser leído
    buffer.seek(0)

    # Crear la respuesta con el contenido del PDF
    response = make_response(buffer.getvalue())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename="ticket_alumno_{alumno_id}.pdf"'

    session.close()

    return response

# Función para generar el código QR
def generate_qr_code(data):
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)

    # Crear una imagen en memoria
    img = qr.make_image(fill='black', back_color='white')

    # Guardar la imagen en un buffer de memoria
    img_buffer = BytesIO()
    img.save(img_buffer)
    img_buffer.seek(0)

    return img_buffer

# Ruta para buscar un alumno registrado y mostrar sus datos
@app.route('/buscar_alumno', methods=['GET', 'POST'])
def buscar_alumno():
    session = db.get_session()

    if request.method == 'POST':
        curp = request.form['curp']
        ordTicket = request.form['ordTicket']

        # Buscar al alumno por su CURP y número de turno, precargando las relaciones de grado, municipio y asunto
        alumno = session.query(Alumno).options(
            joinedload(Alumno.grado),
            joinedload(Alumno.municipio),
            joinedload(Alumno.asunto)
        ).join(Ticket).filter(
            Alumno.curp == curp,
            Ticket.ordTicket == ordTicket
        ).first()

        if alumno:
            # Renderizar la página intermedia que muestra los datos del alumno
            response = render_template('datos_alumno.html', alumno=alumno)
            session.close()
            return response
        else:
            flash("No se encontró ningún registro con los datos proporcionados.", "error")
            session.close()
            return redirect(url_for('buscar_alumno'))

    session.close()
    # Si es un GET, simplemente muestra el formulario para buscar el alumno
    return render_template('buscar_registro.html')

# Ruta para mostrar el formulario de modificación del alumno
@app.route('/modificar_alumno/<int:idAlumno>', methods=['GET'])
def modificar_alumno(idAlumno):
    session = db.get_session()

    # Obtener los datos del alumno por su ID
    alumno = session.query(Alumno).filter_by(idAlumno=idAlumno).first()

    if alumno:
        grados = session.query(Grado).all()
        municipios = session.query(Municipio).all()
        asuntos = session.query(Asunto).all()

        response = render_template('modificar_alumno.html', alumno=alumno, grados=grados, municipios=municipios, asuntos=asuntos)
        session.close()
        return response
    else:
        flash("No se encontró ningún registro para modificar.", "error")
        session.close()
        return redirect(url_for('buscar_alumno'))

@app.route('/actualizar_alumno/<int:idAlumno>', methods=['POST'])
def actualizar_alumno(idAlumno):
    session = db.get_session()

    # Obtener los datos actualizados desde el formulario
    nombre = request.form['nombre']
    primerApe = request.form['primerApe']
    segundoApe = request.form.get('segundoApe', '')
    telefono = request.form['telefono']
    correo = request.form['correo']
    idGrado = request.form['idGrado']
    idMunicipio = request.form['idMunicipio']
    idAsunto = request.form['idAsunto']

    try:
        # Buscar al alumno por su ID
        alumno = session.query(Alumno).filter_by(idAlumno=idAlumno).first()

        if alumno:
            # Guardar el municipio anterior
            municipio_anterior = alumno.idMunicipio

            # Actualizar los datos del alumno
            alumno.nombre = nombre
            alumno.primerApe = primerApe
            alumno.segundoApe = segundoApe
            alumno.telefono = telefono
            alumno.correo = correo
            alumno.idGrado = idGrado
            alumno.idMunicipio = idMunicipio
            alumno.idAsunto = idAsunto

            # Si el municipio ha cambiado, recalcular el turno
            ticket = session.query(Ticket).filter_by(idAlumno=idAlumno).first()
            if ticket and municipio_anterior != idMunicipio:
                # Obtener el nuevo turno para el nuevo municipio
                max_turno = session.query(func.max(Ticket.ordTicket)).filter(Ticket.idMunicipio == idMunicipio).scalar() or 0
                nuevo_turno = max_turno + 1
                ticket.ordTicket = nuevo_turno
                ticket.idMunicipio = idMunicipio  # Actualizar también el municipio en el ticket

            session.commit()

            # Flash para notificación de éxito
            flash("Datos actualizados exitosamente. El PDF se descargará automáticamente.", "success")

            # Redirigir a la ruta para generar el PDF
            session.close()
            return redirect(url_for('generar_pdf', alumno_id=alumno.idAlumno))

        else:
            flash("No se encontró el alumno a modificar.", "error")

    except SQLAlchemyError as e:
        session.rollback()
        app.logger.error(f"Error al actualizar los datos: {e}")
        flash("Error al actualizar los datos. Por favor, inténtelo de nuevo.", "error")

    finally:
        session.close()

    return redirect(url_for('buscar_alumno'))

######## Administrador ########
@app.route('/menu_admin')
def menu_admin():
    return render_template('menu_admin.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    session = db.get_session()

    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        nombre = request.form['nombre']
        primerAp = request.form['primerAp']
        segundoAp = request.form['segundoAp']
        idCargo = request.form.get('idCargo', None)

        # Verificar si el email ya está registrado
        existing_user = session.query(Login).filter_by(email=email).first()
        if existing_user:
            flash('El email ya está registrado.', 'danger')
            session.close()
            return redirect(url_for('register'))

        # Crear un nuevo usuario
        new_user = Login(
            email=email,
            nombre=nombre,
            primerAp=primerAp,
            segundoAp=segundoAp,
            idCargo=idCargo
        )
        new_user.set_password(password)

        try:
            session.add(new_user)
            session.commit()
            flash('Usuario registrado exitosamente.', 'success')
            session.close()
            return redirect(url_for('login'))
        except SQLAlchemyError as e:
            session.rollback()
            app.logger.error(f'Error al registrar usuario: {e}')
            flash('Error al registrar usuario. Por favor, inténtelo de nuevo.', 'danger')
        finally:
            session.close()
    else:
        cargos = session.query(Cargo).all()  # Obtener todos los cargos para el formulario
        session.close()
        return render_template('register.html', cargos=cargos)

# Ruta para iniciar sesión
@app.route('/login', methods=['GET', 'POST'])
def login():
    session = db.get_session()

    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        user = session.query(Login).filter_by(email=email).first()

        if user and user.check_password(password):
            flash('Inicio de sesión exitoso.', 'success')
            session.close()
            return redirect(url_for('dashboard'))
        else:
            flash('Email o contraseña incorrectos.', 'danger')
            session.close()
            return redirect(url_for('login'))

    session.close()
    return render_template('login.html')

# Ruta de ejemplo para el dashboard
@app.route('/dashboard')
def dashboard():
    return "Bienvenido al Dashboard."

if __name__ == '__main__':
    app.run(debug=True)
