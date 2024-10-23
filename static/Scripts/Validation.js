// Función de validación del formulario
function validarFormulario() {
    var nombre = document.getElementById('nombre').value.trim();
    var primerApe = document.getElementById('primerApe').value.trim();
    var telefono = document.getElementById('telefono').value.trim();
    var correo = document.getElementById('correo').value.trim();
    var grado = document.getElementById('grado').value;
    var municipio = document.getElementById('municipio').value;
    var asunto = document.getElementById('asunto').value;
    var curp = document.getElementById('curp').value.trim();  // Nuevo campo de CURP

    // Validación de campos vacíos
    if (nombre === '') {
        alert("El campo 'Nombre' es obligatorio.");
        return false;
    } 
    if (primerApe === '') {
        alert("El campo 'Primer Apellido' es obligatorio.");
        return false;
    } 
    if (telefono === '') {
        alert("El campo 'Teléfono' es obligatorio.");
        return false;
    } 
    if (correo === '') {
        alert("El campo 'Correo Electrónico' es obligatorio.");
        return false;
    }
    if (curp === '') {  // Validación del campo CURP
        alert("El campo 'CURP' es obligatorio.");
        return false;
    } 
    if (grado === '') {
        alert("Debe seleccionar un Grado.");
        return false;
    } 
    if (municipio === '') {
        alert("Debe seleccionar un Municipio.");
        return false;
    } 
    if (asunto === '') {
        alert("Debe seleccionar un Asunto.");
        return false;
    }

    // Validación de formato de CURP (18 caracteres alfanuméricos)
    var patronCurp = /^[A-Z0-9]{18}$/i;
    if (!patronCurp.test(curp)) {
        alert("Por favor, ingrese un CURP válido (18 caracteres alfanuméricos).");
        return false;
    }

    // Validación de formato de correo electrónico
    var patronCorreo = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
    if (!patronCorreo.test(correo)) {
        alert("Por favor, ingrese un correo electrónico válido.");
        return false;
    }

    // Validación de formato de teléfono (solo números y mínimo 10 caracteres)
    var patronTelefono = /^\d{10}$/;
    if (!patronTelefono.test(telefono)) {
        alert("Por favor, ingrese un número de teléfono válido (10 dígitos).");
        return false;
    }

    return true;  // Si todas las validaciones pasan, devuelve true
}

// Evento de envío del formulario
document.getElementById('registerForm').addEventListener('submit', function (event) {
    event.preventDefault();  // Evita el envío inmediato del formulario

    // Primero realizar la validación del lado del cliente
    if (!validarFormulario()) {
        return;  // Si hay errores en la validación, no continuar
    }

    // Obtener los valores del formulario
    const nombre = document.getElementById('nombre').value;
    const primerApe = document.getElementById('primerApe').value;
    const segundoApe = document.getElementById('segundoApe').value;
    const curp = document.getElementById('curp').value;  // Obtener el valor del CURP

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
    .then(response => response.json())
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
            .then(response => response.json())
            .then(data => {
                // Descargar el PDF
                if (data.alumno_id) {
                    fetch(`/generar_pdf/${data.alumno_id}`)
                    .then(response => response.blob())
                    .then(blob => {
                        const url = window.URL.createObjectURL(blob);
                        const a = document.createElement('a');
                        a.href = url;
                        a.download = `ticket_alumno_${data.alumno_id}.pdf`;
                        document.body.appendChild(a);
                        a.click();
                        a.remove();
                    });
                }
            });
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Ocurrió un error al verificar el registro del alumno. Por favor, intente de nuevo.');
    });
});
