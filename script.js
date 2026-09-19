
const menuToggle = document.querySelector(".menu-toggle");
const nav = document.querySelector("nav");

if (menuToggle && nav) {
const mobileMenuOverlay = document.createElement("div");
mobileMenuOverlay.className = "mobile-menu-overlay";
mobileMenuOverlay.innerHTML = `
    <div class="mobile-menu-content">
        <ul>
            <li><a href="/">Home</a></li>
            <li><a href="/products">Products</a></li>
            <li><a href="/about">About Us</a></li>
            <li><a href="/contact">Contact Us</a></li>
        </ul>
    </div>
`;
document.body.appendChild(mobileMenuOverlay);

menuToggle.addEventListener("click", () => {
  menuToggle.classList.toggle("active");
  nav.classList.toggle("active");
  mobileMenuOverlay.classList.toggle("active");
});

mobileMenuOverlay.addEventListener("click", (e) => {
  if (e.target === mobileMenuOverlay) {
    menuToggle.classList.remove("active");
    nav.classList.remove("active");
    mobileMenuOverlay.classList.remove("active");
  }
});

const mobileMenuLinks = mobileMenuOverlay.querySelectorAll("a");
mobileMenuLinks.forEach((link) => {
  link.addEventListener("click", () => {
    menuToggle.classList.remove("active");
    nav.classList.remove("active");
    mobileMenuOverlay.classList.remove("active");
  });
});
}

const topBtn = document.createElement("button");

topBtn.innerHTML = "↑";

topBtn.classList.add("top-btn");

document.body.appendChild(topBtn);

topBtn.style.position = "fixed";
topBtn.style.left = "25px";
topBtn.style.bottom = "25px";
topBtn.style.width = "55px";
topBtn.style.height = "55px";
topBtn.style.border = "none";
topBtn.style.borderRadius = "50%";
topBtn.style.cursor = "pointer";
topBtn.style.background = "#00a8ff";
topBtn.style.color = "#fff";
topBtn.style.fontSize = "24px";
topBtn.style.display = "none";
topBtn.style.zIndex = "999";

window.addEventListener("scroll", () => {
  if (window.scrollY > 400) {
    topBtn.style.display = "block";
  } else {
    topBtn.style.display = "none";
  }
});

topBtn.addEventListener("click", () => {
  window.scrollTo({
    top: 0,
    behavior: "smooth",
  });
});

const revealElements = document.querySelectorAll(
  ".feature,.product-card,.testimonial,.stat-box",
);

function reveal() {
  revealElements.forEach((el) => {
    const windowHeight = window.innerHeight;

    const elementTop = el.getBoundingClientRect().top;

    if (elementTop < windowHeight - 120) {
      el.style.opacity = "1";
      el.style.transform = "translateY(0)";
    }
  });
}

revealElements.forEach((el) => {
  el.style.opacity = "0";
  el.style.transform = "translateY(40px)";
  el.style.transition = ".8s";
});

window.addEventListener("scroll", reveal);

reveal();

const counters = document.querySelectorAll(".stat-box h2");

counters.forEach((counter) => {
  const target = parseInt(counter.innerText);

  if (isNaN(target)) return;

  let count = 0;

  const speed = target / 120;

  function updateCounter() {
    count += speed;

    if (count < target) {
      counter.innerText = Math.floor(count);

      requestAnimationFrame(updateCounter);
    } else {
      counter.innerText = target + "+";
    }
  }

  updateCounter();
});

const slides = document.querySelectorAll(".slide");

let current = 0;

if (slides.length > 0) {
  slides[current].classList.add("active");

  setInterval(() => {
    slides[current].classList.remove("active");

    current++;

    if (current >= slides.length) {
      current = 0;
    }

    slides[current].classList.add("active");
  }, 4000);
}

const searchInput = document.getElementById("search");

if (searchInput) {
  searchInput.addEventListener("keyup", function () {
    let value = this.value.toLowerCase();

    document.querySelectorAll(".product-card").forEach((card) => {
      let text = card.innerText.toLowerCase();

      if (text.indexOf(value) > -1) {
        card.style.display = "";
      } else {
        card.style.display = "none";
      }
    });
  });
}

window.addEventListener("load", () => {
  document.body.classList.add("loaded");
});

window.addEventListener("DOMContentLoaded", () => {
  const widget = document.querySelector(".tiny-widget");
  if (!widget) return;

  const closeBtn = widget.querySelector(".tiny-close");
  const dismiss = () => {
    widget.classList.add("is-hidden");
    try {
      localStorage.setItem("berlinmed_widget_dismissed", "1");
    } catch (e) {}
  };

  try {
    if (localStorage.getItem("berlinmed_widget_dismissed") === "1") {
      widget.classList.add("is-hidden");
    }
  } catch (e) {}

  if (closeBtn) closeBtn.addEventListener("click", dismiss);
});

console.log("BerlinMed Loaded Successfully");

