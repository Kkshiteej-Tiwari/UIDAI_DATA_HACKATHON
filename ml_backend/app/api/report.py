"""
Gender Inclusion Tracker - Report API Router
Endpoints for generating reports and maps.
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, Response
from typing import Optional, Dict, Any
from pathlib import Path
from datetime import datetime
from io import BytesIO
import base64

from ..core.config import settings
from ..services.visualizations import GenderVisualization
from .analyze import _analysis_cache

router = APIRouter(prefix="/report", tags=["Reports"])


@router.get("/{analysis_id}")
async def generate_report(
    analysis_id: str,
    format: str = "json"  # 'json' or 'pdf'
):
    """
    Generate analysis report.
    
    Args:
        analysis_id: ID of the analysis to report on
        format: Output format (json or pdf)
    
    Returns:
        JSON report or PDF file
    """
    if analysis_id not in _analysis_cache:
        raise HTTPException(
            status_code=404,
            detail=f"Analysis {analysis_id} not found"
        )
    
    cached = _analysis_cache[analysis_id]
    df = cached['df']
    report = cached['report']
    
    try:
        # Build report data
        report_data = build_report(df, report, analysis_id)
        
        if format == 'json':
            return report_data
        
        elif format == 'pdf':
            # Generate PDF
            pdf_path = generate_pdf_report(report_data, analysis_id)
            if pdf_path and pdf_path.exists():
                return FileResponse(
                    pdf_path,
                    media_type='application/pdf',
                    filename=f'gender_tracker_report_{analysis_id}.pdf'
                )
            else:
                raise HTTPException(
                    status_code=500,
                    detail="PDF generation not available. Install fpdf2."
                )
        
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported format: {format}. Use 'json' or 'pdf'."
            )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Report generation failed: {str(e)}"
        )


@router.get("/map/choropleth")
async def get_choropleth_map(
    analysis_id: str,
    metric: str = "female_coverage_ratio",
    geography: str = "state"
):
    """
    Get choropleth map data for visualization.
    
    Returns GeoJSON-compatible data that can be rendered
    by frontend mapping libraries (Leaflet, Mapbox, etc.)
    """
    if analysis_id not in _analysis_cache:
        raise HTTPException(
            status_code=404,
            detail=f"Analysis {analysis_id} not found"
        )
    
    df = _analysis_cache[analysis_id]['df']
    
    if metric not in df.columns:
        raise HTTPException(
            status_code=400,
            detail=f"Metric '{metric}' not found in data. Available: {list(df.columns)}"
        )
    
    if geography not in df.columns:
        raise HTTPException(
            status_code=400,
            detail=f"Geography column '{geography}' not found"
        )
    
    try:
        viz = GenderVisualization()
        map_data = viz.create_choropleth_data(df, geo_column=geography, value_column=metric)
        
        return {
            'success': True,
            'metric': metric,
            'geography': geography,
            **map_data
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Map generation failed: {str(e)}"
        )


@router.get("/export/{analysis_id}")
async def export_data(
    analysis_id: str,
    format: str = "csv",
    include_predictions: bool = False
):
    """
    Export analysis data for field teams.
    
    Args:
        analysis_id: Analysis ID
        format: Export format ('csv' or 'json')
        include_predictions: Whether to include risk predictions
    """
    if analysis_id not in _analysis_cache:
        raise HTTPException(
            status_code=404,
            detail=f"Analysis {analysis_id} not found"
        )
    
    df = _analysis_cache[analysis_id]['df'].copy()
    
    # Select relevant columns for field teams
    export_columns = []
    priority_columns = ['state', 'district', 'district_code', 'female_coverage_ratio',
                       'gender_gap', 'male_enrolled', 'female_enrolled', 'total_enrolled']
    
    for col in priority_columns:
        if col in df.columns:
            export_columns.append(col)
    
    if include_predictions:
        pred_columns = ['high_risk', 'risk_probability', 'predicted_high_risk']
        for col in pred_columns:
            if col in df.columns:
                export_columns.append(col)
    
    export_df = df[export_columns] if export_columns else df
    
    if format == 'csv':
        csv_content = export_df.to_csv(index=False)
        return Response(
            content=csv_content,
            media_type='text/csv',
            headers={
                'Content-Disposition': f'attachment; filename=gender_data_{analysis_id}.csv'
            }
        )
    
    elif format == 'json':
        return {
            'analysis_id': analysis_id,
            'columns': export_columns,
            'n_records': len(export_df),
            'data': export_df.to_dict(orient='records')
        }
    
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported format: {format}"
        )


def build_report(df, preprocessing_report, analysis_id: str) -> Dict[str, Any]:
    """Build comprehensive report data."""
    report = {
        'title': 'Gender Inclusion Tracker - Analysis Report',
        'generated_at': datetime.now().isoformat(),
        'analysis_id': analysis_id,
        'summary': {
            'total_records': len(df),
            'geography_coverage': {}
        },
        'key_findings': [],
        'recommendations': [],
        'data_quality': {},
        'preprocessing': {}
    }
    
    # Summary
    if 'state' in df.columns:
        report['summary']['geography_coverage']['states'] = int(df['state'].nunique())
    if 'district' in df.columns:
        report['summary']['geography_coverage']['districts'] = int(df['district'].nunique())
    
    # Key findings
    if 'female_coverage_ratio' in df.columns:
        coverage = df['female_coverage_ratio'].dropna()
        mean_coverage = coverage.mean()
        
        report['summary']['mean_female_coverage'] = float(mean_coverage)
        report['summary']['min_female_coverage'] = float(coverage.min())
        report['summary']['max_female_coverage'] = float(coverage.max())
        
        # Finding: Overall coverage
        if mean_coverage < 0.5:
            report['key_findings'].append({
                'severity': 'critical',
                'finding': f'National average female coverage is critically low at {mean_coverage:.1%}'
            })
        elif mean_coverage < 0.85:
            report['key_findings'].append({
                'severity': 'warning',
                'finding': f'National average female coverage is {mean_coverage:.1%}, below target of 85%'
            })
        else:
            report['key_findings'].append({
                'severity': 'info',
                'finding': f'National average female coverage is {mean_coverage:.1%}'
            })
        
        # Finding: High-risk count
        if 'high_risk' in df.columns:
            high_risk_count = int(df['high_risk'].sum())
            high_risk_pct = df['high_risk'].mean() * 100
            report['key_findings'].append({
                'severity': 'warning' if high_risk_pct > 20 else 'info',
                'finding': f'{high_risk_count} districts ({high_risk_pct:.1f}%) classified as high-risk'
            })
            report['summary']['high_risk_districts'] = high_risk_count
    
    if 'gender_gap' in df.columns:
        gap = df['gender_gap'].dropna()
        avg_gap = gap.mean()
        max_gap = gap.max()
        
        report['summary']['avg_gender_gap'] = float(avg_gap)
        report['key_findings'].append({
            'severity': 'info',
            'finding': f'Average gender gap is {avg_gap:.1%}, maximum gap is {max_gap:.1%}'
        })
    
    # Recommendations
    if 'high_risk' in df.columns and df['high_risk'].sum() > 0:
        report['recommendations'].append({
            'priority': 'high',
            'action': 'Deploy mobile enrollment camps to high-risk districts',
            'target': f'{int(df["high_risk"].sum())} districts'
        })
    
    if 'gender_gap' in df.columns:
        high_gap = (df['gender_gap'] > 0.1).sum()
        if high_gap > 0:
            report['recommendations'].append({
                'priority': 'high',
                'action': 'Launch women-only registration drives',
                'target': f'{int(high_gap)} districts with >10% gender gap'
            })
    
    report['recommendations'].append({
        'priority': 'medium',
        'action': 'Partner with local women\'s self-help groups for awareness',
        'target': 'All districts below 80% coverage'
    })
    
    # Data quality
    report['data_quality'] = {
        'columns_renamed': len(preprocessing_report.columns_renamed),
        'missing_values_imputed': sum(preprocessing_report.missing_values.values()) if preprocessing_report.missing_values else 0,
        'features_computed': len(preprocessing_report.computed_features),
        'warnings': preprocessing_report.warnings
    }
    
    return report


def generate_pdf_report(report_data: Dict, analysis_id: str) -> Optional[Path]:
    """Generate PDF report using fpdf2."""
    try:
        from fpdf import FPDF
    except ImportError:
        return None
    
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    
    # Title
    pdf.set_font('Helvetica', 'B', 20)
    pdf.cell(0, 15, 'Gender Inclusion Tracker', ln=True, align='C')
    pdf.set_font('Helvetica', '', 12)
    pdf.cell(0, 10, 'Analysis Report', ln=True, align='C')
    pdf.cell(0, 10, f'Generated: {report_data["generated_at"]}', ln=True, align='C')
    pdf.ln(10)
    
    # Summary section
    pdf.set_font('Helvetica', 'B', 14)
    pdf.cell(0, 10, 'Summary', ln=True)
    pdf.set_font('Helvetica', '', 11)
    
    summary = report_data.get('summary', {})
    for key, value in summary.items():
        if isinstance(value, dict):
            pdf.cell(0, 8, f'{key}:', ln=True)
            for k, v in value.items():
                pdf.cell(20)
                pdf.cell(0, 8, f'  - {k}: {v}', ln=True)
        else:
            pdf.cell(0, 8, f'{key}: {value}', ln=True)
    
    pdf.ln(5)
    
    # Key Findings
    pdf.set_font('Helvetica', 'B', 14)
    pdf.cell(0, 10, 'Key Findings', ln=True)
    pdf.set_font('Helvetica', '', 11)
    
    for finding in report_data.get('key_findings', []):
        severity = finding.get('severity', 'info').upper()
        text = finding.get('finding', '')
        pdf.cell(0, 8, f'[{severity}] {text}', ln=True)
    
    pdf.ln(5)
    
    # Recommendations
    pdf.set_font('Helvetica', 'B', 14)
    pdf.cell(0, 10, 'Recommendations', ln=True)
    pdf.set_font('Helvetica', '', 11)
    
    for rec in report_data.get('recommendations', []):
        priority = rec.get('priority', 'medium').upper()
        action = rec.get('action', '')
        target = rec.get('target', '')
        pdf.cell(0, 8, f'[{priority}] {action}', ln=True)
        pdf.cell(0, 6, f'       Target: {target}', ln=True)
    
    # Save
    output_path = settings.artifacts_dir / f'report_{analysis_id}.pdf'
    pdf.output(str(output_path))
    
    return output_path
