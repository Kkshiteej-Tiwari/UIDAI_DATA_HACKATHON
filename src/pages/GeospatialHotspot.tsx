/**
 * GeospatialHotspot Page
 * Interactive dashboard for Geospatial Hotspot Detection featuring:
 * - Choropleth map with hot/cold spot visualization
 * - Moran's I statistics panel
 * - State-level drill-down with forecasts
 * - Anomaly alerts
 */

import React, { useState, useEffect, useCallback } from 'react';
import { MapContainer, TileLayer, GeoJSON, useMap } from 'react-leaflet';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, Area, AreaChart } from 'recharts';
import { AlertTriangle, TrendingUp, TrendingDown, MapPin, Activity, Target, Zap } from 'lucide-react';
import 'leaflet/dist/leaflet.css';

// Custom CSS for tooltips
const tooltipStyles = `
  .leaflet-tooltip.custom-tooltip {
    background: transparent !important;
    border: none !important;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.3) !important;
  }
  .leaflet-tooltip.custom-tooltip::before {
    display: none !important;
  }
`;

// Inject styles
if (typeof document !== 'undefined') {
  const styleElement = document.createElement('style');
  styleElement.textContent = tooltipStyles;
  document.head.appendChild(styleElement);
}

// Types
interface MoransIResult {
  morans_i: number;
  p_value: number;
  z_score: number;
  interpretation: string;
  n: number;
}

interface HotspotData {
  state: string;
  penetration_rate: number;
  gi_z_score: number;
  confidence_level: string;
}

interface Anomaly {
  region: string;
  value: number;
  z_score: number;
  severity: 'critical' | 'high' | 'medium';
  direction: 'above' | 'below';
}

interface ForecastData {
  forecast: number[];
  lower_ci: number[];
  upper_ci: number[];
  dates: string[];
}

interface SpatialAnalysisResponse {
  success: boolean;
  morans_i: MoransIResult;
  hotspots: HotspotData[];
  coldspots: HotspotData[];
  summary: {
    total_regions: number;
    hotspot_count: number;
    coldspot_count: number;
    neutral_count: number;
  };
  geojson?: any;
}

// API functions
const API_BASE = 'http://localhost:8000';

async function fetchSpatialAnalysis(): Promise<SpatialAnalysisResponse> {
  const response = await fetch(`${API_BASE}/api/hotspots/spatial-analysis`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({})
  });
  if (!response.ok) throw new Error('Failed to fetch spatial analysis');
  return response.json();
}

async function fetchAnomalies(threshold: number = 2.0): Promise<{ anomalies: Anomaly[] }> {
  const response = await fetch(`${API_BASE}/api/hotspots/anomalies`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ threshold, granularity: 'state' })
  });
  if (!response.ok) throw new Error('Failed to fetch anomalies');
  return response.json();
}

async function fetchStateForecast(state: string): Promise<{ forecast: ForecastData; historical: any }> {
  const response = await fetch(`${API_BASE}/api/forecast/state/${encodeURIComponent(state)}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ horizon_months: 6 })
  });
  if (!response.ok) throw new Error('Failed to fetch forecast');
  return response.json();
}

// Color utilities
function getHotspotColor(zScore: number): string {
  if (zScore > 2.58) return '#b91c1c'; // Hot red (99% confidence)
  if (zScore > 1.96) return '#dc2626'; // Red (95% confidence)
  if (zScore > 1.65) return '#f97316'; // Orange (90% confidence)
  if (zScore < -2.58) return '#1e40af'; // Cold blue (99% confidence)
  if (zScore < -1.96) return '#2563eb'; // Blue (95% confidence)
  if (zScore < -1.65) return '#3b82f6'; // Light blue (90% confidence)
  return '#9ca3af'; // Neutral gray
}

function getPenetrationColor(rate: number): string {
  if (rate >= 0.95) return '#059669'; // Excellent - green
  if (rate >= 0.85) return '#10b981'; // Good - light green
  if (rate >= 0.75) return '#fbbf24'; // Fair - yellow
  if (rate >= 0.65) return '#f97316'; // Poor - orange
  return '#dc2626'; // Critical - red
}

// Components
const StatisticsCard: React.FC<{ title: string; value: string | number; subtitle?: string; icon: React.ReactNode; trend?: 'up' | 'down' | 'neutral' }> =
  ({ title, value, subtitle, icon, trend }) => (
    <Card className="bg-gradient-to-br from-slate-900 to-slate-800 border-slate-700">
      <CardContent className="p-6">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-slate-400 text-sm font-medium">{title}</p>
            <p className="text-2xl font-bold text-white mt-1">{value}</p>
            {subtitle && <p className="text-slate-500 text-xs mt-1">{subtitle}</p>}
          </div>
          <div className={`p-3 rounded-full ${trend === 'up' ? 'bg-green-500/20 text-green-400' : trend === 'down' ? 'bg-red-500/20 text-red-400' : 'bg-blue-500/20 text-blue-400'}`}>
            {icon}
          </div>
        </div>
      </CardContent>
    </Card>
  );

const AnomalyAlert: React.FC<{ anomaly: Anomaly }> = ({ anomaly }) => (
  <Alert className={`mb-2 ${anomaly.severity === 'critical' ? 'border-red-500 bg-red-500/10' : anomaly.severity === 'high' ? 'border-orange-500 bg-orange-500/10' : 'border-yellow-500 bg-yellow-500/10'}`}>
    <AlertTriangle className={`h-4 w-4 ${anomaly.severity === 'critical' ? 'text-red-500' : anomaly.severity === 'high' ? 'text-orange-500' : 'text-yellow-500'}`} />
    <AlertTitle className="text-white">{anomaly.region}</AlertTitle>
    <AlertDescription className="text-slate-300">
      Penetration rate {(anomaly.value * 100).toFixed(1)}% ({anomaly.direction === 'below' ? 'below' : 'above'} average)
      <Badge variant="outline" className="ml-2">{anomaly.severity}</Badge>
    </AlertDescription>
  </Alert>
);

const ForecastChart: React.FC<{ data: ForecastData; historical?: any[] }> = ({ data, historical }) => {
  const chartData = data.dates.map((date, i) => ({
    date,
    forecast: data.forecast[i],
    lower: data.lower_ci[i],
    upper: data.upper_ci[i]
  }));

  return (
    <ResponsiveContainer width="100%" height={300}>
      <AreaChart data={chartData}>
        <defs>
          <linearGradient id="colorCI" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
            <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
        <XAxis dataKey="date" stroke="#9ca3af" />
        <YAxis stroke="#9ca3af" tickFormatter={(v) => `${(v / 1000000).toFixed(1)}M`} />
        <Tooltip
          contentStyle={{ backgroundColor: '#1f2937', border: 'none', borderRadius: '8px' }}
          labelStyle={{ color: '#9ca3af' }}
          formatter={(value: number) => [`${(value / 1000000).toFixed(2)}M`, '']}
        />
        <Legend />
        <Area
          type="monotone"
          dataKey="upper"
          stroke="transparent"
          fill="url(#colorCI)"
          name="95% CI Upper"
        />
        <Area
          type="monotone"
          dataKey="lower"
          stroke="transparent"
          fill="#1f2937"
          name="95% CI Lower"
        />
        <Line
          type="monotone"
          dataKey="forecast"
          stroke="#3b82f6"
          strokeWidth={2}
          dot={{ fill: '#3b82f6' }}
          name="Forecast"
        />
      </AreaChart>
    </ResponsiveContainer>
  );
};

// Main Component
const GeospatialHotspot: React.FC = () => {
  const [spatialData, setSpatialData] = useState<SpatialAnalysisResponse | null>(null);
  const [anomalies, setAnomalies] = useState<Anomaly[]>([]);
  const [selectedState, setSelectedState] = useState<string | null>(null);
  const [forecastData, setForecastData] = useState<ForecastData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState('map');

  // Load initial data
  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      setError(null);
      try {
        const [spatial, anomalyData] = await Promise.all([
          fetchSpatialAnalysis(),
          fetchAnomalies(2.0)
        ]);
        setSpatialData(spatial);
        setAnomalies(anomalyData.anomalies || []);
      } catch (err) {
        console.error('Error loading data:', err);
        setError(err instanceof Error ? err.message : 'Failed to load data');
        // Use mock data for development
        setSpatialData({
          success: true,
          morans_i: { morans_i: 0.432, p_value: 0.0012, z_score: 3.21, interpretation: 'Strong positive spatial autocorrelation', n: 30 },
          hotspots: [
            { state: 'Kerala', penetration_rate: 0.96, gi_z_score: 2.87, confidence_level: '99%' },
            { state: 'Goa', penetration_rate: 0.97, gi_z_score: 2.65, confidence_level: '99%' }
          ],
          coldspots: [
            { state: 'Nagaland', penetration_rate: 0.63, gi_z_score: -2.45, confidence_level: '95%' },
            { state: 'Arunachal Pradesh', penetration_rate: 0.60, gi_z_score: -2.78, confidence_level: '99%' }
          ],
          summary: { total_regions: 30, hotspot_count: 5, coldspot_count: 4, neutral_count: 21 }
        });
        setAnomalies([
          { region: 'Nagaland', value: 0.63, z_score: -2.45, severity: 'high', direction: 'below' },
          { region: 'Arunachal Pradesh', value: 0.60, z_score: -2.78, severity: 'high', direction: 'below' }
        ]);
      } finally {
        setLoading(false);
      }
    };
    loadData();
  }, []);

  // Load forecast when state is selected
  useEffect(() => {
    if (selectedState) {
      const loadForecast = async () => {
        try {
          const data = await fetchStateForecast(selectedState);
          setForecastData(data.forecast);
        } catch (err) {
          console.error('Error loading forecast:', err);
          // Mock forecast data
          setForecastData({
            forecast: [1200000, 1250000, 1300000, 1350000, 1400000, 1450000],
            lower_ci: [1100000, 1120000, 1140000, 1160000, 1180000, 1200000],
            upper_ci: [1300000, 1380000, 1460000, 1540000, 1620000, 1700000],
            dates: ['2025-02', '2025-03', '2025-04', '2025-05', '2025-06', '2025-07']
          });
        }
      };
      loadForecast();
    }
  }, [selectedState]);

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 flex items-center justify-center">
        <div className="animate-spin rounded-full h-16 w-16 border-t-2 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-white mb-2">Geospatial Hotspot Detection</h1>
          <p className="text-slate-400">Spatial clustering analysis and forecasting for Aadhaar enrollment</p>
        </div>

        {/* Statistics Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          <StatisticsCard
            title="Moran's I"
            value={spatialData?.morans_i?.morans_i?.toFixed(3) || 'N/A'}
            subtitle={`p-value: ${spatialData?.morans_i?.p_value?.toFixed(4) || 'N/A'}`}
            icon={<Activity className="h-6 w-6" />}
            trend="neutral"
          />
          <StatisticsCard
            title="Hotspots"
            value={spatialData?.summary?.hotspot_count || 0}
            subtitle="High enrollment clusters"
            icon={<TrendingUp className="h-6 w-6" />}
            trend="up"
          />
          <StatisticsCard
            title="Coldspots"
            value={spatialData?.summary?.coldspot_count || 0}
            subtitle="Low enrollment clusters"
            icon={<TrendingDown className="h-6 w-6" />}
            trend="down"
          />
          <StatisticsCard
            title="Anomalies"
            value={anomalies.length}
            subtitle="Regions with unusual patterns"
            icon={<AlertTriangle className="h-6 w-6" />}
            trend={anomalies.length > 0 ? 'down' : 'neutral'}
          />
        </div>

        {/* Main Content */}
        <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-4">
          <TabsList className="bg-slate-800">
            <TabsTrigger value="map">Map View</TabsTrigger>
            <TabsTrigger value="analysis">Analysis</TabsTrigger>
            <TabsTrigger value="forecast">Forecast</TabsTrigger>
            <TabsTrigger value="anomalies">Anomalies</TabsTrigger>
          </TabsList>

          {/* Map View Tab */}
          <TabsContent value="map">
            <div className="grid grid-cols-1 gap-6 mb-6">
              {/* State Selection Controls */}
              <Card className="bg-slate-800/50 border-slate-700">
                <CardContent className="p-4">
                  <div className="flex items-center gap-4">
                    <div className="flex-1">
                      <label className="text-slate-300 text-sm mb-2 block">Filter by State</label>
                      <Select
                        value={selectedState || 'all'}
                        onValueChange={(value) => setSelectedState(value === 'all' ? null : value)}
                      >
                        <SelectTrigger className="bg-slate-700 border-slate-600 text-white">
                          <SelectValue placeholder="View All States" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="all">View All States</SelectItem>
                          {spatialData?.hotspots?.map((spot, i) => (
                            <SelectItem key={`hot-${i}`} value={spot.state}>{spot.state} (Hotspot)</SelectItem>
                          ))}
                          {spatialData?.coldspots?.map((spot, i) => (
                            <SelectItem key={`cold-${i}`} value={spot.state}>{spot.state} (Coldspot)</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="flex gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setSelectedState(null)}
                        className="bg-slate-700 border-slate-600 hover:bg-slate-600"
                      >
                        Reset View
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              <div className="lg:col-span-2">
                <Card className="bg-slate-800/50 border-slate-700">
                  <CardHeader>
                    <CardTitle className="text-white flex items-center gap-2">
                      <MapPin className="h-5 w-5" />
                      Hotspot Map
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="h-[500px] rounded-lg overflow-hidden">
                      <MapContainer
                        center={[22.5, 82.5]}
                        zoom={5}
                        style={{ height: '100%', width: '100%' }}
                        scrollWheelZoom={true}
                      >
                        <TileLayer
                          attribution='&copy; <a href="https://www.maptiler.com/">MapTiler</a>'
                          url={`https://api.maptiler.com/maps/dataviz-dark/{z}/{x}/{y}.png?key=afI6Qeow12GLYkRT50ND`}
                        />

                        {/* GeoJSON Choropleth Layer */}
                        {spatialData?.geojson && (
                          <GeoJSON
                            key={JSON.stringify(spatialData.geojson)}
                            data={spatialData.geojson}
                            style={(feature) => {
                              const props = feature?.properties;
                              const zScore = props?.gi_z_score || 0;
                              const color = getHotspotColor(zScore);

                              return {
                                fillColor: color,
                                weight: 2,
                                opacity: 1,
                                color: '#1e293b',
                                fillOpacity: 0.7
                              };
                            }}
                            onEachFeature={(feature, layer) => {
                              const props = feature.properties;
                              const stateName = props?.state || props?.state_name || 'Unknown';
                              const penetrationRate = props?.penetration_rate || 0;
                              const classification = props?.classification || 'neutral';
                              const confidenceLevel = props?.confidence_level || 'N/A';

                              // Tooltip
                              layer.bindTooltip(
                                `<div style="background: #1e293b; padding: 8px; border-radius: 4px;">
                                  <strong style="color: white; font-size: 14px;">${stateName}</strong><br/>
                                  <span style="color: #94a3b8;">Penetration: ${(penetrationRate * 100).toFixed(1)}%</span><br/>
                                  <span style="color: #94a3b8;">Classification: ${classification}</span><br/>
                                  <span style="color: #94a3b8;">Confidence: ${confidenceLevel}</span>
                                </div>`,
                                {
                                  permanent: false,
                                  direction: 'top',
                                  className: 'custom-tooltip'
                                }
                              );

                              // Click handler
                              layer.on('click', () => {
                                setSelectedState(stateName);
                                setActiveTab('forecast');
                              });

                              // Hover effects
                              layer.on('mouseover', function () {
                                this.setStyle({
                                  weight: 3,
                                  fillOpacity: 0.9
                                });
                              });

                              layer.on('mouseout', function () {
                                this.setStyle({
                                  weight: 2,
                                  fillOpacity: 0.7
                                });
                              });
                            }}
                          />
                        )}
                      </MapContainer>
                    </div>
                  </CardContent>
                </Card>
              </div>

              <div>
                <Card className="bg-slate-800/50 border-slate-700 mb-4">
                  <CardHeader>
                    <CardTitle className="text-white text-lg">Legend</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-2">
                      <div className="flex items-center gap-2">
                        <div className="w-4 h-4 rounded" style={{ backgroundColor: '#b91c1c' }}></div>
                        <span className="text-slate-300 text-sm">Hotspot (99% CI)</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <div className="w-4 h-4 rounded" style={{ backgroundColor: '#dc2626' }}></div>
                        <span className="text-slate-300 text-sm">Hotspot (95% CI)</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <div className="w-4 h-4 rounded" style={{ backgroundColor: '#f97316' }}></div>
                        <span className="text-slate-300 text-sm">Hotspot (90% CI)</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <div className="w-4 h-4 rounded" style={{ backgroundColor: '#9ca3af' }}></div>
                        <span className="text-slate-300 text-sm">Neutral</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <div className="w-4 h-4 rounded" style={{ backgroundColor: '#3b82f6' }}></div>
                        <span className="text-slate-300 text-sm">Coldspot (90% CI)</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <div className="w-4 h-4 rounded" style={{ backgroundColor: '#2563eb' }}></div>
                        <span className="text-slate-300 text-sm">Coldspot (95% CI)</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <div className="w-4 h-4 rounded" style={{ backgroundColor: '#1e40af' }}></div>
                        <span className="text-slate-300 text-sm">Coldspot (99% CI)</span>
                      </div>
                    </div>
                  </CardContent>
                </Card>

                <Card className="bg-slate-800/50 border-slate-700">
                  <CardHeader>
                    <CardTitle className="text-white text-lg">Top Coldspots</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-3">
                      {spatialData?.coldspots?.slice(0, 5).map((spot, i) => (
                        <div
                          key={i}
                          className="flex items-center justify-between p-2 bg-slate-700/50 rounded cursor-pointer hover:bg-slate-700"
                          onClick={() => {
                            setSelectedState(spot.state);
                            setActiveTab('forecast');
                          }}
                        >
                          <span className="text-white">{spot.state}</span>
                          <Badge variant="destructive">{(spot.penetration_rate * 100).toFixed(1)}%</Badge>
                        </div>
                      ))}
                      {(!spatialData?.coldspots || spatialData.coldspots.length === 0) && (
                        <p className="text-slate-400 text-sm text-center py-4">No coldspots detected</p>
                      )}
                    </div>
                  </CardContent>
                </Card>
              </div>
            </div>
          </TabsContent>

          {/* Analysis Tab */}
          <TabsContent value="analysis">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <Card className="bg-slate-800/50 border-slate-700">
                <CardHeader>
                  <CardTitle className="text-white">Moran's I Analysis</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    <div className="p-4 bg-slate-700/50 rounded-lg">
                      <div className="text-4xl font-bold text-blue-400 mb-2">
                        {spatialData?.morans_i?.morans_i?.toFixed(4) || 'N/A'}
                      </div>
                      <p className="text-slate-300 text-sm">
                        {spatialData?.morans_i?.interpretation || 'No interpretation available'}
                      </p>
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                      <div className="p-3 bg-slate-700/30 rounded">
                        <div className="text-slate-400 text-xs">P-Value</div>
                        <div className="text-white font-semibold">
                          {spatialData?.morans_i?.p_value?.toFixed(4) || 'N/A'}
                        </div>
                      </div>
                      <div className="p-3 bg-slate-700/30 rounded">
                        <div className="text-slate-400 text-xs">Z-Score</div>
                        <div className="text-white font-semibold">
                          {spatialData?.morans_i?.z_score?.toFixed(2) || 'N/A'}
                        </div>
                      </div>
                      <div className="p-3 bg-slate-700/30 rounded">
                        <div className="text-slate-400 text-xs">Regions Analyzed</div>
                        <div className="text-white font-semibold">
                          {spatialData?.morans_i?.n || 'N/A'}
                        </div>
                      </div>
                      <div className="p-3 bg-slate-700/30 rounded">
                        <div className="text-slate-400 text-xs">Significance</div>
                        <div className="text-white font-semibold">
                          {(spatialData?.morans_i?.p_value || 1) < 0.05 ? 'Significant' : 'Not Significant'}
                        </div>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card className="bg-slate-800/50 border-slate-700">
                <CardHeader>
                  <CardTitle className="text-white">Cluster Summary</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    <div className="flex items-center justify-between p-3 bg-red-500/10 border border-red-500/30 rounded-lg">
                      <div className="flex items-center gap-2">
                        <TrendingUp className="h-5 w-5 text-red-400" />
                        <span className="text-white">Hotspots</span>
                      </div>
                      <span className="text-2xl font-bold text-red-400">{spatialData?.summary?.hotspot_count || 0}</span>
                    </div>
                    <div className="flex items-center justify-between p-3 bg-blue-500/10 border border-blue-500/30 rounded-lg">
                      <div className="flex items-center gap-2">
                        <TrendingDown className="h-5 w-5 text-blue-400" />
                        <span className="text-white">Coldspots</span>
                      </div>
                      <span className="text-2xl font-bold text-blue-400">{spatialData?.summary?.coldspot_count || 0}</span>
                    </div>
                    <div className="flex items-center justify-between p-3 bg-slate-500/10 border border-slate-500/30 rounded-lg">
                      <div className="flex items-center gap-2">
                        <Target className="h-5 w-5 text-slate-400" />
                        <span className="text-white">Neutral</span>
                      </div>
                      <span className="text-2xl font-bold text-slate-400">{spatialData?.summary?.neutral_count || 0}</span>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          {/* Forecast Tab */}
          <TabsContent value="forecast">
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              <div className="lg:col-span-2">
                <Card className="bg-slate-800/50 border-slate-700">
                  <CardHeader>
                    <CardTitle className="text-white flex items-center justify-between">
                      <span>6-Month Enrollment Forecast</span>
                      <Select value={selectedState || ''} onValueChange={setSelectedState}>
                        <SelectTrigger className="w-48 bg-slate-700 border-slate-600">
                          <SelectValue placeholder="Select State" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="Maharashtra">Maharashtra</SelectItem>
                          <SelectItem value="Bihar">Bihar</SelectItem>
                          <SelectItem value="Uttar Pradesh">Uttar Pradesh</SelectItem>
                          <SelectItem value="Tamil Nadu">Tamil Nadu</SelectItem>
                          <SelectItem value="Kerala">Kerala</SelectItem>
                        </SelectContent>
                      </Select>
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    {forecastData ? (
                      <ForecastChart data={forecastData} />
                    ) : (
                      <div className="h-64 flex items-center justify-center text-slate-400">
                        Select a state to view forecast
                      </div>
                    )}
                  </CardContent>
                </Card>
              </div>

              <div>
                <Card className="bg-slate-800/50 border-slate-700">
                  <CardHeader>
                    <CardTitle className="text-white text-lg flex items-center gap-2">
                      <Zap className="h-5 w-5 text-yellow-400" />
                      Intervention Modeling
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="text-slate-400 text-sm mb-4">
                      Simulate the impact of deploying mobile enrollment camps in underperforming regions.
                    </p>
                    <Button className="w-full bg-blue-600 hover:bg-blue-700">
                      Run Scenario Analysis
                    </Button>
                  </CardContent>
                </Card>
              </div>
            </div>
          </TabsContent>

          {/* Anomalies Tab */}
          <TabsContent value="anomalies">
            <Card className="bg-slate-800/50 border-slate-700">
              <CardHeader>
                <CardTitle className="text-white flex items-center gap-2">
                  <AlertTriangle className="h-5 w-5 text-yellow-400" />
                  Anomaly Alerts ({anomalies.length})
                </CardTitle>
              </CardHeader>
              <CardContent>
                {anomalies.length > 0 ? (
                  <div className="space-y-2">
                    {anomalies.map((anomaly, i) => (
                      <AnomalyAlert key={i} anomaly={anomaly} />
                    ))}
                  </div>
                ) : (
                  <p className="text-slate-400 text-center py-8">No anomalies detected</p>
                )}
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
};

export default GeospatialHotspot;
