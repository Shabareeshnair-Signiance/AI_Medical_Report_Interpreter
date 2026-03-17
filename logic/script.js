const form = document.getElementById("uploadForm");
const loader = document.getElementById("loader");

form.addEventListener("submit", function () {
    loader.classList.remove("hidden");
});