// ======================
// Dropdown Menu
// ======================


window.toggleMenu = function (id) {
    const menu = document.getElementById(id);
    if (!menu)
        return;

    if (menu.style.display === "flex") {
        menu.style.display = "none";
    }
    else {
        menu.style.display = "flex";
    }
};


// ======================
// Active menu
// ======================


document.addEventListener("DOMContentLoaded", () => {
    const currentPath = window.location.pathname;
    document.querySelectorAll(".menu-btn")
        .forEach(btn => {
            const href = btn.getAttribute("href");
            if (href && href === currentPath) {
                btn.classList.add("active");
                const parent = btn.closest(".submenu");
                if (parent) {
                    parent.style.display = "flex";
                }
            }
        });
});
