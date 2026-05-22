import { Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout';
import ChatConsole from './pages/ChatConsole';
import CreateProject from './pages/CreateProject';
import DataManager from './pages/DataManager';

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<Navigate to="/chat" replace />} />
        <Route path="chat" element={<ChatConsole />} />
        <Route path="create-project" element={<CreateProject />} />
        <Route path="data-manager" element={<DataManager />} />
      </Route>
    </Routes>
  );
}
