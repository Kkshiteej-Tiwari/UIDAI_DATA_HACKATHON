"""
Gender Inclusion Tracker - Sample Data Generator
Generates realistic sample data for local testing without API access.
"""

import pandas as pd
import numpy as np
import json
from pathlib import Path
import random

# Set seed for reproducibility
np.random.seed(42)
random.seed(42)

# Indian states with codes
STATES = [
    ('AN', 'Andaman and Nicobar'),
    ('AP', 'Andhra Pradesh'),
    ('AR', 'Arunachal Pradesh'),
    ('AS', 'Assam'),
    ('BR', 'Bihar'),
    ('CH', 'Chandigarh'),
    ('CG', 'Chhattisgarh'),
    ('DD', 'Daman and Diu'),
    ('DL', 'Delhi'),
    ('GA', 'Goa'),
    ('GJ', 'Gujarat'),
    ('HR', 'Haryana'),
    ('HP', 'Himachal Pradesh'),
    ('JK', 'Jammu and Kashmir'),
    ('JH', 'Jharkhand'),
    ('KA', 'Karnataka'),
    ('KL', 'Kerala'),
    ('LA', 'Ladakh'),
    ('LD', 'Lakshadweep'),
    ('MP', 'Madhya Pradesh'),
    ('MH', 'Maharashtra'),
    ('MN', 'Manipur'),
    ('ML', 'Meghalaya'),
    ('MZ', 'Mizoram'),
    ('NL', 'Nagaland'),
    ('OR', 'Odisha'),
    ('PY', 'Puducherry'),
    ('PB', 'Punjab'),
    ('RJ', 'Rajasthan'),
    ('SK', 'Sikkim'),
    ('TN', 'Tamil Nadu'),
    ('TS', 'Telangana'),
    ('TR', 'Tripura'),
    ('UP', 'Uttar Pradesh'),
    ('UK', 'Uttarakhand'),
    ('WB', 'West Bengal'),
]

# Districts per state (sample)
DISTRICTS_PER_STATE = {
    'UP': ['Agra', 'Lucknow', 'Varanasi', 'Kanpur', 'Prayagraj', 'Ghaziabad', 'Gorakhpur', 'Meerut', 'Bareilly', 'Aligarh'],
    'MH': ['Mumbai', 'Pune', 'Nagpur', 'Thane', 'Nashik', 'Aurangabad', 'Solapur', 'Kolhapur', 'Sangli', 'Satara'],
    'BR': ['Patna', 'Gaya', 'Bhagalpur', 'Muzaffarpur', 'Darbhanga', 'Purnia', 'Madhubani', 'Araria', 'Kishanganj', 'Samastipur'],
    'RJ': ['Jaipur', 'Jodhpur', 'Kota', 'Bikaner', 'Ajmer', 'Udaipur', 'Alwar', 'Bharatpur', 'Sikar', 'Banswara'],
    'MP': ['Bhopal', 'Indore', 'Gwalior', 'Jabalpur', 'Ujjain', 'Sagar', 'Satna', 'Rewa', 'Chhindwara', 'Betul'],
    'WB': ['Kolkata', 'Howrah', 'North 24 Parganas', 'South 24 Parganas', 'Murshidabad', 'Nadia', 'Hooghly', 'Malda', 'Darjeeling', 'Bardhaman'],
    'TN': ['Chennai', 'Coimbatore', 'Madurai', 'Tiruchirappalli', 'Salem', 'Tirunelveli', 'Erode', 'Vellore', 'Thanjavur', 'Dindigul'],
    'KA': ['Bengaluru', 'Mysuru', 'Mangalore', 'Hubli', 'Belgaum', 'Gulbarga', 'Davangere', 'Bellary', 'Shimoga', 'Tumkur'],
    'GJ': ['Ahmedabad', 'Surat', 'Vadodara', 'Rajkot', 'Bhavnagar', 'Jamnagar', 'Junagadh', 'Gandhinagar', 'Anand', 'Kutch'],
    'KL': ['Thiruvananthapuram', 'Kochi', 'Kozhikode', 'Thrissur', 'Kollam', 'Kannur', 'Alappuzha', 'Palakkad', 'Malappuram', 'Kottayam'],
}


def generate_district_code(state_code: str, district_name: str, idx: int) -> str:
    """Generate a unique district code."""
    return f"{state_code}-{idx:03d}"


def generate_gender_data(n_records: int = 500) -> pd.DataFrame:
    """
    Generate realistic gender enrollment data.
    
    Simulates Aadhaar enrollment with realistic gender patterns:
    - Southern states generally have better gender parity
    - Bihar, Rajasthan, UP have larger gender gaps
    - Urban districts have better coverage
    """
    records = []
    
    # State-level gender gap biases (negative = more females, positive = more males)
    state_bias = {
        'KL': -0.02,  # Kerala - slight female advantage
        'TN': 0.01,
        'KA': 0.02,
        'MH': 0.03,
        'GJ': 0.04,
        'WB': 0.03,
        'MP': 0.06,
        'UP': 0.08,
        'RJ': 0.10,  # Rajasthan - larger male bias
        'BR': 0.12,  # Bihar - largest male bias
    }
    
    idx = 0
    for state_code, state_name in STATES:
        # Get districts for this state
        if state_code in DISTRICTS_PER_STATE:
            districts = DISTRICTS_PER_STATE[state_code]
        else:
            # Generate random districts
            districts = [f"District_{i}" for i in range(1, random.randint(5, 8))]
        
        bias = state_bias.get(state_code, random.uniform(0.02, 0.06))
        
        for district in districts:
            idx += 1
            
            # Base population (log-normal distribution)
            population = int(np.random.lognormal(12, 1))
            
            # Enrollment rates (higher in urban, lower in rural/remote)
            is_urban = random.random() < 0.3
            base_enrollment_rate = 0.92 if is_urban else random.uniform(0.75, 0.90)
            
            total_enrolled = int(population * base_enrollment_rate)
            
            # Gender split with state bias
            # Add some noise to individual districts
            district_bias = bias + random.gauss(0, 0.03)
            district_bias = max(-0.15, min(0.25, district_bias))  # Clamp
            
            male_pct = 0.50 + district_bias / 2
            female_pct = 1 - male_pct
            
            male_enrolled = int(total_enrolled * male_pct)
            female_enrolled = int(total_enrolled * female_pct)
            
            # Age group distribution
            age_0_5 = int(total_enrolled * random.uniform(0.08, 0.12))
            age_5_17 = int(total_enrolled * random.uniform(0.18, 0.25))
            age_18_plus = total_enrolled - age_0_5 - age_5_17
            
            record = {
                'state': state_name,
                'state_code': state_code,
                'district': district,
                'district_code': generate_district_code(state_code, district, idx),
                'pincode': f"{random.randint(100, 999)}{random.randint(100, 999)}",
                'date': f"2024-{random.randint(1, 12):02d}-01",
                'year': 2024,
                'male_enrolled': male_enrolled,
                'female_enrolled': female_enrolled,
                'total_enrolled': total_enrolled,
                'age_0_5': age_0_5,
                'age_5_17': age_5_17,
                'age_18_greater': age_18_plus,
            }
            
            records.append(record)
            
            if len(records) >= n_records:
                break
        
        if len(records) >= n_records:
            break
    
    return pd.DataFrame(records)


def generate_sample_with_indicators(n_records: int = 300) -> pd.DataFrame:
    """
    Generate sample data with additional socio-economic indicators.
    """
    df = generate_gender_data(n_records)
    
    # Add socio-economic indicators based on state characteristics
    # These are correlated with gender gap
    
    indicators = []
    for _, row in df.iterrows():
        coverage = row['female_enrolled'] / row['total_enrolled']
        
        # Literacy correlates with coverage
        female_literacy = 0.5 + coverage * 0.5 + random.gauss(0, 0.1)
        female_literacy = max(0.3, min(0.98, female_literacy))
        
        # Mobile ownership correlates somewhat
        female_mobile = 0.3 + coverage * 0.4 + random.gauss(0, 0.15)
        female_mobile = max(0.15, min(0.85, female_mobile))
        
        # Bank account
        female_bank = 0.4 + coverage * 0.3 + random.gauss(0, 0.12)
        female_bank = max(0.2, min(0.90, female_bank))
        
        indicators.append({
            'female_literacy': round(female_literacy, 3),
            'female_mobile_ownership': round(female_mobile, 3),
            'female_bank_account_pct': round(female_bank, 3),
            'poverty_rate': round(random.uniform(0.05, 0.45), 3),
            'urban_pct': round(random.uniform(0.15, 0.85), 3),
            'internet_penetration': round(random.uniform(0.20, 0.75), 3),
        })
    
    indicators_df = pd.DataFrame(indicators)
    return pd.concat([df, indicators_df], axis=1)


def save_sample_data(output_dir: Path = None):
    """
    Save sample data to files for testing.
    """
    if output_dir is None:
        output_dir = Path(__file__).parent.parent / 'sample_data'
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate datasets
    basic_data = generate_gender_data(500)
    extended_data = generate_sample_with_indicators(300)
    
    # Save as CSV
    basic_data.to_csv(output_dir / 'gender_enrollment_sample.csv', index=False)
    extended_data.to_csv(output_dir / 'gender_enrollment_extended.csv', index=False)
    
    # Save as JSON
    basic_data.to_json(output_dir / 'gender_enrollment_sample.json', orient='records', indent=2)
    
    print(f"Sample data saved to {output_dir}")
    print(f"  - gender_enrollment_sample.csv ({len(basic_data)} records)")
    print(f"  - gender_enrollment_extended.csv ({len(extended_data)} records)")
    print(f"  - gender_enrollment_sample.json")
    
    # Print summary statistics
    print("\nSummary Statistics:")
    print(f"  States: {basic_data['state'].nunique()}")
    print(f"  Districts: {basic_data['district'].nunique()}")
    
    female_coverage = basic_data['female_enrolled'] / basic_data['total_enrolled']
    print(f"  Avg female coverage: {female_coverage.mean():.2%}")
    print(f"  Min female coverage: {female_coverage.min():.2%}")
    print(f"  Max female coverage: {female_coverage.max():.2%}")
    
    return output_dir


if __name__ == "__main__":
    save_sample_data()
