import os
import sys
import json
import csv
import pandas as pd
from pathlib import Path
from collections import defaultdict
from game import game_logging
import matplotlib.pyplot as plt
import seaborn as sns

# Finds the N most recent game sessions
def find_recent_sessions(n=None):
    logs_dir = Path("output_metrics/logs")
    if not logs_dir.exists():
        return []
    
    sessions = []
    for session_dir in logs_dir.iterdir():
        if session_dir.is_dir() and session_dir.name.startswith("session_"):
            # Check if it has a complete game
            if (session_dir / "game_complete.json").exists():
                sessions.append(session_dir)
    
    # Sort by modification time
    sessions.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    
    if n:
        sessions = sessions[:n]
    
    return sessions

# Loads game state from a session directory
def load_game_data(session_dir):
    try:
        state, logs = game_logging.load_game(str(session_dir))
        return state, logs, None
    except Exception as e:
        return None, None, str(e)

# Analyzes multiple games and computes statistics
def analyze_games(session_dirs):
    results = {
        'games': [],
        'win_rates': defaultdict(int),
        'role_survival': defaultdict(lambda: defaultdict(list)),
        'total_games': 0,
        'errors': []
    }
    
    print(f"\nAnalyzing {len(session_dirs)} games...\n")
    
    for i, session_dir in enumerate(session_dirs, 1):
        print(f"Loading game {i}/{len(session_dirs)}: {session_dir.name}")
        
        state, logs, error = load_game_data(session_dir)
        
        if error:
            print(f"Error: {error}")
            results['errors'].append({
                'session': session_dir.name,
                'error': error
            })
            continue
        
        results['total_games'] += 1
        
        # Game metadata
        game_info = {
            'session_id': state.session_id,
            'session_dir': session_dir.name,
            'winner': state.winner,
            'total_rounds': len(state.rounds),
            'players': {}
        }
        
        # Track each player
        for player_name, player in state.players.items():
            role = player.role
            
            # Find when they died (if they did)
            eliminated_round = None
            exiled_round = None
            survived = False
            
            for round_idx, round_state in enumerate(state.rounds):
                if round_state.eliminated == player_name:
                    eliminated_round = round_idx
                if round_state.exiled == player_name:
                    exiled_round = round_idx
            
            # Check if survived
            if state.rounds:
                survived = player_name in state.rounds[-1].players
            
            game_info['players'][player_name] = {
                'role': role,
                'survived': survived,
                'eliminated_round': eliminated_round,
                'exiled_round': exiled_round
            }
            
            # Track survival per round for this role
            for round_idx, round_state in enumerate(state.rounds):
                alive = player_name in round_state.players
                results['role_survival'][role][round_idx].append(1 if alive else 0)
        
        # Win rate tracking
        results['win_rates'][state.winner] += 1
        
        results['games'].append(game_info)
        print(f"Winner: {state.winner}, Rounds: {len(state.rounds)}")
    
    return results

# Saves win rate statistics
def save_win_rates(results, output_dir):
    output_file = output_dir / "win_rates.csv"
    
    with open(output_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['team', 'wins', 'total_games', 'win_rate'])
        
        total = results['total_games']
        
        for team in ['Villagers', 'Werewolves']:
            wins = results['win_rates'][team]
            rate = (wins / total * 100) if total > 0 else 0
            writer.writerow([team, wins, total, f"{rate:.1f}%"])
    
    print(f"\nWin rates saved to: {output_file}")

# Saves survival rate statistics per role per round
def save_survival_rates(results, output_dir):
    output_file = output_dir / "survival_rates.csv"
    
    with open(output_file, 'w', newline='') as f:
        writer = csv.writer(f)
        
        # Determine max rounds
        max_rounds = 0
        for role_data in results['role_survival'].values():
            max_rounds = max(max_rounds, max(role_data.keys()) + 1 if role_data else 0)
        
        # Header
        header = ['role', 'initial_count']
        for r in range(max_rounds):
            header.append(f'alive_after_round_{r}')
            header.append(f'survival_rate_round_{r}')
        writer.writerow(header)
        
        # Write data for each role
        for role in ['Villager', 'Werewolf', 'Seer', 'Doctor']:
            if role not in results['role_survival']:
                continue
            
            role_data = results['role_survival'][role]
            
            # Count initial (round 0 start = all alive)
            initial = len(role_data.get(0, []))
            
            row = [role, initial]
            
            for round_idx in range(max_rounds):
                if round_idx in role_data:
                    alive_count = sum(role_data[round_idx])
                    total_count = len(role_data[round_idx])
                    survival_rate = (alive_count / total_count * 100) if total_count > 0 else 0
                    
                    row.append(alive_count)
                    row.append(f"{survival_rate:.1f}%")
                else:
                    row.extend(['', ''])
            
            writer.writerow(row)
    
    print(f"Survival rates saved to: {output_file}")

# Saves detailed game-by-game summary
def save_game_summary(results, output_dir):
    output_file = output_dir / "games_summary.csv"
    
    with open(output_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            'session_id', 'session_dir', 'winner', 'total_rounds',
            'villagers_survived', 'werewolves_survived', 
            'seer_survived', 'doctor_survived'
        ])
        
        for game in results['games']:
            villagers_alive = sum(1 for p in game['players'].values() 
                                if p['role'] == 'Villager' and p['survived'])
            werewolves_alive = sum(1 for p in game['players'].values() 
                                 if p['role'] == 'Werewolf' and p['survived'])
            seer_alive = sum(1 for p in game['players'].values() 
                           if p['role'] == 'Seer' and p['survived'])
            doctor_alive = sum(1 for p in game['players'].values() 
                             if p['role'] == 'Doctor' and p['survived'])
            
            writer.writerow([
                game['session_id'],
                game['session_dir'],
                game['winner'],
                game['total_rounds'],
                villagers_alive,
                werewolves_alive,
                seer_alive,
                doctor_alive
            ])
    
    print(f"Game summary saved to: {output_file}")

# Saves detailed survival data for plotting
def save_detailed_survival(results, output_dir):
    output_file = output_dir / "survival_by_role_round.csv"
    
    rows = []
    for role, rounds_data in results['role_survival'].items():
        for round_idx, survival_list in rounds_data.items():
            alive_count = sum(survival_list)
            total_count = len(survival_list)
            survival_rate = (alive_count / total_count) if total_count > 0 else 0
            
            rows.append({
                'role': role,
                'round': round_idx,
                'alive_count': alive_count,
                'total_count': total_count,
                'survival_rate': survival_rate,
                'survival_pct': f"{survival_rate * 100:.1f}%"
            })
    
    df = pd.DataFrame(rows)
    df.to_csv(output_file, index=False)
    
    print(f"Detailed survival data saved to: {output_file}")

# Visualizes win rates as a bar chart
def visualize_win_rates(results, output_dir):
    teams = ['Villagers', 'Werewolves']
    win_counts = [results['win_rates'][team] for team in teams]
    total_games = results['total_games']
    win_rates = [(wins / total_games * 100) if total_games > 0 else 0 for wins in win_counts]

    plt.figure(figsize=(8, 6))
    sns.barplot(x=teams, y=win_rates, palette='viridis')
    plt.title('Win Rates by Team')
    plt.ylabel('Win Rate (%)')
    plt.xlabel('Team')
    plt.ylim(0, 100)
    plt.savefig(output_dir / 'win_rates.png')
    plt.close()
    print(f"Win rate visualization saved to: {output_dir / 'win_rates.png'}")

# Visualizes survival rates by role across rounds
def visualize_survival_rates(results, output_dir):
    rows = []
    for role, rounds_data in results['role_survival'].items():
        for round_idx, survival_list in rounds_data.items():
            alive_count = sum(survival_list)
            total_count = len(survival_list)
            survival_rate = (alive_count / total_count * 100) if total_count > 0 else 0
            rows.append({'role': role, 'round': round_idx, 'survival_rate': survival_rate})

    df = pd.DataFrame(rows)

    plt.figure(figsize=(10, 6))
    sns.lineplot(data=df, x='round', y='survival_rate', hue='role', marker='o')
    plt.title('Survival Rates by Role Across Rounds')
    plt.ylabel('Survival Rate (%)')
    plt.xlabel('Round')
    plt.ylim(0, 100)
    plt.legend(title='Role')
    plt.savefig(output_dir / 'survival_rates.png')
    plt.close()
    print(f"Survival rate visualization saved to: {output_dir / 'survival_rates.png'}")

# Prints summary statistics to console
def print_summary(results):
    print("\n" + "="*70)
    print("MULTI-GAME ANALYSIS SUMMARY")
    print("="*70)
    
    total = results['total_games']
    print(f"\nSuccessfully analyzed: {total} games")
    
    if results['errors']:
        print(f"Errors encountered: {len(results['errors'])}")
    
    # Win rates
    print("\nWIN RATES:")
    print("-" * 40)
    for team in ['Villagers', 'Werewolves']:
        wins = results['win_rates'][team]
        rate = (wins / total * 100) if total > 0 else 0
        print(f"  {team:12} {wins}/{total} ({rate:.1f}%)")
    
    # Survival rates
    print("\nSURVIVAL RATES BY ROLE:")
    print("-" * 40)
    
    for role in ['Villager', 'Werewolf', 'Seer', 'Doctor']:
        if role not in results['role_survival']:
            continue
        
        role_data = results['role_survival'][role]
        print(f"\n  {role}:")
        
        for round_idx in sorted(role_data.keys()):
            alive = sum(role_data[round_idx])
            total_count = len(role_data[round_idx])
            rate = (alive / total_count * 100) if total_count > 0 else 0
            print(f"    After Round {round_idx}: {alive}/{total_count} alive ({rate:.1f}%)")

# Main analysis function
def main():
    # Parse arguments
    if len(sys.argv) > 1 and sys.argv[1] == '--recent':
        n = int(sys.argv[2]) if len(sys.argv) > 2 else None
        session_dirs = find_recent_sessions(n)
        print(f"Found {len(session_dirs)} recent game sessions")
    elif len(sys.argv) > 1:
        # Use provided directories
        session_dirs = [Path(d) for d in sys.argv[1:]]
    else:
        # Default: analyze 3 most recent
        session_dirs = find_recent_sessions(10)
        print(f"Analyzing 3 most recent games (use --recent N to change)")
    
    if not session_dirs:
        print("No game sessions found!")
        print("\nUsage:")
        print("  python analyzers/analyze_multiple_games.py --recent 3")
        print("  python analyzers/analyze_multiple_games.py output_metrics/logs/session_1 output_metrics/logs/session_2")
        return
    
    # Analyze games
    results = analyze_games(session_dirs)
    
    if results['total_games'] == 0:
        print("\nNo valid games to analyze!")
        return
    
    # Create output directory
    output_dir = Path("output_metrics")
    output_dir.mkdir(exist_ok=True)
    
    # Save all analysis files
    save_win_rates(results, output_dir)
    save_survival_rates(results, output_dir)
    save_game_summary(results, output_dir)
    save_detailed_survival(results, output_dir)

    # Generate visualizations
    visualize_win_rates(results, output_dir)
    visualize_survival_rates(results, output_dir)

    # Print summary
    print_summary(results)
    
    print("\n" + "="*70)
    print(f"All analysis files saved to: {output_dir}/")
    print("="*70)
    print("\nFiles:")
    print("  - win_rates.csv              (win rates by team)")
    print("  - survival_rates.csv         (survival by role per round)")
    print("  - games_summary.csv          (game-by-game details)")
    print("  - survival_by_role_round.csv (detailed survival data)")
    print()

if __name__ == '__main__':
    main()
