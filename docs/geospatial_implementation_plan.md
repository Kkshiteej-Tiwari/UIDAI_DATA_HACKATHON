# Geospatial Hotspot Detection - Implementation Plan

## 🎯 Feature Overview

### Feature 1.1: Geographic Hotspot Detection Engine

**What This Feature Does:**

This feature analyzes Aadhaar enrollment data across India's districts and states to identify geographic patterns and anomalies. It uses statistical spatial analysis to detect regions with unusually high or low enrollment rates, helping identify "digital exclusion blindspots" where Aadhaar penetration is significantly below national averages. The system applies advanced geospatial algorithms like Moran's I (to detect clustering patterns) and Getis-Ord Gi* (to identify statistically significant hot and cold spots) to pinpoint areas requiring immediate policy intervention. It also performs time-series decomposition to separate seasonal enrollment fluctuations from long-term trends, enabling more accurate identification of regions with persistent low coverage versus temporary dips.

### Feature 1.2: Spatio-Temporal Forecasting Model

**What This Feature Does:**

This feature predicts future Aadhaar enrollment patterns for each state and district over the next 6 months using time-series forecasting models. It employs SARIMA (Seasonal AutoRegressive Integrated Moving Average) models that account for both seasonal patterns and long-term trends in enrollment data. The system also considers spatial relationships between neighboring regions (spatial lag regression), recognizing that enrollment trends in one state often influence neighboring states. Most importantly, it provides scenario modeling capabilities that allow policymakers to compare "business as usual" projections against "intervention deployed" scenarios, quantifying the expected impact of deploying mobile enrollment units or awareness campaigns in specific regions.

---

## 📚 Required Technologies & APIs

### Python Libraries (ML Backend)

| Library | Purpose | Installation |
|---------|---------|--------------|
| **PySAL** (`pysal`, `esda`) | Spatial statistics: Moran's I, Getis-Ord Gi* | `pip install pysal esda` |
| **shapely** | Geometric operations and GIS data handling | `pip install shapely` |
| **geopandas** | Geospatial dataframes for district/state boundaries | `pip install geopandas` |
| **statsmodels** | SARIMA time-series modeling | `pip install statsmodels` |
| **scikit-learn** | Spatial lag regression, clustering | `pip install scikit-learn` |
| **numpy** & **pandas** | Data manipulation and statistical operations | `pip install numpy pandas` |
| **scipy** | Statistical tests and spatial distance calculations | `pip install scipy` |

### External Data Sources & APIs

| Data Source | Purpose | API/Source |
|-------------|---------|------------|
| **UIDAI Aadhaar Data** | State/district enrollment counts | Provided hackathon dataset |
| **Census Data** | Population figures for penetration rate calculation | [Census India API](https://censusindia.gov.in/) |
| **India GeoJSON** | State/district boundary files for mapping | [DataMeet India Maps](http://projects.datameet.org/maps/) |
| **PMJDY Open Data** | Financial inclusion metrics | [data.gov.in](https://data.gov.in) |
| **NITI Aayog SDG Data** | Socio-economic indicators by district | [SDG India Index](https://sdgindiaindex.niti.gov.in/) |

### Frontend Libraries

| Library | Purpose |
|---------|---------|
| **Leaflet.js** with **react-leaflet** | Interactive map rendering (already in dependencies) |
| **Recharts** | Forecast charts and confidence intervals (already in dependencies) |
| **D3.js** (optional) | Advanced heatmap visualizations |

---

## 🏗️ Backend Implementation Roadmap

### **Phase 1: Setup & Data Preparation** (1-2 hours)

#### 1.1 Install Required Libraries
```bash
cd ml_backend
pip install pysal esda geopandas shapely statsmodels scipy
```

#### 1.2 Prepare GeoJSON Data
- [ ] Download India state/district boundary GeoJSON files
- [ ] Store in `ml_backend/data/geojson/` directory
- [ ] Create district-to-state mapping lookup table
- [ ] Normalize district/state names to match Aadhaar dataset

#### 1.3 Create Data Processing Module
- [ ] Create `ml_backend/services/geo_processor.py`
- [ ] Implement function to load and merge Aadhaar data with GeoJSON
- [ ] Calculate penetration rates (Aadhaar count / population)
- [ ] Generate spatial weights matrix for neighboring regions

---

### **Phase 2: Feature 1.1 - Spatial Hotspot Detection** (3-4 hours)

#### 2.1 Create Spatial Analysis Service
**File:** `ml_backend/services/spatial_analysis.py`

**Functions to implement:**
- [ ] `calculate_morans_i(gdf: GeoDataFrame) -> dict`
  - Computes global Moran's I statistic
  - Returns I-value, p-value, and interpretation
  
- [ ] `detect_hotspots_getis_ord(gdf: GeoDataFrame) -> GeoDataFrame`
  - Applies Getis-Ord Gi* statistic to each region
  - Returns Z-scores indicating hotspot significance
  - Flags: Hot (Z > 1.96), Cold (Z < -1.96), Neutral
  
- [ ] `detect_anomalies(gdf: GeoDataFrame, threshold: float = 2.0) -> list`
  - Identifies regions >2 std deviations from mean penetration
  - Returns list of anomalous districts with severity scores

- [ ] `decompose_time_series(state_data: pd.DataFrame) -> dict`
  - Seasonal decomposition using statsmodels
  - Returns trend, seasonal, and residual components

#### 2.2 Create API Endpoints
**File:** `ml_backend/routes/hotspots.py`

**Endpoints:**
- [ ] `POST /api/hotspots/spatial-analysis`
  - Input: State/district filter, date range
  - Output: Moran's I results, hotspot GeoJSON with Z-scores
  
- [ ] `POST /api/hotspots/anomalies`
  - Input: Threshold (default 2.0), region granularity
  - Output: List of anomalous regions with metadata
  
- [ ] `GET /api/hotspots/heatmap/{state}`
  - Output: GeoJSON with penetration rates and hotspot classifications

#### 2.3 Integration Tasks
- [ ] Add routes to `ml_backend/main.py`
- [ ] Test with sample Aadhaar dataset
- [ ] Optimize for <5 second response time

---

### **Phase 3: Feature 1.2 - Forecasting Model** (3-4 hours)

#### 3.1 Create Forecasting Service
**File:** `ml_backend/services/forecasting.py`

**Functions to implement:**
- [ ] `train_sarima_model(state_ts: pd.Series) -> SARIMAResults`
  - Auto-determine SARIMA(p,d,q)(P,D,Q,s) parameters using AIC
  - Train on historical enrollment data
  
- [ ] `forecast_6_months(model: SARIMAResults) -> dict`
  - Generate point forecasts + 95% confidence intervals
  - Return as JSON with dates and values
  
- [ ] `spatial_lag_regression(gdf: GeoDataFrame, neighbors: dict) -> dict`
  - Model: enrollment_rate ~ lag(neighbor_avg_rate) + socioeconomic_vars
  - Returns regression coefficients and predictions
  
- [ ] `scenario_modeling(state: str, intervention: bool) -> dict`
  - Baseline: Current trend continues
  - Intervention: +10% boost in enrollment velocity for 3 months
  - Returns comparison of both scenarios

#### 3.2 Create API Endpoints
**File:** `ml_backend/routes/forecasting.py`

**Endpoints:**
- [ ] `POST /api/forecast/state/{state_name}`
  - Input: Forecast horizon (default 6 months)
  - Output: Forecast values, confidence bounds, trend summary
  
- [ ] `POST /api/forecast/scenario-comparison`
  - Input: State list, intervention parameters
  - Output: Side-by-side scenario projections
  
- [ ] `GET /api/forecast/cluster-predictions`
  - Clusters states by enrollment patterns
  - Returns cluster-level forecasts

#### 3.3 Integration Tasks
- [ ] Add routes to `ml_backend/main.py`
- [ ] Cache model training results (avoid retraining on every request)
- [ ] Add endpoint for model diagnostics (residuals, AIC/BIC)

---

### **Phase 4: Express Backend Integration** (1 hour)

**File:** `server/routes/hotspots.js`

**Tasks:**
- [ ] Update existing `/api/hotspots/spatial` to call new ML backend endpoints
- [ ] Add caching layer (cache hotspot results for 1 hour)
- [ ] Error handling for ML backend unavailability
- [ ] Add `/api/hotspots/forecast` proxy endpoint

---

### **Phase 5: Frontend Dashboard** (2-3 hours)

#### 5.1 Create Hotspot Map Component
**File:** `src/components/HotspotMap.tsx`

**Features:**
- [ ] Leaflet choropleth map colored by penetration rate
- [ ] Overlay hotspot/coldspot markers (red/blue)
- [ ] Click district → show time-series chart
- [ ] Toggle layers: Penetration, Hotspots, Anomalies

#### 5.2 Create Forecast Dashboard
**File:** `src/pages/ForecastDashboard.tsx`

**Features:**
- [ ] State selector dropdown
- [ ] Line chart showing historical + forecasted enrollment
- [ ] Confidence interval shading
- [ ] Scenario comparison toggles
- [ ] Export to PDF/PNG

---

## ✅ Structured TODO List (Backend Priority)

### **Immediate Actions** (Start Here)

1. **Setup Environment**
   ```bash
   cd ml_backend
   pip install pysal esda geopandas shapely statsmodels scipy
   ```

2. **Download GeoJSON Data**
   - Get India district boundaries from [DataMeet](http://projects.datameet.org/maps/)
   - Save to `ml_backend/data/geojson/india_districts.geojson`

3. **Create Base Services**
   - [ ] `ml_backend/services/geo_processor.py` → Load & merge spatial data
   - [ ] `ml_backend/services/spatial_analysis.py` → Moran's I, Getis-Ord
   - [ ] `ml_backend/services/forecasting.py` → SARIMA models

4. **Build API Routes**
   - [ ] `ml_backend/routes/hotspots.py` → Spatial endpoints
   - [ ] `ml_backend/routes/forecasting.py` → Forecast endpoints
   - [ ] Register routes in `ml_backend/main.py`

5. **Test Core Functionality**
   - [ ] Test Moran's I calculation with sample data
   - [ ] Verify hotspot detection returns valid GeoJSON
   - [ ] Train SARIMA on one state, check forecast accuracy

6. **Optimize & Deploy**
   - [ ] Add response caching (Redis or in-memory)
   - [ ] Ensure <5s response times
   - [ ] Add comprehensive error handling

---

## 🎯 Success Metrics

- **Spatial Analysis**: Correctly identifies Nagaland (62.8%) and Arunachal (78.4%) as coldspots
- **Forecasting**: 6-month predictions with <15% MAPE on validation data
- **Performance**: Hotspot map loads in <3 seconds
- **Impact**: Generates actionable policy recommendations (e.g., "Deploy units to top 10 coldspots")

---

## 🚀 Quick Wins (If Time Constrained)

1. **Skip SARIMA** → Use simple moving averages with bootstrapped confidence intervals
2. **Skip Spatial Lag** → Just use univariate time series per state
3. **Pre-compute Hotspots** → Calculate once, store in JSON, update daily
4. **Use Static GeoJSON** → Avoid real-time spatial calculations, use pre-rendered heatmap tiles
