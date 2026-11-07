import { Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider, useAuth } from "./context/AuthContext";
import { ThemeProvider } from "./context/ThemeContext";
import { Layout } from "./components/Layout";
import { Login } from "./pages/Login";
import { Dashboard } from "./pages/Dashboard";
import { CircuitLab } from "./pages/CircuitLab";
import { JobExplorer } from "./pages/JobExplorer";
import { JobDetails } from "./pages/JobDetails";
import { NoiseStudio } from "./pages/NoiseStudio";
import { AlgorithmLibrary } from "./pages/AlgorithmLibrary";
import { Backends } from "./pages/Backends";
import { Compilation } from "./pages/Compilation";
import { Documentation } from "./pages/Documentation";
import { Settings } from "./pages/Settings";

function ProtectedLayout() {
  const { isAuthenticated } = useAuth();
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  return <Layout />;
}

function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route element={<ProtectedLayout />}>
        <Route path="/" element={<Dashboard />} />
        <Route path="/circuit-lab" element={<CircuitLab />} />
        <Route path="/jobs" element={<JobExplorer />} />
        <Route path="/jobs/:jobId" element={<JobDetails />} />
        <Route path="/backends" element={<Backends />} />
        <Route path="/compilation" element={<Compilation />} />
        <Route path="/experiments" element={<NoiseStudio />} />
        <Route path="/algorithms" element={<AlgorithmLibrary />} />
        <Route path="/docs" element={<Documentation />} />
        <Route path="/settings" element={<Settings />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </ThemeProvider>
  );
}
