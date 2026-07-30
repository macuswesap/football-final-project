# NFL Matchup Lab

A Flask web app for exploring 2025-2026 NFL team stats, building head-to-head
matchups, running playoff simulations, and tracking your matchup history.

## Features

- **Home** — simple landing page with links to every section of the site.
- **Matchup** — pick any two teams (Team 1 and Team 2) and get:
  - A win probability for each team, based on their Adjusted Strength rating.
  - An offense vs. defense breakdown for both teams (does each offense
    project to *thrive* or *struggle* against the opponent's defense?).
  - A Strength of Schedule comparison.
  - Every matchup you run is automatically saved to the History page.
- **Data Table** — the full stat line for all 32 teams, sortable by record,
  Adjusted Strength, points/game, or points allowed/game. Click any team
  name to view their profile page.
- **Team Profile** — a dedicated page for each team's full stats.
- **Simulate** — runs the real 2025-2026 NFL playoff bracket thousands of
  times (Monte Carlo simulation) using each team's Adjusted Strength, and
  shows how often each team wins their conference / the Super Bowl.
- **History** — a log of every matchup you've run, stored in a SQLite
  database, with the ability to delete individual entries or clear it out
  entirely.
- **About** — explains how the stats and projections work.

## Project structure

```
football_project/
├── app.py                # Flask app: routes + matchup/analysis logic
├── nfl_playoffs.py         # Playoff bracket + Monte Carlo simulation logic
├── nfl_teams.csv            # Team stats data source
├── requirements.txt
├── static/
│   └── favicon.png
└── templates/
    ├── base.html           # Shared layout + nav bar
    ├── index.html          # Home
    ├── matchup.html         # Matchup builder + analysis
    ├── data.html           # Sortable team data table
    ├── team_profile.html     # Individual team page
    ├── simulate.html         # Playoff simulation
    ├── history.html          # Matchup history log
    └── about.html            # About / how it works
```

## Data

`nfl_teams.csv` holds one row per team with the following columns:

| Column | Description |
|---|---|
| `Team` | Team name |
| `Wins` / `Losses` | Season record |
| `Total Tds` | Total touchdowns |
| `Turnovers` | Turnovers committed |
| `Yards/G` | Offensive yards per game |
| `Yards Allowed/G` | Defensive yards allowed per game |
| `Points Scored/G` | Offensive points per game |
| `Points Allowed/G` | Defensive points allowed per game |
| `Strength of Schedule` | Relative difficulty of a team's schedule |
| `Adjusted_Strength` | Overall team strength rating used for win probability and playoff simulations |

## How the matchup analysis works

Win probability is based on each team's `Adjusted_Strength`:

```
home_win_probability = home_strength / (home_strength + away_strength)
```

Each team's offense is separately projected to **thrive** or **struggle**
against the opponent's defense using three rules, checked in order:

1. If the offense averages under 23 points/game **and** the opposing
   defense allows under 23 points/game, the offense struggles — a
   below-average offense won't suddenly thrive just because the score gap
   looks small.
2. Otherwise, if the opposing defense allows more points/game than the
   offense usually scores, the offense thrives.
3. Otherwise, if the scoring gap is small (≤7 points) and the opposing
   defense allows 23+ points/game (a below-average defense), the offense
   still thrives — a good offense shouldn't be considered "struggling"
   against a bad defense just because of a small gap.
4. Otherwise, the offense struggles.

## Setup

Just click on this link: https://football-final-project.vercel.app/

## Tech stack

- [Flask](https://flask.palletsprojects.com/) — web framework
- [Pandas](https://pandas.pydata.org/) — data loading/handling
- [SQLite](https://www.sqlite.org/) — matchup history storage
- [Pico CSS](https://picocss.com/) — styling
