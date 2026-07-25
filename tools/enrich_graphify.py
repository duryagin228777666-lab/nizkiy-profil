"""Enrich graphify-out/graph.json with HTML/MD/CSS/config/image file nodes."""
import json
import re
import hashlib
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "graphify-out" / "graph.json"
IGNORE_DIRS = {
    ".git", ".venv", "venv", "node_modules", "graphify-out",
    "__pycache__", ".cursor", "cache", "converted",
}
DOC_EXT = {".md", ".txt", ".rst", ".docx"}
WEB_EXT = {".html", ".htm", ".css"}
CFG_EXT = {".yml", ".yaml", ".toml", ".json", ".ini", ".conf", ".sh", ".bat"}
IMG_EXT = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".ico", ".svg"}
CODE_EXT = {".py", ".js", ".ts"}
NAMED = {"Dockerfile", "Makefile", "Procfile", "main", "robots.txt", "requirements.txt"}

data = json.loads(OUT.read_text(encoding="utf-8"))
nodes = {n["id"]: n for n in data.get("nodes", [])}
edges = list(data.get("links", data.get("edges", [])))


def nid(*parts: str) -> str:
    raw = "::".join(parts)
    return "file_" + hashlib.sha1(raw.encode()).hexdigest()[:16]


def rel(p: Path) -> str:
    return p.relative_to(ROOT).as_posix()


src_index = defaultdict(list)
for n in nodes.values():
    src = (n.get("source") or n.get("file") or "").replace("\\", "/")
    if src:
        src_index[Path(src).name].append(n["id"])
        src_index[src].append(n["id"])

html_refs = defaultdict(set)
css_js_use = defaultdict(set)
css_refs = defaultdict(set)

# Attributes that can point at local assets, plus CSS url(...) used inline
# (e.g. style="--service-bg:url('...')") so background images are not orphaned.
ATTR_RE = re.compile(
    r'(?:src|href|poster|data-full|data-src|data-thumb)=["\']([^"\']+)["\']', re.I
)
URL_RE = re.compile(r'url\(\s*["\']?([^"\')]+)["\']?\s*\)', re.I)


def resolve_local(base_dir, ref):
    """Return repo-relative path for a local reference, or None if external/missing."""
    ref = ref.split("?")[0].split("#")[0].strip()
    if not ref or ref.startswith(("http://", "https://", "mailto:", "tel:", "data:", "//")):
        return None
    target = (base_dir / ref).resolve()
    try:
        trel = target.relative_to(ROOT).as_posix()
    except ValueError:
        return None
    return trel if target.exists() else None


for html in ROOT.rglob("*.html"):
    if any(part in IGNORE_DIRS for part in html.parts):
        continue
    text = html.read_text(encoding="utf-8", errors="ignore")
    hrel = rel(html)
    for m in ATTR_RE.finditer(text):
        trel = resolve_local(html.parent, m.group(1))
        if not trel:
            continue
        html_refs[hrel].add(trel)
        if trel.endswith((".css", ".js")):
            css_js_use[hrel].add(trel)
    # inline url(...) in style attributes / <style> blocks (background images)
    for m in URL_RE.finditer(text):
        trel = resolve_local(html.parent, m.group(1))
        if trel:
            html_refs[hrel].add(trel)

# Parse CSS files so background images referenced from stylesheets get linked
# to the stylesheet node instead of floating as isolated assets.
for css in ROOT.rglob("*.css"):
    if any(part in IGNORE_DIRS for part in css.parts):
        continue
    crel = rel(css)
    ctext = css.read_text(encoding="utf-8", errors="ignore")
    for m in URL_RE.finditer(ctext):
        trel = resolve_local(css.parent, m.group(1))
        if trel:
            css_refs[crel].add(trel)

# Parse Python/JS for asset paths served at runtime (e.g. seo.py injects
# "/assets/images/favicon.ico" into <head>). These are real references that
# static HTML parsing cannot see, so link them from the code file.
code_refs = defaultdict(set)
code_name_refs = defaultdict(set)
ASSET_STR_RE = re.compile(
    r'["\']((?:/|\./|\.\./|assets/)[^"\']*?\.(?:png|jpe?g|webp|gif|ico|svg))["\']',
    re.I,
)
# Bare data-file names referenced by code, e.g. config.py -> "bookings.json".
DATA_STR_RE = re.compile(r'["\']([A-Za-z0-9._\-/]+\.(?:json|txt|xml))["\']', re.I)
for code in list(ROOT.rglob("*.py")) + list(ROOT.rglob("*.js")):
    if any(part in IGNORE_DIRS for part in code.parts):
        continue
    krel = rel(code)
    ktext = code.read_text(encoding="utf-8", errors="ignore")
    for m in ASSET_STR_RE.finditer(ktext):
        ref = m.group(1).lstrip("/")
        trel = resolve_local(ROOT, ref)
        if trel:
            code_refs[krel].add(trel)
    for m in DATA_STR_RE.finditer(ktext):
        code_name_refs[krel].add(Path(m.group(1)).name)

added_nodes = 0
added_edges = 0
existing_edge_keys = set()
for e in edges:
    s = e.get("source") or e.get("from")
    t = e.get("target") or e.get("to")
    r = e.get("relation") or e.get("type") or e.get("label") or "related"
    existing_edge_keys.add((s, t, r))


def add_node(node_id, label, ntype, source, **extra):
    global added_nodes
    if node_id in nodes:
        return nodes[node_id]
    n = {
        "id": node_id,
        "label": label,
        "file_type": ntype,
        "source_file": source,
        "source_location": "L1",
        "_origin": "enrich",
        "norm_label": label.lower(),
    }
    n.update({k: v for k, v in extra.items() if v is not None})
    nodes[node_id] = n
    added_nodes += 1
    return n


def add_edge(src, tgt, relation="references", confidence="EXTRACTED", context="file"):
    global added_edges
    key = (src, tgt, relation)
    if key in existing_edge_keys or src not in nodes or tgt not in nodes:
        return
    src_file = nodes[src].get("source_file") or nodes[src].get("path") or ""
    edges.append({
        "source": src,
        "target": tgt,
        "relation": relation,
        "confidence": confidence,
        "confidence_score": 1.0,
        "context": context,
        "source_file": src_file,
        "source_location": "L1",
        "weight": 1.0,
        "_origin": "enrich",
        "directed": True,
    })
    existing_edge_keys.add(key)
    added_edges += 1


file_nodes = {}

for path in ROOT.rglob("*"):
    if not path.is_file():
        continue
    if any(part in IGNORE_DIRS for part in path.parts):
        continue
    if path.name.startswith(".env") and path.name != ".env.example":
        continue
    ext = path.suffix.lower()
    if ext not in (CODE_EXT | DOC_EXT | WEB_EXT | CFG_EXT | IMG_EXT) and path.name not in NAMED:
        continue

    r = rel(path)
    if ext in CODE_EXT:
        # Prefer existing AST file/module node; do not create a duplicate.
        node_id = None
        for cand in src_index.get(r, []) + src_index.get(path.name, []):
            n = nodes[cand]
            if n.get("label") == path.name or n.get("source_file") == r:
                node_id = cand
                break
        if node_id:
            file_nodes[r] = node_id
            continue
        node_id = nid("codefile", r)
        add_node(node_id, path.name, "code", r)
        file_nodes[r] = node_id
        continue

    if ext in DOC_EXT or path.name in {"robots.txt", "requirements.txt"}:
        ntype = "document"
    elif ext in WEB_EXT:
        ntype = "web"
    elif ext in CFG_EXT or path.name in {"Dockerfile", "fly.toml", "docker-compose.yml", "main"}:
        ntype = "config"
    elif ext in IMG_EXT:
        ntype = "image"
    else:
        ntype = "file"

    node_id = nid("file", r)
    label = path.name if len(path.name) < 80 else r
    add_node(node_id, label, ntype, r, path=r)
    file_nodes[r] = node_id

for hrel, refs in html_refs.items():
    hid = file_nodes.get(hrel)
    if not hid:
        continue
    for trel in refs:
        tid = file_nodes.get(trel)
        if tid:
            add_edge(hid, tid, "references")
    for trel in css_js_use.get(hrel, set()):
        for sid in src_index.get(Path(trel).name, []):
            add_edge(hid, sid, "uses")

for crel, refs in css_refs.items():
    cid = file_nodes.get(crel)
    if not cid:
        continue
    for trel in refs:
        tid = file_nodes.get(trel)
        if tid:
            add_edge(cid, tid, "references")

for krel, refs in code_refs.items():
    kid = file_nodes.get(krel)
    if not kid:
        continue
    for trel in refs:
        tid = file_nodes.get(trel)
        if tid:
            add_edge(kid, tid, "references")

# Link code files to data files (bookings.json etc.) matched by basename.
name_index = {}
for r, fid in file_nodes.items():
    name_index.setdefault(Path(r).name, fid)
for krel, names in code_name_refs.items():
    kid = file_nodes.get(krel)
    if not kid:
        continue
    for name in names:
        tid = name_index.get(name)
        if tid and tid != kid:
            add_edge(kid, tid, "references")

readme_id = file_nodes.get("README.md")
for r, fid in file_nodes.items():
    if r.endswith(".md") and r != "README.md" and readme_id:
        add_edge(readme_id, fid, "documents")

for r, fid in list(file_nodes.items()):
    if r.startswith("server/") and r.endswith(".py"):
        for doc in ("ИНСТРУКЦИЯ-БОТ.md", "ИНСТРУКЦИЯ-VPS.md", "README.md"):
            did = file_nodes.get(doc)
            if did:
                add_edge(did, fid, "describes")

for cfg in (
    "Dockerfile",
    "docker-compose.yml",
    "fly.toml",
    "deploy/nginx-site.conf",
    "deploy/deploy.sh",
    "deploy/setup-server.sh",
):
    cid = file_nodes.get(cfg)
    vid = file_nodes.get("ИНСТРУКЦИЯ-VPS.md")
    if cid and vid:
        add_edge(vid, cid, "describes")

out = {
    "directed": data.get("directed", True),
    "multigraph": data.get("multigraph", False),
    "graph": data.get("graph", {}),
    "nodes": list(nodes.values()),
    "links": edges,
}
OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"nodes_total={len(nodes)} edges_total={len(edges)}")
print(f"added_nodes={added_nodes} added_edges={added_edges} file_nodes={len(file_nodes)}")
