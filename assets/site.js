document.addEventListener("DOMContentLoaded", () => {
  const year = document.getElementById("year");
  if (year) {
    year.textContent = new Date().getFullYear();
  }

  const nav = document.querySelector("nav");
  const menuToggle = document.querySelector(".menu-toggle");
  const navLinks = document.querySelector("nav ul");

  if (navLinks) {
    const currentPage = window.location.pathname.split("/").pop() || "index.html";

    navLinks.querySelectorAll("a").forEach((link) => {
      const linkPage = new URL(link.href, window.location.href).pathname.split("/").pop();
      if (linkPage === currentPage) {
        link.setAttribute("aria-current", "page");
      }
    });
  }

  if (menuToggle && navLinks) {
    menuToggle.addEventListener("click", () => {
      const isOpen = navLinks.classList.toggle("show");
      menuToggle.setAttribute("aria-expanded", String(isOpen));
    });

    navLinks.querySelectorAll("a").forEach((link) => {
      link.addEventListener("click", () => {
        navLinks.classList.remove("show");
        menuToggle.setAttribute("aria-expanded", "false");
      });
    });

    document.addEventListener("click", (event) => {
      if (!nav || !navLinks.classList.contains("show")) {
        return;
      }

      if (!nav.contains(event.target)) {
        navLinks.classList.remove("show");
        menuToggle.setAttribute("aria-expanded", "false");
      }
    });

    window.addEventListener("resize", () => {
      if (window.innerWidth > 1024) {
        navLinks.classList.remove("show");
        menuToggle.setAttribute("aria-expanded", "false");
      }
    });
  }

  const carousel = document.querySelector(".highlights-carousel");
  if (carousel) {
    const track = carousel.querySelector(".highlights-track");
    const slides = Array.from(carousel.querySelectorAll(".highlight-slide"));
    const dotsContainer = carousel.querySelector(".carousel-dots");
    const previousButton = carousel.querySelector(".carousel-previous");
    const nextButton = carousel.querySelector(".carousel-next");
    let currentSlide = 0;
    let rotationTimer;

    const dots = slides.map((slide, index) => {
      const dot = document.createElement("button");
      dot.type = "button";
      dot.className = "carousel-dot";
      dot.setAttribute("aria-label", `Show highlight ${index + 1} of ${slides.length}`);
      dot.addEventListener("click", () => showSlide(index));
      dotsContainer.appendChild(dot);
      return dot;
    });

    function showSlide(index) {
      currentSlide = (index + slides.length) % slides.length;
      track.style.transform = `translateX(-${currentSlide * 100}%)`;

      slides.forEach((slide, slideIndex) => {
        slide.setAttribute("aria-hidden", slideIndex === currentSlide ? "false" : "true");
      });

      dots.forEach((dot, dotIndex) => {
        dot.setAttribute("aria-current", dotIndex === currentSlide ? "true" : "false");
      });
    }

    function startRotation() {
      window.clearInterval(rotationTimer);
      rotationTimer = window.setInterval(() => showSlide(currentSlide + 1), 6000);
    }

    function restartRotation() {
      window.clearInterval(rotationTimer);
      startRotation();
    }

    previousButton.addEventListener("click", () => {
      showSlide(currentSlide - 1);
      restartRotation();
    });

    nextButton.addEventListener("click", () => {
      showSlide(currentSlide + 1);
      restartRotation();
    });

    carousel.addEventListener("mouseenter", () => window.clearInterval(rotationTimer));
    carousel.addEventListener("mouseleave", startRotation);
    carousel.addEventListener("focusin", () => window.clearInterval(rotationTimer));
    carousel.addEventListener("focusout", (event) => {
      if (!carousel.contains(event.relatedTarget)) {
        startRotation();
      }
    });

    showSlide(0);
    startRotation();
  }
});
