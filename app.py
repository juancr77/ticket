from flask import Flask, render_template, request, redirect, url_for, flash, make_response, jsonify, session
from models.orm_models import Database, Alumno, Grado, Municipio, Asunto, Ticket, Login, Cargo ,Estatus
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy import func
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from io import BytesIO
import qrcode
from sqlalchemy.orm import joinedload
import hashlib

app = Flask(__name__)
app.secret_key = 'juannumbres12'  # Clave secreta para los mensajes flash y otras funcionalidades de seguridad
db = Database()  # Instancia de la base de datos
db_session = Database().get_session()

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
    session_db = db.get_session()

    grados = session_db.query(Grado).all()
    municipios = session_db.query(Municipio).all()
    asuntos = session_db.query(Asunto).all()

    session_db.close()
    return render_template('register_alumno.html', grados=grados, municipios=municipios, asuntos=asuntos)

# Verificar si el alumno ya está registrado
@app.route('/check_alumno', methods=['POST'])
def check_alumno():
    session_db = db.get_session()

    data = request.get_json()
    nombre = data.get('nombre')
    primerApe = data.get('primerApe')
    segundoApe = data.get('segundoApe', '')
    curp = data.get('curp')

    if not nombre or not primerApe or not curp:
        session_db.close()
        return jsonify({'exists': False, 'message': 'Datos incompletos'}), 400

    # Buscar si el alumno ya está registrado por CURP
    alumno_existente = session_db.query(Alumno).filter(Alumno.curp == curp).first()

    if alumno_existente:
        # Obtener la información del ticket asociado al alumno
        ticket_existente = session_db.query(Ticket).filter_by(idAlumno=alumno_existente.idAlumno).first()

        if ticket_existente:
            mensaje = f"El alumno {alumno_existente.nombre} {alumno_existente.primerApe} ya está registrado con el ticket número {ticket_existente.ordTicket}."
        else:
            mensaje = f"El alumno {alumno_existente.nombre} {alumno_existente.primerApe} ya está registrado, pero no tiene ticket asignado."

        session_db.close()
        return jsonify({'exists': True, 'message': mensaje}), 200
    else:
        session_db.close()
        return jsonify({'exists': False}), 200

# Ruta para registrar al alumno
@app.route('/register_alumno', methods=['POST'])
def register_alumno():
    session_db = db.get_session()

    # Capturar datos del formulario
    nombre = request.form['nombre']
    primerApe = request.form['primerApe']
    segundoApe = request.form.get('segundoApe', '')
    telefono = request.form['telefono']
    correo = request.form['correo']
    curp = request.form['curp']
    idGrado = request.form['idGrado']
    idMunicipio = request.form['idMunicipio']
    idAsunto = request.form['idAsunto']

    # Validaciones
    if not nombre or not primerApe or not telefono or not correo or not curp or not idGrado or not idMunicipio or not idAsunto:
        session_db.close()
        return jsonify({'error': 'Todos los campos obligatorios deben ser completados.'}), 400

    try:
        # Verificar si el alumno ya está registrado por CURP
        alumno_existente = session_db.query(Alumno).filter_by(curp=curp).first()

        if alumno_existente:
            session_db.close()
            return jsonify({'error': f"El alumno con CURP '{curp}' ya está registrado."}), 400

        # Crear un nuevo alumno
        nuevo_alumno = Alumno(
            nombre=nombre,
            primerApe=primerApe,
            segundoApe=segundoApe,
            telefono=telefono,
            correo=correo,
            curp=curp,
            idGrado=idGrado,
            idMunicipio=idMunicipio,
            idAsunto=idAsunto
        )
        session_db.add(nuevo_alumno)
        session_db.commit()

        # Obtener el ID del nuevo alumno
        alumno_id = nuevo_alumno.idAlumno

        # Asignar turno y crear un ticket
        max_turno = session_db.query(func.max(Ticket.ordTicket)).filter(Ticket.idMunicipio == idMunicipio).scalar() or 0
        nuevo_turno = max_turno + 1

        nuevo_ticket = Ticket(
            ordTicket=nuevo_turno,
            idMunicipio=idMunicipio,
            idAlumno=alumno_id,
            idAsunto=idAsunto,
            fecha=func.now(),
            idestatus=1  # Estado inicial de "Pendiente"
        )
        session_db.add(nuevo_ticket)
        session_db.commit()

        session_db.close()
        return jsonify({'alumno_id': alumno_id, 'message': 'Registro exitoso.'}), 200

    except IntegrityError:
        session_db.rollback()
        session_db.close()
        return jsonify({'error': 'Este registro ya existe en la base de datos.'}), 400

    except SQLAlchemyError as e:
        session_db.rollback()
        app.logger.error(f"Error al registrar el alumno o ticket: {e}")
        session_db.close()
        return jsonify({'error': 'Error al registrar el alumno. Por favor, inténtelo de nuevo.'}), 500

# Ruta para generar el PDF con QR
@app.route('/generar_pdf/<int:alumno_id>')
def generar_pdf(alumno_id):
    session_db = db.get_session()

    # Obtener los datos del alumno
    alumno = session_db.query(Alumno).filter_by(idAlumno=alumno_id).first()
    
    if not alumno:
        session_db.close()
        return jsonify({'error': 'Alumno no encontrado.'}), 404

    # Obtener el ticket del alumno
    ticket = session_db.query(Ticket).filter_by(idAlumno=alumno_id).first()

    if not ticket:
        session_db.close()
        return jsonify({'error': 'Ticket no encontrado para el alumno.'}), 404

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
    pdf.drawImage(ImageReader(qr_code_img), 400, 600, 100, 100)

    pdf.showPage()
    pdf.save()

    buffer.seek(0)

    response = make_response(buffer.getvalue())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename="ticket_alumno_{alumno_id}.pdf"'

    session_db.close()

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
    session_db = db.get_session()

    # Obtener los datos del alumno por su ID
    alumno = session_db.query(Alumno).filter_by(idAlumno=idAlumno).first()

    if alumno:
        grados = session_db.query(Grado).all()
        municipios = session_db.query(Municipio).all()
        asuntos = session_db.query(Asunto).all()

        response = render_template('modificar_alumno.html', alumno=alumno, grados=grados, municipios=municipios, asuntos=asuntos)
        session_db.close()
        return response
    else:
        session_db.close()
        flash("No se encontró ningún registro para modificar.", "error")
        return redirect(url_for('buscar_alumno'))


@app.route('/actualizar_alumno/<int:idAlumno>', methods=['POST'])
def actualizar_alumno(idAlumno):
    session_db = db.get_session()

    # Obtener los datos actualizados desde el formulario
    nombre = request.form['nombre']
    primerApe = request.form['primerApe']
    segundoApe = request.form.get('segundoApe', '')
    telefono = request.form['telefono']
    correo = request.form['correo']
    curp = request.form['curp']  # Agregar el CURP
    idGrado = request.form['idGrado']
    idMunicipio = request.form['idMunicipio']
    idAsunto = request.form['idAsunto']

    try:
        # Buscar al alumno por su ID
        alumno = session_db.query(Alumno).filter_by(idAlumno=idAlumno).first()

        if alumno:
            # Guardar el municipio anterior
            municipio_anterior = alumno.idMunicipio

            # Actualizar los datos del alumno
            alumno.nombre = nombre
            alumno.primerApe = primerApe
            alumno.segundoApe = segundoApe
            alumno.telefono = telefono
            alumno.correo = correo
            alumno.curp = curp  # Actualizar el CURP
            alumno.idGrado = idGrado
            alumno.idMunicipio = idMunicipio
            alumno.idAsunto = idAsunto

            # Si el municipio ha cambiado, recalcular el turno
            ticket = session_db.query(Ticket).filter_by(idAlumno=idAlumno).first()
            if ticket and municipio_anterior != int(idMunicipio):
                # Obtener el nuevo turno para el nuevo municipio
                max_turno = session_db.query(func.max(Ticket.ordTicket)).filter(Ticket.idMunicipio == idMunicipio).scalar() or 0
                nuevo_turno = max_turno + 1
                ticket.ordTicket = nuevo_turno
                ticket.idMunicipio = idMunicipio  # Actualizar también el municipio en el ticket

            session_db.commit()

            # Enviar respuesta JSON de éxito
            alumno_id = alumno.idAlumno  # Obtener el ID antes de cerrar la sesión
            session_db.close()
            return jsonify({'alumno_id': alumno_id, 'message': 'Datos actualizados exitosamente.'}), 200

        else:
            session_db.close()
            return jsonify({'error': 'No se encontró el alumno a modificar.'}), 404

    except SQLAlchemyError as e:
        session_db.rollback()
        app.logger.error(f"Error al actualizar los datos: {e}")
        session_db.close()
        return jsonify({'error': 'Error al actualizar los datos. Por favor, inténtelo de nuevo.'}), 500


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
    session_db = db.get_session()

    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        user = session_db.query(Login).filter_by(email=email).first()

        if user and user.check_password(password):
            # Guardar el nombre y el cargo del usuario en la sesión
            session['user_name'] = f"{user.nombre} {user.primerAp}"
            session['user_cargo'] = user.idCargo  # O puedes usar el nombre del cargo si lo tienes disponible

            flash('Inicio de sesión exitoso.', 'success')
            session_db.close()
            return redirect(url_for('menu_admin2'))
        else:
            flash('Email o contraseña incorrectos.', 'danger')
            session_db.close()
            return redirect(url_for('login'))

    session_db.close()
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()  # Limpiar la sesión
    flash('Has cerrado sesión correctamente.', 'success')
    return redirect(url_for('login'))


@app.route('/menu_admin2')
def menu_admin2():
    if 'user_name' in session and 'user_cargo' in session:
        user_name = session['user_name']
        user_cargo = session['user_cargo']
        return render_template('menu_admin2.html', user_name=user_name, user_cargo=user_cargo)
    else:
        flash('Por favor, inicia sesión primero.', 'warning')
        return redirect(url_for('login'))




# Ruta para la consulta, modificación y eliminación de alumnos y tickets@app.route('/consulta_admin', methods=['GET', 'POST'])
@app.route('/consulta_admin', methods=['GET', 'POST'])
def consulta_admin():
    if 'user_name' not in session:
        flash('Debes iniciar sesión primero.', 'warning')
        return redirect(url_for('login'))

    session_db = db.get_session()

    if request.method == 'POST':
        # Obtener datos de búsqueda
        curp = request.form.get('curp')
        nombre = request.form.get('nombre')
        primerApe = request.form.get('primerApe')

        # Si es búsqueda de alumno
        if curp or (nombre and primerApe):
            # Buscar al alumno por CURP o por nombre y primer apellido
            if curp:
                alumno = session_db.query(Alumno).filter_by(curp=curp).first()
            elif nombre and primerApe:
                alumno = session_db.query(Alumno).filter_by(nombre=nombre, primerApe=primerApe).first()

            # Si se encuentra el alumno, también obtenemos el ticket relacionado
            if alumno:
                ticket = session_db.query(Ticket).filter_by(idAlumno=alumno.idAlumno).first()

                # Obtener todos los municipios y asuntos para los selects
                municipios = session_db.query(Municipio).all()
                asuntos = session_db.query(Asunto).all()

                # Verificar si no se encuentran municipios o asuntos en la base de datos
                if not municipios or not asuntos:
                    flash('No hay datos disponibles para municipios o asuntos.', 'danger')
                    session_db.close()
                    return redirect(url_for('consulta_admin'))

                session_db.close()

                # Renderizamos el formulario de modificación o eliminación, pasando los municipios y asuntos
                return render_template('consulta_admin.html', alumno=alumno, ticket=ticket, municipios=municipios, asuntos=asuntos)
            else:
                flash('No se encontró ningún alumno con los datos proporcionados.', 'danger')
                session_db.close()
                return redirect(url_for('consulta_admin'))

    return render_template('consulta_admin.html')


# Ruta para actualizar alumno y ticket
@app.route('/actualizar_alumno_ticket/<int:idAlumno>', methods=['POST'])
def actualizar_alumno_ticket(idAlumno):
    session_db = db.get_session()

    # Obtener los datos actualizados del alumno
    nombre = request.form.get('nombre')
    primerApe = request.form.get('primerApe')
    segundoApe = request.form.get('segundoApe')
    telefono = request.form.get('telefono')
    correo = request.form.get('correo')

    # Obtener los datos del ticket
    ordTicket = request.form.get('ordTicket')
    fecha = request.form.get('fecha')
    idestatus = request.form.get('idestatus')
    idMunicipio = request.form.get('idMunicipio')
    idAsunto = request.form.get('idAsunto')

    # Validar si todos los datos están presentes
    if not (nombre and primerApe and ordTicket and fecha and idMunicipio and idAsunto):
        flash('Todos los campos son obligatorios.', 'danger')
        return redirect(url_for('consulta_admin'))

    try:
        # Actualizar el alumno
        alumno = session_db.query(Alumno).filter_by(idAlumno=idAlumno).first()
        if alumno:
            alumno.nombre = nombre
            alumno.primerApe = primerApe
            alumno.segundoApe = segundoApe
            alumno.telefono = telefono
            alumno.correo = correo

        # Actualizar el ticket
        ticket = session_db.query(Ticket).filter_by(idAlumno=idAlumno).first()
        if ticket:
            ticket.ordTicket = ordTicket
            ticket.fecha = fecha
            ticket.idestatus = idestatus
            ticket.idMunicipio = idMunicipio
            ticket.idAsunto = idAsunto

        session_db.commit()
        flash('Alumno y Ticket actualizados correctamente.', 'success')

    except SQLAlchemyError as e:
        session_db.rollback()
        flash('Error al actualizar los datos.', 'danger')
        app.logger.error(f"Error: {e}")

    finally:
        session_db.close()

    return redirect(url_for('consulta_admin'))


# Ruta para eliminar alumno y ticket
@app.route('/eliminar_alumno_ticket/<int:idAlumno>', methods=['POST'])
def eliminar_alumno_ticket(idAlumno):
    session_db = db.get_session()

    try:
        # Eliminar el ticket primero
        ticket = session_db.query(Ticket).filter_by(idAlumno=idAlumno).first()
        if ticket:
            session_db.delete(ticket)
            session_db.commit()

        # Eliminar al alumno
        alumno = session_db.query(Alumno).filter_by(idAlumno=idAlumno).first()
        if alumno:
            session_db.delete(alumno)
            session_db.commit()

        flash('Alumno y Ticket eliminados correctamente.', 'success')

    except SQLAlchemyError as e:
        session_db.rollback()
        flash('Error al eliminar los datos.', 'danger')
        app.logger.error(f"Error: {e}")

    finally:
        session_db.close()

    return redirect(url_for('consulta_admin'))



@app.route('/dashboard')
def dashboard():
    if 'user_name' not in session:
        flash('Debes iniciar sesión primero.', 'warning')
        return redirect(url_for('login'))
    return render_template('dashboard.html')

@app.route('/dashboard/data', methods=['GET'])
def dashboard_data():
    session_db = db.get_session()

    try:
        # Obtener el número de tickets por estatus ("Resuelto" y "Pendiente")
        total_por_estatus = session_db.query(
            Ticket.idestatus,
            func.count(Ticket.idticket).label('total')
        ).group_by(Ticket.idestatus).all()

        # Obtener los tickets filtrados por municipio usando el campo nombreN en Municipio
        tickets_por_municipio = session_db.query(
            Municipio.nombreN,  # Correcto: usa 'nombreN'
            Ticket.idestatus,
            func.count(Ticket.idticket).label('total')
        ).join(Municipio, Ticket.idMunicipio == Municipio.idMunicipio).group_by(
            Municipio.nombreN, Ticket.idestatus
        ).all()

        session_db.close()

        # Preparar los datos para enviar al frontend
        data = {
            'total_por_estatus': [{'estatus': estatus, 'total': total} for estatus, total in total_por_estatus],
            'tickets_por_municipio': [
                {'municipio': municipio, 'estatus': estatus, 'total': total}
                for municipio, estatus, total in tickets_por_municipio
            ]
        }

        return jsonify(data)

    except SQLAlchemyError as e:
        session_db.rollback()
        print(f"Error: {e}")
        return jsonify({'error': 'Ocurrió un error al obtener los datos.'}), 500

####Cruds#################################################################
# Ruta para listar y gestionar los estatus
@app.route('/asunto', methods=['GET', 'POST'])
def asunto_crud():
    if 'user_name' not in session:
        flash('Debes iniciar sesión primero.', 'warning')
        return redirect(url_for('login'))
    
    session_db = db.get_session()
    if request.method == 'POST':
        if 'create' in request.form:
            # Crear nuevo Asunto
            asunto_name = request.form.get('asuntoN')
            if asunto_name:
                new_asunto = Asunto(asuntoN=asunto_name)
                session_db.add(new_asunto)
                session_db.commit()
                session_db.close()
                return redirect(url_for('asunto_crud'))
        elif 'update' in request.form:
            # Actualizar Asunto existente
            asunto_id = request.form.get('idAsunto')
            asunto_name = request.form.get('asuntoN')
            if asunto_id and asunto_name:
                asunto = session_db.query(Asunto).get(int(asunto_id))
                if asunto:
                    asunto.asuntoN = asunto_name
                    session_db.commit()
                    session_db.close()
                    return redirect(url_for('asunto_crud'))
        elif 'delete' in request.form:
            # Eliminar Asunto
            asunto_id = request.form.get('idAsunto')
            if asunto_id:
                asunto = session_db.query(Asunto).get(int(asunto_id))
                if asunto:
                    session_db.delete(asunto)
                    session_db.commit()
                    session_db.close()
                    return redirect(url_for('asunto_crud'))
    # Solicitud GET o después de POST
    asuntos = session_db.query(Asunto).all()
    session_db.close()
    return render_template('asunto.html', asuntos=asuntos)
### GRado####################################################
@app.route('/grado', methods=['GET', 'POST'])
def grado_crud():
    if 'user_name' not in session:
        flash('Debes iniciar sesión primero.', 'warning')
        return redirect(url_for('login'))

    session_db = db.get_session()
    if request.method == 'POST':
        if 'create' in request.form:
            # Crear nuevo Grado
            grado_name = request.form.get('gradoN')
            if grado_name:
                new_grado = Grado(gradoN=grado_name)
                session_db.add(new_grado)
                session_db.commit()
                session_db.close()
                return redirect(url_for('grado_crud'))
        elif 'update' in request.form:
            # Actualizar Grado existente
            grado_id = request.form.get('idGrado')
            grado_name = request.form.get('gradoN')
            if grado_id and grado_name:
                grado = session_db.query(Grado).get(int(grado_id))
                if grado:
                    grado.gradoN = grado_name
                    session_db.commit()
                    session_db.close()
                    return redirect(url_for('grado_crud'))
        elif 'delete' in request.form:
            # Eliminar Grado
            grado_id = request.form.get('idGrado')
            if grado_id:
                grado = session_db.query(Grado).get(int(grado_id))
                if grado:
                    session_db.delete(grado)
                    session_db.commit()
                    session_db.close()
                    return redirect(url_for('grado_crud'))
    # Solicitud GET o después de POST
    grados = session_db.query(Grado).all()
    session_db.close()
    return render_template('grado.html', grados=grados)

@app.route('/cargo', methods=['GET', 'POST'])
def cargo_crud():
    if 'user_name' not in session:
        flash('Debes iniciar sesión primero.', 'warning')
        return redirect(url_for('login'))

    session_db = db.get_session()
    if request.method == 'POST':
        if 'create' in request.form:
            # Crear nuevo Cargo
            cargo_name = request.form.get('cargoN')
            if cargo_name:
                new_cargo = Cargo(cargoN=cargo_name)
                session_db.add(new_cargo)
                session_db.commit()
                session_db.close()
                return redirect(url_for('cargo_crud'))
        elif 'update' in request.form:
            # Actualizar Cargo existente
            cargo_id = request.form.get('idCargo')
            cargo_name = request.form.get('cargoN')
            if cargo_id and cargo_name:
                cargo = session_db.query(Cargo).get(int(cargo_id))
                if cargo:
                    cargo.cargoN = cargo_name
                    session_db.commit()
                    session_db.close()
                    return redirect(url_for('cargo_crud'))
        elif 'delete' in request.form:
            # Eliminar Cargo
            cargo_id = request.form.get('idCargo')
            if cargo_id:
                cargo = session_db.query(Cargo).get(int(cargo_id))
                if cargo:
                    session_db.delete(cargo)
                    session_db.commit()
                    session_db.close()
                    return redirect(url_for('cargo_crud'))
    # Solicitud GET o después de POST
    cargos = session_db.query(Cargo).all()
    session_db.close()
    return render_template('cargo.html', cargos=cargos)


if __name__ == '__main__':
    app.run(debug=True, use_reloader=True)
