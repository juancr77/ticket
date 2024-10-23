// Función de validación del formulario
function validarFormulario(event) {
    var nombre = document.getElementById('nombre').value.trim();
    var primerApe = document.getElementById('primerApe').value.trim();
    var telefono = document.getElementById('telefono').value.trim();
    var correo = document.getElementById('correo').value.trim();
    var grado = document.getElementById('grado').value;
    var municipio = document.getElementById('municipio').value;
    var asunto = document.getElementById('asunto').value;

    // Validación de campos vacíos
    if (nombre === '') {
        alert("El campo 'Nombre' es obligatorio.");
        event.preventDefault();
        return;
    } 
    if (primerApe === '') {
        alert("El campo 'Primer Apellido' es obligatorio.");
        event.preventDefault();
        return;
    } 
    if (telefono === '') {
        alert("El campo 'Teléfono' es obligatorio.");
        event.preventDefault();
        return;
    } 
    if (correo === '') {
        alert("El campo 'Correo Electrónico' es obligatorio.");
        event.preventDefault();
        return;
    } 
    if (grado === '') {
        alert("Debe seleccionar un Grado.");
        event.preventDefault();
        return;
    } 
    if (municipio === '') {
        alert("Debe seleccionar un Municipio.");
        event.preventDefault();
        return;
    } 
    if (asunto === '') {
        alert("Debe seleccionar un Asunto.");
        event.preventDefault();
        return;
    }

    // Validación de formato de correo electrónico
    var patronCorreo = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
    if (!patronCorreo.test(correo)) {
        alert("Por favor, ingrese un correo electrónico válido.");
        event.preventDefault();
        return;
    }

    // Validación de formato de teléfono (solo números y mínimo 10 caracteres)
    var patronTelefono = /^\d{10}$/;
    if (!patronTelefono.test(telefono)) {
        alert("Por favor, ingrese un número de teléfono válido (10 dígitos).");
        event.preventDefault();
        return;
    }
}
document.getElementById('registerForm').addEventListener('submit', function (event) {
    event.preventDefault(); // Evita el envío inmediato del formulario

    // Obtener los valores del formulario
    const nombre = document.getElementById('nombre').value;
    const primerApe = document.getElementById('primerApe').value;
    const segundoApe = document.getElementById('segundoApe').value;

    // Realizar la petición al servidor para verificar si el alumno ya existe
    fetch('/check_alumno', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            nombre: nombre,
            primerApe: primerApe,
            segundoApe: segundoApe
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.exists) {
            // Si el alumno ya está registrado, mostrar mensaje detallado
            alert(data.message);
        } else {
            // Si no está registrado, permitir el envío del formulario
            document.getElementById('registerForm').submit();
        }
    })
    .catch(error => {
        console.error('Error:', error);
    });
});
