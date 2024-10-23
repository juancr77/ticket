from flask import Flask, render_template, request, redirect, url_for, flash, make_response, jsonify
from models.models import Database, Alumno, Grado, Municipio, Asunto, Ticket
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


# Ruta principal para el menú de opciones
@app.route('/menu_alumno', methods=['GET'])
def menu_alumno():
    return render_template('menu_alumno.html')


# Redirigir la ruta raíz al menú de alumno
@app.route('/')
def root():
    return redirect(url_for('menu_alumno'))


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

    nombre = request.json.get('nombre')
    primerApe = request.json.get('primerApe')
    segundoApe = request.json.get('segundoApe', '')

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

        # Respuesta exitosa con el ID del alumno registrado
        return jsonify({'alumno_id': alumno_id})

    except IntegrityError:
        session.rollback()
        flash("Error: Este registro ya existe en la base de datos. No se puede duplicar la clave primaria.", "error")
        return redirect(url_for('index'))

    except SQLAlchemyError as e:
        session.rollback()
        flash(f"Error al registrar el alumno o ticket: {e}", "error")
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
    pdf.drawString(100, 690, f"CURP: {alumno.curp}")  # Añadir la CURP al PDF
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

    # Cerrar la sesión de la base de datos
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
            session.close()
            # Renderizar la página intermedia que muestra los datos del alumno
            return render_template('datos_alumno.html', alumno=alumno)
        else:
            flash("No se encontró ningún registro con los datos proporcionados.", "error")
            session.close()
            return redirect(url_for('buscar_alumno'))

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

        session.close()
        return render_template('modificar_alumno.html', alumno=alumno, grados=grados, municipios=municipios, asuntos=asuntos)
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
            flash("Datos actualizados exitosamente.", "success")
        else:
            flash("No se encontró el alumno a modificar.", "error")

    except SQLAlchemyError as e:
        session.rollback()
        flash(f"Error al actualizar los datos: {e}", "error")

    finally:
        session.close()

    return redirect(url_for('buscar_alumno'))



if __name__ == '__main__':
    app.run(debug=True)
