document.documentElement.classList.add("animations-ready");

const COOKIE_CONSENT_KEY = "np_cookie_consent";

function hasCookieConsent() {
  try {
    return window.localStorage.getItem(COOKIE_CONSENT_KEY) === "1";
  } catch (_) {
    return false;
  }
}

function setCookieConsent() {
  try {
    window.localStorage.setItem(COOKIE_CONSENT_KEY, "1");
  } catch (_) {
    /* localStorage может быть недоступен */
  }
}

function initAnalytics() {
  const meta = document.querySelector('meta[name="np-yandex-metrika"]');
  const counterId = meta && meta.getAttribute("content");
  if (!counterId || window.__npMetrikaLoaded) return;

  window.__npMetrikaLoaded = true;
  (function (m, e, t, r, i, k, a) {
    m[i] = m[i] || function () { (m[i].a = m[i].a || []).push(arguments); };
    m[i].l = 1 * new Date();
    k = e.createElement(t);
    a = e.getElementsByTagName(t)[0];
    k.async = 1;
    k.src = r;
    a.parentNode.insertBefore(k, a);
  })(window, document, "script", "https://mc.yandex.ru/metrika/tag.js", "ym");

  window.ym(counterId, "init", {
    clickmap: true,
    trackLinks: true,
    accurateTrackBounce: true,
    webvisor: true
  });
}

function initCookieBanner() {
  const banner = document.getElementById("cookieBanner");
  if (!banner) return;

  if (hasCookieConsent()) {
    initAnalytics();
    return;
  }

  banner.hidden = false;
  const acceptBtn = document.getElementById("cookieAccept");
  if (acceptBtn) {
    acceptBtn.addEventListener("click", () => {
      setCookieConsent();
      banner.hidden = true;
      initAnalytics();
    });
  }
}

function injectPrivacyConsent() {
  document.querySelectorAll(".booking-form").forEach((form) => {
    if (form.querySelector('[name="privacy_consent"]')) return;
    const submitBtn = form.querySelector('button[type="submit"]');
    if (!submitBtn) return;

    const label = document.createElement("label");
    label.className = "form-consent";
    label.innerHTML =
      '<input type="checkbox" name="privacy_consent" required>' +
      '<span>Соглашаюсь с <a href="privacy.html" target="_blank" rel="noopener">политикой конфиденциальности</a> и обработкой персональных данных</span>';
    submitBtn.insertAdjacentElement("beforebegin", label);
  });
}

function refreshIcons() {
  if (window.lucide) {
    window.lucide.createIcons();
  }
}

const navToggle = document.querySelector(".nav-toggle");
const navLinks = document.querySelector(".nav-links");
const modal = document.getElementById("bookingModal");
const lightbox = document.getElementById("lightbox");

if (navToggle && navLinks) {
  navToggle.addEventListener("click", () => {
    const isOpen = navLinks.classList.toggle("is-open");
    navToggle.setAttribute("aria-expanded", String(isOpen));
  });

  navLinks.querySelectorAll("a").forEach((link) => {
    link.addEventListener("click", () => {
      navLinks.classList.remove("is-open");
      navToggle.setAttribute("aria-expanded", "false");
    });
  });
}

function openModal() {
  if (!modal) return;
  modal.classList.add("is-open");
  modal.classList.add("is-opening");
  modal.setAttribute("aria-hidden", "false");
  document.body.classList.add("modal-lock");
  window.setTimeout(() => modal.classList.remove("is-opening"), 420);
}

function closeModal() {
  if (!modal) return;
  modal.classList.remove("is-open");
  modal.classList.remove("is-opening");
  modal.setAttribute("aria-hidden", "true");
  document.body.classList.remove("modal-lock");
}

document.querySelectorAll("[data-open-booking]").forEach((button) => {
  button.addEventListener("click", () => {
    button.classList.remove("is-clicked");
    void button.offsetWidth;
    button.classList.add("is-clicked");
    window.setTimeout(openModal, 170);
  });

  button.addEventListener("animationend", () => {
    button.classList.remove("is-clicked");
  });
});

document.querySelectorAll("[data-close-modal]").forEach((button) => {
  button.addEventListener("click", closeModal);
});

const phoneInputs = document.querySelectorAll('input[type="tel"][name="phone"]');

function getPhoneDigits(value) {
  const digits = value.replace(/\D/g, "");
  const startsWithCountryCode = value.trim().startsWith("+7") || (digits.length > 10 && (digits[0] === "7" || digits[0] === "8"));
  const withoutCountry = startsWithCountryCode ? digits.slice(1) : digits;
  return withoutCountry.slice(0, 10);
}

function formatPhone(value) {
  const digits = getPhoneDigits(value);
  let result = "+7";

  if (!digits.length) return `${result} `;
  result += ` (${digits.slice(0, 3)}`;
  if (digits.length >= 3) result += ")";
  if (digits.length > 3) result += ` ${digits.slice(3, 6)}`;
  if (digits.length > 6) result += `-${digits.slice(6, 8)}`;
  if (digits.length > 8) result += `-${digits.slice(8, 10)}`;

  return result;
}

function updatePhoneValidity(input) {
  const digits = getPhoneDigits(input.value);
  input.setCustomValidity(digits.length === 10 ? "" : "Введите 10 цифр после +7");
}

phoneInputs.forEach((input) => {
  input.placeholder = "+7 (___) ___-__-__";
  input.maxLength = 18;
  input.inputMode = "tel";
  input.autocomplete = "tel";

  input.addEventListener("focus", () => {
    if (!input.value.trim()) {
      input.value = "+7 ";
    }
  });

  input.addEventListener("input", () => {
    input.value = formatPhone(input.value);
    input.setSelectionRange(input.value.length, input.value.length);
    updatePhoneValidity(input);
  });

  input.addEventListener("blur", () => {
    if (!getPhoneDigits(input.value).length) {
      input.value = "";
      input.setCustomValidity("");
      return;
    }
    updatePhoneValidity(input);
  });
});

// Адрес бэкенда. Пусто = тот же домен, что и сайт (когда сайт открыт через сервер).
// Если сайт и сервер на разных адресах, задайте window.BOOKING_API_BASE до подключения script.js.
const BOOKING_API = (window.BOOKING_API_BASE || "") + "/api/booking";

const SITE_PHONE = "+79654357272";

async function copyToClipboard(text) {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch (error) {
    const area = document.createElement("textarea");
    area.value = text;
    area.style.position = "fixed";
    area.style.opacity = "0";
    document.body.appendChild(area);
    area.focus();
    area.select();
    let ok = false;
    try {
      ok = document.execCommand("copy");
    } catch (_) {
      ok = false;
    }
    document.body.removeChild(area);
    return ok;
  }
}

function showBookingSuccess(form, code, botLink) {
  const previous = form.parentNode && form.parentNode.querySelector(".booking-success");
  if (previous) previous.remove();

  const box = document.createElement("div");
  box.className = "booking-success";

  const telegramBtn = botLink
    ? `<a class="btn btn--small btn--primary" href="${botLink}" target="_blank" rel="noopener"><i data-lucide="send"></i>Открыть в Telegram</a>`
    : "";

  box.innerHTML =
    `<p class="booking-success__title">Заявка принята! Ваш код:</p>` +
    `<div class="booking-success__code"><span class="booking-code">${code}</span></div>` +
    `<div class="booking-success__actions">` +
    `<button type="button" class="btn btn--small btn--ghost copy-code-btn"><i data-lucide="copy"></i>Копировать код</button>` +
    `<a class="btn btn--small btn--call" href="tel:${SITE_PHONE}"><i data-lucide="phone"></i>Позвонить</a>` +
    telegramBtn +
    `</div>`;

  form.insertAdjacentElement("afterend", box);
  refreshIcons();

  const copyBtn = box.querySelector(".copy-code-btn");
  if (copyBtn) {
    copyBtn.addEventListener("click", async () => {
      const done = await copyToClipboard(code);
      const original = copyBtn.innerHTML;
      copyBtn.classList.add("is-copied");
      copyBtn.innerHTML = done ? "Скопировано!" : "Не удалось";
      window.setTimeout(() => {
        copyBtn.classList.remove("is-copied");
        copyBtn.innerHTML = original;
        refreshIcons();
      }, 1600);
    });
  }
}

const BOOKING_COOLDOWN_MS = 5 * 60 * 1000;
const BOOKING_COOLDOWN_KEY = "nb_last_booking";

function bookingCooldownLeft() {
  let last = 0;
  try {
    last = parseInt(window.localStorage.getItem(BOOKING_COOLDOWN_KEY) || "0", 10);
  } catch (_) {
    last = 0;
  }
  const passed = Date.now() - last;
  return passed >= 0 && passed < BOOKING_COOLDOWN_MS ? BOOKING_COOLDOWN_MS - passed : 0;
}

function markBookingSent() {
  try {
    window.localStorage.setItem(BOOKING_COOLDOWN_KEY, String(Date.now()));
  } catch (_) {
    /* localStorage может быть недоступен — не критично */
  }
}

function addHoneypot(form) {
  const trap = document.createElement("input");
  trap.type = "text";
  trap.name = "website";
  trap.tabIndex = -1;
  trap.autocomplete = "off";
  trap.setAttribute("aria-hidden", "true");
  trap.style.cssText = "position:absolute;left:-9999px;width:1px;height:1px;opacity:0;";
  form.appendChild(trap);
}

injectPrivacyConsent();

document.querySelectorAll(".booking-form").forEach((form) => {
  addHoneypot(form);
  form.dataset.renderTime = String(Date.now());

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const status = form.querySelector(".form-status");
    const submitBtn = form.querySelector('button[type="submit"]');

    form.querySelectorAll('input[type="tel"][name="phone"]').forEach(updatePhoneValidity);

    if (!form.reportValidity()) return;

    const cooldown = bookingCooldownLeft();
    if (cooldown > 0) {
      const minutes = Math.ceil(cooldown / 60000);
      if (status) {
        status.classList.add("is-error");
        status.textContent = `Вы недавно уже оставили заявку. Попробуйте через ${minutes} мин или позвоните нам.`;
      }
      return;
    }

    if (status) {
      status.classList.remove("is-error");
      status.textContent = "Отправляем заявку...";
    }
    if (submitBtn) submitBtn.disabled = true;

    const data = new FormData(form);
    const payload = {
      name: data.get("name") || "",
      phone: data.get("phone") || "",
      service: data.get("service") || "Шиномонтаж",
      comment: data.get("comment") || "",
      website: data.get("website") || "",
      elapsed: Date.now() - parseInt(form.dataset.renderTime || "0", 10)
    };

    try {
      const response = await fetch(BOOKING_API, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      const result = await response.json().catch(() => ({}));

      if (!response.ok || !result.ok) {
        if (status) {
          status.classList.add("is-error");
          status.textContent = result.error || "Не удалось отправить заявку. Позвоните нам: +7 965 435-72-72";
        }
        return;
      }

      markBookingSent();
      form.reset();
      if (status) {
        status.classList.remove("is-error");
        status.textContent = "";
      }
      showBookingSuccess(form, result.code || "", result.bot || "");
    } catch (error) {
      if (status) {
        status.classList.add("is-error");
        status.textContent = "Не удалось отправить заявку. Позвоните нам: +7 965 435-72-72";
      }
    } finally {
      if (submitBtn) submitBtn.disabled = false;
    }
  });
});

document.querySelectorAll(".gallery-card").forEach((button) => {
  button.addEventListener("click", () => {
    if (!lightbox) return;
    const image = lightbox.querySelector("img");
    image.src = button.dataset.full;
    lightbox.classList.add("is-open");
    lightbox.setAttribute("aria-hidden", "false");
    document.body.classList.add("modal-lock");
  });
});

function closeLightbox() {
  if (!lightbox) return;
  lightbox.classList.remove("is-open");
  lightbox.setAttribute("aria-hidden", "true");
  document.body.classList.remove("modal-lock");
  const image = lightbox.querySelector("img");
  if (image) image.src = "";
}

document.querySelectorAll("[data-close-lightbox]").forEach((button) => {
  button.addEventListener("click", closeLightbox);
});

document.addEventListener("keydown", (event) => {
  if (event.key !== "Escape") return;
  closeModal();
  closeLightbox();
});

const textRiseTargets = document.querySelectorAll([
  "h1",
  "h2",
  ".hero-subtitle",
  ".hero-list li",
  ".page-hero p",
  ".service-copy p",
  ".service-copy li",
  ".red-checks li",
  ".section-title-row h2",
  ".service-overview-card h2",
  ".service-overview-card p",
  ".contact-list li",
  ".footer-grid p"
].join(", "));

textRiseTargets.forEach((element, index) => {
  element.classList.add("text-rise");
  element.style.setProperty("--rise-delay", `${Math.min((index % 7) * 55, 330)}ms`);
});

const animated = document.querySelectorAll("[data-animate], .text-rise");
if ("IntersectionObserver" in window) {
  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.classList.add("is-visible");
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.14 });

  animated.forEach((element) => observer.observe(element));
  window.setTimeout(() => {
    animated.forEach((element) => element.classList.add("is-visible"));
  }, 900);
} else {
  animated.forEach((element) => element.classList.add("is-visible"));
}

initCookieBanner();
refreshIcons();
