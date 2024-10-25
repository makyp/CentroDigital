document.addEventListener("DOMContentLoaded", function () {
    const loadingDiv = document.getElementById("loading");

    // Mostrar "Cargando..." al enviar cualquier formulario
    document.querySelectorAll("form").forEach(function (form) {
        form.addEventListener("submit", function (event) {
            // Aquí puedes prevenir el envío si es necesario
            // event.preventDefault();

            // Mostrar la ventana de carga
            loadingDiv.style.display = "flex";
        });
    });

    // Mostrar "Cargando..." al hacer solicitudes AJAX
    $(document).ajaxStart(function () {
        loadingDiv.style.display = "flex"; // Muestra la ventana al iniciar una solicitud
    }).ajaxStop(function () {
        loadingDiv.style.display = "none"; // Oculta la ventana al finalizar la solicitud
    });
});

// Ocultar mensaje de flash después de 3 segundos
setTimeout(function() {
    var flashMessage = document.getElementById('flash-message');
    if (flashMessage) {
        flashMessage.style.display = 'none';
    }
}, 3000);
