(() => {
    const menuToggle = document.getElementById("menu-toggle");
    const navMenu = document.getElementById("nav-menu");

    const setMenuState = (isOpen) => {
        if (!menuToggle || !navMenu) {
            return;
        }

        navMenu.classList.toggle("show", isOpen);
        menuToggle.setAttribute("aria-expanded", String(isOpen));
        menuToggle.setAttribute(
            "aria-label",
            isOpen ? "关闭导航菜单 / Close navigation menu" : "打开导航菜单 / Open navigation menu"
        );
    };

    if (menuToggle && navMenu) {
        menuToggle.addEventListener("click", () => {
            setMenuState(menuToggle.getAttribute("aria-expanded") !== "true");
        });

        navMenu.querySelectorAll("a").forEach((link) => {
            link.addEventListener("click", () => setMenuState(false));
        });

        document.addEventListener("keydown", (event) => {
            if (event.key === "Escape" && menuToggle.getAttribute("aria-expanded") === "true") {
                setMenuState(false);
                menuToggle.focus();
            }
        });
    }

    const heroImage = document.getElementById("dynamic-image");
    if (heroImage) {
        const images = Array.from({ length: 38 }, (_, index) => `/home/image_${index + 1}.png`);

        window.setInterval(() => {
            const randomIndex = Math.floor(Math.random() * images.length);
            heroImage.src = images[randomIndex];
        }, 4000);
    }
})();
