import { Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import ChatConsole from './pages/ChatConsole';
import ForecastUpload from './pages/ForecastUpload';
import ApprovalQueue from './pages/ApprovalQueue';

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<Dashboard />} />
        <Route path="chat" element={<ChatConsole />} />
        <Route path="forecast" element={<ForecastUpload />} />
        <Route path="approvals" element={<ApprovalQueue />} />
      </Route>
    </Routes>
  );
}
