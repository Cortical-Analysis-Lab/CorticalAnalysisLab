document.addEventListener("DOMContentLoaded", () => {
  const year = document.getElementById("year");
  if (year) {
    year.textContent = new Date().getFullYear();
  }

  const nav = document.querySelector("nav");
  const menuToggle = document.querySelector(".menu-toggle");
  const navLinks = document.querySelector("nav ul");

  if (menuToggle && navLinks) {
    menuToggle.addEventListener("click", () => {
      navLinks.classList.toggle("show");
    });

    navLinks.querySelectorAll("a").forEach((link) => {
      link.addEventListener("click", () => {
        navLinks.classList.remove("show");
      });
    });

    document.addEventListener("click", (event) => {
      if (!nav || !navLinks.classList.contains("show")) {
        return;
      }

      if (!nav.contains(event.target)) {
        navLinks.classList.remove("show");
      }
    });

    window.addEventListener("resize", () => {
      if (window.innerWidth > 1024) {
        navLinks.classList.remove("show");
      }
    });
  }
});
