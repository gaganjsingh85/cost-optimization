import React from 'react';
import { Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import AzureAdvisor from './pages/AzureAdvisor';
import CostAnalysis from './pages/CostAnalysis';
import M365Licensing from './pages/M365Licensing';
import AIAnalysis from './pages/AIAnalysis';
import Settings from './pages/Settings';

function App() {
  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<Dashboard />} />
        <Route path="advisor" element={<AzureAdvisor />} />
        <Route path="costs" element={<CostAnalysis />} />
        <Route path="m365" element={<M365Licensing />} />
        <Route path="analysis" element={<AIAnalysis />} />
        <Route path="settings" element={<Settings />} />
      </Route>
    </Routes>
  );
}

export default App;
