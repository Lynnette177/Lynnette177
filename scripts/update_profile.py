#!/usr/bin/env python3
"""Generate self-hosted profile SVGs using only Python's standard library.

Run: python3 scripts/update_profile.py
GITHUB_TOKEN is optional locally; Actions supplies its built-in token.
All requests must succeed before any asset is replaced. Never write API tokens.
"""

import collections
import concurrent.futures
import datetime as dt
import json
import os
from pathlib import Path
import time
import urllib.error
import urllib.request
from xml.sax.saxutils import escape


ROOT = Path(__file__).resolve().parents[1]
USERNAME = "Lynnette177"
THEMES = {
    "dark": {
        "bg": "#11121c", "text": "#f2f0ff", "muted": "#a5a5bf",
        "line": "#2a2b40", "accent": "#b9a0ff", "cyan": "#78ded6",
        "soft": "#1c1b30", "orb": "#22203b",
    },
    "light": {
        "bg": "#f6f5fc", "text": "#242139", "muted": "#65617e",
        "line": "#dedbea", "accent": "#7652c8", "cyan": "#147f80",
        "soft": "#eeebf8", "orb": "#e7e0f7",
    },
}
LANGUAGE_COLORS = {
    "C++": "#a895eb", "C": "#7ca8dd", "Python": "#e5bb6c",
    "Swift": "#e89986", "Objective-C++": "#9bc9bc",
    "Objective-C": "#8fc9e9", "JavaScript": "#daca7c",
    "TypeScript": "#78accd", "Lua": "#9ba3d9", "Go": "#79ced4",
    "HTML": "#dd9aaf", "Shell": "#a9c985", "Other": "#8a8c9c",
}


def api(path):
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": f"{USERNAME}-profile",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(f"https://api.github.com{path}", headers=headers)
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            if error.code not in (429, 500, 502, 503, 504) or attempt == 2:
                raise RuntimeError(f"GitHub API returned HTTP {error.code} for {path}") from None
        except (urllib.error.URLError, TimeoutError):
            if attempt == 2:
                raise RuntimeError(f"GitHub API request failed for {path}") from None
        time.sleep(2 ** (attempt + 1))


def collect():
    user = api(f"/users/{USERNAME}")
    repos = []
    page = 1
    while True:
        batch = api(f"/users/{USERNAME}/repos?type=owner&per_page=100&page={page}")
        repos.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    originals = [repo for repo in repos if not repo["fork"] and not repo["private"]]
    languages = collections.Counter()
    paths = [f"/repos/{repo['full_name']}/languages" for repo in originals]
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        for result in pool.map(api, paths):
            languages.update(result)
    return {
        "updated": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d"),
        "repos": user["public_repos"],
        "stars": sum(repo["stargazers_count"] for repo in originals),
        "followers": user["followers"],
        "forks": sum(repo["forks_count"] for repo in originals),
        "languages": dict(languages.most_common()),
    }


def svg_start(height, title, description, theme):
    return [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="960" height="{height}" '
        f'viewBox="0 0 960 {height}" role="img" aria-labelledby="title desc">',
        f'<title id="title">{escape(title)}</title>',
        f'<desc id="desc">{escape(description)}</desc>',
        '<style>text{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Arial,sans-serif}'
        '.mono{font-family:ui-monospace,SFMono-Regular,Consolas,monospace}</style>',
        f'<rect x=".5" y=".5" width="959" height="{height - 1}" rx="18" '
        f'fill="{theme["bg"]}" stroke="{theme["line"]}"/>',
    ]


def text(x, y, value, color, size=16, extra=""):
    return (f'<text x="{x}" y="{y}" fill="{color}" font-size="{size}" '
            f'{extra}>{escape(str(value))}</text>')


def header(theme):
    t = theme
    parts = svg_start(280, "Lynnette", "Explore internals. Build useful things. "
                      "AI agent security, software security, and advanced persistent threats.", t)
    parts += [
        '<defs><clipPath id="edge"><rect width="960" height="280" rx="18"/></clipPath></defs>',
        '<g clip-path="url(#edge)">',
        f'<circle cx="822" cy="144" r="165" fill="{t["soft"]}"/>',
        f'<g fill="none" stroke="{t["orb"]}" stroke-width="1.5">',
        '<circle cx="822" cy="144" r="133"/><circle cx="822" cy="144" r="104"/>',
        '<path d="M647 144h350M822 -20v330"/>',
        '<ellipse cx="822" cy="144" rx="166" ry="63" transform="rotate(-34 822 144)"/>',
        '</g>',
        text(724, 178, "177", t["accent"], 100, 'font-weight="700" opacity=".22"'),
        f'<circle cx="694" cy="204" r="5" fill="{t["cyan"]}"/>',
        f'<circle cx="914" cy="49" r="4" fill="{t["accent"]}"/>',
        '</g>',
        text(40, 47, "LYNNETTE177 / RESEARCH & ENGINEERING", t["accent"], 12,
             'class="mono" letter-spacing="1.8"'),
        text(37, 127, "Lynnette", t["text"], 68, 'font-weight="700" letter-spacing="-2"'),
        text(40, 171, "Explore internals.", t["text"], 24),
        text(40, 205, "Build useful things.", t["muted"], 24),
        f'<path d="M40 242h26" stroke="{t["cyan"]}" stroke-width="3"/>',
        text(77, 247, "AI AGENT SECURITY  /  SOFTWARE SECURITY  /  APT", t["muted"], 11,
             'class="mono" letter-spacing=".8"'),
        '</svg>',
    ]
    return "\n".join(parts) + "\n"


def overview(data, theme):
    t = theme
    metrics = [("PUBLIC REPOS", data["repos"]), ("STARS EARNED", data["stars"]),
               ("FOLLOWERS", data["followers"]), ("FORKS EARNED", data["forks"])]
    description = ", ".join(f"{value} {label.lower()}" for label, value in metrics)
    parts = svg_start(364, "Lynnette's GitHub overview", description, t)
    parts += [text(32, 38, "GITHUB / PUBLIC SNAPSHOT", t["accent"], 12,
                   'class="mono" letter-spacing="1.3"'),
              text(928, 38, f'UPDATED {data["updated"]} UTC', t["muted"], 11,
                   'class="mono" text-anchor="end"')]
    for index, (label, value) in enumerate(metrics):
        x = 32 + index * 230
        parts += [text(x, 99, f"{value:,}", t["text"], 38, 'font-weight="650"'),
                  text(x, 126, label, t["muted"], 11, 'class="mono" letter-spacing="1"')]
    parts += [f'<path d="M32 151h896" stroke="{t["line"]}"/>',
              text(32, 183, "Language mix", t["text"], 18, 'font-weight="600"'),
              text(928, 183, "Original public repositories · by code bytes", t["muted"], 12,
                   'text-anchor="end"')]
    ranked = sorted(data["languages"].items(), key=lambda item: (-item[1], item[0]))
    top = ranked[:7]
    remaining = sum(value for _, value in ranked[7:])
    if remaining:
        top.append(("Other", remaining))
    total = sum(value for _, value in top)
    if not total:
        parts.append(text(32, 235, "No language data available yet.", t["muted"], 16))
    else:
        parts += ['<defs><clipPath id="bar"><rect x="32" y="204" width="896" '
                  'height="12" rx="6"/></clipPath></defs>', '<g clip-path="url(#bar)">']
        x = 32.0
        for index, (language, value) in enumerate(top):
            width = 896 * value / total
            color = LANGUAGE_COLORS.get(language, ["#b6a1d9", "#8bbdc7", "#d0aa87"][index % 3])
            parts.append(f'<rect x="{x:.3f}" y="204" width="{width + .05:.3f}" height="12" fill="{color}"/>')
            x += width
        parts.append('</g>')
        for index, (language, value) in enumerate(top):
            x = 32 + index % 4 * 230
            y = 250 + index // 4 * 34
            color = LANGUAGE_COLORS.get(language, ["#b6a1d9", "#8bbdc7", "#d0aa87"][index % 3])
            parts += [f'<circle cx="{x + 4}" cy="{y - 5}" r="4" fill="{color}"/>',
                      text(x + 17, y, language, t["text"], 13),
                      text(x + 202, y, f"{100 * value / total:.1f}%", t["muted"], 13,
                           'text-anchor="end"')]
    parts += [text(32, 333, "A growing collection of things built and shared.", t["muted"], 12), '</svg>']
    return "\n".join(parts) + "\n"


def main():
    data = collect()
    assets = ROOT / "assets"
    assets.mkdir(exist_ok=True)
    outputs = {}
    for name, theme in THEMES.items():
        outputs[f"header-{name}.svg"] = header(theme)
        outputs[f"overview-{name}.svg"] = overview(data, theme)
    # Build every image first; an API failure leaves the committed snapshot intact.
    for name, contents in outputs.items():
        temporary = assets / f".{name}.tmp"
        temporary.write_text(contents, encoding="utf-8")
        temporary.replace(assets / name)
    print(f"Updated profile for {USERNAME}: {data['repos']} public repositories, "
          f"{data['stars']} stars, {len(data['languages'])} languages.")


if __name__ == "__main__":
    main()
