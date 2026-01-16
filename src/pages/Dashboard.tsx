import { useState, useCallback } from 'react';
import { DashboardLayout } from '@/components/layout';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { useToast } from '@/hooks/use-toast';
import {
  Users, MapPin, TrendingUp, AlertTriangle,
  CheckCircle2, Clock, Activity, Loader2, Shield, Download, RefreshCw
} from 'lucide-react';
import { Link } from 'react-router-dom';
import { useStateData } from '@/hooks/useData';
import {
  formatNumber, formatPercentage, getTotalEnrollments,
  getAverageEnrollmentCoverage, getTotalPendingUpdates
} from '@/data/dataUtils';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell
} from 'recharts';

const genderData = [
  { name: 'Male', value: 52.3, color: 'hsl(var(--chart-1))' },
  { name: 'Female', value: 47.7, color: 'hsl(var(--chart-3))' },
];

export default function Dashboard() {
  const { statesData, isLoading, error, refetch } = useStateData();
  const { toast } = useToast();
  const [refreshing, setRefreshing] = useState(false);
  const [downloading, setDownloading] = useState(false);

  const handleRefresh = useCallback(async () => {
    setRefreshing(true);
    try {
      await refetch();
      toast({
        title: "Data Refreshed",
        description: "Dashboard data has been updated with latest values.",
      });
    } catch {
      toast({
        title: "Refresh Failed",
        description: "Could not refresh data. Please try again.",
        variant: "destructive"
      });
    }
    setRefreshing(false);
  }, [refetch, toast]);

  const handleDownloadReport = useCallback(() => {
    setDownloading(true);

    // Generate report data
    const reportData = {
      generatedAt: new Date().toISOString(),
      summary: {
        totalEnrollments: getTotalEnrollments(statesData),
        averageCoverage: getAverageEnrollmentCoverage(statesData),
        pendingUpdates: getTotalPendingUpdates(statesData),
        activeStates: statesData.length
      },
      stateWiseData: statesData.map(s => ({
        state: s.state,
        enrolled: s.enrolledPopulation,
        coverage: s.enrollmentCoverage,
        activeCenters: s.activeCenters
      }))
    };

    // Create downloadable file
    const blob = new Blob([JSON.stringify(reportData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `dashboard-report-${new Date().toISOString().split('T')[0]}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);

    toast({
      title: "Report Downloaded",
      description: "Dashboard report has been downloaded successfully.",
    });
    setDownloading(false);
  }, [statesData, toast]);

  if (isLoading) {
    return (
      <DashboardLayout>
        <div className="flex items-center justify-center h-96">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
          <span className="ml-2">Loading dashboard data...</span>
        </div>
      </DashboardLayout>
    );
  }

  if (error) {
    return (
      <DashboardLayout>
        <div className="flex flex-col items-center justify-center h-96 text-destructive">
          <AlertTriangle className="h-12 w-12 mb-4" />
          <p>Error loading data. Make sure the backend servers are running.</p>
          <p className="text-sm text-muted-foreground mt-2">
            Start with: npm run dev:all
          </p>
          <Button className="mt-4" onClick={() => window.location.reload()}>
            <RefreshCw className="mr-2 h-4 w-4" /> Retry
          </Button>
        </div>
      </DashboardLayout>
    );
  }

  const totalEnrollments = getTotalEnrollments(statesData);
  const avgCoverage = getAverageEnrollmentCoverage(statesData);
  const totalCenters = statesData.reduce((sum, s) => sum + s.activeCenters, 0);
  const pendingUpdates = getTotalPendingUpdates(statesData);

  const kpiCards = [
    {
      title: 'Total Enrollments',
      value: formatNumber(totalEnrollments),
      change: '+2.4%',
      changeType: 'positive' as const,
      icon: Users,
      color: 'text-primary',
      bgColor: 'bg-primary/10',
    },
    {
      title: 'Coverage Rate',
      value: formatPercentage(avgCoverage),
      change: '+0.8%',
      changeType: 'positive' as const,
      icon: CheckCircle2,
      color: 'text-success',
      bgColor: 'bg-success/10',
    },
    {
      title: 'Active Centers',
      value: formatNumber(totalCenters),
      change: '+12',
      changeType: 'positive' as const,
      icon: MapPin,
      color: 'text-info',
      bgColor: 'bg-info/10',
    },
    {
      title: 'Pending Updates',
      value: formatNumber(pendingUpdates),
      change: '-5.2%',
      changeType: 'negative' as const,
      icon: Clock,
      color: 'text-warning',
      bgColor: 'bg-warning/10',
    },
  ];

  const topStates = statesData
    .slice(0, 6)
    .map(s => ({ name: s.code, enrollments: s.enrolledPopulation / 1000000 }));

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* Page Header */}
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div>
            <h1 className="text-2xl font-bold text-foreground">Dashboard Overview</h1>
            <p className="text-muted-foreground">
              Real-time Aadhaar enrollment analytics from data.gov.in APIs
            </p>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={handleRefresh} disabled={refreshing}>
              {refreshing ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Activity className="mr-2 h-4 w-4" />
              )}
              {refreshing ? 'Refreshing...' : 'Live Data'}
            </Button>
            <Button size="sm" onClick={handleDownloadReport} disabled={downloading}>
              {downloading ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Download className="mr-2 h-4 w-4" />
              )}
              Download Report
            </Button>
          </div>
        </div>

        {/* KPI Cards */}
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {kpiCards.map((card) => (
            <Card key={card.title} className="shadow-card hover:shadow-card-hover transition-shadow">
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div className={`rounded-lg p-2.5 ${card.bgColor}`}>
                    <card.icon className={`h-5 w-5 ${card.color}`} />
                  </div>
                  <Badge
                    variant={card.changeType === 'positive' ? 'default' : 'secondary'}
                    className={card.changeType === 'positive' ? 'bg-success/20 text-success' : 'bg-destructive/20 text-destructive'}
                  >
                    {card.change}
                  </Badge>
                </div>
                <div className="mt-4">
                  <p className="text-2xl font-bold">{card.value}</p>
                  <p className="text-sm text-muted-foreground">{card.title}</p>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>

        {/* Charts Row */}
        <div className="grid gap-6 lg:grid-cols-2">
          {/* Top States Chart */}
          <Card className="shadow-card">
            <CardHeader>
              <CardTitle className="text-lg">Top States by Enrollment</CardTitle>
              <CardDescription>Enrolled population in millions (from live API)</CardDescription>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={250}>
                <BarChart data={topStates}>
                  <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
                  <XAxis dataKey="name" className="text-xs" />
                  <YAxis className="text-xs" />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: 'hsl(var(--popover))',
                      border: '1px solid hsl(var(--border))',
                      borderRadius: '8px'
                    }}
                  />
                  <Bar dataKey="enrollments" fill="hsl(var(--primary))" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>

          {/* Gender Distribution */}
          <Card className="shadow-card">
            <CardHeader>
              <CardTitle className="text-lg">Gender Distribution</CardTitle>
              <CardDescription>National enrollment by gender</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex items-center justify-center">
                <ResponsiveContainer width="100%" height={250}>
                  <PieChart>
                    <Pie
                      data={genderData}
                      cx="50%"
                      cy="50%"
                      innerRadius={60}
                      outerRadius={100}
                      paddingAngle={2}
                      dataKey="value"
                    >
                      {genderData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.color} />
                      ))}
                    </Pie>
                    <Tooltip />
                  </PieChart>
                </ResponsiveContainer>
              </div>
              <div className="mt-4 flex justify-center gap-6">
                {genderData.map((item) => (
                  <div key={item.name} className="flex items-center gap-2">
                    <div
                      className="h-3 w-3 rounded-full"
                      style={{ backgroundColor: item.color }}
                    />
                    <span className="text-sm">{item.name}: {item.value}%</span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Data Source Info & Quick Actions */}
        <div className="grid gap-6 lg:grid-cols-3">
          {/* Data Source Info */}
          <Card className="shadow-card lg:col-span-2">
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle className="text-lg">Data Source</CardTitle>
                <CardDescription>Live data from data.gov.in APIs</CardDescription>
              </div>
              <Badge variant="outline" className="bg-success/10 text-success">
                <Activity className="mr-1 h-3 w-3" /> Connected
              </Badge>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                <div className="flex items-center justify-between p-3 rounded-lg border border-border">
                  <div>
                    <p className="font-medium">Aadhaar Monthly Enrolment</p>
                    <p className="text-sm text-muted-foreground">State-wise enrollment statistics</p>
                  </div>
                  <Badge variant="secondary">{statesData.length} states</Badge>
                </div>
                <div className="flex items-center justify-between p-3 rounded-lg border border-border">
                  <div>
                    <p className="font-medium">Operations Monitoring</p>
                    <p className="text-sm text-muted-foreground">AI-powered anomaly detection</p>
                  </div>
                  <Button variant="outline" size="sm" asChild>
                    <Link to="/monitoring">Open</Link>
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Quick Actions */}
          <Card className="shadow-card">
            <CardHeader>
              <CardTitle className="text-lg">Quick Actions</CardTitle>
              <CardDescription>Navigate to key features</CardDescription>
            </CardHeader>
            <CardContent className="space-y-2">
              <Button variant="default" className="w-full justify-start bg-primary hover:bg-primary/90" asChild>
                <Link to="/monitoring">
                  <Shield className="mr-2 h-4 w-4" />
                  Operations Monitoring
                </Link>
              </Button>
              <Button variant="outline" className="w-full justify-start" asChild>
                <Link to="/hotspots">
                  <MapPin className="mr-2 h-4 w-4 text-destructive" />
                  View Hotspots
                </Link>
              </Button>
              <Button variant="outline" className="w-full justify-start" asChild>
                <Link to="/forecast">
                  <TrendingUp className="mr-2 h-4 w-4 text-success" />
                  Run Forecast
                </Link>
              </Button>
              <Button variant="outline" className="w-full justify-start" asChild>
                <Link to="/gender">
                  <Users className="mr-2 h-4 w-4 text-info" />
                  Gender Analysis
                </Link>
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>
    </DashboardLayout>
  );
}
