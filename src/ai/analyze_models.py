# src/ai/analyze_models.py
#!/usr/bin/env python3
"""
Script to analyze trained AI models
"""

import argparse
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from ai.utils import (
    analyze_model_performance, 
    benchmark_model_speed, 
    get_model_complexity,
    validate_model_consistency,
    visualize_training_progress
)

def main():
    parser = argparse.ArgumentParser(description='Analyze trained AI models')
    parser.add_argument('--model-dir', type=str, required=True,
                       help='Directory containing trained models')
    parser.add_argument('--benchmark', action='store_true',
                       help='Run speed benchmarks')
    parser.add_argument('--complexity', action='store_true',
                       help='Analyze model complexity')
    parser.add_argument('--validate', action='store_true',
                       help='Validate model consistency')
    parser.add_argument('--visualize', action='store_true',
                       help='Create training visualizations')
    parser.add_argument('--all', action='store_true',
                       help='Run all analyses')
    parser.add_argument('--output-dir', type=str, default='analysis_output',
                       help='Directory for output files')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.model_dir):
        print(f"Error: Model directory {args.model_dir} does not exist")
        return
    
    os.makedirs(args.output_dir, exist_ok=True)
    
    print(f"Analyzing models in: {args.model_dir}")
    print("="*50)
    
    # Performance analysis
    if args.all or True:  # Always run basic performance analysis
        print("\n📊 PERFORMANCE ANALYSIS")
        print("-" * 30)
        performance = analyze_model_performance(args.model_dir)
        
        if 'error' in performance:
            print(f"❌ {performance['error']}")
        else:
            print(f"Total training games: {performance['total_training_games']}")
            print("Final win rates:")
            for i, rate in enumerate(performance['final_win_rates']):
                print(f"  Player {i+1}: {rate:.3f}")
            print("Model sizes (MB):")
            for i, size in enumerate(performance['model_sizes']):
                print(f"  Player {i+1}: {size:.2f} MB")
    
    # Speed benchmarks
    if args.benchmark or args.all:
        print("\n⚡ SPEED BENCHMARKS")
        print("-" * 30)
        try:
            benchmark_results = benchmark_model_speed(args.model_dir)
            for player_name, results in benchmark_results.items():
                print(f"{player_name}:")
                print(f"  Decisions/sec: {results['decisions_per_second']:.1f}")
                print(f"  Avg decision time: {results['avg_decision_time_ms']:.2f}ms")
        except Exception as e:
            print(f"❌ Benchmark failed: {e}")
    
    # Model complexity
    if args.complexity or args.all:
        print("\n🧠 MODEL COMPLEXITY")
        print("-" * 30)
        try:
            complexity = get_model_complexity(args.model_dir)
            for player_name, info in complexity.items():
                print(f"{player_name}:")
                print(f"  Parameters: {info['total_parameters']:,}")
                print(f"  Size: {info['model_size_mb']:.2f} MB")
        except Exception as e:
            print(f"❌ Complexity analysis failed: {e}")
    
    # Validation
    if args.validate or args.all:
        print("\n✅ MODEL VALIDATION")
        print("-" * 30)
        validation = validate_model_consistency(args.model_dir)
        
        if validation['all_models_present']:
            print("✅ All 4 models present")
        else:
            print("❌ Missing models")
        
        loadable_count = sum(validation['models_loadable'])
        print(f"✅ {loadable_count}/4 models loadable")
        
        if validation['errors']:
            print("Errors found:")
            for error in validation['errors']:
                print(f"  ❌ {error}")
    
    # Visualizations
    if args.visualize or args.all:
        print("\n📈 CREATING VISUALIZATIONS")
        print("-" * 30)
        try:
            viz_path = os.path.join(args.output_dir, "training_analysis.png")
            visualize_training_progress(args.model_dir, viz_path)
            print(f"✅ Visualization saved to {viz_path}")
        except Exception as e:
            print(f"❌ Visualization failed: {e}")
    
    print(f"\n📁 Analysis complete! Check {args.output_dir} for output files.")

if __name__ == "__main__":
    main()
