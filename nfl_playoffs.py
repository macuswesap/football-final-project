"""
Simulates the real 2025-2026 NFL playoff bracket (single-elimination,
one game per round) using each team's Adjusted_Strength rating from
nfl_teams.csv.

Bracket (confirmed seeding for the actual 2026 postseason):

AFC: 1 Denver Broncos (bye), 2 New England Patriots, 3 Jacksonville Jaguars,
     4 Pittsburgh Steelers, 5 Houston Texans, 6 Buffalo Bills,
     7 Los Angeles Chargers

NFC: 1 Seattle Seahawks (bye), 2 Chicago Bears, 3 Philadelphia Eagles,
     4 Carolina Panthers, 5 Los Angeles Rams, 6 San Francisco 49ers,
     7 Green Bay Packers

Wild Card Round:  2 vs 7, 3 vs 6, 4 vs 5 (no. 1 seed gets a bye)
Divisional Round:  no. 1 seed plays the lowest remaining seed;
                    the other two wild-card winners play each other
Conference Championship:  the two divisional-round winners play
Super Bowl:  AFC champion vs NFC champion
"""

import random

AFC_SEEDS = [
    "Denver Broncos",
    "New England Patriots",
    "Jacksonville Jaguars",
    "Pittsburgh Steelers",
    "Houston Texans",
    "Buffalo Bills",
    "Los Angeles Chargers",
]

NFC_SEEDS = [
    "Seattle Seahawks",
    "Chicago Bears",
    "Philadelphia Eagles",
    "Carolina Panthers",
    "Los Angeles Rams",
    "San Francisco 49ers",
    "Green Bay Packers",
]


def all_playoff_teams():
    """Flat list of every team that made the 2025-2026 playoffs."""
    return AFC_SEEDS + NFC_SEEDS


def build_seed_lookup():
    """Maps team name -> seed number (1-7) within its conference."""
    lookup = {}
    for seed, team in enumerate(AFC_SEEDS, start=1):
        lookup[team] = seed
    for seed, team in enumerate(NFC_SEEDS, start=1):
        lookup[team] = seed
    return lookup


# Single game (not a series, since the NFL playoffs are single-elimination).
# Win probability is each team's share of the two teams' combined strength,
# same approach as the NBA example's get_strength/simulate_game.
def simulate_game(team1, team2, strengths, seed_lookup, statistics):
    """
    Simulates one playoff game between two teams.

    Parameters:
        team1 (str): Name of the first team.
        team2 (str): Name of the second team.
        strengths (dict): Maps team name -> Adjusted_Strength rating.
        seed_lookup (dict): Maps team name -> seed number (1 best - 7 worst).
        statistics (dict): Dictionary used to track simulation statistics.

    Returns:
        str: The name of the team that wins the game.
    """
    strength_1 = float(strengths[team1])
    strength_2 = float(strengths[team2])

    prob = strength_1 / (strength_1 + strength_2)
    winner = team1 if random.random() < prob else team2
    loser = team2 if winner == team1 else team1

    statistics["games_played"] += 1
    statistics["wins"][winner] += 1

    # An upset is a worse (higher-numbered) seed beating a better seed.
    if seed_lookup[winner] > seed_lookup[loser]:
        statistics["upsets"] += 1
        statistics["upsets_by"][winner] += 1
        k=f"{winner} over {loser}"
        statistics["upset_matchups"][k]=statistics["upset_matchups"].get(k,0)+1

    return winner


def simulate_wild_card_round(seeds, strengths, seed_lookup, statistics):
    """
    Simulates Wild Card Weekend for one conference.

    Parameters:
        seeds (list): The 7 playoff teams for a conference, ordered 1-7.

    Returns:
        tuple: (bye_team, wild_card_winners) where wild_card_winners is a
               list of the 3 teams that won their Wild Card game.
    """
    bye_team = seeds[0]
    matchups = [
        (seeds[1], seeds[6]),  # 2 vs 7
        (seeds[2], seeds[5]),  # 3 vs 6
        (seeds[3], seeds[4]),  # 4 vs 5
    ]

    winners = []
    for team1, team2 in matchups:
        winners.append(simulate_game(team1, team2, strengths, seed_lookup, statistics))

    return bye_team, winners


def simulate_divisional_round(bye_team, wild_card_winners, strengths, seed_lookup, statistics):
    """
    Simulates the Divisional Round for one conference.

    The no. 1 seed (bye_team) plays the lowest remaining seed; the other
    two Wild Card winners play each other.

    Returns:
        list: The 2 teams that advance to the Conference Championship.
    """
    remaining = sorted(wild_card_winners, key=lambda team: seed_lookup[team])
    lowest_remaining_seed = remaining[-1]
    other_two = [team for team in remaining if team != lowest_remaining_seed]

    game1_winner = simulate_game(bye_team, lowest_remaining_seed, strengths, seed_lookup, statistics)
    game2_winner = simulate_game(other_two[0], other_two[1], strengths, seed_lookup, statistics)

    return [game1_winner, game2_winner]


def simulate_conference_championship(divisional_winners, strengths, seed_lookup, statistics):
    """
    Simulates the Conference Championship game.

    Returns:
        str: The team that becomes conference champion.
    """
    team1, team2 = divisional_winners
    return simulate_game(team1, team2, strengths, seed_lookup, statistics)


def simulate_super_bowl(afc_champion, nfc_champion, strengths, seed_lookup, statistics):
    """
    Simulates the Super Bowl.

    Returns:
        str: The team that wins the championship.
    """
    return simulate_game(afc_champion, nfc_champion, strengths, seed_lookup, statistics)


def new_statistics():
    """
    Builds a fresh statistics dictionary for one playoff simulation.
    Every key is pre-initialized to 0 so later code can safely do
    statistics[key] += 1 without hitting a KeyError.
    """
    teams = all_playoff_teams()
    return {
        "games_played": 0,
        "upsets": 0,
        "wins": {team: 0 for team in teams},
        "upsets_by": {team: 0 for team in teams},
        "reached_conf_champ": {team: 0 for team in teams},
        "reached_super_bowl": {team: 0 for team in teams},
        "super_bowl_matchup": None,
        "upset_matchups": {},
        "bracket": {},
    }


def simulate_playoffs(strengths):
    """
    Simulates one full run of the 2025-2026 NFL playoffs.

    Parameters:
        strengths (dict): Maps team name -> Adjusted_Strength rating,
                           for all teams (only the 14 playoff teams matter).

    Returns:
        tuple: (champion, statistics)
    """
    seed_lookup = build_seed_lookup()
    statistics = new_statistics()

    afc_bye, afc_wc_winners = simulate_wild_card_round(AFC_SEEDS, strengths, seed_lookup, statistics)
    nfc_bye, nfc_wc_winners = simulate_wild_card_round(NFC_SEEDS, strengths, seed_lookup, statistics)

    afc_div_winners = simulate_divisional_round(afc_bye, afc_wc_winners, strengths, seed_lookup, statistics)
    nfc_div_winners = simulate_divisional_round(nfc_bye, nfc_wc_winners, strengths, seed_lookup, statistics)

    for team in afc_div_winners + nfc_div_winners:
        statistics["reached_conf_champ"][team] = 1

    afc_champion = simulate_conference_championship(afc_div_winners, strengths, seed_lookup, statistics)
    nfc_champion = simulate_conference_championship(nfc_div_winners, strengths, seed_lookup, statistics)

    statistics["reached_super_bowl"][afc_champion] = 1
    statistics["reached_super_bowl"][nfc_champion] = 1
    statistics["super_bowl_matchup"] = (afc_champion, nfc_champion)

    champion = simulate_super_bowl(afc_champion, nfc_champion, strengths, seed_lookup, statistics)
    statistics["bracket"]={"AFC Wild Card":afc_wc_winners,"NFC Wild Card":nfc_wc_winners,"AFC Divisional":afc_div_winners,"NFC Divisional":nfc_div_winners,"AFC Champion":afc_champion,"NFC Champion":nfc_champion,"Super Bowl Champion":champion}

    return champion, statistics


def run_simulations(n, strengths):
    """
    Runs the full NFL playoff simulation `n` times and aggregates results.

    Parameters:
        n (int): Number of times to simulate the playoffs.
        strengths (dict): Maps team name -> Adjusted_Strength rating.

    Returns:
        tuple: (results, summary)
            - results (list): One dict per playoff team, sorted by Super
              Bowl wins (most to least), each with team name, Super Bowl
              win count/percentage, and Super Bowl appearance count/pct.
            - summary (dict): Aggregate info - the team with the most Super
              Bowl wins, the most common Super Bowl matchup, and the
              average number of upsets per playoff run.
    """
    teams = all_playoff_teams()

    super_bowl_wins = {team: 0 for team in teams}
    reached_super_bowl = {team: 0 for team in teams}
    total_upsets = 0
    matchup_counts = {}
    upset_counts={}
    bracket_counts={}

    for _ in range(n):
        champion, statistics = simulate_playoffs(strengths)

        super_bowl_wins[champion] += 1
        total_upsets += statistics["upsets"]

        for team in teams:
            reached_super_bowl[team] += statistics["reached_super_bowl"][team]

        matchup_key = frozenset(statistics["super_bowl_matchup"])
        matchup_counts[matchup_key]=matchup_counts.get(matchup_key,0)+1
        import json
        b=json.dumps(statistics["bracket"],sort_keys=True)
        bracket_counts[b]=bracket_counts.get(b,0)+1
        for u,c in statistics["upset_matchups"].items(): upset_counts[u]=upset_counts.get(u,0)+c

    results = []
    for team in teams:
        wins = super_bowl_wins[team]
        appearances = reached_super_bowl[team]
        results.append({
            "team": team,
            "super_bowl_wins": wins,
            "win_pct": round(100 * wins / n, 1),
            "super_bowl_appearances": appearances,
            "appearance_pct": round(100 * appearances / n, 1),
        })
    results.sort(key=lambda row: row["super_bowl_wins"], reverse=True)

    most_wins_team = results[0]["team"]
    most_wins_count = results[0]["super_bowl_wins"]

    most_common_matchup_key = max(matchup_counts, key=lambda key: matchup_counts[key])
    most_common_matchup_teams = list(most_common_matchup_key)
    most_common_matchup_count = matchup_counts[most_common_matchup_key]

    summary = {
        "n": n,
        "most_wins_team": most_wins_team,
        "most_wins_count": most_wins_count,
        "most_wins_pct": round(100 * most_wins_count / n, 1),
        "most_common_matchup_teams": most_common_matchup_teams,
        "most_common_matchup_count": most_common_matchup_count,
        "most_common_matchup_pct": round(100 * most_common_matchup_count / n, 1),
        "avg_upsets": round(total_upsets / n, 2),
        "most_common_upset": max(upset_counts,key=upset_counts.get) if upset_counts else "None",
        "bracket": json.loads(max(bracket_counts,key=bracket_counts.get)),
    }

    return results, summary
