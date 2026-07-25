# Graph Report - NIZKIPROF  (2026-07-25)

## Corpus Check
- 14 files · ~588,958 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 289 nodes · 610 edges · 19 communities (18 shown, 1 thin omitted)
- Extraction: 100% EXTRACTED · 0% INFERRED · 0% AMBIGUOUS · INFERRED: 1 edges (avg confidence: 0.5)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `53ae36a8`
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
- reminders.py

## God Nodes (most connected - your core abstractions)
1. `_handle_callback()` - 17 edges
2. `_handle_owner_text()` - 12 edges
3. `_read()` - 11 edges
4. `_handle_owner_menu_button()` - 9 edges
5. `_set_state()` - 8 edges
6. `_finish_visit()` - 8 edges
7. `_abs_url()` - 8 edges
8. `_owner_booking_keyboard()` - 7 edges
9. `_send_status()` - 7 edges
10. `_owner_text()` - 6 edges

## Surprising Connections (you probably didn't know these)
- None detected - all connections are within the same source files.

## Import Cycles
- None detected.

## Communities (19 total, 1 thin omitted)

### Community 1 - "store.py"
Cohesion: 0.08
Nodes (19): deploy.sh script, DEBIAN_FRONTEND, setup-server.sh script, api_booking(), _base_url(), _client_ip(), index(), _is_local_proxy() (+11 more)

### Community 3 - "script.js"
Cohesion: 0.10
Nodes (17): animated, copyToClipboard(), formatPhone(), getPhoneDigits(), hasCookieConsent(), initAnalytics(), initCookieBanner(), lightbox (+9 more)

### Community 4 - "bot.py"
Cohesion: 0.10
Nodes (50): InlineKeyboardMarkup, ReplyKeyboardMarkup, _ask_day(), _ask_time(), _call_keyboard(), _clear_state(), _client_menu_keyboard(), _client_text() (+42 more)

### Community 5 - "seo.py"
Cohesion: 0.22
Nodes (15): _abs_url(), _analytics_meta(), _breadcrumb_schema(), build_head_block(), enhance(), _faq_schema(), _get_base(), _inject_cookie_banner() (+7 more)

### Community 6 - "app.py"
Cohesion: 0.13
Nodes (27): datetime, active_for_visit(), add_booking(), _digits(), due_for_reminder(), find_by_phone(), format_visit_at(), format_visit_human() (+19 more)

### Community 7 - "enrich_graphify.py"
Cohesion: 0.15
Nodes (5): Path, Enrich graphify-out/graph.json with HTML/MD/CSS/config/image file nodes., Return repo-relative path for a local reference, or None if external/missing., rel(), resolve_local()

### Community 9 - "reminders.py"
Cohesion: 0.27
Nodes (11): _e(), _loop(), _mask_phone(), notify_owners_reminder(), process_due(), Напоминания о визите.  Сейчас SMS не подключено: при срабатывании пишем в лог, Отправить напоминание клиенту.      Заглушка до подключения SMS: возвращает Tr, # TODO: SMS.ru — отправка по API (SMS_API_ID в .env) (+3 more)

## Knowledge Gaps
- **11 isolated node(s):** `python`, `deploy.sh script`, `setup-server.sh script`, `DEBIAN_FRONTEND`, `navToggle` (+6 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **1 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What connects `python`, `deploy.sh script`, `setup-server.sh script` to the rest of the system?**
  _11 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `index.html` be split into smaller, more focused modules?**
  _Cohesion score 0.09090909090909091 - nodes in this community are weakly interconnected._
- **Should `store.py` be split into smaller, more focused modules?**
  _Cohesion score 0.0773109243697479 - nodes in this community are weakly interconnected._
- **Should `gallery.html` be split into smaller, more focused modules?**
  _Cohesion score 0.07692307692307693 - nodes in this community are weakly interconnected._
- **Should `script.js` be split into smaller, more focused modules?**
  _Cohesion score 0.10333333333333333 - nodes in this community are weakly interconnected._
- **Should `bot.py` be split into smaller, more focused modules?**
  _Cohesion score 0.09568627450980392 - nodes in this community are weakly interconnected._
- **Should `app.py` be split into smaller, more focused modules?**
  _Cohesion score 0.1330049261083744 - nodes in this community are weakly interconnected._