document.getElementById('registerForm').addEventListener('submit', function (event) {
    event.preventDefault();  // Evita el envío inmediato del formulario

    // Primero realizar la validación del lado del cliente
    if (!validarFormulario()) {
        return;  // Si hay errores en la validación, no continuar
    }

    // Obtener los valores del formulario
    const nombre = document.getElementById('nombre').value.trim();
    const primerApe = document.getElementById('primerApe').value.trim();
    const segundoApe = document.getElementById('segundoApe').value.trim();
    const curp = document.getElementById('curp').value.trim();  // Obtener el valor del CURP

    // Realizar la petición al servidor para verificar si el alumno ya existe
    fetch('/check_alumno', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            nombre: nombre,
            primerApe: primerApe,
            segundoApe: segundoApe,
            curp: curp  // Enviar el valor del CURP
        })
    })
    .then(response => {
        if (!response.ok) {
            return response.json().then(data => {
                throw new Error(data.message || 'Error al verificar el alumno.');
            });
        }
        return response.json();
    })
    .then(data => {
        if (data.exists) {
            // Si el alumno ya está registrado, mostrar mensaje detallado
            alert(data.message);
        } else {
            // Si no está registrado, permitir el registro y descargar el PDF
            fetch('/register_alumno', {
                method: 'POST',
                body: new FormData(document.getElementById('registerForm'))
            })
            .then(response => {
                if (!response.ok) {
                    return response.json().then(data => {
                        throw new Error(data.error || 'Error al registrar al alumno.');
                    });
                }
                return response.json();
            })
            .then(data => {
                // Mostrar mensaje de éxito
                alert('Registro exitoso. El PDF se descargará a continuación.');

                // Descargar el PDF
                if (data.alumno_id) {
                    fetch(`/generar_pdf/${data.alumno_id}`)
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
                        a.download = `ticket_alumno_${data.alumno_id}.pdf`;
                        document.body.appendChild(a);
                        a.click();
                        a.remove();

                        // Esperar un momento antes de redirigir para asegurar que la descarga inicie
                        setTimeout(() => {
                            // Redirigir al formulario para registrar un nuevo alumno
                            window.location.href = '/registrar_alumno';
                        }, 2000); // Espera 2 segundos antes de redirigir
                    })
                    .catch(error => {
                        console.error('Error al descargar el PDF:', error);
                        alert('Ocurrió un error al descargar el PDF. Por favor, intente de nuevo.');
                    });
                }
            })
            .catch(error => {
                console.error('Error al registrar al alumno:', error);
                alert(error.message);
            });
        }
    })
    .catch(error => {
        console.error('Error al verificar el alumno:', error);
        alert(error.message);
    });
});

// Definir la función validarFormulario()
function validarFormulario() {
    const nombre = document.getElementById('nombre').value.trim();
    const primerApe = document.getElementById('primerApe').value.trim();
    const correo = document.getElementById('correo').value.trim();
    const curp = document.getElementById('curp').value.trim();

    if (!nombre || !primerApe || !correo || !curp) {
        alert('Por favor, completa todos los campos obligatorios.');
        return false;
    }

    // Validar formato del correo electrónico
    const correoRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!correoRegex.test(correo)) {
        alert('Por favor, ingresa un correo electrónico válido.');
        return false;
    }

    // Aquí puedes agregar validaciones adicionales, como el formato del CURP

    return true;
}
