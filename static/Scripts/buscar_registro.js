document.getElementById('searchForm').addEventListener('submit', function(event) {
    const curp = document.getElementById('curp').value.trim();
    const ordTicket = document.getElementById('ordTicket').value.trim();

    // Expresión regular para validar el formato del CURP
    const curpPattern = /^[A-Z]{4}\d{6}[HM][A-Z]{5}\d{2}$/;

    if (!curp || !ordTicket) {
        event.preventDefault();
        Swal.fire({
            icon: 'warning',
            title: 'Campos Vacíos',
            text: 'Por favor, completa todos los campos antes de continuar.'
        });
    } else if (!curpPattern.test(curp)) {
        event.preventDefault();
        Swal.fire({
            icon: 'error',
            title: 'CURP Inválido',
            text: 'El formato del CURP es incorrecto. Asegúrate de ingresarlo correctamente.'
        });
    }
});
