"""
Gender Inclusion Tracker - Data Preprocessing
Handles data cleaning, normalization, and feature computation.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from sklearn.impute import SimpleImputer, KNNImputer
from sklearn.preprocessing import StandardScaler, MinMaxScaler
<<<<<<< HEAD
import structlog

from ..core.config import settings

logger = structlog.get_logger()
=======
import logging

from ..core.config import settings

logger = logging.getLogger(__name__)
>>>>>>> origin/ridwan/gender-tracker-v2


@dataclass
class PreprocessingReport:
    """Report of preprocessing operations performed."""
    original_rows: int
    final_rows: int
    columns_renamed: Dict[str, str]
    missing_values: Dict[str, int]
    imputed_columns: List[str]
    computed_features: List[str]
    warnings: List[str] = field(default_factory=list)


class GenderDataPreprocessor:
    """Preprocessor for gender-related Aadhaar data."""
    
    # Standard column mappings for various naming conventions
    COLUMN_MAPPINGS = {
        # State columns
        'state': ['state', 'state_name', 'statename', 'state_cd'],
        'state_code': ['state_code', 'state_cd', 'statecode'],
        
        # District columns
        'district': ['district', 'district_name', 'districtname', 'dist_name'],
        'district_code': ['district_code', 'district_cd', 'districtcode', 'dist_code'],
        
        # Gender columns
        'male_enrolled': ['male_enrolled', 'male_count', 'male', 'm_enrolled', 'men_enrolled', 'male_aadhaar'],
        'female_enrolled': ['female_enrolled', 'female_count', 'female', 'f_enrolled', 'women_enrolled', 'female_aadhaar'],
        
        # Age group columns
        'age_0_5': ['age_0_5', 'age0_5', '0_5', 'infant', 'age_0to5', 'age_below_5'],
        'age_5_17': ['age_5_17', 'age5_17', '5_17', 'child', 'age_5to17', 'age_5_to_17'],
        'age_18_plus': ['age_18_greater', 'age_18_plus', 'age18_plus', 'adult', 'age_above_18', 'age_18_above'],
        
        # Date columns
        'date': ['date', 'month', 'period', 'month_year', 'report_date'],
        'year': ['year', 'yr', 'financial_year', 'fy'],
        
        # Other demographic indicators
        'pincode': ['pincode', 'pin_code', 'pin', 'postal_code'],
        'total_enrolled': ['total', 'total_enrolled', 'total_count', 'all_enrolled'],
    }
    
    def __init__(self):
        self.scaler = StandardScaler()
        self.imputer = SimpleImputer(strategy='median')
        self.report: Optional[PreprocessingReport] = None
    
    def normalize_columns(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, str]]:
        """
        Normalize column names to standard format.
        
        Returns:
            Tuple of (normalized DataFrame, mapping of old -> new names)
        """
        df = df.copy()
        column_map = {}
        columns_lower = {col.lower().strip(): col for col in df.columns}
        
        for standard_name, variations in self.COLUMN_MAPPINGS.items():
            for variation in variations:
                if variation.lower() in columns_lower:
                    original_col = columns_lower[variation.lower()]
                    if original_col != standard_name:
                        column_map[original_col] = standard_name
                    break
        
        # Apply renaming
        if column_map:
            df = df.rename(columns=column_map)
        
        return df, column_map
    
    def compute_gender_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Compute gender-related features.
        
        Features computed:
        - female_coverage_ratio: Female / Total enrollment
        - male_coverage_ratio: Male / Total enrollment
        - gender_gap: Male - Female ratio difference
        - female_to_male_ratio: Female / Male
        """
        df = df.copy()
        computed = []
        
        # Try to compute from available columns
        has_male = 'male_enrolled' in df.columns
        has_female = 'female_enrolled' in df.columns
        has_total = 'total_enrolled' in df.columns
        
        # Compute total if not present
        if not has_total and has_male and has_female:
            df['total_enrolled'] = df['male_enrolled'] + df['female_enrolled']
            has_total = True
            computed.append('total_enrolled')
        
        # If we have age groups but not gender, estimate from age distribution
        if not has_male and not has_female:
            age_cols = ['age_0_5', 'age_5_17', 'age_18_plus']
            available_age = [col for col in age_cols if col in df.columns]
            
            if available_age:
                # Sum all age groups as total
                df['total_enrolled'] = df[available_age].sum(axis=1)
                # Estimate gender split (use national average ~51.5% male, 48.5% female)
                df['male_enrolled'] = df['total_enrolled'] * 0.515
                df['female_enrolled'] = df['total_enrolled'] * 0.485
                has_male = has_female = has_total = True
                computed.extend(['total_enrolled (estimated)', 'male_enrolled (estimated)', 'female_enrolled (estimated)'])
                logger.warning("Gender data not available, using estimated split based on national averages")
        
        # Compute ratios
        if has_male and has_female:
            # Safe division
            total = df.get('total_enrolled', df['male_enrolled'] + df['female_enrolled'])
            total = total.replace(0, np.nan)
            
            df['female_coverage_ratio'] = df['female_enrolled'] / total
            df['male_coverage_ratio'] = df['male_enrolled'] / total
            computed.extend(['female_coverage_ratio', 'male_coverage_ratio'])
            
            # Gender gap (positive = more males)
            df['gender_gap'] = df['male_coverage_ratio'] - df['female_coverage_ratio']
            computed.append('gender_gap')
            
            # Female to male ratio
            male_safe = df['male_enrolled'].replace(0, np.nan)
            df['female_to_male_ratio'] = df['female_enrolled'] / male_safe
            computed.append('female_to_male_ratio')
        
        return df, computed
    
    def handle_missing_values(
        self,
        df: pd.DataFrame,
        strategy: str = 'median',
        create_indicators: bool = True
    ) -> Tuple[pd.DataFrame, List[str]]:
        """
        Handle missing values in the dataset.
        
        Args:
            df: Input DataFrame
            strategy: Imputation strategy ('median', 'mean', 'knn')
            create_indicators: Whether to create missing indicator columns
        
        Returns:
            Tuple of (imputed DataFrame, list of imputed columns)
        """
        df = df.copy()
        imputed_cols = []
        
        # Identify numeric columns with missing values
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        missing_cols = [col for col in numeric_cols if df[col].isna().sum() > 0]
        
        if not missing_cols:
            return df, imputed_cols
        
        # Create missing indicators
        if create_indicators:
            for col in missing_cols:
                indicator_name = f'{col}_missing'
                df[indicator_name] = df[col].isna().astype(int)
        
        # Impute missing values
        if strategy == 'knn':
            imputer = KNNImputer(n_neighbors=5)
        else:
            imputer = SimpleImputer(strategy=strategy)
        
        df[missing_cols] = imputer.fit_transform(df[missing_cols])
        imputed_cols = missing_cols
        
        return df, imputed_cols
    
    def aggregate_by_geography(
        self,
        df: pd.DataFrame,
        level: str = 'district'
    ) -> pd.DataFrame:
        """
        Aggregate data by geographic level.
        
        Args:
            df: Input DataFrame
            level: 'district', 'state', or 'pincode'
        
        Returns:
            Aggregated DataFrame
        """
        group_cols = []
        
        if level == 'state':
            group_cols = ['state'] if 'state' in df.columns else []
        elif level == 'district':
            group_cols = [col for col in ['state', 'district'] if col in df.columns]
        elif level == 'pincode':
            group_cols = [col for col in ['state', 'district', 'pincode'] if col in df.columns]
        
        if not group_cols:
            logger.warning(f"No geographic columns found for {level} aggregation")
            return df
        
        # Define aggregation functions
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        agg_funcs = {col: 'sum' for col in numeric_cols}
        
        # Ratios should be recalculated after aggregation, not summed
        ratio_cols = ['female_coverage_ratio', 'male_coverage_ratio', 'gender_gap', 'female_to_male_ratio']
        for col in ratio_cols:
            if col in agg_funcs:
                del agg_funcs[col]
        
        aggregated = df.groupby(group_cols).agg(agg_funcs).reset_index()
        
        # Recompute ratios
        aggregated, _ = self.compute_gender_features(aggregated)
        
        return aggregated
    
    def preprocess(
        self,
        df: pd.DataFrame,
        geography_level: str = 'district',
        imputation_strategy: str = 'median'
    ) -> Tuple[pd.DataFrame, PreprocessingReport]:
        """
        Full preprocessing pipeline.
        
        Args:
            df: Raw input DataFrame
            geography_level: Aggregation level
            imputation_strategy: How to handle missing values
        
        Returns:
            Tuple of (processed DataFrame, preprocessing report)
        """
        original_rows = len(df)
        warnings = []
        
        # Step 1: Normalize column names
        df, column_map = self.normalize_columns(df)
        
        # Step 2: Record missing values before imputation
        missing_before = {
            col: int(df[col].isna().sum())
            for col in df.columns
            if df[col].isna().sum() > 0
        }
        
        # Step 3: Aggregate by geography if needed
        if geography_level:
            df = self.aggregate_by_geography(df, geography_level)
        
        # Step 4: Compute gender features
        df, computed_features = self.compute_gender_features(df)
        
        # Step 5: Handle missing values
        df, imputed_cols = self.handle_missing_values(df, strategy=imputation_strategy)
        
        # Step 6: Create binary risk label
        if 'female_coverage_ratio' in df.columns:
            threshold = settings.default_risk_threshold
            df['high_risk'] = (df['female_coverage_ratio'] < threshold).astype(int)
            computed_features.append('high_risk')
        
        # Create report
        self.report = PreprocessingReport(
            original_rows=original_rows,
            final_rows=len(df),
            columns_renamed=column_map,
            missing_values=missing_before,
            imputed_columns=imputed_cols,
            computed_features=computed_features,
            warnings=warnings
        )
        
        return df, self.report
