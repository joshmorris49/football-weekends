# Football Weekends

How good have your football weekends been? Pick a college team and an NFL team. A **good weekend** is one where both won, a **split** is one win and one loss, and a **bad weekend** is both losing.

**Live site:** https://joshmorris49.github.io/football-weekends/ (shareable: `?cfb=texas-longhorns&nfl=houston-texans`)

## How it works

- **Data.** `scripts/fetch_games.py` pulls every FBS and NFL game since 2010 from ESPN's public scoreboard feed into `data/games.json`. No API key needed.
- **Updates.** A GitHub Action (`.github/workflows/update-data.yml`) runs daily at about 6am Central and commits fresh scores. You can also run it from the Actions tab ("Run workflow", with an option to refetch everything). `data/fetch-log.txt` keeps the last run's output.
- **Weekends.** A weekend runs Tuesday through Monday, so midweek college games and Monday Night Football count toward the nearest Saturday. Seasons are labeled by the year they start, so January bowls and playoffs count toward the season before.
- **What counts.** Headline numbers only use weekends when both teams played. Weekends with just one game show on the timeline but aren't counted.
- **Leaderboards** (`#leaders`). Every college × NFL combo is scored in the browser for the chosen range: most good weekends, best rate, best single seasons, luckiest and unluckiest, longest streaks, and most miserable (both lost). A filter hides college teams below .500 (or .600/.700) over the range. The main view also shows where your combo ranks.
- **Luck.** Good weekends compared with what you'd expect if both teams' results were independent at their actual win rates.

The page is a single static `index.html` that reads `data/games.json`; there's no build step. `og.png` is the link-preview image (source: `scripts/og.html`, render with `python3 scripts/og.py`).

Unofficial fan project. Scores via ESPN.
