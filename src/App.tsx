import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import Layout from "./components/layout/Layout";
import TopologyDesign from "./pages/TopologyDesign";
import DeviceManagement from "./pages/DeviceManagement";
import Monitoring from "./pages/Monitoring";
import Simulation from "./pages/Simulation";
import Analytics from "./pages/Analytics";
import AIPanel from "./pages/AIPanel";

function App() {
  return (
    <Router>
      <Layout>
        <Routes>
          <Route path="/" element={<TopologyDesign />} />
          <Route path="/topology" element={<TopologyDesign />} />
          <Route path="/devices" element={<DeviceManagement />} />
          <Route path="/monitoring" element={<Monitoring />} />
          <Route path="/simulation" element={<Simulation />} />
          <Route path="/analytics" element={<Analytics />} />
          <Route path="/ai" element={<AIPanel />} />
        </Routes>
      </Layout>
    </Router>
  );
}

export default App;
