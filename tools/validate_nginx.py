"""Static checks on frontend/nginx.conf.

nginx is not installed on this machine, so `nginx -t` cannot be run. These
checks therefore cover what can be verified offline: block structure, the
directives that matter for a single-page app, and consistency with the
Dockerfile that installs this file.

This is explicitly NOT a substitute for `nginx -t`, and says so when it passes.
"""

from __future__ import annotations

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
conf = (ROOT / "frontend" / "nginx.conf").read_text(encoding="utf-8")
dockerfile = (ROOT / "frontend" / "Dockerfile").read_text(encoding="utf-8")
compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")

errors: list[str] = []
warnings: list[str] = []

# --- 1. Comments removed, for structural checks -----------------------------
no_comments = "\n".join(re.sub(r"#.*$", "", line) for line in conf.splitlines())

# --- 2. Braces must balance -------------------------------------------------
depth = 0
for ch in no_comments:
    if ch == "{":
        depth += 1
    elif ch == "}":
        depth -= 1
        if depth < 0:
            errors.append("a closing brace appears without a matching opening brace")
            break
if depth != 0:
    errors.append(f"{depth} unclosed block(s) — braces do not balance")

# --- 3. Every statement must be terminated ----------------------------------
# A statement ends with ";" or opens a block with "{". Directives with multiple
# values may span several lines (gzip_types does), so blank-line-separated
# chunks are joined before checking termination.
BLOCK_OPENERS = {"server", "location", "if", "map", "upstream"}
KNOWN = {
    "add_header", "default_type", "error_page", "expires", "gzip", "gzip_min_length",
    "gzip_types", "gzip_vary", "index", "listen", "proxy_http_version", "proxy_pass",
    "proxy_read_timeout", "proxy_set_header", "return", "root", "server_name",
    "try_files", "access_log", "error_log", "include", "charset", "sendfile",
    "keepalive_timeout", "client_max_body_size",
}

chunk: list[str] = []
for lineno, raw in enumerate(no_comments.splitlines(), 1):
    line = raw.strip()
    if not line:
        continue
    if line == "}":
        if chunk:
            errors.append(f"line {lineno}: statement never terminated: {' '.join(chunk)!r}")
            chunk = []
        continue
    chunk.append(line)
    if line.endswith(";") or line.endswith("{"):
        joined = " ".join(chunk)
        first = joined.split()[0]
        if joined.endswith("{"):
            if first not in BLOCK_OPENERS:
                errors.append(f"line {lineno}: {first!r} does not open a known block")
        else:
            if first not in KNOWN:
                errors.append(f"line {lineno}: unknown directive {first!r}")
        chunk = []

if chunk:
    errors.append(f"trailing unterminated statement: {' '.join(chunk)!r}")

# --- 4. The things a single-page app actually needs -------------------------
checks = {
    "listens on port 80": r"^\s*listen\s+80\s*;",
    "declares a server block": r"^\s*server\s*\{",
    "SPA fallback to index.html": r"try_files\s+\$uri\s+\$uri/\s+/index\.html\s*;",
    "does not cache index.html": r"location\s+=\s+/index\.html",
    "gzip enabled": r"^\s*gzip\s+on\s*;",
    "clickjacking header": r"X-Frame-Options",
    "nosniff header": r"X-Content-Type-Options",
    "immutable caching for hashed assets": r"location\s+/assets/",
}
for label, pattern in checks.items():
    if not re.search(pattern, no_comments, re.MULTILINE):
        errors.append(f"missing: {label}")

# --- 5. Consistency with the Dockerfile and Compose -------------------------
if "/usr/share/nginx/html" not in conf:
    errors.append("nginx root does not point at the directory the Dockerfile fills")
if "COPY nginx.conf /etc/nginx/conf.d/default.conf" not in dockerfile:
    errors.append("Dockerfile does not place nginx.conf where nginx reads it")
if "COPY --from=build /app/dist /usr/share/nginx/html" not in dockerfile:
    errors.append("Dockerfile does not copy the built assets into the nginx web root")

m = re.search(r"proxy_pass\s+http://([A-Za-z0-9_.-]+):(\d+)", no_comments)
if m:
    host, port = m.group(1), m.group(2)
    if f"  {host}:" not in compose:
        errors.append(f"nginx proxies to host {host!r}, which is not a Compose service")
    else:
        print(f"proxy upstream:  OK (http://{host}:{port} matches a Compose service)")

# --- 6. The proxy block is only correct if the app is built to use it -------
if "location /api/" in no_comments:
    warnings.append(
        "the /api/ proxy block exists but is only used when the frontend is built "
        "with VITE_API_BASE_URL=/api; the default build calls http://localhost:8000 directly"
    )

print(f"braces balanced: {not any('balance' in e for e in errors)}")
print(f"errors:   {len(errors)}")
for e in errors:
    print("  *", e)
print(f"warnings: {len(warnings)}")
for w in warnings:
    print("  -", w)
print()

if errors:
    print("NGINX CONFIG STATIC VALIDATION: FAIL")
    sys.exit(1)

print("NGINX CONFIG STATIC VALIDATION: PASS")
print("NOTE: structural check only. `nginx -t` has NOT been run, because nginx is")
print("      not installed on this machine.")
