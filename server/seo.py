"""SEO-метаданные и вставка тегов в HTML при отдаче страниц."""
import json
import re
from html import escape

import config

BRAND = "Низкий профиль"
LOCALITY = "Жулебино, Москва"
ADDRESS = "Москва, ул. Привольная, 70к1"
PHONE = "+7 965 435-72-72"
EMAIL = "info@nizkiyprofil.ru"
HOURS = "Mo-Su 09:00-22:00"
GEO_LAT = 55.6778
GEO_LNG = 37.8546
YANDEX_MAPS = "https://yandex.ru/maps/org/nizkiy_profil/206629737472/"
DEFAULT_OG_IMAGE = "assets/images/hero-workshop.jpg"

FAQ_ITEMS = [
    {
        "q": "Где находится шиномонтаж?",
        "a": "Москва, ул. Привольная, 70к1, район Жулебино. Удобно заехать с м. Кузьминки и Выхино.",
    },
    {
        "q": "Какой график работы?",
        "a": "Ежедневно с 9:00 до 22:00, без выходных.",
    },
    {
        "q": "Работаете ли с RunFlat и низким профилем?",
        "a": "Да, это наша специализация. Аккуратно монтируем RunFlat, низкий профиль и усиленный борт.",
    },
    {
        "q": "До какого радиуса берётесь?",
        "a": "До R24, включая легковые, кроссоверы, внедорожные A/T и M/T, а также мото-колёса.",
    },
    {
        "q": "Что такое виброконтроль Hunter?",
        "a": (
            "Диагностика колеса под дорожной нагрузкой на стенде Hunter Road Force Elite. "
            "Помогает найти вибрацию, боковой увод и неоднородность шины, "
            "которую не видно при обычной балансировке."
        ),
    },
]

_runtime_base_url: str | None = None


def set_base_url(url: str | None) -> None:
    global _runtime_base_url
    _runtime_base_url = url.rstrip("/") if url else None


def _get_base() -> str:
    if _runtime_base_url:
        return _runtime_base_url
    return config.SITE_URL

HTML_PAGES = [
    "index.html",
    "about.html",
    "services.html",
    "gallery.html",
    "price.html",
    "contacts.html",
    "faq.html",
    "privacy.html",
    "recommendations.html",
    "shinomontazh.html",
    "prodazha-shin.html",
    "vibrocontrol.html",
    "balansirovka.html",
    "pravka-diskov.html",
    "argonnaya-svarka.html",
    "pokraska-diskov.html",
    "hranenie-shin.html",
]

PAGES = {
    "index.html": {
        "path": "/",
        "title": f"Шиномонтаж в Жулебино — {BRAND} | Hunter, диски до R24",
        "description": (
            f"Шиномонтаж в {LOCALITY}: низкий профиль, RunFlat, диски до R24, "
            "виброконтроль Hunter Road Force Elite, правка, сварка, покраска дисков и хранение шин. "
            f"Ежедневно 9:00–22:00, {ADDRESS}."
        ),
        "og_image": DEFAULT_OG_IMAGE,
    },
    "about.html": {
        "path": "/about.html",
        "title": f"О сервисе — {BRAND} | шиномонтаж в {LOCALITY}",
        "description": (
            f"О шиномонтаже «{BRAND}» в {LOCALITY}: сложные колеса до R24, RunFlat, "
            "A/T и M/T, виброконтроль Hunter Road Force Elite, правка, сварка, покраска и хранение."
        ),
    },
    "services.html": {
        "path": "/services.html",
        "title": f"Услуги шиномонтажа и ремонта дисков — {BRAND}",
        "description": (
            "Шиномонтаж, балансировка, продажа шин, виброконтроль Hunter, правка, "
            "аргонная сварка, порошковая покраска и сезонное хранение колес в одном сервисе."
        ),
    },
    "gallery.html": {
        "path": "/gallery.html",
        "title": f"Фото работ и сервиса — {BRAND}",
        "description": (
            f"Фото шиномонтажа «{BRAND}»: оборудование Hunter, ремонт дисков, "
            "рабочая зона и автомобили клиентов в сервисе."
        ),
        "og_image": "assets/images/work-dodge-charger.jpg",
    },
    "price.html": {
        "path": "/price.html",
        "title": f"Прайс на шиномонтаж и работы с дисками — {BRAND}",
        "description": (
            "Стоимость шиномонтажа, правки, покраски, хранения шин и виброконтроля "
            "в зависимости от радиуса, профиля, RunFlat и типа автомобиля."
        ),
    },
    "contacts.html": {
        "path": "/contacts.html",
        "title": f"Контакты и запись — {BRAND} | {LOCALITY}",
        "description": (
            f"Контакты шиномонтажа «{BRAND}»: {ADDRESS}, телефон {PHONE}, "
            "график ежедневно 9:00–22:00. Запись онлайн и на карте."
        ),
    },
    "faq.html": {
        "path": "/faq.html",
        "title": f"Частые вопросы — {BRAND} | шиномонтаж в {LOCALITY}",
        "description": (
            f"Ответы на частые вопросы о шиномонтаже «{BRAND}» в {LOCALITY}: "
            "адрес, график работы, RunFlat, радиус до R24 и виброконтроль Hunter."
        ),
    },
    "privacy.html": {
        "path": "/privacy.html",
        "title": f"Политика конфиденциальности — {BRAND}",
        "description": (
            f"Политика обработки персональных данных и использования cookie "
            f"на сайте шиномонтажа «{BRAND}»."
        ),
    },
    "recommendations.html": {
        "path": "/recommendations.html",
        "title": f"Рекомендательные технологии — {BRAND}",
        "description": (
            f"Информация о применении рекомендательных технологий на сайте "
            f"шиномонтажа «{BRAND}»."
        ),
    },
    "shinomontazh.html": {
        "path": "/shinomontazh.html",
        "title": f"Шиномонтаж сложных колес до R24 — {BRAND} | {LOCALITY}",
        "description": (
            f"Шиномонтаж и балансировка в {LOCALITY}: низкий профиль, RunFlat, A/T, M/T, "
            "мото-колеса и диски до R24 с аккуратной сборкой."
        ),
        "service": "Шиномонтаж",
    },
    "prodazha-shin.html": {
        "path": "/prodazha-shin.html",
        "title": f"Продажа шин R13–R22 — {BRAND} | {LOCALITY}",
        "description": (
            "Продажа новых и б/у шин, пары и комплекты R13–R22, RunFlat. "
            "Подбор по размеру, сезону и индексу нагрузки."
        ),
        "service": "Продажа шин",
    },
    "vibrocontrol.html": {
        "path": "/vibrocontrol.html",
        "title": f"Виброконтроль Hunter Road Force Elite — {BRAND}",
        "description": (
            "Диагностика колеса под дорожной нагрузкой на Hunter Road Force Elite: "
            "поиск вибрации, бокового увода и неоднородности шины."
        ),
        "service": "Виброконтроль Hunter",
    },
    "balansirovka.html": {
        "path": "/balansirovka.html",
        "title": f"Балансировка колес — {BRAND} | {LOCALITY}",
        "description": (
            f"Балансировка колес в {LOCALITY}: проверка диска и шины, точная установка грузов "
            "и контроль результата на стенде."
        ),
        "service": "Балансировка колес",
    },
    "pravka-diskov.html": {
        "path": "/pravka-diskov.html",
        "title": f"Правка литых дисков — {BRAND} | {LOCALITY}",
        "description": (
            f"Правка литых дисков в {LOCALITY}: восстановление геометрии после ударов, "
            "проверка биения и подготовка к балансировке."
        ),
        "service": "Правка дисков",
    },
    "argonnaya-svarka.html": {
        "path": "/argonnaya-svarka.html",
        "title": f"Аргонная сварка дисков — {BRAND} | {LOCALITY}",
        "description": (
            "Аргонная сварка литых дисков: ремонт трещин, сколов и кромки после ударов, "
            "зачистка шва и покраска."
        ),
        "service": "Аргонная сварка",
    },
    "pokraska-diskov.html": {
        "path": "/pokraska-diskov.html",
        "title": f"Порошковая покраска дисков — {BRAND} | {LOCALITY}",
        "description": (
            "Порошковая покраска дисков: очистка, подготовка, подбор цвета и финиша "
            "после эксплуатации или ремонта."
        ),
        "service": "Порошковая покраска дисков",
    },
    "hranenie-shin.html": {
        "path": "/hranenie-shin.html",
        "title": f"Сезонное хранение шин — {BRAND} | {LOCALITY}",
        "description": (
            "Сезонное хранение шин и колес в сервисе до следующей замены. "
            "Проверка состояния перед установкой."
        ),
        "service": "Хранение шин",
    },
}


def _abs_url(path: str) -> str:
    base = _get_base()
    if path.startswith("http"):
        return path
    if not path.startswith("/"):
        path = f"/{path}"
    if not base:
        return path
    return f"{base}{path}"


def _local_business_schema() -> dict:
    return {
        "@context": "https://schema.org",
        "@type": "AutoRepair",
        "@id": _abs_url("/#organization"),
        "name": BRAND,
        "description": PAGES["index.html"]["description"],
        "url": _abs_url("/"),
        "telephone": PHONE,
        "email": EMAIL,
        "image": _abs_url(DEFAULT_OG_IMAGE),
        "address": {
            "@type": "PostalAddress",
            "streetAddress": "ул. Привольная, 70к1",
            "addressLocality": "Москва",
            "addressRegion": "Москва",
            "addressCountry": "RU",
        },
        "geo": {
            "@type": "GeoCoordinates",
            "latitude": GEO_LAT,
            "longitude": GEO_LNG,
        },
        "openingHours": HOURS,
        "sameAs": [YANDEX_MAPS],
        "priceRange": "₽₽",
    }


def _service_schema(service_name: str, page_path: str) -> dict:
    return {
        "@context": "https://schema.org",
        "@type": "Service",
        "name": service_name,
        "provider": {"@id": _abs_url("/#organization")},
        "areaServed": {"@type": "City", "name": "Москва"},
        "url": _abs_url(page_path),
    }


def _breadcrumb_schema(items: list[tuple[str, str]]) -> dict:
    return {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {
                "@type": "ListItem",
                "position": index + 1,
                "name": name,
                "item": _abs_url(path),
            }
            for index, (name, path) in enumerate(items)
        ],
    }


def _faq_schema() -> dict:
    return {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {
                "@type": "Question",
                "name": item["q"],
                "acceptedAnswer": {
                    "@type": "Answer",
                    "text": item["a"],
                },
            }
            for item in FAQ_ITEMS
        ],
    }


def _schema_for_page(page_key: str, page_meta: dict) -> list[dict]:
    schemas = [_local_business_schema()]
    path = page_meta["path"]

    if page_key == "index.html":
        return schemas

    if page_key == "faq.html":
        crumbs = [("Главная", "/"), ("Вопросы", path)]
        schemas.append(_breadcrumb_schema(crumbs))
        schemas.append(_faq_schema())
        return schemas

    crumbs = [("Главная", "/")]
    if page_key == "about.html":
        crumbs.append(("О нас", path))
    elif page_key == "services.html":
        crumbs.append(("Услуги", path))
    elif page_key == "gallery.html":
        crumbs.append(("Работы", path))
    elif page_key == "price.html":
        crumbs.append(("Прайс", path))
    elif page_key == "contacts.html":
        crumbs.append(("Контакты", path))
    elif page_meta.get("service"):
        crumbs.extend([("Услуги", "/services.html"), (page_meta["service"], path)])

    if len(crumbs) > 1:
        schemas.append(_breadcrumb_schema(crumbs))

    if page_meta.get("service"):
        schemas.append(_service_schema(page_meta["service"], path))

    return schemas


FOOTER_LEGAL = """      <p class="footer-legal"><a href="privacy.html">Политика конфиденциальности</a><span aria-hidden="true">·</span><a href="recommendations.html">Рекомендательные технологии</a></p>"""

COOKIE_BANNER = """  <aside class="cookie-banner" id="cookieBanner" role="dialog" aria-live="polite" aria-label="Уведомление о cookie" hidden>
    <div class="cookie-banner__inner section-shell">
      <p class="cookie-banner__text">Мы используем cookie и похожие технологии для работы сайта и аналитики. Подробнее — в <a href="privacy.html">политике конфиденциальности</a>. На сайте могут применяться <a href="recommendations.html">рекомендательные технологии</a>.</p>
      <button type="button" class="btn btn--primary btn--small" id="cookieAccept">Принять</button>
    </div>
  </aside>"""


def _analytics_meta() -> str:
    metrika_id = (config.YANDEX_METRIKA_ID or "").strip()
    return f'  <meta name="np-yandex-metrika" content="{escape(metrika_id)}">'


def _inject_footer_legal(html: str) -> str:
    if "footer-legal" in html:
        return html
    return re.sub(
        r'(<p class="footer-seo">.*?</p>)(\s*</div>\s*</footer>)',
        r"\1\n" + FOOTER_LEGAL + r"\2",
        html,
        count=1,
        flags=re.DOTALL,
    )


def _inject_cookie_banner(html: str) -> str:
    if "cookie-banner" in html:
        return html
    return html.replace("</body>", f"{COOKIE_BANNER}\n</body>", 1)


def build_head_block(page_key: str) -> str:
    page_meta = PAGES[page_key]
    canonical = _abs_url(page_meta["path"])
    title = page_meta["title"]
    description = page_meta["description"]
    og_image = _abs_url(page_meta.get("og_image", DEFAULT_OG_IMAGE))

    schemas = _schema_for_page(page_key, page_meta)
    schema_json = json.dumps(schemas if len(schemas) > 1 else schemas[0], ensure_ascii=False)
    schema_json = schema_json.replace("</", "<\\/")

    return f"""  <link rel="canonical" href="{escape(canonical)}">
  <link rel="icon" href="/assets/images/favicon.ico" type="image/x-icon">
  <link rel="shortcut icon" href="/assets/images/favicon.ico" type="image/x-icon">
  <link rel="apple-touch-icon" href="/assets/images/logo.png">
  <meta name="robots" content="index, follow">
  <meta property="og:type" content="website">
  <meta property="og:locale" content="ru_RU">
  <meta property="og:site_name" content="{escape(BRAND)}">
  <meta property="og:title" content="{escape(title)}">
  <meta property="og:description" content="{escape(description)}">
  <meta property="og:url" content="{escape(canonical)}">
  <meta property="og:image" content="{escape(og_image)}">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{escape(title)}">
  <meta name="twitter:description" content="{escape(description)}">
  <meta name="twitter:image" content="{escape(og_image)}">
  <script type="application/ld+json">{schema_json}</script>
{_analytics_meta()}"""


def enhance(html: str, page_key: str) -> str:
    page_meta = PAGES[page_key]
    title = page_meta["title"]
    description = page_meta["description"]

    html = re.sub(
        r"<title>.*?</title>",
        f"<title>{escape(title)}</title>",
        html,
        count=1,
        flags=re.DOTALL,
    )
    html = re.sub(
        r'<meta name="description" content="[^"]*">',
        f'<meta name="description" content="{escape(description)}">',
        html,
        count=1,
    )

    marker = "<!-- seo:auto -->"
    block = build_head_block(page_key)
    if marker in html:
        html = re.sub(
            rf"{re.escape(marker)}.*?(?=\s*</head>)",
            block,
            html,
            count=1,
            flags=re.DOTALL,
        )
    else:
        html = html.replace("</head>", f"{block}\n</head>", 1)

    html = _inject_footer_legal(html)
    html = _inject_cookie_banner(html)
    return html


def sitemap_xml() -> str:
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    for page_key in HTML_PAGES:
        page_meta = PAGES[page_key]
        priority = "1.0" if page_key == "index.html" else "0.8"
        if page_key in {
            "gallery.html",
            "balansirovka.html",
        }:
            priority = "0.6"
        lines.extend(
            [
                "  <url>",
                f"    <loc>{escape(_abs_url(page_meta['path']))}</loc>",
                f"    <changefreq>{'weekly' if page_key == 'index.html' else 'monthly'}</changefreq>",
                f"    <priority>{priority}</priority>",
                "  </url>",
            ]
        )
    lines.append("</urlset>")
    return "\n".join(lines) + "\n"


def robots_txt() -> str:
    return (
        "User-agent: *\n"
        "Allow: /\n"
        "Disallow: /api/\n"
        "Disallow: /server/\n"
        f"\nSitemap: {_abs_url('/sitemap.xml')}\n"
    )
