import { useState, useCallback } from 'react';
import { DashboardLayout } from '@/components/layout';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { useToast } from '@/hooks/use-toast';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { MapPin, AlertTriangle, Download, Loader2, Eye, Calendar, CheckCircle2 } from 'lucide-react';
import { useHotspots, useStateData } from '@/hooks/useData';
import { formatPercentage } from '@/data/dataUtils';

interface Hotspot {
  state: string;
  district: string;
  coverage: number;
  enrollments: number;
}

export default function Hotspots() {
  const { hotspots, isLoading, error } = useHotspots(0.85);
  const { statesData } = useStateData();
  const { toast } = useToast();
  const [downloading, setDownloading] = useState(false);
  const [selectedHotspot, setSelectedHotspot] = useState<Hotspot | null>(null);
  const [detailsOpen, setDetailsOpen] = useState(false);
  const [planningOpen, setPlanningOpen] = useState(false);

  const handleExportReport = useCallback(() => {
    setDownloading(true);

    const reportData = {
      generatedAt: new Date().toISOString(),
      title: "Enrollment Hotspots Report",
      summary: {
        totalHotspots: hotspots.length,
        criticalCount: hotspots.filter((h: Hotspot) => h.coverage < 70).length,
        statesAffected: new Set(hotspots.map((h: Hotspot) => h.state)).size
      },
      hotspots: hotspots.map((h: Hotspot) => ({
        district: h.district,
        state: h.state,
        coverage: h.coverage,
        enrollments: h.enrollments,
        status: h.coverage < 70 ? 'Critical' : 'Needs Attention'
      }))
    };

    const blob = new Blob([JSON.stringify(reportData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `hotspots-report-${new Date().toISOString().split('T')[0]}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);

    toast({
      title: "Report Exported",
      description: `Exported ${hotspots.length} hotspots to file.`,
    });
    setDownloading(false);
  }, [hotspots, toast]);

  const handleViewDetails = useCallback((hotspot: Hotspot) => {
    setSelectedHotspot(hotspot);
    setDetailsOpen(true);
  }, []);

  const handlePlanOutreach = useCallback(() => {
    setPlanningOpen(true);
  }, []);

  const handleScheduleOutreach = useCallback(() => {
    toast({
      title: "Outreach Scheduled",
      description: `Outreach campaign scheduled for ${hotspots.filter((h: Hotspot) => h.coverage < 70).length} critical districts.`,
    });
    setPlanningOpen(false);
  }, [hotspots, toast]);

  if (isLoading) {
    return (
      <DashboardLayout>
        <div className="flex items-center justify-center h-96">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
          <span className="ml-2">Loading hotspot data...</span>
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
        </div>
      </DashboardLayout>
    );
  }

  const getCoverageColor = (coverage: number) => {
    if (coverage < 70) return 'text-destructive';
    if (coverage < 85) return 'text-warning';
    return 'text-success';
  };

  const getCoverageBg = (coverage: number) => {
    if (coverage < 70) return 'bg-destructive/10';
    if (coverage < 85) return 'bg-warning/10';
    return 'bg-success/10';
  };

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div>
            <h1 className="text-2xl font-bold">Enrollment Hotspots</h1>
            <p className="text-muted-foreground">
              Districts with low enrollment coverage requiring targeted outreach
            </p>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={handleExportReport} disabled={downloading}>
              {downloading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Download className="mr-2 h-4 w-4" />}
              Export Report
            </Button>
            <Button size="sm" onClick={handlePlanOutreach}>
              <Calendar className="mr-2 h-4 w-4" />
              Plan Outreach
            </Button>
          </div>
        </div>

        {/* Summary Stats */}
        <div className="grid gap-4 md:grid-cols-3">
          <Card className="shadow-card">
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <div className="rounded-full bg-destructive/10 p-2">
                  <MapPin className="h-5 w-5 text-destructive" />
                </div>
                <div>
                  <p className="text-2xl font-bold">{hotspots.length}</p>
                  <p className="text-sm text-muted-foreground">Total Hotspots</p>
                </div>
              </div>
            </CardContent>
          </Card>
          <Card className="shadow-card">
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <div className="rounded-full bg-warning/10 p-2">
                  <AlertTriangle className="h-5 w-5 text-warning" />
                </div>
                <div>
                  <p className="text-2xl font-bold">{hotspots.filter((h: Hotspot) => h.coverage < 70).length}</p>
                  <p className="text-sm text-muted-foreground">Critical (&lt;70%)</p>
                </div>
              </div>
            </CardContent>
          </Card>
          <Card className="shadow-card">
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <div className="rounded-full bg-info/10 p-2">
                  <MapPin className="h-5 w-5 text-info" />
                </div>
                <div>
                  <p className="text-2xl font-bold">{new Set(hotspots.map((h: Hotspot) => h.state)).size}</p>
                  <p className="text-sm text-muted-foreground">States Affected</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Hotspots Table */}
        <Card className="shadow-card">
          <CardHeader>
            <CardTitle>Low Coverage Districts</CardTitle>
            <CardDescription>Sorted by coverage percentage (ascending)</CardDescription>
          </CardHeader>
          <CardContent>
            {hotspots.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                <MapPin className="h-12 w-12 mx-auto mb-4 opacity-50" />
                <p>No hotspots detected. All districts have adequate coverage.</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-border">
                      <th className="pb-3 text-left font-medium">District</th>
                      <th className="pb-3 text-left font-medium">State</th>
                      <th className="pb-3 text-left font-medium">Coverage</th>
                      <th className="pb-3 text-left font-medium">Enrollments</th>
                      <th className="pb-3 text-left font-medium">Status</th>
                      <th className="pb-3 text-left font-medium">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {hotspots.slice(0, 20).map((hotspot: Hotspot, idx: number) => (
                      <tr key={`${hotspot.state}-${hotspot.district}-${idx}`} className="border-b border-border/50">
                        <td className="py-3 font-medium">{hotspot.district}</td>
                        <td className="py-3">{hotspot.state}</td>
                        <td className="py-3">
                          <span className={`font-semibold ${getCoverageColor(hotspot.coverage)}`}>
                            {formatPercentage(hotspot.coverage)}
                          </span>
                        </td>
                        <td className="py-3">{hotspot.enrollments.toLocaleString()}</td>
                        <td className="py-3">
                          <Badge className={getCoverageBg(hotspot.coverage)}>
                            {hotspot.coverage < 70 ? 'Critical' : 'Needs Attention'}
                          </Badge>
                        </td>
                        <td className="py-3">
                          <Button variant="ghost" size="sm" onClick={() => handleViewDetails(hotspot)}>
                            <Eye className="mr-1 h-3 w-3" /> View Details
                          </Button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </CardContent>
        </Card>

        {/* State Summary */}
        <Card className="shadow-card">
          <CardHeader>
            <CardTitle>State-wise Overview</CardTitle>
            <CardDescription>Coverage statistics by state</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
              {statesData.slice(0, 12).map((state) => (
                <div
                  key={state.state}
                  className={`p-3 rounded-lg border ${getCoverageBg(state.enrollmentCoverage)}`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-medium">{state.state}</span>
                    <span className={`text-sm ${getCoverageColor(state.enrollmentCoverage)}`}>
                      {formatPercentage(state.enrollmentCoverage)}
                    </span>
                  </div>
                  <div className="mt-2 bg-muted rounded-full h-2">
                    <div
                      className={`h-2 rounded-full ${state.enrollmentCoverage < 70 ? 'bg-destructive' :
                        state.enrollmentCoverage < 85 ? 'bg-warning' : 'bg-success'
                        }`}
                      style={{ width: `${Math.min(100, state.enrollmentCoverage)}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Details Dialog */}
      <Dialog open={detailsOpen} onOpenChange={setDetailsOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>District Details</DialogTitle>
            <DialogDescription>
              Detailed information for {selectedHotspot?.district}
            </DialogDescription>
          </DialogHeader>
          {selectedHotspot && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="p-3 rounded-lg border">
                  <p className="text-sm text-muted-foreground">District</p>
                  <p className="font-medium">{selectedHotspot.district}</p>
                </div>
                <div className="p-3 rounded-lg border">
                  <p className="text-sm text-muted-foreground">State</p>
                  <p className="font-medium">{selectedHotspot.state}</p>
                </div>
                <div className="p-3 rounded-lg border">
                  <p className="text-sm text-muted-foreground">Coverage</p>
                  <p className={`font-medium ${getCoverageColor(selectedHotspot.coverage)}`}>
                    {formatPercentage(selectedHotspot.coverage)}
                  </p>
                </div>
                <div className="p-3 rounded-lg border">
                  <p className="text-sm text-muted-foreground">Enrollments</p>
                  <p className="font-medium">{selectedHotspot.enrollments.toLocaleString()}</p>
                </div>
              </div>
              <div className="p-3 rounded-lg border bg-muted/50">
                <p className="text-sm font-medium mb-2">Recommendations</p>
                <ul className="text-sm text-muted-foreground space-y-1">
                  <li>• Increase enrollment centers in rural areas</li>
                  <li>• Deploy mobile enrollment units</li>
                  <li>• Partner with local government for awareness</li>
                </ul>
              </div>
              <Button className="w-full" onClick={() => {
                toast({ title: "Action Added", description: `Added ${selectedHotspot.district} to outreach plan.` });
                setDetailsOpen(false);
              }}>
                <CheckCircle2 className="mr-2 h-4 w-4" />
                Add to Outreach Plan
              </Button>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Plan Outreach Dialog */}
      <Dialog open={planningOpen} onOpenChange={setPlanningOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Plan Outreach Campaign</DialogTitle>
            <DialogDescription>
              Schedule outreach for low coverage districts
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="p-4 rounded-lg border bg-muted/50">
              <p className="font-medium mb-2">Campaign Summary</p>
              <div className="grid grid-cols-2 gap-2 text-sm">
                <div>Critical Districts:</div>
                <div className="font-medium text-destructive">{hotspots.filter((h: Hotspot) => h.coverage < 70).length}</div>
                <div>States Covered:</div>
                <div className="font-medium">{new Set(hotspots.map((h: Hotspot) => h.state)).size}</div>
                <div>Est. Population:</div>
                <div className="font-medium">{(hotspots.reduce((sum: number, h: Hotspot) => sum + h.enrollments, 0) * 0.2).toLocaleString()}</div>
              </div>
            </div>
            <div className="flex gap-2">
              <Button variant="outline" className="flex-1" onClick={() => setPlanningOpen(false)}>
                Cancel
              </Button>
              <Button className="flex-1" onClick={handleScheduleOutreach}>
                <Calendar className="mr-2 h-4 w-4" />
                Schedule Campaign
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </DashboardLayout>
  );
}
