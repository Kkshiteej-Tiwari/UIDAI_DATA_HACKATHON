#!/usr/bin/env python3
"""
ARIMA Diagnostics Runner Script

Generates all diagnostic outputs for ARIMA enrollment forecasts:
- Interactive HTML dashboard
- Per-district forecast plots
- Per-district diagnostic plots
- Forecasts CSV
- Metrics summary CSV

Usage:
    python scripts/run_diagnostics.py [--output OUTPUT_DIR] [--periods PERIODS]
"""

import argparse
import logging
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from visualization.forecast_diagnostics import ARIMADiagnostics
from visualization.dashboard_generator import DashboardGenerator


def main():
    parser = argparse.ArgumentParser(
        description='Generate ARIMA forecast diagnostics and visualizations'
    )
    parser.add_argument(
        '--output', '-o',
        default='outputs/diagnostics',
        help='Output directory for generated files (default: outputs/diagnostics)'
    )
    parser.add_argument(
        '--periods', '-p',
        type=int,
        default=24,
        help='Forecast horizon in periods (default: 24)'
    )
    parser.add_argument(
        '--confidence', '-c',
        type=float,
        default=0.95,
        help='Confidence level for intervals (default: 0.95)'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)
    
    print("\n" + "="*60)
    print("📊 ARIMA FORECAST DIAGNOSTICS GENERATOR")
    print("="*60)
    
    # Initialize diagnostics
    diagnostics = ARIMADiagnostics()
    
    # Override output directory if specified
    if args.output:
        diagnostics.output_dir = args.output
        os.makedirs(args.output, exist_ok=True)
        os.makedirs(os.path.join(args.output, "plots"), exist_ok=True)
    
    # Load models
    print("\n📦 Loading trained models...")
    if not diagnostics.load_models():
        print("❌ Failed to load models. Make sure forecast models have been trained.")
        print("   Run: curl -X POST 'http://localhost:8000/api/forecast/train'")
        sys.exit(1)
    
    districts = diagnostics.get_districts()
    print(f"✅ Loaded {len(districts)} district models: {', '.join(districts)}")
    
    # Generate outputs
    print(f"\n📈 Generating visualizations (horizon: {args.periods} periods)...")
    outputs = diagnostics.generate_all_outputs(forecast_periods=args.periods)
    
    # Generate dashboard
    print("\n🖥️  Generating interactive dashboard...")
    dashboard_gen = DashboardGenerator(diagnostics)
    dashboard_path = dashboard_gen.generate_dashboard(
        forecast_periods=args.periods,
        confidence_level=args.confidence
    )
    outputs["dashboard"] = dashboard_path
    
    # Print results
    print("\n" + "="*60)
    print("✅ GENERATION COMPLETE")
    print("="*60)
    
    print(f"\n📁 Output directory: {diagnostics.output_dir}")
    print(f"\n📄 Generated files:")
    
    # Categorize outputs
    dashboard_files = [k for k in outputs.keys() if 'dashboard' in k]
    csv_files = [k for k in outputs.keys() if 'csv' in k]
    forecast_files = [k for k in outputs.keys() if 'forecast' in k and 'csv' not in k]
    diag_files = [k for k in outputs.keys() if 'diagnostics' in k]
    
    if dashboard_files:
        print("\n   📊 Dashboard:")
        for k in dashboard_files:
            print(f"      • {outputs[k]}")
    
    if csv_files:
        print("\n   📋 CSV Exports:")
        for k in csv_files:
            print(f"      • {outputs[k]}")
    
    if forecast_files:
        print(f"\n   📈 Forecast Plots ({len(forecast_files)} files):")
        for k in forecast_files[:3]:
            print(f"      • {outputs[k]}")
        if len(forecast_files) > 3:
            print(f"      ... and {len(forecast_files) - 3} more")
    
    if diag_files:
        print(f"\n   🔍 Diagnostic Plots ({len(diag_files)} files):")
        for k in diag_files[:3]:
            print(f"      • {outputs[k]}")
        if len(diag_files) > 3:
            print(f"      ... and {len(diag_files) - 3} more")
    
    # Summary table
    print("\n📊 Cross-District Summary:")
    print("-"*60)
    summary_df = diagnostics.generate_summary_table()
    print(summary_df.to_string(index=False))
    
    print("\n" + "="*60)
    print("🎉 Done! Open the dashboard to explore results:")
    print(f"   open {dashboard_path}")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
