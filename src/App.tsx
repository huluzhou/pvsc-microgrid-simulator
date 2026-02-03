import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import Layout from "./components/layout/Layout";
import TopologyDesign from "./pages/TopologyDesign";
import DeviceControl from "./pages/DeviceControl";
import Simulation from "./pages/Simulation";
import Modbus from "./pages/Modbus";
import Monitoring from "./pages/Monitoring";
import Dashboard from "./pages/Dashboard";
import Analytics from "./pages/Analytics";
import AIPanel from "./pages/AIPanel";

function App() {
  return (
    <Router future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <Layout>
        <Routes>
          <Route path="/" element={<TopologyDesign />} />
          <Route path="/topology" element={<TopologyDesign />} />
          <Route path="/device-control" element={<DeviceControl />} />
          <Route path="/simulation" element={<Simulation />} />
          <Route path="/modbus" element={<Modbus />} />
          <Route path="/monitoring" element={<Monitoring />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/analytics" element={<Analytics />} />
          <Route path="/ai" element={<AIPanel />} />
        </Routes>
      </Layout>
    </Router>
  );
}

export default App;
