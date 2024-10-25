document.getElementById('updateForm').addEventListener('submit', function(event) {
    event.preventDefault(); // Evitar el envío del formulario

    const nombre = document.getElementById('nombre').value.trim();
    const primerApe = document.getElementById('primerApe').value.trim();
    const telefono = document.getElementById('telefono').value.trim();
    const correo = document.getElementById('correo').value.trim();
    const curp = document.getElementById('curp').value.trim();

    // Expresión regular para validar el formato del CURP
    const curpPattern = /^[A-Z]{4}\d{6}[HM][A-Z]{5}\d{2}$/;
    // Expresión regular para validar el correo electrónico
    const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    // Expresión regular para validar el número de teléfono
    const phonePattern = /^[0-9]{10}$/;

    // Validaciones
    if (!nombre || !primerApe || !telefono || !correo || !curp) {
        Swal.fire({
            icon: 'warning',
            title: 'Campos Vacíos',
            text: 'Por favor, completa todos los campos requeridos antes de continuar.'
        });
        return;
    }

    if (!phonePattern.test(telefono)) {
        Swal.fire({
            icon: 'error',
            title: 'Teléfono Inválido',
            text: 'El número de teléfono debe contener 10 dígitos numéricos.'
        });
        return;
    }

    if (!emailPattern.test(correo)) {
        Swal.fire({
            icon: 'error',
            title: 'Correo Electrónico Inválido',
            text: 'Por favor, ingresa un correo electrónico válido.'
        });
        return;
    }

    if (!curpPattern.test(curp)) {
        Swal.fire({
            icon: 'error',
            title: 'CURP Inválido',
            text: 'El formato del CURP es incorrecto. Asegúrate de ingresarlo correctamente.'
        });
        return;
    }

    // Obtener el ID del alumno de forma segura
    const alumnoId = {{ alumno.idAlumno|tojson }};

    // Verificar que alumnoId está definido
    if (!alumnoId) {
        Swal.fire({
            icon: 'error',
            title: 'Error',
            text: 'No se pudo obtener el ID del alumno.'
        });
        return;
    }

    // Crear FormData con los datos del formulario
    const formData = new FormData(document.getElementById('updateForm'));

    // Enviar los datos con fetch
    fetch(`/actualizar_alumno/${alumnoId}`, {
        method: 'POST',
        body: formData
    })
    .then(response => {
        if (!response.ok) {
            return response.json().then(data => {
                throw new Error(data.error || 'Error al actualizar el alumno.');
            });
        }
        return response.json();
    })
    .then(data => {
        // Mostrar mensaje de éxito
        Swal.fire({
            icon: 'success',
            title: 'Alumno Actualizado',
            text: data.message + ' El PDF se descargará a continuación.'
        });

        // Descargar el PDF
        fetch(`/generar_pdf/${alumnoId}`)
        .then(response => {
            if (!response.ok) {
                throw new Error('Error al generar el PDF.');
            }
            return response.blob();
        })
        .then(blob => {
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `ticket_alumno_${alumnoId}.pdf`;
            document.body.appendChild(a);
            a.click();
            a.remove();

            // Esperar un momento antes de redirigir
            setTimeout(() => {
                // Redirigir a 'buscar_alumno'
                window.location.href = '/buscar_alumno';
            }, 2000); // Espera 2 segundos antes de redirigir
        })
        .catch(error => {
            console.error('Error al descargar el PDF:', error);
            Swal.fire({
                icon: 'error',
                title: 'Error',
                text: 'Ocurrió un error al descargar el PDF. Por favor, intente de nuevo.'
            });
        });
    })
    .catch(error => {
        console.error('Error al actualizar el alumno:', error);
        Swal.fire({
            icon: 'error',
            title: 'Error',
            text: error.message
        });
    });
});
