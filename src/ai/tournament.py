# src/ai/tournament.py (continued)
#!/usr/bin/env python3
"""
Tournament system for AI models
"""

import argparse
import sys
import os
import json
from datetime import datetime
from typing import List, Dict, Any
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from ai.utils import compare_models, create_tournament_bracket
import matplotlib.pyplot as plt
import numpy as np

def run_single_elimination_tournament(model_dirs: List[str], games_per_match: int = 50) -> Dict[str, Any]:
    """Run a single elimination tournament"""
    if len(model_dirs) < 2:
        raise ValueError("Need at least 2 model directories for tournament")
    
    # Ensure power of 2 participants (add byes if needed)
    while len(model_dirs) & (len(model_dirs) - 1) != 0:
        model_dirs.append(None)  # Bye

    tournament_log = []
    current_round = model_dirs[:]
    round_num = 1

    while len(current_round) > 1:
        print(f"\n🏆 ROUND {round_num}")
        print("=" * 40)
        
        next_round = []
        round_matches = []
        
        for i in range(0, len(current_round), 2):
            participant1 = current_round[i]
            participant2 = current_round[i + 1] if i + 1 < len(current_round) else None
            
            if participant2 is None:  # Bye
                print(f"  {os.path.basename(participant1)} advances (bye)")
                next_round.append(participant1)
                continue
            
            if participant1 is None:  # Bye in first position
                print(f"  {os.path.basename(participant2)} advances (bye)")
                next_round.append(participant2)
                continue
            
            # Play match
            print(f"  {os.path.basename(participant1)} vs {os.path.basename(participant2)}")
            result = compare_models(participant1, participant2, games_per_match)
            
            if result['model1_win_rate'] > result['model2_win_rate']:
                winner = participant1
                winner_name = os.path.basename(participant1)
            else:
                winner = participant2
                winner_name = os.path.basename(participant2)
            
            print(f"    Winner: {winner_name} ({result['model1_win_rate']:.3f} vs {result['model2_win_rate']:.3f})")
            
            next_round.append(winner)
            round_matches.append({
                'participant1': participant1,
                'participant2': participant2,
                'winner': winner,
                'result': result
            })
        
        tournament_log.append({
            'round': round_num,
            'matches': round_matches
        })
        
        current_round = next_round
        round_num += 1

    champion = current_round[0]
    print(f"\n🏆 TOURNAMENT CHAMPION: {os.path.basename(champion)}")

    return {
        'champion': champion,
        'tournament_log': tournament_log,
        'total_rounds': round_num - 1
    }

def visualize_tournament_results(tournament_result: Dict[str, Any], save_path: str):
    """Create tournament bracket visualization"""
    fig, ax = plt.subplots(figsize=(12, 8))
    
    # Simple text-based tournament bracket
    y_positions = []
    round_positions = []

    for round_data in tournament_result['tournament_log']:
        round_num = round_data['round']
        matches = round_data['matches']
        
        y_start = len(matches)
        for i, match in enumerate(matches):
            y_pos = y_start - i
            y_positions.append(y_pos)
            round_positions.append(round_num)
            
            # Draw match
            p1_name = os.path.basename(match['participant1'])
            p2_name = os.path.basename(match['participant2'])
            winner_name = os.path.basename(match['winner'])
            
            ax.text(round_num - 0.4, y_pos + 0.1, p1_name, fontsize=8, ha='right')
            ax.text(round_num - 0.4, y_pos - 0.1, p2_name, fontsize=8, ha='right')
            ax.text(round_num + 0.1, y_pos, f"→ {winner_name}", fontsize=8, ha='left', 
                   weight='bold', color='green')
            
            # Draw bracket lines
            ax.plot([round_num - 0.5, round_num], [y_pos + 0.1, y_pos], 'k-', alpha=0.3)
            ax.plot([round_num - 0.5, round_num], [y_pos - 0.1, y_pos], 'k-', alpha=0.3)
            ax.plot([round_num, round_num + 0.5], [y_pos, y_pos], 'k-', alpha=0.3)
    
    # Format plot
    ax.set_xlim(0, tournament_result['total_rounds'] + 1)
    ax.set_ylim(0, max(y_positions) + 1)
    ax.set_xlabel('Tournament Round')
    ax.set_title('Tournament Bracket', fontsize=16, fontweight='bold')
    ax.grid(True, alpha=0.3)
    
    # Remove y-axis labels
    ax.set_yticks([])
    
    plt.tight_layout()
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    plt.close()

def run_round_robin_tournament(model_dirs: List[str], games_per_match: int = 50) -> Dict[str, Any]:
    """Run a round-robin tournament where every model plays every other model"""
    if len(model_dirs) < 2:
        raise ValueError("Need at least 2 model directories for tournament")
    
    print(f"\n🏆 ROUND ROBIN TOURNAMENT")
    print(f"Participants: {len(model_dirs)}")
    print("=" * 50)
    
    results_matrix = {}
    match_results = []
    
    # Initialize results matrix
    for dir1 in model_dirs:
        results_matrix[dir1] = {}
        for dir2 in model_dirs:
            if dir1 == dir2:
                results_matrix[dir1][dir2] = {'wins': 0, 'losses': 0, 'win_rate': 0.5}
            else:
                results_matrix[dir1][dir2] = None
    
    # Play all matches
    total_matches = len(model_dirs) * (len(model_dirs) - 1) // 2
    match_count = 0
    
    for i, dir1 in enumerate(model_dirs):
        for j, dir2 in enumerate(model_dirs[i+1:], i+1):
            match_count += 1
            print(f"\nMatch {match_count}/{total_matches}: {os.path.basename(dir1)} vs {os.path.basename(dir2)}")
            
            result = compare_models(dir1, dir2, games_per_match)
            
            # Store results
            results_matrix[dir1][dir2] = {
                'wins': result['model1_wins'],
                'losses': result['model2_wins'],
                'win_rate': result['model1_win_rate']
            }
            results_matrix[dir2][dir1] = {
                'wins': result['model2_wins'],
                'losses': result['model1_wins'],
                'win_rate': result['model2_win_rate']
            }
            
            match_results.append({
                'model1': dir1,
                'model2': dir2,
                'result': result
            })
            
            print(f"  Result: {result['model1_win_rate']:.3f} - {result['model2_win_rate']:.3f}")
    
    # Calculate final standings
    standings = []
    for model_dir in model_dirs:
        total_wins = 0
        total_games = 0
        
        for opponent_dir in model_dirs:
            if model_dir != opponent_dir:
                match_result = results_matrix[model_dir][opponent_dir]
                total_wins += match_result['wins']
                total_games += match_result['wins'] + match_result['losses']
        
        win_rate = total_wins / total_games if total_games > 0 else 0
        standings.append({
            'model': model_dir,
            'wins': total_wins,
            'games': total_games,
            'win_rate': win_rate
        })
    
    # Sort by win rate
    standings.sort(key=lambda x: x['win_rate'], reverse=True)
    
    print(f"\n🏆 FINAL STANDINGS")
    print("=" * 50)
    for i, standing in enumerate(standings):
        print(f"{i+1}. {os.path.basename(standing['model'])}: "
              f"{standing['wins']}/{standing['games']} ({standing['win_rate']:.3f})")
    
    return {
        'standings': standings,
        'results_matrix': results_matrix,
        'match_results': match_results,
        'champion': standings[0]['model']
    }

def save_tournament_results(tournament_result: Dict[str, Any], output_file: str):
    """Save tournament results to JSON file"""
    # Convert any non-serializable objects to strings
    serializable_result = json.loads(json.dumps(tournament_result, default=str))
    
    with open(output_file, 'w') as f:
        json.dump(serializable_result, f, indent=2)
    
    print(f"Tournament results saved to {output_file}")

def main():
    parser = argparse.ArgumentParser(description='Run AI model tournaments')
    parser.add_argument('model_dirs', nargs='+', help='Directories containing trained models')
    parser.add_argument('--type', choices=['elimination', 'round-robin'], default='elimination',
                       help='Tournament type (default: elimination)')
    parser.add_argument('--games-per-match', type=int, default=50,
                       help='Number of games per match (default: 50)')
    parser.add_argument('--output-dir', type=str, default='tournament_results',
                       help='Directory for output files')
    parser.add_argument('--visualize', action='store_true',
                       help='Create tournament visualization')
    
    args = parser.parse_args()
    
    # Validate model directories
    valid_dirs = []
    for model_dir in args.model_dirs:
        if os.path.exists(model_dir):
            valid_dirs.append(model_dir)
        else:
            print(f"Warning: {model_dir} does not exist, skipping")
    
    if len(valid_dirs) < 2:
        print("Error: Need at least 2 valid model directories")
        return
    
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Run tournament
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if args.type == 'elimination':
        print("Running Single Elimination Tournament")
        result = run_single_elimination_tournament(valid_dirs, args.games_per_match)
        result_file = os.path.join(args.output_dir, f"elimination_tournament_{timestamp}.json")
    else:
        print("Running Round Robin Tournament")
        result = run_round_robin_tournament(valid_dirs, args.games_per_match)
        result_file = os.path.join(args.output_dir, f"round_robin_tournament_{timestamp}.json")
    
    # Save results
    save_tournament_results(result, result_file)
    
    # Create visualization
    if args.visualize and args.type == 'elimination':
        viz_file = os.path.join(args.output_dir, f"tournament_bracket_{timestamp}.png")
        visualize_tournament_results(result, viz_file)
        print(f"Tournament bracket saved to {viz_file}")

if __name__ == "__main__":
    main()
