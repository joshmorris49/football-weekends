"""Pull every FBS and NFL game since 2010 from ESPN's public scoreboard feed into data/games.json.

Runs in GitHub Actions (see .github/workflows/update-data.yml). Standard library only.

    python3 scripts/fetch_games.py            # refresh the current season(s), backfill anything missing
    python3 scripts/fetch_games.py --full     # refetch every season

Output (data/games.json):
    teams.cfb / teams.nfl : {id: [display name, short name, abbreviation, color, alt color]}
    games.cfb / games.nfl : [[season, date ET (YYYY-MM-DD), home id, away id, home pts, away pts, flags, note], ...]
        pts are null until the game is final; flags: "n" = neutral site, "p" = postseason
"""
import json, sys, time, urllib.request, urllib.error
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

FIRST_SEASON = 2010
VERSION = 3  # bump to force a full refetch after a fetch-logic change
OUT = Path(__file__).resolve().parent.parent / "data" / "games.json"
ET = ZoneInfo("America/New_York")
BASE = "https://site.api.espn.com/apis/site/v2/sports/football/{sport}/scoreboard"
# ESPN conference group ids: ACC, Big East (to 2012), Big 12, Big Ten, SEC, Pac-12, C-USA, MAC, WAC (to 2012),
# Mountain West, FBS Independents, Sun Belt, American
CFB_CONFERENCES = [1, 10, 4, 5, 8, 9, 12, 15, 16, 17, 18, 37, 151]
LEAGUES = {
    # sport path, extra params, regular-season weeks to try, postseason weeks to try
    "cfb": ("college-football", {"groups": "80", "limit": "1000"}, range(1, 18), range(1, 3)),
    "nfl": ("nfl", {"limit": "1000"}, range(1, 19), range(1, 6)),
}


def get(url, tries=4):
    for n in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "football-weekends (github.com/joshmorris49/football-weekends)"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
            if n == tries - 1:
                raise
            print(f"  retry {n + 1} after {e}", flush=True)
            time.sleep(2 * (n + 1))


def fetch_season(league, season, teams):
    sport, extra, reg_weeks, post_weeks = LEAGUES[league]
    games = {}
    for stype, weeks in ((2, reg_weeks), (3, post_weeks)):
        for wk in weeks:
            q = "&".join(f"{k}={v}" for k, v in {**extra, "dates": season, "seasontype": stype, "week": wk}.items())
            try:
                data = get(BASE.format(sport=sport) + "?" + q)
            except Exception as e:  # a missing week shouldn't sink the whole run
                print(f"  skip {league} {season} type {stype} week {wk}: {type(e).__name__}: {e}", flush=True)
                continue
            events = data.get("events", [])
            if league == "cfb" and events and len(events) % 25 == 0:
                # ESPN pages newer seasons at 25 events no matter the limit; re-ask one conference at a time
                for grp in CFB_CONFERENCES:
                    qq = q.replace("groups=80", f"groups={grp}")
                    try:
                        events += get(BASE.format(sport=sport) + "?" + qq).get("events", [])
                    except Exception as e:
                        print(f"  skip {league} {season} week {wk} group {grp}: {e}", flush=True)
                    time.sleep(0.1)
            for ev in events:
                try:
                    g = parse(ev, season, stype, teams)
                except (KeyError, IndexError, TypeError, ValueError) as e:
                    print(f"  bad event {ev.get('id')} ({season} week {wk}): {type(e).__name__} {e}", flush=True)
                    continue
                if g:
                    games[ev["id"]] = g
            time.sleep(0.15)
    return sorted(games.values(), key=lambda g: (g[1], g[2]))


def parse(ev, season, stype, teams):
    comp = ev["competitions"][0]
    sides = {c["homeAway"]: c for c in comp["competitors"]}
    if set(sides) != {"home", "away"}:
        return None
    ids = [sides[k]["team"]["id"] for k in ("home", "away")]
    abbrs = {sides[k]["team"].get("abbreviation", "") for k in ("home", "away")}
    if any(i.startswith("-") for i in ids) or abbrs <= {"AFC", "NFC", "TBD"}:  # unset playoff slots, Pro Bowl
        return None
    for c in sides.values():
        t = c["team"]
        teams[t["id"]] = [t.get("displayName") or t.get("name", ""), t.get("shortDisplayName") or t.get("location", ""),
                          t.get("abbreviation", ""), t.get("color", ""), t.get("alternateColor", "")]
    status = comp.get("status", ev.get("status", {})).get("type", {})
    if status.get("name") in ("STATUS_CANCELED", "STATUS_POSTPONED", "STATUS_FORFEIT"):
        return None
    final = status.get("completed", False)
    pts = lambda c: int(float(c["score"])) if final and c.get("score") not in (None, "") else None
    when = datetime.fromisoformat(ev["date"].replace("Z", "+00:00")).astimezone(ET).strftime("%Y-%m-%d")
    flags = ("n" if comp.get("neutralSite") else "") + ("p" if stype == 3 else "")
    note = ""
    if stype == 3 and comp.get("notes"):
        note = comp["notes"][0].get("headline", "")
    return [season, when, sides["home"]["team"]["id"], sides["away"]["team"]["id"], pts(sides["home"]), pts(sides["away"]), flags, note]


def current_season(now):
    # football seasons are labeled by the year they start; Jan-Jul belongs to the previous season
    return now.year if now.month >= 8 else now.year - 1


def main():
    print("python", sys.version.split()[0], flush=True)
    full = "--full" in sys.argv
    now = datetime.now(timezone.utc)
    cur = current_season(now)
    empty = {"teams": {"cfb": {}, "nfl": {}}, "games": {"cfb": [], "nfl": []}}
    old = json.loads(OUT.read_text()) if OUT.exists() else empty
    if old.get("v") != VERSION:
        full = True
    if full:
        old = empty
    out = {"v": VERSION, "updated": now.strftime("%Y-%m-%dT%H:%MZ"), "teams": old["teams"], "games": {}}
    for league in LEAGUES:
        have = {}
        for g in old["games"].get(league, []):
            have.setdefault(g[0], []).append(g)
        seasons = range(FIRST_SEASON, cur + 1)
        todo = [s for s in seasons if full or s not in have or s >= cur]
        for s in todo:
            t0 = time.time()
            try:
                have[s] = fetch_season(league, s, out["teams"][league])
            except Exception as e:
                print(f"{league} {s}: FAILED {type(e).__name__}: {e}", flush=True)
                import traceback; traceback.print_exc(file=sys.stdout)
                continue
            done = sum(1 for g in have[s] if g[4] is not None)
            print(f"{league} {s}: {len(have[s])} games ({done} final) in {time.time() - t0:.0f}s", flush=True)
        out["games"][league] = [g for s in seasons for g in have.get(s, [])
                                if not (g[2].startswith("-") or g[3].startswith("-"))]
        used = {t for g in out["games"][league] for t in (g[2], g[3])}
        out["teams"][league] = {k: v for k, v in out["teams"][league].items() if k in used}
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(out, separators=(",", ":"), ensure_ascii=False))
    print(f"wrote {OUT} ({OUT.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
