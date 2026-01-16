import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import Dashboard from "./pages/Dashboard";
import Hotspots from "./pages/Hotspots";
import Forecast from "./pages/Forecast";
import GenderTracker from "./pages/GenderTracker";
import RiskPredictor from "./pages/RiskPredictor";
import Monitoring from "./pages/Monitoring";
import SpatialIntelligence from "./pages/SpatialIntelligence";
import NotFound from "./pages/NotFound";

const queryClient = new QueryClient();

const App = () => (
  <QueryClientProvider client={queryClient}>
    <TooltipProvider>
      <Toaster />
      <Sonner />
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/risk-predictor" element={<RiskPredictor />} />
          <Route path="/monitoring" element={<Monitoring />} />
          <Route path="/hotspots" element={<Hotspots />} />
          <Route path="/spatial-intelligence" element={<SpatialIntelligence />} />
          <Route path="/forecast" element={<Forecast />} />
          <Route path="/gender" element={<GenderTracker />} />
          {/* Redirect old anomalies route to monitoring */}
          <Route path="/anomalies" element={<Navigate to="/monitoring" replace />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </BrowserRouter>
    </TooltipProvider>
  </QueryClientProvider>
);

export default App;
