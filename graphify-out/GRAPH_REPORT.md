# Graph Report - .  (2026-07-23)

## Corpus Check
- code AST + HTML/MD/CSS/config/images (no LLM semantic pass; set OPENAI/GEMINI/ANTHROPIC key for deep doc/image concepts)

## Summary
- 261 nodes · 470 edges · 65 communities (64 shown, 1 thin omitted)
- Extraction: 100% EXTRACTED · 0% INFERRED · 0% AMBIGUOUS
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `7433b8cf`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- store.py
- script.js
- bot.py
- seo.py
- app.py
- enrich_graphify.py
- graphify

## God Nodes (most connected - your core abstractions)
1. `_abs_url()` - 8 edges
2. `_read()` - 7 edges
3. `_schema_for_page()` - 6 edges
4. `build_head_block()` - 5 edges
5. `add_booking()` - 5 edges
6. `initCookieBanner()` - 4 edges
7. `_base_url()` - 4 edges
8. `_serve_html()` - 4 edges
9. `_call_keyboard()` - 4 edges
10. `_owner_call_keyboard()` - 4 edges

## Surprising Connections (you probably didn't know these)
- None detected - all connections are within the same source files.

## Import Cycles
- None detected.

## Communities (65 total, 1 thin omitted)

### Community 1 - "store.py"
Cohesion: 0.09
Nodes (20): deploy.sh script, DEBIAN_FRONTEND, setup-server.sh script, bot_link(), Конфигурация сервера и бота. Все секреты берутся из .env / переменных окружения., Ссылка для клиента: открыть бота и сразу проверить статус по коду., add_booking(), _digits() (+12 more)

### Community 3 - "script.js"
Cohesion: 0.10
Nodes (17): animated, copyToClipboard(), formatPhone(), getPhoneDigits(), hasCookieConsent(), initAnalytics(), initCookieBanner(), lightbox (+9 more)

### Community 4 - "bot.py"
Cohesion: 0.14
Nodes (18): InlineKeyboardMarkup, _call_keyboard(), _client_text(), _e(), _normalize_phone(), notify_owners(), _owner_call_keyboard(), _owner_text() (+10 more)

### Community 5 - "seo.py"
Cohesion: 0.24
Nodes (15): _abs_url(), _analytics_meta(), _breadcrumb_schema(), build_head_block(), enhance(), _faq_schema(), _get_base(), _inject_cookie_banner() (+7 more)

### Community 6 - "app.py"
Cohesion: 0.26
Nodes (9): api_booking(), _base_url(), _client_ip(), index(), Веб-сервер сервиса «Низкий профиль».  Делает три вещи в одном процессе: 1. Отдаё, _register_html_routes(), robots(), _serve_html() (+1 more)

### Community 7 - "enrich_graphify.py"
Cohesion: 0.29
Nodes (3): Path, Enrich graphify-out/graph.json with HTML/MD/CSS/config/image file nodes., rel()

## Knowledge Gaps
- **11 isolated node(s):** `python`, `deploy.sh script`, `setup-server.sh script`, `DEBIAN_FRONTEND`, `navToggle` (+6 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **1 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What connects `python`, `deploy.sh script`, `setup-server.sh script` to the rest of the system?**
  _11 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `index.html` be split into smaller, more focused modules?**
  _Cohesion score 0.12316384180790961 - nodes in this community are weakly interconnected._
- **Should `store.py` be split into smaller, more focused modules?**
  _Cohesion score 0.0928030303030303 - nodes in this community are weakly interconnected._
- **Should `gallery.html` be split into smaller, more focused modules?**
  _Cohesion score 0.07407407407407407 - nodes in this community are weakly interconnected._
- **Should `script.js` be split into smaller, more focused modules?**
  _Cohesion score 0.10333333333333333 - nodes in this community are weakly interconnected._
- **Should `bot.py` be split into smaller, more focused modules?**
  _Cohesion score 0.14210526315789473 - nodes in this community are weakly interconnected._