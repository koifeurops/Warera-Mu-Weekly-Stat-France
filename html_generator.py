import json
import re
from pathlib import Path
from datetime import datetime

INPUT_JSON = "cleaneddata.json"
OVERVIEW_HTML = "overview.html"

# --- Timestamp logic ---
now = datetime.now()
formatted_date = now.strftime("%A, %d %B %H:%M")

# --- Week number logic ---
current_week = now.isocalendar()[1]
previous_week = current_week - 1
previous_week_folder = f"week_{previous_week}_log"
previous_week_json = f"{previous_week_folder}/cleaneddata.json"

# Where the published pages end up (see .github/workflows/main.yml).
DOCS_DIR = "docs"
BASE_URL = "https://koifeurops.github.io/Warera-Mu-Weekly-Stat-France"

TIER_COLORS = {
    "master": "#ff4d4d",
    "diamond": "#3fa9ff",
    "platinum": "#b8c2cc",
    "gold": "#f5c542",
    "silver": "#bcbcbc",
    "bronze": "#c57a44",
}

TIER_ICONS = {
    "master": "👑",
    "diamond": "💎",
    "platinum": "🔷",
    "gold": "🥇",
    "silver": "🥈",
    "bronze": "🥉",
}


def fmt_number(value):
    if isinstance(value, float):
        return f"{value:,.2f}"
    return f"{value:,}"


def safe_name(name, fallback):
    base = name or fallback or "mu"
    return re.sub(r"[^a-z0-9_-]", "_", base, flags=re.IGNORECASE)


def mu_page_filename(mu):
    return f"mu-{safe_name(mu.get('name'), mu.get('id'))}.html"


def docs_page_name(week, mu):
    """Filename used once a per-MU page is published under docs/ for a given week."""
    return f"Week-{week}-{mu_page_filename(mu)}"


# ============================================
# Load + normalize data
# (accepts both the new multi-MU shape and the legacy single-MU shape,
#  so older week_*_log/cleaneddata.json files still work as "previous week")
# ============================================

def normalize_cleaned(data):
    if data is None:
        return []
    if "mus" in data:
        return data["mus"]
    if "mu" in data or "members" in data:
        mu = data.get("mu", {}) or {}
        return [{
            "id": mu.get("id"),
            "name": mu.get("name"),
            "avatarUrl": mu.get("avatarUrl"),
            "rankings": mu.get("rankings", {}),
            "members": data.get("members", []) or [],
        }]
    return []


with open(INPUT_JSON, "r", encoding="utf-8") as f:
    current_mus = normalize_cleaned(json.load(f))

previous_mus = []
if Path(previous_week_json).exists():
    with open(previous_week_json, "r", encoding="utf-8") as f:
        previous_mus = normalize_cleaned(json.load(f))


# ============================================
# Matching helpers — MATCH BY ID, NOT NAME/USERNAME
# (falls back to name/username only for legacy data that predates ids)
# ============================================

def find_prev_mu(mu):
    for prev in previous_mus:
        if mu.get("id") is not None and prev.get("id") is not None:
            if prev["id"] == mu["id"]:
                return prev
        elif prev.get("name") == mu.get("name"):
            return prev
    return None


def find_prev_member(member, prev_members):
    for prev in prev_members:
        if member.get("id") is not None and prev.get("id") is not None:
            if prev["id"] == member["id"]:
                return prev
        elif prev.get("username") == member.get("username"):
            return prev
    return None


def get_previous_rank(prev_member, stat_key):
    if not prev_member:
        return None
    return prev_member.get("rankings", {}).get(stat_key, {}).get("rank")


def get_rank_evolution(current_rank, previous_rank):
    if previous_rank is None:
        return "New"
    if current_rank < previous_rank:
        return f"#{previous_rank} → #{current_rank} (↑{previous_rank - current_rank})"
    elif current_rank > previous_rank:
        return f"#{previous_rank} → #{current_rank} (↓{current_rank - previous_rank})"
    else:
        return f"#{previous_rank} → #{current_rank}"


def calculate_diff(current_value, previous_value):
    if previous_value is None:
        return None
    return current_value - previous_value


# ============================================
# Shared CSS (used by both per-MU pages and the overview page)
# ============================================

SHARED_STYLE = """
* { margin:0; padding:0; box-sizing:border-box; }
body { background:#0b1220; color:white; font-family:Arial,sans-serif; padding:24px; }
.container { max-width:1900px; margin:auto; }

.mu-header {
    display:flex; align-items:center; justify-content:space-between;
    gap:20px; padding:24px; margin-bottom:24px;
    background:#131d31; border:1px solid #25324d; border-radius:18px;
}
.mu-header-left { display:flex; align-items:center; gap:20px; }
.mu-header img { width:96px; height:96px; border-radius:50%; }
.mu-name { font-size:2rem; font-weight:bold; }
.mu-subtitle { color:#94a3b8; margin-top:6px; }
.generated-at { color:#94a3b8; font-size:0.9rem; text-align:right; }

.stats {
    display:grid; grid-template-columns:repeat(4,1fr);
    gap:18px; margin-bottom:24px;
}
.stat-card {
    background:#131d31; border:1px solid #25324d;
    border-radius:16px; padding:20px;
}
.stat-title { color:#94a3b8; font-size:.9rem; }
.stat-value { font-size:1.8rem; font-weight:bold; margin-top:10px; }
.stat-rank { margin-top:8px; color:#cbd5e1; }
.stat-diff { font-size:0.9rem; margin-top:6px; }
.stat-rank-evolution { font-size:0.8rem; color:#94a3b8; margin-top:4px; }

.master   { border-left:6px solid #ff4d4d; }
.diamond  { border-left:6px solid #3fa9ff; }
.platinum { border-left:6px solid #b8c2cc; }
.gold     { border-left:6px solid #f5c542; }
.silver   { border-left:6px solid #bcbcbc; }
.bronze   { border-left:6px solid #c57a44; }

.section-label {
    color:#94a3b8; font-size:0.8rem; text-transform:uppercase;
    letter-spacing:0.08em; margin-bottom:10px; margin-top:24px; padding-left:4px;
}
.rankings, .rankings-two-col {
    display:grid; grid-template-columns:repeat(2,1fr); gap:20px;
}
.ranking-card {
    background:#131d31; border:1px solid #25324d;
    border-radius:18px; overflow:hidden;
}
.ranking-title {
    background:#1a2740; padding:18px;
    font-weight:bold; font-size:1.1rem;
}
.roster-count { font-weight:400; color:#94a3b8; font-size:0.9rem; }

table { width:100%; border-collapse:collapse; }
thead th { position:sticky; top:0; background:#1f2f4d; }
th { text-align:left; padding:12px; }
td { padding:12px; border-bottom:1px solid #202f49; }
tbody tr:hover { background:rgba(255,255,255,.03); }

.member { display:flex; align-items:center; gap:12px; }
.avatar {
    width:42px; height:42px; border-radius:50%;
    object-fit:cover; border:2px solid #334155;
}
.member-info { display:flex; flex-direction:column; }
.member-name { font-weight:600; }
.member-name .former-name { color:#94a3b8; font-size:0.78rem; font-weight:400; margin-left:6px; }
.member-level { color:#94a3b8; font-size:.85rem; }
.tier {
    display:inline-flex; align-items:center; gap:6px;
    padding:5px 10px; border-radius:999px;
    color:white; font-size:.85rem; font-weight:bold;
}
.rank-col { width:110px; white-space:nowrap; }
.pos-up   { font-size:0.72rem; font-weight:700; color:#4ade80; background:rgba(74,222,128,0.12); padding:2px 6px; border-radius:6px; margin-left:4px; }
.pos-down { font-size:0.72rem; font-weight:700; color:#f87171; background:rgba(248,113,113,0.12); padding:2px 6px; border-radius:6px; margin-left:4px; }
.pos-same { font-size:0.72rem; color:#64748b; margin-left:4px; }
.pos-new  { font-size:0.72rem; font-weight:700; color:#60a5fa; background:rgba(96,165,250,0.12); padding:2px 6px; border-radius:6px; margin-left:4px; }
.value-col { font-weight:bold; }
.rank-evolution-col { font-weight:bold; color:#94a3b8; font-size:0.9rem; }
.diff-col { font-weight:bold; }

/* Roster changes */
.roster-list { padding:12px 16px; display:flex; flex-direction:column; gap:10px; }
.roster-row {
    display:flex; align-items:center; gap:12px;
    padding:10px 12px; border-radius:10px;
    background:#0f1929; border:1px solid #1e2f48;
}
.roster-badge {
    margin-left:auto; padding:4px 12px;
    border-radius:999px; font-size:0.8rem; font-weight:bold; color:white;
}
.roster-empty {
    padding:20px 16px; color:#94a3b8; font-size:0.9rem; text-align:center;
}

/* Navigation buttons */
.nav-buttons {
    display:flex; justify-content:space-between; align-items:center;
    gap:16px; margin-top:32px; padding-top:24px; border-top:1px solid #25324d;
}
.nav-btn {
    display:inline-flex; align-items:center; gap:10px;
    padding:14px 28px; background:#131d31; border:1px solid #25324d;
    border-radius:12px; color:white; font-size:1rem; font-weight:600;
    text-decoration:none; cursor:pointer;
    transition:background 0.18s, border-color 0.18s, transform 0.12s;
}
.nav-btn:hover { background:#1a2740; border-color:#3fa9ff; transform:translateY(-2px); }
.nav-btn:active { transform:translateY(0); }
.nav-btn-prev::before { content:"←"; font-size:1.1rem; }
.nav-btn-next::after  { content:"→"; font-size:1.1rem; }
.nav-btn-disabled { opacity:0.35; pointer-events:none; }

/* Overview page: MU comparison + damage-share bars */
.mu-overview-card {
    background:#131d31; border:1px solid #25324d; border-radius:18px;
    padding:20px; margin-bottom:18px;
}
.mu-overview-top { display:flex; align-items:center; gap:16px; margin-bottom:16px; }
.mu-overview-top img { width:56px; height:56px; border-radius:50%; }
.mu-overview-name { font-size:1.3rem; font-weight:bold; }
.mu-overview-name a { color:inherit; text-decoration:none; }
.mu-overview-name a:hover { text-decoration:underline; }
.mu-overview-bars { display:grid; grid-template-columns:1fr 1fr; gap:20px; }
.share-block { }
.share-label { display:flex; justify-content:space-between; color:#94a3b8; font-size:0.85rem; margin-bottom:6px; }
.share-bar-track { background:#0f1929; border-radius:999px; height:14px; overflow:hidden; border:1px solid #1e2f48; }
.share-bar-fill { height:100%; border-radius:999px; background:linear-gradient(90deg,#3fa9ff,#60a5fa); }
.share-bar-fill.total { background:linear-gradient(90deg,#f5c542,#ff9d4d); }
.share-value { margin-top:6px; font-size:0.9rem; color:#cbd5e1; }

.week-history { display:flex; flex-direction:column; gap:10px; }
.week-history-row {
    display:flex; align-items:center; gap:12px; flex-wrap:wrap;
    padding:12px 16px; border-radius:10px;
    background:#0f1929; border:1px solid #1e2f48;
}
.week-history-title { font-weight:600; min-width:90px; }
.week-history-links { display:flex; gap:8px; flex-wrap:wrap; }
.week-history-links a {
    color:#cbd5e1; text-decoration:none; background:#1a2740;
    border:1px solid #25324d; border-radius:8px; padding:4px 10px; font-size:0.85rem;
}
.week-history-links a:hover { border-color:#3fa9ff; color:white; }

@media(max-width:1400px) { .rankings, .rankings-two-col, .mu-overview-bars { grid-template-columns:1fr; } }
@media(max-width:900px)  { .stats { grid-template-columns:repeat(2,1fr); } }
@media(max-width:600px)  {
    .stats { grid-template-columns:1fr; }
    .mu-header { flex-direction:column; text-align:center; }
    .nav-buttons { flex-direction:column; }
    .nav-btn { width:100%; justify-content:center; }
}
"""


# ============================================
# Per-MU page builders
# ============================================

def build_stat_card(title, value, rank, tier, diff=None, previous_rank=None):
    diff_html = ""
    if diff is not None:
        diff_color = "#4ade80" if diff >= 0 else "#f87171"
        diff_symbol = "+" if diff >= 0 else ""
        diff_html = f'<div class="stat-diff" style="color:{diff_color}">{diff_symbol}{fmt_number(diff)}</div>'

    rank_evolution_html = ""
    if previous_rank is not None:
        evolution = get_rank_evolution(rank, previous_rank)
        rank_evolution_html = f'<div class="stat-rank-evolution">{evolution}</div>'

    return f"""
    <div class="stat-card {tier}">
        <div class="stat-title">{title}</div>
        <div class="stat-value">{fmt_number(value)}</div>
        {diff_html}
        {rank_evolution_html}
        <div class="stat-rank">
            {TIER_ICONS.get(tier,'')} Rank #{rank}
        </div>
    </div>
    """


def build_table(title, ranking, stat_key, prev_members):
    # Internal position (this week) lookup, keyed by id, for the position-change badge
    prev_positions = {}
    if prev_members:
        prev_sorted = sorted(
            prev_members,
            key=lambda m: m["rankings"].get(stat_key, {}).get("value", 0),
            reverse=True,
        )
        for i, m in enumerate(prev_sorted, start=1):
            prev_positions[m.get("id") or m.get("username")] = i

    rows = []
    for position, member in enumerate(ranking, start=1):
        data = member["rankings"][stat_key]
        value = data["value"]
        tier = data["tier"]
        current_rank = data["rank"]
        color = TIER_COLORS.get(tier, "#999999")
        icon = TIER_ICONS.get(tier, "🏅")

        prev_member = find_prev_member(member, prev_members) if prev_members else None
        previous_value = None
        if prev_member:
            previous_value = prev_member.get("rankings", {}).get(stat_key, {}).get("value")
        diff = calculate_diff(value, previous_value)

        previous_rank = get_previous_rank(prev_member, stat_key)
        rank_evolution = get_rank_evolution(current_rank, previous_rank)

        # Internal position change badge (e.g. 6→3), matched by id
        member_key = member.get("id") or member.get("username")
        prev_pos = prev_positions.get(member_key)
        if prev_pos is None:
            pos_badge = '<span class="pos-new">New</span>'
        elif prev_pos == position:
            pos_badge = '<span class="pos-same">—</span>'
        elif prev_pos > position:
            pos_badge = f'<span class="pos-up">{prev_pos}→{position}</span>'
        else:
            pos_badge = f'<span class="pos-down">{prev_pos}→{position}</span>'

        diff_html = ""
        if diff is not None:
            diff_color = "#4ade80" if diff >= 0 else "#f87171"
            diff_symbol = "+" if diff >= 0 else ""
            diff_html = f'<td class="diff-col" style="color:{diff_color}">{diff_symbol}{fmt_number(diff)}</td>'

        # If this same player (matched by id) had a different username last week,
        # surface the namechange instead of losing the history.
        former_name_html = ""
        if prev_member and prev_member.get("username") and prev_member["username"] != member["username"]:
            former_name_html = f'<span class="former-name">(formerly {prev_member["username"]})</span>'

        rows.append(f"""
            <tr>
                <td class="rank-col">#{position} {pos_badge}</td>
                <td>
                    <div class="member">
                        <img class="avatar" src="{member['avatarUrl']}" alt="{member['username']}">
                        <div class="member-info">
                            <div class="member-name">{member['username']}{former_name_html}</div>
                            <div class="member-level">Level {member['level']}</div>
                        </div>
                    </div>
                </td>
                <td class="value-col">{fmt_number(value)}</td>
                <td class="rank-evolution-col">{rank_evolution}</td>
                {diff_html}
                <td><span class="tier" style="background:{color};">{icon} {tier.title()}</span></td>
            </tr>
        """)

    return f"""
    <div class="ranking-card">
        <div class="ranking-title">{title}</div>
        <table>
            <thead>
                <tr>
                    <th>Rank</th>
                    <th>Member</th>
                    <th>Value</th>
                    <th>Rank Evolution</th>
                    <th>Diff</th>
                    <th>Tier</th>
                </tr>
            </thead>
            <tbody>{''.join(rows)}</tbody>
        </table>
    </div>
    """


def build_roster_changes(current_members, prev_members):
    if not prev_members:
        return ""

    def key_of(m):
        return m.get("id") or m.get("username")

    current_keys = {key_of(m) for m in current_members}
    prev_keys = {key_of(m) for m in prev_members}

    # Matched by id: a namechange keeps the same id, so it is neither
    # "new" nor "departed" here — see the "(formerly ...)" tag in the tables instead.
    new_members = [m for m in current_members if key_of(m) not in prev_keys]
    departed_members = [m for m in prev_members if key_of(m) not in current_keys]

    def member_row(m, badge_color, badge_label):
        return f"""
        <div class="roster-row">
            <img class="avatar" src="{m['avatarUrl']}" alt="{m['username']}">
            <div class="member-info">
                <div class="member-name">{m['username']}</div>
                <div class="member-level">Level {m['level']}</div>
            </div>
            <span class="roster-badge" style="background:{badge_color};">{badge_label}</span>
        </div>
        """

    def build_panel(title, icon, members_list, badge_color, badge_label, empty_msg):
        if members_list:
            rows_html = "".join(member_row(m, badge_color, badge_label) for m in members_list)
        else:
            rows_html = f'<div class="roster-empty">{empty_msg}</div>'
        return f"""
        <div class="ranking-card">
            <div class="ranking-title">{icon} {title} <span class="roster-count">({len(members_list)})</span></div>
            <div class="roster-list">{rows_html}</div>
        </div>
        """

    new_panel = build_panel(
        "New Recruits", "🟢", new_members,
        "#166534", "Joined",
        "No new members this week."
    )
    departed_panel = build_panel(
        "Departed Members", "🔴", departed_members,
        "#7f1d1d", "Left",
        "No departures this week."
    )

    return f"""
    <div class="section-label">Roster Changes</div>
    <div class="rankings-two-col">
        {new_panel}
        {departed_panel}
    </div>
    """


def generate_mu_page(mu):
    prev_mu = find_prev_mu(mu)
    prev_members = prev_mu["members"] if prev_mu else []

    members = mu["members"]
    rankings = mu["rankings"]

    mu_weekly_damage = rankings["muWeeklyDamages"]
    mu_total_damage = rankings["muDamages"]
    mu_bounty = rankings["muBounty"]
    mu_reputation = rankings["muReputation"]

    mu_weekly_damage_diff = mu_total_damage_diff = mu_bounty_diff = mu_reputation_diff = None
    mu_weekly_damage_prev_rank = mu_total_damage_prev_rank = mu_bounty_prev_rank = mu_reputation_prev_rank = None

    if prev_mu:
        prev_rankings = prev_mu.get("rankings", {})
        if "muWeeklyDamages" in prev_rankings:
            mu_weekly_damage_diff = calculate_diff(mu_weekly_damage["value"], prev_rankings["muWeeklyDamages"]["value"])
            mu_weekly_damage_prev_rank = prev_rankings["muWeeklyDamages"]["rank"]
        if "muDamages" in prev_rankings:
            mu_total_damage_diff = calculate_diff(mu_total_damage["value"], prev_rankings["muDamages"]["value"])
            mu_total_damage_prev_rank = prev_rankings["muDamages"]["rank"]
        if "muBounty" in prev_rankings:
            mu_bounty_diff = calculate_diff(mu_bounty["value"], prev_rankings["muBounty"]["value"])
            mu_bounty_prev_rank = prev_rankings["muBounty"]["rank"]
        if "muReputation" in prev_rankings:
            mu_reputation_diff = calculate_diff(mu_reputation["value"], prev_rankings["muReputation"]["value"])
            mu_reputation_prev_rank = prev_rankings["muReputation"]["rank"]

    stats_html = "".join([
        build_stat_card("Weekly Damage", mu_weekly_damage["value"], mu_weekly_damage["rank"], mu_weekly_damage["tier"],
                        diff=mu_weekly_damage_diff, previous_rank=mu_weekly_damage_prev_rank),
        build_stat_card("Total Damage", mu_total_damage["value"], mu_total_damage["rank"], mu_total_damage["tier"],
                        diff=mu_total_damage_diff, previous_rank=mu_total_damage_prev_rank),
        build_stat_card("Bounty", mu_bounty["value"], mu_bounty["rank"], mu_bounty["tier"],
                        diff=mu_bounty_diff, previous_rank=mu_bounty_prev_rank),
        build_stat_card("Reputation", mu_reputation["value"], mu_reputation["rank"], mu_reputation["tier"],
                        diff=mu_reputation_diff, previous_rank=mu_reputation_prev_rank),
    ])

    weekly_damage_ranking = sorted(members, key=lambda m: m["rankings"]["weeklyUserDamages"]["value"], reverse=True)
    total_damage_ranking = sorted(members, key=lambda m: m["rankings"]["userDamages"]["value"], reverse=True)
    bounty_ranking = sorted(members, key=lambda m: m["rankings"]["userBounty"]["value"], reverse=True)
    wealth_ranking = sorted(members, key=lambda m: m["rankings"]["userWealth"]["value"], reverse=True)

    roster_changes_html = build_roster_changes(members, prev_members)

    filename = mu_page_filename(mu)
    overview_link = f"{BASE_URL}/index.html"
    prev_page_url = f"{BASE_URL}/{docs_page_name(previous_week, mu)}"
    next_page_url = f"{BASE_URL}/{docs_page_name(current_week + 1, mu)}"

    html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{mu['name']} Dashboard</title>
<style>{SHARED_STYLE}</style>
</head>
<body>
<div class="container">

    <!-- Header -->
    <div class="mu-header">
        <div class="mu-header-left">
            <img src="{mu['avatarUrl']}">
            <div>
                <div class="mu-name">{mu['name']}</div>
                <div class="mu-subtitle">Guild Dashboard</div>
            </div>
        </div>
        <div class="generated-at">Generated: {formatted_date}</div>
    </div>

    <!-- MU Stat Cards -->
    <div class="stats">{stats_html}</div>

    <!-- Standard Rankings -->
    <div class="section-label">Standard Rankings</div>
    <div class="rankings">
        {build_table("Weekly Damage Ranking", weekly_damage_ranking, "weeklyUserDamages", prev_members)}
        {build_table("Total Damage Ranking", total_damage_ranking, "userDamages", prev_members)}
        {build_table("Bounty Ranking", bounty_ranking, "userBounty", prev_members)}
        {build_table("Wealth Ranking", wealth_ranking, "userWealth", prev_members)}
    </div>

    <!-- Roster Changes -->
    {roster_changes_html if roster_changes_html else ""}

    <!-- Navigation Buttons -->
    <div class="nav-buttons">
        <a href="{prev_page_url}" class="nav-btn nav-btn-prev">Semaine dernière</a>
        <a href="{overview_link}" class="nav-btn">Overview</a>
        <a href="{next_page_url}" class="nav-btn nav-btn-next">Semaine prochaine</a>
    </div>

</div>
</body>
</html>
"""

    Path(filename).write_text(html, encoding="utf-8")
    print(f"Generated {filename}")
    return filename


# ============================================
# Overview page — replaces the old hand-maintained docs/index.html.
# Shows, for every tracked MU, its share of this week's combined weekly
# damage and combined total damage (both computed across the MUs listed
# in data/mu_id.txt), side by side.
# ============================================

def discover_week_history():
    """
    Scan docs/ for already-published pages so the overview can link back
    to previous weeks without anyone having to hand-edit a list again.
    Groups by week number; supports both the old single-page-per-week
    naming (Week-N.html) and the new per-MU naming (Week-N-mu-xxx.html).
    """
    docs_path = Path(DOCS_DIR)
    if not docs_path.exists():
        return []

    weeks = {}
    pattern = re.compile(r"^Week-(\d+)(?:-(.+))?\.html$")
    for entry in sorted(docs_path.glob("Week-*.html")):
        match = pattern.match(entry.name)
        if not match:
            continue
        week_num = int(match.group(1))
        label = match.group(2) or "overview"
        weeks.setdefault(week_num, []).append((label, entry.name))

    history = []
    for week_num in sorted(weeks.keys(), reverse=True):
        history.append((week_num, sorted(weeks[week_num])))
    return history


def build_week_history_html():
    history = discover_week_history()
    if not history:
        return ""

    rows = []
    for week_num, links in history:
        link_parts = []
        for label, name in links:
            if label == "overview":
                display_label = f"Week {week_num}"
            else:
                display_label = re.sub(r"^mu-", "", label).replace("_", " ")
            link_parts.append(f'<a href="{name}">{display_label}</a>')
        link_html = "".join(link_parts)
        rows.append(f"""
        <div class="week-history-row">
            <div class="week-history-title">Week {week_num}</div>
            <div class="week-history-links">{link_html}</div>
        </div>
        """)

    return f"""
    <div class="section-label">Weekly Updates</div>
    <div class="week-history">{''.join(rows)}</div>
    """


def generate_overview(mu_entries):
    total_weekly = sum(m["rankings"]["muWeeklyDamages"]["value"] for m in mu_entries)
    total_all_time = sum(m["rankings"]["muDamages"]["value"] for m in mu_entries)

    # Rank MUs by weekly damage share for display order
    ordered = sorted(mu_entries, key=lambda m: m["rankings"]["muWeeklyDamages"]["value"], reverse=True)

    cards = []
    for mu in ordered:
        weekly_value = mu["rankings"]["muWeeklyDamages"]["value"]
        total_value = mu["rankings"]["muDamages"]["value"]
        weekly_pct = (weekly_value / total_weekly * 100) if total_weekly else 0
        total_pct = (total_value / total_all_time * 100) if total_all_time else 0

        page_link = docs_page_name(current_week, mu)

        cards.append(f"""
        <div class="mu-overview-card">
            <div class="mu-overview-top">
                <img src="{mu['avatarUrl']}">
                <div class="mu-overview-name"><a href="{page_link}">{mu['name']}</a></div>
            </div>
            <div class="mu-overview-bars">
                <div class="share-block">
                    <div class="share-label"><span>Weekly Damage Share</span><span>{weekly_pct:.1f}%</span></div>
                    <div class="share-bar-track"><div class="share-bar-fill" style="width:{weekly_pct:.2f}%"></div></div>
                    <div class="share-value">{fmt_number(weekly_value)} damage this week</div>
                </div>
                <div class="share-block">
                    <div class="share-label"><span>Total Damage Share</span><span>{total_pct:.1f}%</span></div>
                    <div class="share-bar-track"><div class="share-bar-fill total" style="width:{total_pct:.2f}%"></div></div>
                    <div class="share-value">{fmt_number(total_value)} damage all-time</div>
                </div>
            </div>
        </div>
        """)

    week_history_html = build_week_history_html()

    html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Warera Spectre Log — Overview</title>
<style>{SHARED_STYLE}</style>
</head>
<body>
<div class="container">

    <div class="mu-header">
        <div class="mu-header-left">
            <div>
                <div class="mu-name">MU Overview</div>
                <div class="mu-subtitle">Damage share across all tracked MUs — Week {current_week}</div>
            </div>
        </div>
        <div class="generated-at">Generated: {formatted_date}</div>
    </div>

    <div class="section-label">Tracked MUs ({len(mu_entries)})</div>
    {''.join(cards)}

    {week_history_html}

</div>
</body>
</html>
"""

    Path(OVERVIEW_HTML).write_text(html, encoding="utf-8")
    print(f"Generated {OVERVIEW_HTML}")


# ============================================
# MAIN
# ============================================

def main():
    if not current_mus:
        print("No MUs found in cleaneddata.json — nothing to generate.")
        return

    for mu in current_mus:
        generate_mu_page(mu)

    generate_overview(current_mus)


if __name__ == "__main__":
    main()
