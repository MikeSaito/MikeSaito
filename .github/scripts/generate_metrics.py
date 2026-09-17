from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.request
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path


USER = "MikeSaito"
API = "https://api.github.com"
FEATURED = ["Game-Settings-Master", "Chatterino-RT", "DeskPad"]
LANGUAGE_COLORS = {
    "C#": "#9b72cf",
    "Rust": "#dea584",
    "TypeScript": "#3178c6",
    "JavaScript": "#f1e05a",
    "Python": "#3572a5",
}


def api_request(path: str):
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "MikeSaito-profile-metrics",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(f"{API}{path}", headers=headers)
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=45) as response:
                return json.load(response)
        except (TimeoutError, urllib.error.URLError):
            if attempt == 2:
                raise
            time.sleep(2 ** attempt)


def official_contribution_calendar() -> dict | None:
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        return None
    query = """
    query($login: String!) {
      user(login: $login) {
        contributionsCollection {
          contributionCalendar {
            totalContributions
            weeks {
              contributionDays { contributionCount date }
            }
          }
        }
      }
    }
    """
    body = json.dumps({"query": query, "variables": {"login": USER}}).encode()
    request = urllib.request.Request(
        f"{API}/graphql",
        data=body,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "MikeSaito-profile-metrics",
        },
    )
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=45) as response:
                payload = json.load(response)
            return payload["data"]["user"]["contributionsCollection"]["contributionCalendar"]
        except (KeyError, TypeError, TimeoutError, urllib.error.URLError):
            if attempt == 2:
                return None
            time.sleep(2 ** attempt)


def commit_calendar(repos: list[dict]) -> dict:
    today = datetime.now(timezone.utc).date()
    start = today - timedelta(days=364)
    counts: Counter[str] = Counter()

    for repo in repos:
        page = 1
        while True:
            commits = api_request(
                f"/repos/{USER}/{repo['name']}/commits"
                f"?author={USER}&since={start.isoformat()}T00:00:00Z&per_page=100&page={page}"
            )
            for commit in commits:
                author = commit.get("commit", {}).get("author") or {}
                if author.get("date"):
                    counts[author["date"][:10]] += 1
            if len(commits) < 100:
                break
            page += 1

    first_sunday = start - timedelta(days=(start.weekday() + 1) % 7)
    weeks = []
    cursor = first_sunday
    while cursor <= today:
        days = []
        for offset in range(7):
            day = cursor + timedelta(days=offset)
            if day <= today:
                days.append(
                    {
                        "date": day.isoformat(),
                        "contributionCount": counts[day.isoformat()],
                    }
                )
        weeks.append({"contributionDays": days})
        cursor += timedelta(days=7)

    return {"totalContributions": sum(counts.values()), "weeks": weeks[-53:]}


def escape(value: object) -> str:
    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def truncate(value: str | None, limit: int) -> str:
    text = value or "No description"
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def calendar_cells(calendar: dict) -> str:
    palette = ["#172033", "#193b5b", "#235d8f", "#347fc4", "#66b8ff"]
    cells = []
    weeks = calendar.get("weeks", [])[-53:]
    for week_index, week in enumerate(weeks):
        for day_index, day in enumerate(week.get("contributionDays", [])):
            count = int(day.get("contributionCount", 0))
            level = 0 if count == 0 else min(4, 1 + (count - 1) // 2)
            x = 122 + week_index * 15
            y = 547 + day_index * 15
            cells.append(
                f'<rect x="{x}" y="{y}" width="11" height="11" rx="2.5" '
                f'fill="{palette[level]}"><title>{escape(day.get("date", ""))}: {count}</title></rect>'
            )
    return "".join(cells)


def render_repo_card(repo: dict) -> str:
    name = escape(repo["name"])
    description = escape(truncate(repo.get("description"), 82))
    language = escape(repo.get("language") or "Other")
    language_color = LANGUAGE_COLORS.get(repo.get("language"), "#64748b")
    stars = repo.get("stargazers_count", 0)
    forks = repo.get("forks_count", 0)
    updated = datetime.fromisoformat(repo["pushed_at"].replace("Z", "+00:00")).strftime("%b %Y").upper()
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="320" height="190" viewBox="0 0 320 190" role="img" aria-label="{name} repository">
<defs>
  <linearGradient id="card-bg" x1="0" y1="0" x2="1" y2="1">
    <stop stop-color="#0b1220"/><stop offset="1" stop-color="#111a2b"/>
  </linearGradient>
  <linearGradient id="line" x1="0" y1="0" x2="1" y2="0">
    <stop stop-color="#38bdf8"/><stop offset=".55" stop-color="#6366f1"/><stop offset="1" stop-color="#c084fc"/>
  </linearGradient>
  <style>
    text {{ font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; }}
    .repo {{ fill:#f1f5f9;font-size:18px;font-weight:730; }}
    .desc {{ fill:#7f8ca3;font-size:11px;font-weight:500; }}
    .meta {{ fill:#718096;font-size:10px;font-weight:650;letter-spacing:.4px; }}
    .updated {{ fill:#475569;font-size:9px;font-weight:700;letter-spacing:1px; }}
  </style>
</defs>
<rect x="1" y="1" width="318" height="188" rx="18" fill="url(#card-bg)" stroke="#26344d" stroke-width="2"/>
<rect x="18" y="18" width="44" height="3" rx="1.5" fill="url(#line)"/>
<circle cx="285" cy="28" r="4" fill="#34d399"/>
<text x="18" y="58" class="repo">{name}</text>
<text x="18" y="86" class="desc">{description[:46]}</text>
<text x="18" y="103" class="desc">{description[46:]}</text>
<line x1="18" y1="128" x2="302" y2="128" stroke="#1f2c40"/>
<circle cx="22" cy="151" r="5" fill="{language_color}"/>
<text x="34" y="155" class="meta">{language}</text>
<text x="147" y="155" class="meta">★ {stars}</text>
<text x="195" y="155" class="meta">⑂ {forks}</text>
<text x="302" y="155" text-anchor="end" class="updated">{updated}</text>
<text x="18" y="176" class="updated">OPEN REPOSITORY ↗</text>
</svg>
'''


def main() -> None:
    user = api_request(f"/users/{USER}")
    repos = api_request(f"/users/{USER}/repos?per_page=100&type=owner&sort=updated")
    owned = [repo for repo in repos if not repo.get("fork")]
    calendar = official_contribution_calendar()
    activity_kind = "ALL CONTRIBUTIONS"
    if not calendar:
        calendar = commit_calendar(owned)
        activity_kind = "PUBLIC COMMITS"

    stars = sum(repo.get("stargazers_count", 0) for repo in owned)
    languages = Counter(repo["language"] for repo in owned if repo.get("language"))
    language_rows = languages.most_common(4)
    total_languages = max(sum(count for _, count in language_rows), 1)
    updated = datetime.now(timezone.utc).strftime("%d %b %Y · %H:%M UTC").upper()
    total_contributions = calendar.get("totalContributions", 0)
    active_days = sum(
        1
        for week in calendar.get("weeks", [])
        for day in week.get("contributionDays", [])
        if day.get("contributionCount", 0) > 0
    )

    metrics = [
        ("REPOSITORIES", user.get("public_repos", 0), "PUBLIC"),
        ("STARS EARNED", stars, "TOTAL"),
        ("CONTRIBUTIONS", total_contributions, "12 MONTHS"),
        ("ACTIVE DAYS", active_days, "12 MONTHS"),
    ]
    cards = []
    for index, (label, value, note) in enumerate(metrics):
        x = 56 + index * 225
        cards.append(f'''<g transform="translate({x} 150)">
  <rect width="205" height="126" rx="18" fill="#111827" stroke="#24324a"/>
  <rect x="18" y="18" width="30" height="3" rx="1.5" fill="url(#accent)"/>
  <text x="18" y="48" class="label">{escape(label)}</text>
  <text x="18" y="91" class="value">{escape(value)}</text>
  <text x="187" y="92" text-anchor="end" class="note">{escape(note)}</text>
</g>''')

    colors = ["#60a5fa", "#818cf8", "#c084fc", "#22d3ee"]
    language_svg = []
    for index, (language, count) in enumerate(language_rows):
        y = 334 + index * 31
        width = max(18, round(260 * count / total_languages))
        language_svg.append(f'''<text x="578" y="{y}" class="lang">{escape(language)}</text>
<rect x="686" y="{y - 10}" width="260" height="8" rx="4" fill="#1f2937"/>
<rect x="686" y="{y - 10}" width="{width}" height="8" rx="4" fill="{colors[index]}"/>
<text x="952" y="{y}" text-anchor="end" class="lang-count">{count}</text>''')

    cells = calendar_cells(calendar)
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="720" viewBox="0 0 1000 720" role="img" aria-label="Mike Saito GitHub metrics">
<defs>
  <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#080d18"/><stop offset=".58" stop-color="#0b1220"/><stop offset="1" stop-color="#101827"/></linearGradient>
  <linearGradient id="accent" x1="0" y1="0" x2="1" y2="0"><stop stop-color="#38bdf8"/><stop offset=".5" stop-color="#6366f1"/><stop offset="1" stop-color="#c084fc"/></linearGradient>
  <radialGradient id="glow"><stop stop-color="#3b82f6" stop-opacity=".28"/><stop offset="1" stop-color="#3b82f6" stop-opacity="0"/></radialGradient>
  <filter id="blur"><feGaussianBlur stdDeviation="30"/></filter>
  <style>
    text {{ font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; }}
    .eyebrow {{ fill:#7dd3fc;font-size:12px;font-weight:700;letter-spacing:3px; }}
    .title {{ fill:#f8fafc;font-size:38px;font-weight:760;letter-spacing:1px; }}
    .updated {{ fill:#64748b;font-size:11px;font-weight:600;letter-spacing:1px; }}
    .label {{ fill:#7c8aa5;font-size:11px;font-weight:700;letter-spacing:1.4px; }}
    .value {{ fill:#f8fafc;font-size:38px;font-weight:760; }}
    .note {{ fill:#526077;font-size:9px;font-weight:700;letter-spacing:1px; }}
    .section {{ fill:#cbd5e1;font-size:11px;font-weight:700;letter-spacing:1.6px; }}
    .lang {{ fill:#9ca9bd;font-size:12px;font-weight:600; }}
    .lang-count {{ fill:#536078;font-size:10px;font-weight:700; }}
    .micro {{ fill:#526077;font-size:10px;font-weight:650;letter-spacing:1px; }}
    .big {{ fill:#e2e8f0;font-size:24px;font-weight:740; }}
    .day {{ fill:#526077;font-size:9px;font-weight:650; }}
  </style>
</defs>
<rect x="1" y="1" width="998" height="718" rx="28" fill="url(#bg)" stroke="#1e293b" stroke-width="2"/>
<circle cx="885" cy="30" r="170" fill="url(#glow)" filter="url(#blur)"/>
<rect x="28" y="24" width="944" height="4" rx="2" fill="url(#accent)"/>
<text x="56" y="75" class="eyebrow">GITHUB · LIVE METRICS</text>
<text x="56" y="122" class="title">MIKE SAITO</text>
<circle cx="758" cy="91" r="5" fill="#34d399"/>
<text x="774" y="95" class="updated">UPDATED {escape(updated)}</text>
{''.join(cards)}
<g transform="translate(56 314)">
  <rect width="480" height="136" rx="18" fill="#0d1524" stroke="#1d2a3f"/>
  <text x="20" y="30" class="section">REPOSITORY SIGNAL</text>
  <text x="20" y="75" class="big">{len(owned)} original</text>
  <text x="20" y="99" class="micro">PUBLIC REPOSITORIES</text>
  <line x1="190" y1="24" x2="190" y2="112" stroke="#1f2c40"/>
  <text x="220" y="75" class="big">{len(languages)}</text>
  <text x="220" y="99" class="micro">PRIMARY LANGUAGES</text>
  <circle cx="432" cy="68" r="24" fill="#111f35" stroke="#28466f"/>
  <path d="M421 69l7 7 15-17" fill="none" stroke="#60a5fa" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>
</g>
<text x="578" y="309" class="section">PRIMARY LANGUAGES</text>
{''.join(language_svg)}
<rect x="56" y="486" width="888" height="174" rx="18" fill="#0d1524" stroke="#1d2a3f"/>
<text x="76" y="519" class="section">CONTRIBUTION ACTIVITY</text>
<text x="924" y="519" text-anchor="end" class="micro">{total_contributions} {activity_kind} · LAST 12 MONTHS</text>
<text x="83" y="570" class="day">MON</text><text x="83" y="600" class="day">WED</text><text x="83" y="630" class="day">FRI</text>
{cells}
<text x="56" y="694" class="micro">GITHUB.COM/{USER.upper()}</text>
<text x="944" y="694" text-anchor="end" class="micro">AUTOMATICALLY GENERATED</text>
</svg>
'''

    output = Path("assets/profile-metrics-v2.svg")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(svg, encoding="utf-8")

    by_name = {repo["name"]: repo for repo in owned}
    for name in FEATURED:
        repo = by_name.get(name)
        if repo:
            Path(f"assets/repo-{slug(name)}.svg").write_text(render_repo_card(repo), encoding="utf-8")


if __name__ == "__main__":
    main()
