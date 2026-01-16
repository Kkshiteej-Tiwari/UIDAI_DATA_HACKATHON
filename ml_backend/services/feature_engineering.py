"""
Feature Engineering for Biometric Risk Prediction

PRIVACY NOTICE:
- All features derived from aggregated, anonymized data
- No individual-level features or PII
- Operations performed on state/district/age-group aggregates only
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from sklearn.preprocessing import LabelEncoder

from config import HIGH_RISK_STATES, AGE_BUCKETS, RISK_THRESHOLDS


class FeatureEngineer:
    """Feature engineering for biometric re-enrollment risk prediction"""
    
    def __init__(self):
        self.label_encoders = {}
        self.feature_names = []
        
    def process_enrolment_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Process enrollment data and extract features"""
        if df.empty:
            return df
            
        df = df.copy()
        
        # Parse date
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'], format='%d-%m-%Y', errors='coerce')
            df['month'] = df['date'].dt.month
            df['year'] = df['date'].dt.year
        
        # Convert age columns to numeric
        for col in ['age_0_5', 'age_5_17', 'age_18_greater']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
        # Total enrollments per record
        age_cols = [c for c in ['age_0_5', 'age_5_17', 'age_18_greater'] if c in df.columns]
        if age_cols:
            df['total_enrollments'] = df[age_cols].sum(axis=1)
            
            # Age distribution percentages
            for col in age_cols:
                df[f'{col}_pct'] = (df[col] / df['total_enrollments'].replace(0, 1)) * 100
        
        return df
    
    def process_demographic_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Process demographic update data"""
        if df.empty:
            return df
            
        df = df.copy()
        
        # Parse date
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'], format='%d-%m-%Y', errors='coerce')
            df['month'] = df['date'].dt.month
            df['year'] = df['date'].dt.year
        
        # Convert age columns to numeric
        for col in ['demo_age_5_17', 'demo_age_17_']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
        # Total demographic updates
        demo_cols = [c for c in ['demo_age_5_17', 'demo_age_17_'] if c in df.columns]
        if demo_cols:
            df['total_demo_updates'] = df[demo_cols].sum(axis=1)
        
        return df
    
    def process_biometric_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Process biometric update data"""
        if df.empty:
            return df
            
        df = df.copy()
        
        # Parse date
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'], format='%d-%m-%Y', errors='coerce')
            df['month'] = df['date'].dt.month
            df['year'] = df['date'].dt.year
        
        # Convert age columns to numeric
        for col in ['bio_age_5_17', 'bio_age_17_']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
        # Total biometric updates
        bio_cols = [c for c in ['bio_age_5_17', 'bio_age_17_'] if c in df.columns]
        if bio_cols:
            df['total_bio_updates'] = df[bio_cols].sum(axis=1)
        
        return df
    
    def aggregate_by_state(self, df: pd.DataFrame) -> pd.DataFrame:
        """Aggregate data at state level"""
        if df.empty or 'state' not in df.columns:
            return df
            
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        
        agg_dict = {col: 'sum' for col in numeric_cols if col not in ['month', 'year']}
        
        if agg_dict:
            return df.groupby('state').agg(agg_dict).reset_index()
        return df
    
    def aggregate_by_district(self, df: pd.DataFrame) -> pd.DataFrame:
        """Aggregate data at district level"""
        if df.empty or 'district' not in df.columns:
            return df
            
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        
        agg_dict = {col: 'sum' for col in numeric_cols if col not in ['month', 'year']}
        
        group_cols = ['state', 'district'] if 'state' in df.columns else ['district']
        
        if agg_dict:
            return df.groupby(group_cols).agg(agg_dict).reset_index()
        return df
    
    def create_risk_features(
        self,
        enrolment_df: Optional[pd.DataFrame] = None,
        demographic_df: Optional[pd.DataFrame] = None,
        biometric_df: Optional[pd.DataFrame] = None,
        aggregation_level: str = 'state'
    ) -> pd.DataFrame:
        """
        Create comprehensive risk features from multiple datasets
        
        Args:
            enrolment_df: Processed enrollment data
            demographic_df: Processed demographic data
            biometric_df: Processed biometric data
            aggregation_level: 'state' or 'district'
            
        Returns:
            DataFrame with engineered risk features
        """
        dfs_to_merge = []
        
        # Process each dataset
        if enrolment_df is not None and not enrolment_df.empty:
            enrol = self.process_enrolment_data(enrolment_df)
            if aggregation_level == 'state':
                enrol = self.aggregate_by_state(enrol)
            else:
                enrol = self.aggregate_by_district(enrol)
            enrol = enrol.add_prefix('enrol_')
            if aggregation_level == 'state':
                enrol = enrol.rename(columns={'enrol_state': 'state'})
            else:
                enrol = enrol.rename(columns={'enrol_state': 'state', 'enrol_district': 'district'})
            dfs_to_merge.append(enrol)
        
        if demographic_df is not None and not demographic_df.empty:
            demo = self.process_demographic_data(demographic_df)
            if aggregation_level == 'state':
                demo = self.aggregate_by_state(demo)
            else:
                demo = self.aggregate_by_district(demo)
            demo = demo.add_prefix('demo_')
            if aggregation_level == 'state':
                demo = demo.rename(columns={'demo_state': 'state'})
            else:
                demo = demo.rename(columns={'demo_state': 'state', 'demo_district': 'district'})
            dfs_to_merge.append(demo)
        
        if biometric_df is not None and not biometric_df.empty:
            bio = self.process_biometric_data(biometric_df)
            if aggregation_level == 'state':
                bio = self.aggregate_by_state(bio)
            else:
                bio = self.aggregate_by_district(bio)
            bio = bio.add_prefix('bio_')
            if aggregation_level == 'state':
                bio = bio.rename(columns={'bio_state': 'state'})
            else:
                bio = bio.rename(columns={'bio_state': 'state', 'bio_district': 'district'})
            dfs_to_merge.append(bio)
        
        if not dfs_to_merge:
            return pd.DataFrame()
        
        # Merge all dataframes
        merge_cols = ['state', 'district'] if aggregation_level == 'district' else ['state']
        result = dfs_to_merge[0]
        for df in dfs_to_merge[1:]:
            result = result.merge(df, on=merge_cols, how='outer')
        
        # Fill missing values
        result = result.fillna(0)
        
        # Create derived features
        result = self._create_derived_features(result, aggregation_level)
        
        return result
    
    def _create_derived_features(self, df: pd.DataFrame, aggregation_level: str) -> pd.DataFrame:
        """Create derived features for risk prediction"""
        df = df.copy()
        
        # Biometric update ratio (if both bio and demo data available)
        bio_total_col = [c for c in df.columns if 'bio_total' in c]
        demo_total_col = [c for c in df.columns if 'demo_total' in c]
        
        if bio_total_col and demo_total_col:
            bio_col = bio_total_col[0]
            demo_col = demo_total_col[0]
            df['biometric_update_ratio'] = df[bio_col] / (df[bio_col] + df[demo_col]).replace(0, 1)
        
        # High risk state flag
        if 'state' in df.columns:
            df['is_high_risk_state'] = df['state'].isin(HIGH_RISK_STATES).astype(int)
        
        # Encode state
        if 'state' in df.columns:
            if 'state' not in self.label_encoders:
                self.label_encoders['state'] = LabelEncoder()
                df['encoded_state'] = self.label_encoders['state'].fit_transform(df['state'].astype(str))
            else:
                # Handle unseen labels
                known_states = set(self.label_encoders['state'].classes_)
                df['state_temp'] = df['state'].apply(lambda x: x if x in known_states else 'Unknown')
                if 'Unknown' not in known_states:
                    self.label_encoders['state'].classes_ = np.append(self.label_encoders['state'].classes_, 'Unknown')
                df['encoded_state'] = self.label_encoders['state'].transform(df['state_temp'].astype(str))
                df = df.drop('state_temp', axis=1)
        
        # Encode district
        if 'district' in df.columns:
            if 'district' not in self.label_encoders:
                self.label_encoders['district'] = LabelEncoder()
                df['encoded_district'] = self.label_encoders['district'].fit_transform(df['district'].astype(str))
            else:
                known_districts = set(self.label_encoders['district'].classes_)
                df['district_temp'] = df['district'].apply(lambda x: x if x in known_districts else 'Unknown')
                if 'Unknown' not in known_districts:
                    self.label_encoders['district'].classes_ = np.append(self.label_encoders['district'].classes_, 'Unknown')
                df['encoded_district'] = self.label_encoders['district'].transform(df['district_temp'].astype(str))
                df = df.drop('district_temp', axis=1)
        
        # Store feature names
        self.feature_names = [c for c in df.columns if c not in ['state', 'district']]
        
        return df
    
    def create_proxy_risk_labels(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Create proxy risk labels when ground truth is unavailable
        
        Risk factors:
        - High risk state
        - Low biometric update ratio
        - High elderly population percentage
        """
        df = df.copy()
        
        risk_score = np.zeros(len(df))
        
        # Factor 1: High risk state (weight: 0.3)
        if 'is_high_risk_state' in df.columns:
            risk_score += df['is_high_risk_state'] * 0.3
        
        # Factor 2: Low biometric update ratio (weight: 0.4)
        if 'biometric_update_ratio' in df.columns:
            # Lower ratio = higher risk
            risk_score += (1 - df['biometric_update_ratio']) * 0.4
        
        # Factor 3: High elderly percentage (weight: 0.3)
        elderly_cols = [c for c in df.columns if 'age_18_greater' in c or 'age_17_' in c]
        total_cols = [c for c in df.columns if 'total' in c and 'enrol' in c]
        
        if elderly_cols and total_cols:
            elderly_pct = df[elderly_cols].sum(axis=1) / df[total_cols].sum(axis=1).replace(0, 1)
            risk_score += elderly_pct * 0.3
        
        df['proxy_risk_score'] = risk_score
        df['risk_category'] = pd.cut(
            df['proxy_risk_score'],
            bins=[0, RISK_THRESHOLDS['low'], RISK_THRESHOLDS['medium'], RISK_THRESHOLDS['high'], 1.0],
            labels=['Low', 'Medium', 'High', 'Critical']
        )
        
        return df
    
    def get_feature_names(self) -> List[str]:
        """Return list of engineered feature names"""
        return self.feature_names


# Singleton instance
feature_engineer = FeatureEngineer()
