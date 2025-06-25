# src/ai/metrics.py
"""
Performance metrics and analysis for AI training
"""

import numpy as np
from typing import List, Dict, Any, Tuple
import matplotlib.pyplot as plt
from collections import defaultdict

class PerformanceAnalyzer:
    """Analyze AI performance metrics"""
    
    def __init__(self):
        self.game_results = []
        self.player_stats = []

    def add_game_result(self, result: Dict[str, Any], player_stats: List[Dict[str, Any]]):
        """Add game result for analysis"""
        self.game_results.append(result)
        self.player_stats.append(player_stats)

    def calculate_win_rates(self, window_size: int = 100) -> Dict[str, List[float]]:
        """Calculate rolling win rates for each player"""
        win_rates = defaultdict(list)
        
        for i in range(len(self.game_results)):
            start_idx = max(0, i - window_size + 1)
            window_results = self.game_results[start_idx:i+1]
            
            # Count wins for each player in window
            wins = [0, 0, 0, 0]
            for result in window_results:
                winner = result.get('winner', -1)
                if winner >= 0:
                    wins[winner] += 1
            
            # Calculate win rates
            total_games = len(window_results)
            for player_idx in range(4):
                win_rate = wins[player_idx] / total_games if total_games > 0 else 0
                win_rates[f'player_{player_idx}'].append(win_rate)
        
        return dict(win_rates)

    def calculate_average_scores(self, window_size: int = 100) -> Dict[str, List[float]]:
        """Calculate rolling average scores"""
        avg_scores = defaultdict(list)
        
        for i in range(len(self.game_results)):
            start_idx = max(0, i - window_size + 1)
            window_results = self.game_results[start_idx:i+1]
            
            # Calculate average scores
            player_totals = [0, 0, 0, 0]
            for result in window_results:
                scores = result.get('final_scores', [25000, 25000, 25000, 25000])
                for j, score in enumerate(scores):
                    player_totals[j] += score
            
            total_games = len(window_results)
            for player_idx in range(4):
                avg_score = player_totals[player_idx] / total_games if total_games > 0 else 25000
                avg_scores[f'player_{player_idx}'].append(avg_score)
        
        return dict(avg_scores)

    def analyze_learning_progress(self) -> Dict[str, Any]:
        """Analyze overall learning progress"""
        if len(self.game_results) < 100:
            return {"error": "Not enough games for analysis"}
        
        # Compare early vs late performance
        early_games = self.game_results[:100]
        late_games = self.game_results[-100:]
        
        # Win rate improvement
        early_wins = [0, 0, 0, 0]
        late_wins = [0, 0, 0, 0]
        
        for result in early_games:
            winner = result.get('winner', -1)
            if winner >= 0:
                early_wins[winner] += 1
        
        for result in late_games:
            winner = result.get('winner', -1)
            if winner >= 0:
                late_wins[winner] += 1
        
        early_win_rates = [w / 100 for w in early_wins]
        late_win_rates = [w / 100 for w in late_wins]
        
        # Score improvement
        early_avg_scores = [0, 0, 0, 0]
        late_avg_scores = [0, 0, 0, 0]
        
        for result in early_games:
            scores = result.get('final_scores', [25000, 25000, 25000, 25000])
            for i, score in enumerate(scores):
                early_avg_scores[i] += score
        
        for result in late_games:
            scores = result.get('final_scores', [25000, 25000, 25000, 25000])
            for i, score in enumerate(scores):
                late_avg_scores[i] += score
        
        early_avg_scores = [s / 100 for s in early_avg_scores]
        late_avg_scores = [s / 100 for s in late_avg_scores]
        
        return {
            'early_win_rates': early_win_rates,
            'late_win_rates': late_win_rates,
            'win_rate_improvement': [late - early for early, late in zip(early_win_rates, late_win_rates)],
            'early_avg_scores': early_avg_scores,
            'late_avg_scores': late_avg_scores,
            'score_improvement': [late - early for early, late in zip(early_avg_scores, late_avg_scores)]
        }

    def plot_learning_curves(self, save_path: str = None):
        """Plot learning curves"""
        if len(self.game_results) < 50:
            print("Not enough data for plotting")
            return
        
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 10))
        
        # Win rates
        win_rates = self.calculate_win_rates()
        for player_name, rates in win_rates.items():
            ax1.plot(rates, label=player_name.replace('_', ' ').title())
        ax1.set_title('Win Rates Over Time')
        ax1.set_xlabel('Games')
        ax1.set_ylabel('Win Rate')
        ax1.legend()
        ax1.grid(True)
        
        # Average scores
        avg_scores = self.calculate_average_scores()
        for player_name, scores in avg_scores.items():
            ax2.plot(scores, label=player_name.replace('_', ' ').title())
        ax2.set_title('Average Scores Over Time')
        ax2.set_xlabel('Games')
        ax2.set_ylabel('Score')
        ax2.legend()
        ax2.grid(True)
        
        # Game length distribution
        game_lengths = [result.get('turns', 0) for result in self.game_results]
        ax3.hist(game_lengths, bins=30, alpha=0.7, edgecolor='black')
        ax3.set_title('Game Length Distribution')
        ax3.set_xlabel('Number of Turns')
        ax3.set_ylabel('Frequency')
        ax3.grid(True)
        
        # Learning progress comparison
        progress = self.analyze_learning_progress()
        if 'error' not in progress:
            players = ['Player 1', 'Player 2', 'Player 3', 'Player 4']
            early_rates = progress['early_win_rates']
            late_rates = progress['late_win_rates']
            
            x = np.arange(len(players))
            width = 0.35
            
            ax4.bar(x - width/2, early_rates, width, label='Early Games', alpha=0.7)
            ax4.bar(x + width/2, late_rates, width, label='Late Games', alpha=0.7)
            ax4.set_title('Win Rate Improvement')
            ax4.set_xlabel('Players')
            ax4.set_ylabel('Win Rate')
            ax4.set_xticks(x)
            ax4.set_xticklabels(players)
            ax4.legend()
            ax4.grid(True)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"Learning curves saved to {save_path}")
        else:
            plt.show()
        
        plt.close()

    def generate_report(self) -> str:
        """Generate a text report of training progress"""
        if len(self.game_results) < 10:
            return "Not enough games for meaningful analysis"
        
        report = []
        report.append("=== AI TRAINING ANALYSIS REPORT ===\n")
        
        # Basic statistics
        total_games = len(self.game_results)
        report.append(f"Total Games Played: {total_games}")
        
        # Win distribution
        wins = [0, 0, 0, 0]
        for result in self.game_results:
            winner = result.get('winner', -1)
            if winner >= 0:
                wins[winner] += 1
        
        report.append("\nOverall Win Distribution:")
        for i, win_count in enumerate(wins):
            win_rate = win_count / total_games
            report.append(f"  Player {i+1}: {win_count} wins ({win_rate:.3f})")
        
        # Average game length
        game_lengths = [result.get('turns', 0) for result in self.game_results]
        avg_length = np.mean(game_lengths)
        report.append(f"\nAverage Game Length: {avg_length:.1f} turns")
        
        # Learning progress
        progress = self.analyze_learning_progress()
        if 'error' not in progress:
            report.append("\nLearning Progress (Early vs Late 100 games):")
            for i in range(4):
                early = progress['early_win_rates'][i]
                late = progress['late_win_rates'][i]
                improvement = late - early
                report.append(f"  Player {i+1}: {early:.3f} → {late:.3f} ({improvement:+.3f})")
        
        return "\n".join(report)
