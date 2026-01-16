"""
Quick verification script to test geospatial API endpoints
Run this to verify the backend is working correctly
"""
import requests
import json

API_BASE = "http://localhost:8000"

def test_spatial_analysis():
    """Test spatial analysis endpoint"""
    print("Testing /api/hotspots/spatial-analysis...")
    try:
        response = requests.post(
            f"{API_BASE}/api/hotspots/spatial-analysis",
            json={},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Spatial analysis endpoint working!")
            print(f"   - Moran's I: {data.get('morans_i', {}).get('morans_i', 'N/A')}")
            print(f"   - Hotspots: {data.get('summary', {}).get('hotspot_count', 0)}")
            print(f"   - Coldspots: {data.get('summary', {}).get('coldspot_count', 0)}")
            
            if data.get('geojson'):
                features = data['geojson'].get('features', [])
                print(f"   - GeoJSON features: {len(features)}")
                if features:
                    print(f"   - Sample feature properties: {list(features[0].get('properties', {}).keys())}")
            else:
                print("   ⚠️ Warning: No GeoJSON in response")
            
            return True
        else:
            print(f"❌ Failed with status {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Connection failed - is the ML backend running on port 8000?")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_anomalies():
    """Test anomaly detection endpoint"""
    print("\nTesting /api/hotspots/anomalies...")
    try:
        response = requests.post(
            f"{API_BASE}/api/hotspots/anomalies",
            json={"threshold": 2.0, "granularity": "state"},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            anomalies = data.get('anomalies', [])
            print(f"✅ Anomaly detection working!")
            print(f"   - Total anomalies: {len(anomalies)}")
            if anomalies:
                print(f"   - Sample: {anomalies[0].get('region')} - {anomalies[0].get('severity')}")
            return True
        else:
            print(f"❌ Failed with status {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_forecast():
    """Test state forecast endpoint"""
    print("\nTesting /api/forecast/state/Maharashtra...")
    try:
        response = requests.post(
            f"{API_BASE}/api/forecast/state/Maharashtra",
            json={"horizon_months": 6},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            forecast = data.get('forecast', {})
            print(f"✅ Forecast endpoint working!")
            print(f"   - Forecast points: {len(forecast.get('forecast', []))}")
            print(f"   - Dates: {forecast.get('dates', [])[:3]}...")
            return True
        else:
            print(f"❌ Failed with status {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("Geospatial Hotspot API Verification")
    print("=" * 60)
    
    results = []
    results.append(test_spatial_analysis())
    results.append(test_anomalies())
    results.append(test_forecast())
    
    print("\n" + "=" * 60)
    if all(results):
        print("✅ All tests passed! Backend is working correctly.")
        print("\nNext steps:")
        print("1. Start the Express server: cd server && npm run dev")
        print("2. Start the frontend: npm run dev")
        print("3. Navigate to: http://localhost:5173/geospatial-hotspot")
    else:
        print("❌ Some tests failed. Check the ML backend is running:")
        print("   cd ml_backend && uvicorn main:app --reload --port 8000")
    print("=" * 60)
