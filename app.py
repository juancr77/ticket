from flask import Flask, render_template, request, redirect, url_for, flash
from models.models import Database, Alumno, Grado, Municipio, Asunto, Ticket
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy import func

app = Flask(__name__)
app.secret_key = 'juannumbres12'  

db = Database()

@app.route('/')
def index():
    session = db.get_session()

    grados = session.query(Grado).all()
    municipios = session.query(Municipio).all()
    asuntos = session.query(Asunto).all()

    session.close()
    return render_template('register_alumno.html', grados=grados, municipios=municipios, asuntos=asuntos)

# Ruta para validar si un alumno ya existe (Lado del servidor)@app.route('/check_alumno', methods=['POST'])
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

        # Construir un mensaje más detallado si el alumno ya tiene un ticket
        if ticket_existente:
            mensaje = f"El alumno {alumno_existente.nombre} {alumno_existente.primerApe} {alumno_existente.segundoApe} ya está registrado con el ticket número {ticket_existente.ordTicket}."
        else:
            mensaje = f"El alumno {alumno_existente.nombre} {alumno_existente.primerApe} {alumno_existente.segundoApe} ya está registrado, pero no tiene ticket asignado."

        session.close()
        return {'exists': True, 'message': mensaje}, 200
    else:
        session.close()
        return {'exists': False}, 200



# Ruta para registrar el alumno (con validación de duplicados del lado del servidor)
@app.route('/register_alumno', methods=['POST'])
def register_alumno():
    session = db.get_session()

    nombre = request.form['nombre']
    primerApe = request.form['primerApe']
    segundoApe = request.form.get('segundoApe', '')
    telefono = request.form['telefono']
    correo = request.form['correo']
    idGrado = request.form['idGrado']
    idMunicipio = request.form['idMunicipio']
    idAsunto = request.form['idAsunto']

    # Validaciones del lado del servidor
    if not nombre or not primerApe or not telefono or not correo or not idGrado or not idMunicipio or not idAsunto:
        flash("Todos los campos obligatorios deben ser completados.", "error")
        return redirect(url_for('index'))

    try:
        # Verificar si el alumno ya está registrado en el servidor (validación de seguridad adicional)
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

        flash("Registro exitoso.", "success")
        return redirect(url_for('index'))

    except IntegrityError as e:
        session.rollback()
        flash("Error: Este registro ya existe en la base de datos. No se puede duplicar la clave primaria.", "error")
        return redirect(url_for('index'))

    except SQLAlchemyError as e:
        session.rollback()
        flash(f"Error al registrar el alumno o ticket: {e}", "error")
        return redirect(url_for('index'))

    finally:
        session.close()

if __name__ == '__main__':
    app.run(debug=True)