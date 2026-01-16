"""
ARIMA Forecast Dashboard Generator

Generates an interactive HTML dashboard with:
- District selector
- Time range controls
- Toggle for forecast/fitted/actual
- Embedded Plotly charts
- Metrics summary table
"""

import os
import logging
from typing import Dict, List, Optional
from datetime import datetime

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from visualization.forecast_diagnostics import ARIMADiagnostics
from config import OUTPUT_DIR

logger = logging.getLogger(__name__)


class DashboardGenerator:
    """
    Generates interactive HTML dashboard for ARIMA forecast analysis.
    """
    
    def __init__(self, diagnostics: Optional[ARIMADiagnostics] = None):
        """
        Initialize dashboard generator.
        
        Args:
            diagnostics: ARIMADiagnostics instance (will create if not provided)
        """
        self.diagnostics = diagnostics or ARIMADiagnostics()
        self.output_dir = os.path.join(OUTPUT_DIR, "diagnostics")
        os.makedirs(self.output_dir, exist_ok=True)
    
    def generate_dashboard(
        self,
        forecast_periods: int = 24,
        confidence_level: float = 0.95
    ) -> str:
        """
        Generate complete interactive HTML dashboard.
        
        Returns:
            Path to generated dashboard HTML file
        """
        # Ensure models are loaded
        if not self.diagnostics.models:
            if not self.diagnostics.load_models():
                raise ValueError("Could not load models")
        
        districts = self.diagnostics.get_districts()
        
        # Generate summary metrics table
        summary_df = self.diagnostics.generate_summary_table()
        
        # Generate all forecast plots as JSON for embedding
        plots_json = {}
        for district in districts:
            fig = self.diagnostics.generate_forecast_plot(
                district, 
                forecast_periods=forecast_periods,
                confidence_level=confidence_level
            )
            if fig:
                plots_json[district] = fig.to_json()
        
        # Generate diagnostic plots
        diag_plots_json = {}
        for district in districts:
            fig = self.diagnostics.generate_residual_plots(district)
            if fig:
                diag_plots_json[district] = fig.to_json()
        
        # Build HTML
        html_content = self._build_html(
            districts=districts,
            summary_df=summary_df,
            plots_json=plots_json,
            diag_plots_json=diag_plots_json,
            forecast_periods=forecast_periods,
            confidence_level=confidence_level
        )
        
        # Save dashboard
        dashboard_path = os.path.join(self.output_dir, "dashboard.html")
        with open(dashboard_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        logger.info(f"Dashboard saved to {dashboard_path}")
        return dashboard_path
    
    def _build_html(
        self,
        districts: List[str],
        summary_df: pd.DataFrame,
        plots_json: Dict[str, str],
        diag_plots_json: Dict[str, str],
        forecast_periods: int,
        confidence_level: float
    ) -> str:
        """Build the complete HTML dashboard."""
        
        # Convert summary to HTML table
        summary_html = summary_df.to_html(
            classes='metrics-table',
            index=False,
            border=0
        )
        
        # District options
        district_options = '\n'.join([
            f'<option value="{d}">{d}</option>' for d in districts
        ])
        
        # Plots JSON string
        import json
        plots_data = json.dumps(plots_json)
        diag_plots_data = json.dumps(diag_plots_json)
        
        html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ARIMA Enrollment Forecast Dashboard</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #fff;
            min-height: 100vh;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }}
        
        header {{
            text-align: center;
            padding: 30px 0;
            border-bottom: 1px solid #333;
            margin-bottom: 30px;
        }}
        
        header h1 {{
            font-size: 2.5rem;
            background: linear-gradient(135deg, #00d4ff, #00ff88);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }}
        
        header p {{
            color: #888;
            margin-top: 10px;
        }}
        
        .controls {{
            display: flex;
            gap: 20px;
            flex-wrap: wrap;
            align-items: center;
            padding: 20px;
            background: #2a2a4a;
            border-radius: 12px;
            margin-bottom: 30px;
        }}
        
        .control-group {{
            display: flex;
            flex-direction: column;
            gap: 5px;
        }}
        
        .control-group label {{
            font-size: 0.85rem;
            color: #888;
        }}
        
        select, input[type="range"] {{
            padding: 10px 15px;
            background: #1a1a2e;
            border: 1px solid #444;
            border-radius: 8px;
            color: #fff;
            font-size: 14px;
            cursor: pointer;
        }}
        
        select:focus {{
            outline: none;
            border-color: #00d4ff;
        }}
        
        .toggle-group {{
            display: flex;
            gap: 10px;
        }}
        
        .toggle-btn {{
            padding: 10px 20px;
            background: #333;
            border: none;
            border-radius: 8px;
            color: #fff;
            cursor: pointer;
            transition: all 0.2s;
        }}
        
        .toggle-btn.active {{
            background: linear-gradient(135deg, #00d4ff, #00ff88);
            color: #1a1a2e;
        }}
        
        .chart-container {{
            background: #2a2a4a;
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 30px;
        }}
        
        .chart-title {{
            font-size: 1.3rem;
            margin-bottom: 15px;
            color: #00d4ff;
        }}
        
        #forecast-chart, #diagnostics-chart {{
            width: 100%;
            min-height: 500px;
        }}
        
        .metrics-section {{
            background: #2a2a4a;
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 30px;
        }}
        
        .metrics-section h2 {{
            color: #00d4ff;
            margin-bottom: 20px;
        }}
        
        .metrics-table {{
            width: 100%;
            border-collapse: collapse;
        }}
        
        .metrics-table th, .metrics-table td {{
            padding: 12px 15px;
            text-align: left;
            border-bottom: 1px solid #444;
        }}
        
        .metrics-table th {{
            background: #333;
            color: #00d4ff;
            font-weight: 600;
        }}
        
        .metrics-table tr:hover {{
            background: #333;
        }}
        
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 30px;
        }}
        
        .stat-card {{
            background: #333;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
        }}
        
        .stat-value {{
            font-size: 2rem;
            font-weight: bold;
            color: #00d4ff;
        }}
        
        .stat-label {{
            font-size: 0.85rem;
            color: #888;
            margin-top: 5px;
        }}
        
        .export-buttons {{
            display: flex;
            gap: 10px;
            margin-top: 20px;
        }}
        
        .export-btn {{
            padding: 10px 20px;
            background: linear-gradient(135deg, #00d4ff, #00ff88);
            border: none;
            border-radius: 8px;
            color: #1a1a2e;
            font-weight: bold;
            cursor: pointer;
            transition: transform 0.2s;
        }}
        
        .export-btn:hover {{
            transform: translateY(-2px);
        }}
        
        footer {{
            text-align: center;
            padding: 30px;
            color: #666;
            border-top: 1px solid #333;
            margin-top: 30px;
        }}
        
        .tab-buttons {{
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
        }}
        
        .tab-btn {{
            padding: 12px 24px;
            background: #333;
            border: none;
            border-radius: 8px;
            color: #fff;
            cursor: pointer;
            font-size: 14px;
            transition: all 0.2s;
        }}
        
        .tab-btn.active {{
            background: #00d4ff;
            color: #1a1a2e;
        }}
        
        .tab-content {{
            display: none;
        }}
        
        .tab-content.active {{
            display: block;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>📊 ARIMA Enrollment Forecast Dashboard</h1>
            <p>Comprehensive diagnostics and visualization for district-level enrollment predictions</p>
            <p style="font-size: 0.8rem; margin-top: 5px;">Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
        </header>
        
        <div class="controls">
            <div class="control-group">
                <label>Select District</label>
                <select id="district-select">
                    {district_options}
                </select>
            </div>
            
            <div class="control-group">
                <label>Forecast Horizon</label>
                <select id="horizon-select">
                    <option value="6">6 Periods</option>
                    <option value="12">12 Periods</option>
                    <option value="24" selected>24 Periods</option>
                    <option value="36">36 Periods</option>
                </select>
            </div>
            
            <div class="toggle-group">
                <button class="toggle-btn active" onclick="toggleView('forecast')">📈 Forecast</button>
                <button class="toggle-btn" onclick="toggleView('diagnostics')">🔍 Diagnostics</button>
            </div>
        </div>
        
        <!-- Stats Cards -->
        <div class="stats-grid" id="stats-grid">
            <div class="stat-card">
                <div class="stat-value" id="stat-districts">{len(districts)}</div>
                <div class="stat-label">Districts Analyzed</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="stat-rmse">-</div>
                <div class="stat-label">Avg RMSE</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="stat-mape">-</div>
                <div class="stat-label">Avg MAPE (%)</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="stat-coverage">-</div>
                <div class="stat-label">Avg CI Coverage (%)</div>
            </div>
        </div>
        
        <!-- Forecast Chart -->
        <div class="chart-container" id="forecast-section">
            <h3 class="chart-title">📈 Enrollment Forecast</h3>
            <div id="forecast-chart"></div>
        </div>
        
        <!-- Diagnostics Chart -->
        <div class="chart-container" id="diagnostics-section" style="display: none;">
            <h3 class="chart-title">🔍 Residual Diagnostics</h3>
            <div id="diagnostics-chart"></div>
        </div>
        
        <!-- Metrics Summary Table -->
        <div class="metrics-section">
            <h2>📋 Cross-District Metrics Summary</h2>
            {summary_html}
            <div class="export-buttons">
                <button class="export-btn" onclick="downloadCSV()">📥 Export Metrics CSV</button>
                <button class="export-btn" onclick="downloadForecasts()">📥 Export Forecasts CSV</button>
            </div>
        </div>
        
        <footer>
            <p>UIDAI Enrollment Forecast Analytics | ARIMA Models | Confidence Level: {int(confidence_level*100)}%</p>
        </footer>
    </div>
    
    <script>
        // Data
        const forecastPlots = {plots_data};
        const diagnosticsPlots = {diag_plots_data};
        const districts = {json.dumps(districts)};
        
        // Initialize
        let currentDistrict = districts[0];
        let currentView = 'forecast';
        
        // Update chart when district changes
        document.getElementById('district-select').addEventListener('change', function() {{
            currentDistrict = this.value;
            updateCharts();
        }});
        
        function updateCharts() {{
            if (currentView === 'forecast' && forecastPlots[currentDistrict]) {{
                const plotData = JSON.parse(forecastPlots[currentDistrict]);
                Plotly.react('forecast-chart', plotData.data, plotData.layout);
            }} else if (currentView === 'diagnostics' && diagnosticsPlots[currentDistrict]) {{
                const plotData = JSON.parse(diagnosticsPlots[currentDistrict]);
                Plotly.react('diagnostics-chart', plotData.data, plotData.layout);
            }}
        }}
        
        function toggleView(view) {{
            currentView = view;
            
            // Update buttons
            document.querySelectorAll('.toggle-btn').forEach(btn => btn.classList.remove('active'));
            event.target.classList.add('active');
            
            // Show/hide sections
            if (view === 'forecast') {{
                document.getElementById('forecast-section').style.display = 'block';
                document.getElementById('diagnostics-section').style.display = 'none';
            }} else {{
                document.getElementById('forecast-section').style.display = 'none';
                document.getElementById('diagnostics-section').style.display = 'block';
            }}
            
            updateCharts();
        }}
        
        function downloadCSV() {{
            window.open('metrics_summary.csv', '_blank');
        }}
        
        function downloadForecasts() {{
            window.open('forecasts.csv', '_blank');
        }}
        
        // Calculate and display average metrics
        function updateStats() {{
            const table = document.querySelector('.metrics-table');
            if (!table) return;
            
            const rows = table.querySelectorAll('tbody tr');
            let totalRMSE = 0, totalMAPE = 0, totalCoverage = 0;
            let countRMSE = 0, countMAPE = 0, countCoverage = 0;
            
            rows.forEach(row => {{
                const cells = row.querySelectorAll('td');
                if (cells.length >= 8) {{
                    const rmse = parseFloat(cells[1].textContent);
                    const mape = parseFloat(cells[3].textContent);
                    const coverage = parseFloat(cells[7].textContent);
                    
                    if (!isNaN(rmse)) {{ totalRMSE += rmse; countRMSE++; }}
                    if (!isNaN(mape)) {{ totalMAPE += mape; countMAPE++; }}
                    if (!isNaN(coverage)) {{ totalCoverage += coverage; countCoverage++; }}
                }}
            }});
            
            if (countRMSE > 0) document.getElementById('stat-rmse').textContent = (totalRMSE / countRMSE).toFixed(1);
            if (countMAPE > 0) document.getElementById('stat-mape').textContent = (totalMAPE / countMAPE).toFixed(1);
            if (countCoverage > 0) document.getElementById('stat-coverage').textContent = (totalCoverage / countCoverage).toFixed(1);
        }}
        
        // Initialize on load
        window.onload = function() {{
            updateCharts();
            updateStats();
        }};
    </script>
</body>
</html>'''
        
        return html


def generate_dashboard(forecast_periods: int = 24, confidence_level: float = 0.95) -> str:
    """
    Convenience function to generate dashboard.
    
    Returns:
        Path to generated dashboard
    """
    generator = DashboardGenerator()
    return generator.generate_dashboard(forecast_periods, confidence_level)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    path = generate_dashboard()
    print(f"Dashboard generated: {path}")
