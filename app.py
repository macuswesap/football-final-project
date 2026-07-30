import csv
import sqlite3
from datetime import datetime
from pathlib import Path
from flask import Flask, render_template, request, flash, redirect, url_for
import pandas as pd

import nfl_playoffs

app = Flask(__name__)
app.secret_key = "dev-secret-key"  # needed for flash messages it wont work if we dont have this

DATA_FILE = Path(__file__).parent / "nfl_teams.csv"
#This is our database file for the history of matchups
DB_FILE = Path("/tmp/matchup_log.db")

#Here we make the method to get our database of matchups
def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

#actually creates the database
def init_db():
    conn = get_db()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS matchup_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            home_team TEXT NOT NULL,
            away_team TEXT NOT NULL,
            home_score REAL NOT NULL,
            away_score REAL NOT NULL,
            winner TEXT NOT NULL,
            probability TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )
    conn.commit()
    conn.close()

#We get the matchup and insert it into our databse of history of matchups
def log_matchup(home_team, away_team, home_score, away_score, winner, probability):
    conn = get_db()
    conn.execute(
        """
        INSERT INTO matchup_log (home_team, away_team, home_score, away_score, winner, probability, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            home_team,
            away_team,
            float(home_score),
            float(away_score),
            winner,
            probability,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        ),
    )
    conn.commit()
    conn.close()


init_db()

#Here we read a CSV data file into a list of dictionaries, and the UTF part ensures 
#it decodes text using standard utf-8 character encoding.
def load_team_rows():
    with DATA_FILE.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))

#just to make the catgeory names simple and good from the csvS
def normalize_team_row(raw_row):
    wins = int(raw_row["Wins"])
    losses = int(raw_row["Losses"])
    total_tds = int(raw_row["Total Tds"])
    turnovers = int(raw_row["Turnovers"])
    yards_per_game = float(raw_row["Yards/G"])
    yards_allowed_per_game = float(raw_row["Yards Allowed/G"])
    points_scored_per_game = float(raw_row["Points Scored/G"])
    points_allowed_per_game = float(raw_row["Points Allowed/G"])
    strength_of_schedule = float(raw_row["Strength of Schedule"])
    
    adjusted_strength = float(raw_row["Adjusted_Strength"])

    win_pct = wins / (wins + losses)

    return {
        "Team": raw_row["Team"],                  
        "team": raw_row["Team"],                  
        "Adjusted_Strength": adjusted_strength,   
        "wins": wins,
        "losses": losses,
        "record": f"{wins}-{losses}",
        "total_tds": total_tds,
        "turnovers": turnovers,
        "yards_per_game": yards_per_game,
        "yards_allowed_per_game": yards_allowed_per_game,
        "points_scored_per_game": points_scored_per_game,
        "points_allowed_per_game": points_allowed_per_game,
        "strength_of_schedule": strength_of_schedule,
        "win_pct": round(win_pct, 3),
    }

#We use normalize_team_row to modify the rows to what we want then we make a dataframe for future calculations
def load_team_data():
    rows = [normalize_team_row(row) for row in load_team_rows()]
    df = pd.DataFrame(rows)
    return rows, df

#Our home screen
@app.route("/")
def index():
    return render_template("index.html")

#Our matchup screen takes in different user request for different teams
@app.route("/matchup", methods=["GET", "POST"])
def matchup():
    teams, df = load_team_data()
    matchup_result = None

    if request.method == "POST":
        home_name = request.form.get("home_team")
        away_name = request.form.get("away_team")

        home_team = next((team for team in teams if team["team"] == home_name), None)
        away_team = next((team for team in teams if team["team"] == away_name), None)

        if home_team and away_team:
            # --- Original matchup probability / adjusted strength logic (unchanged) ---
            home_score = df.loc[df['Team'] == home_name, 'Adjusted_Strength'].values[0]
            away_score = df.loc[df['Team'] == away_name, 'Adjusted_Strength'].values[0]
            home_team_prob = home_score / (home_score + away_score)
            away_team_prob = 1 - home_team_prob

            probability = f"{home_name} have a {home_team_prob * 100:.2f}% chance to win, and {away_name} have a {away_team_prob * 100:.2f}% chance to win"

            winner = (
                home_team["team"]
                if home_score >= away_score
                else away_team["team"]
            )

            matchup_result = {
                "home_team": home_team,
                "away_team": away_team,
                "home_score": home_score,
                "away_score": away_score,
                "winner": winner,
                "probability": probability,
            }

            log_matchup(
                home_team["team"],
                away_team["team"],
                home_score,
                away_score,
                winner,
                probability,
            )
            flash(f"Matchup logged: {home_team['team']} vs {away_team['team']}", "success")

            # --- New: offense/defense projection & strength of schedule comparison ---
            matchup_result["analysis"] = build_matchup_analysis(home_team, away_team, df)

    return render_template(
        "matchup.html",
        teams=teams,
        matchup_result=matchup_result,
        df=df,
    )

#Advanced offense vs defense comaprison. Explanation below
def offense_projection(offense_team, defense_team):
    """
    Figures out whether offense_team's offense should THRIVE or STRUGGLE
    against defense_team's defense.

    Rule 1 (new, checked first): a below-average offense (scoring less than
    23 pts/g) facing a good defense (allowing less than 23 pts/g) will
    struggle, no matter how close the raw point gap looks. A weak offense
    shouldn't be projected to thrive just because a good defense keeps
    things close.

    Rule 2 (original): otherwise, if the defense allows more points/game
    than the offense usually scores, the offense projects to thrive.

    Rule 3: otherwise, a good offense should still be favored against a
    bad/league-average defense. Specifically - if the gap between what the
    offense scores and what the defense allows is small (<=7 points) AND
    the defense is allowing 23+ points/game (a below-average defense), the
    offense still projects to thrive, since a bad defense shouldn't be able
    to shut down a good offense just because of a small point gap.

    Otherwise, the offense projects to struggle.
    """
    offense_ppg = offense_team["points_scored_per_game"]
    defense_papg = defense_team["points_allowed_per_game"]
    diff = offense_ppg - defense_papg  # positive = offense usually outscores what defense allows

    if offense_ppg < 23 and defense_papg < 23:
        thrives = False
        reason = (
            f"{offense_team['team']} averages just {offense_ppg:.1f} pts/g (a below-average offense), "
            f"and {defense_team['team']} allows only {defense_papg:.1f} pts/g (a good defense), "
            f"so {offense_team['team']}'s offense projects to struggle."
        )
    elif diff < 0:
        thrives = True
        reason = (
            f"{defense_team['team']} allows {defense_papg:.1f} pts/g, more than the "
            f"{offense_ppg:.1f} pts/g {offense_team['team']} usually scores."
        )
    elif diff <= 7 and defense_papg >= 23:
        thrives = True
        reason = (
            f"{defense_team['team']}'s defense allows {defense_papg:.1f} pts/g (a below-average defense), "
            f"so even with only a small scoring edge, {offense_team['team']}'s offense should still thrive."
        )
    else:
        thrives = False
        reason = (
            f"{defense_team['team']} allows just {defense_papg:.1f} pts/g, well below the "
            f"{offense_ppg:.1f} pts/g {offense_team['team']} usually scores, so their offense may struggle."
        )

    return {
        "team": offense_team["team"],
        "opponent": defense_team["team"],
        "thrives": thrives,
        "verdict": "thrive" if thrives else "struggle",
        "reason": reason,
    }

#This one actually sees if an offense will thrive or not more below
def build_matchup_analysis(home_team, away_team, df):
    """
    Builds supplementary matchup analysis: it does NOT touch win probability
    or Adjusted_Strength. For each team's offense against the other team's
    defense, it decides whether that offense should thrive or struggle
    (see offense_projection above), then compares Strength of Schedule.
    """
    home_offense = offense_projection(home_team, away_team)
    away_offense = offense_projection(away_team, home_team)

    # Strength of schedule comparison (higher value = tougher schedule faced).
    sos_diff = home_team["strength_of_schedule"] - away_team["strength_of_schedule"]
    if abs(sos_diff) < 0.01:
        sos_note = f"{home_team['team']} and {away_team['team']} have faced a similarly tough schedule this season."
    elif sos_diff > 0:
        sos_note = (
            f"{home_team['team']} has faced the tougher schedule "
            f"({home_team['strength_of_schedule']:.3f} vs {away_team['strength_of_schedule']:.3f})."
        )
    else:
        sos_note = (
            f"{away_team['team']} has faced the tougher schedule "
            f"({away_team['strength_of_schedule']:.3f} vs {home_team['strength_of_schedule']:.3f})."
        )

    return {
        "home_offense": home_offense,
        "away_offense": away_offense,
        "sos_note": sos_note,
    }

#Our datatable screen we use lamba x and reverse=True to sort for different categories
@app.route("/data")
def data_view():
    rows = load_team_rows()
    sort = request.args.get("sort", "")
    if sort == "record": 
        rows.sort(key=lambda x: int(x["Wins"]) - int(x["Losses"]), reverse=True)
    elif sort == "adjusted_strength": 
        rows.sort(key=lambda x: float(x["Adjusted_Strength"]), reverse=True)
    elif sort == "ppg": 
        rows.sort(key=lambda x: float(x["Points Scored/G"]), reverse=True)
    elif sort == "papg": 
        rows.sort(key=lambda x: float(x["Points Allowed/G"]))
    return render_template("data.html", rows=rows, columns=list(rows[0].keys()), sort=sort)

#Our simulate screen where we use methods from nfl_playoffs.py to run simulations and siplay results
@app.route("/simulate", methods=["GET", "POST"])
def simulate():
    teams, df = load_team_data()
    strengths = {team["team"]: team["Adjusted_Strength"] for team in teams}

    playoff_results = None
    summary = None
    n = 1000
    error = None

    if request.method == "POST":
        try:
            n = int(request.form.get("num_simulations", 1000))
        except ValueError:
            n = 0

        if n < 1:
            error = "Please enter a number of simulations that's at least 1."
        else:
            playoff_results, summary = nfl_playoffs.run_simulations(n, strengths)

    return render_template(
        "simulate.html",
        playoff_results=playoff_results,
        summary=summary,
        n=n,
        error=error,
        afc_seeds=nfl_playoffs.AFC_SEEDS,
        nfc_seeds=nfl_playoffs.NFC_SEEDS,
    )
#Our about screen that just has text no interactive components
@app.route("/about")
def about_view():
    return render_template("about.html")

#This is for our "team profile screen" in our datatable
@app.route("/team/<team_name>")
def team_profile(team_name):
    teams, df = load_team_data()
    team = next((t for t in teams if t["team"] == team_name), None)
    if team is None:
        return render_template("team_profile.html", team=None, team_name=team_name), 404
    return render_template("team_profile.html", team=team, team_name=team_name)

#This is our history screen that uses conn (sqlite database) to save histories of matchups
@app.route("/history")
def history():
    conn = get_db()
    logs = conn.execute(
        "SELECT * FROM matchup_log ORDER BY id DESC"
    ).fetchall()
    conn.close()
    return render_template("history.html", logs=logs)

#This helps us delete histories 
@app.route("/history/delete/<int:log_id>", methods=["POST"])
def delete_matchup(log_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM matchup_log WHERE id = ?", (log_id,)).fetchone()
    conn.execute("DELETE FROM matchup_log WHERE id = ?", (log_id,))
    conn.commit()
    conn.close()

    if row:
        flash(f"Deleted matchup: {row['home_team']} vs {row['away_team']}", "success")
    else:
        flash("That matchup no longer exists.", "error")

    return redirect(url_for("history"))

#This clears all of the histories
@app.route("/history/clear", methods=["POST"])
def clear_history():
    conn = get_db()
    conn.execute("DELETE FROM matchup_log")
    conn.commit()
    conn.close()

    flash("Matchup history cleared.", "success")
    return redirect(url_for("history"))


if __name__ == "__main__":
    app.run(debug=True)