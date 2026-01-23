import React, { useEffect, useState } from 'react';
import { Route, Routes, Link, useNavigate } from 'react-router-dom';
import axios from 'axios';

// Set base URL for all axios requests to point to the backend API
axios.defaults.baseURL = 'http://localhost:8000';

import { msalInstance, login, logout, isMsalConfigured } from './utils/auth';
import LoginPage from './pages/LoginPage';
import DetectorsPage from './pages/DetectorsPage';
import QueryHistoryPage from './pages/QueryHistoryPage';
import EscalationQueuePage from './pages/EscalationQueuePage';
import HubStatusPage from './pages/HubStatusPage';
import AdminPage from './pages/AdminPage';
import DetectorConfigPage from './pages/DetectorConfigPage';
import AlertSettingsPage from './pages/AlertSettingsPage';
import DeploymentManagerPage from './pages/DeploymentManagerPage';
import CameraInspectionPage from './pages/CameraInspectionPage';
import DetectorAlertsPage from './pages/DetectorAlertsPage';
import DemoStreamPage from './pages/DemoStreamPage';
import DetectorAlertConfigPage from './pages/DetectorAlertConfigPage';

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [accessToken, setAccessToken] = useState<string | null>(null);
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    localStorage.removeItem('local_access_token');
    setIsAuthenticated(false);
    setAccessToken(null);
  };

  useEffect(() => {
    // Check for local token first
    const localToken = localStorage.getItem('local_access_token');
    if (localToken) {
        setIsAuthenticated(true);
        setAccessToken(localToken);
        axios.defaults.headers.common['Authorization'] = `Bearer ${localToken}`;
        return;
    }

    // Only check MSAL if it's configured
    if (isMsalConfigured && msalInstance) {
      const account = msalInstance.getActiveAccount();
      if (account) {
        setIsAuthenticated(true);
        // Acquire token silently
        msalInstance
          .acquireTokenSilent({
            scopes: ['openid', 'profile', 'email'],
            account,
          })
          .then((res) => {
            setAccessToken(res.accessToken);
            axios.defaults.headers.common['Authorization'] = `Bearer ${res.accessToken}`;
          })
          .catch(() => {
            setIsAuthenticated(false);
          });
      }
    }
  }, []);

  // Axios interceptor to handle 401 errors globally
  useEffect(() => {
    const interceptor = axios.interceptors.response.use(
      (response) => response,
      (error) => {
        if (error.response && error.response.status === 401) {
          console.warn('Unauthorized request detected. Clearing session.');
          handleLogout();
        }
        return Promise.reject(error);
      }
    );

    return () => {
      axios.interceptors.response.eject(interceptor);
    };
  }, []);

  const handleLogin = async () => {
    try {
      const res = await login();
      if (res) {
        setIsAuthenticated(true);
        setAccessToken(res.accessToken);
        axios.defaults.headers.common['Authorization'] = `Bearer ${res.accessToken}`;
        navigate('/');
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleLocalLogin = (token: string) => {
    localStorage.setItem('local_access_token', token);
    setAccessToken(token);
    axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
    setIsAuthenticated(true);
    navigate('/');
  };

  if (!isAuthenticated) {
    return <LoginPage onLogin={handleLogin} onLocalLogin={handleLocalLogin} />;
  }

  return (
    <div className="min-h-screen bg-gray-900 text-gray-300 flex flex-col">
      <nav className="bg-gray-800 shadow border-b border-gray-700">
        <div className="max-w-7xl mx-auto px-4 py-4 flex justify-between items-center">
          <div className="flex items-center space-x-4">
            <Link to="/" className="text-xl font-bold text-blue-500">
              IntelliOptics 2.0
            </Link>
            {/* Primary Operations */}
            <Link to="/detectors" className="text-gray-300 hover:text-blue-400">
              Detectors
            </Link>
            <Link to="/deployments" className="text-gray-300 hover:text-blue-400">
              Deployments
            </Link>
            <Link to="/hubs" className="text-gray-300 hover:text-blue-400">
              Hubs
            </Link>
            {/* Monitoring & Analysis */}
            <span className="text-gray-600">|</span>
            <Link to="/queries" className="text-gray-300 hover:text-blue-400">
              Queries
            </Link>
            <Link to="/escalations" className="text-gray-300 hover:text-blue-400">
              Escalations
            </Link>
            <Link to="/detector-alerts" className="text-gray-300 hover:text-blue-400">
              Alerts
            </Link>
            <Link to="/camera-inspection" className="text-gray-300 hover:text-blue-400">
              Camera Health
            </Link>
            {/* Settings & Tools */}
            <span className="text-gray-600">|</span>
            <Link to="/settings/alerts" className="text-gray-300 hover:text-blue-400">
              Settings
            </Link>
            <Link to="/admin" className="text-gray-300 hover:text-blue-400">
              Admin
            </Link>
            <Link to="/demo" className="text-gray-300 hover:text-blue-400">
              Demo
            </Link>
          </div>
          <button onClick={handleLogout} className="text-red-400 hover:text-red-300 font-bold">
            Logout
          </button>
        </div>
      </nav>
      <div className="flex-1 max-w-7xl mx-auto w-full py-4">
        <Routes>
          <Route path="/" element={<DetectorsPage />} />
          <Route path="/detectors" element={<DetectorsPage />} />
          <Route path="/detectors/:id/configure" element={<DetectorConfigPage />} />
          <Route path="/detectors/:detectorId/alert-config" element={<DetectorAlertConfigPage />} />
          <Route path="/queries" element={<QueryHistoryPage />} />
          <Route path="/escalations" element={<EscalationQueuePage />} />
          <Route path="/hubs" element={<HubStatusPage />} />
          <Route path="/camera-inspection" element={<CameraInspectionPage />} />
          <Route path="/detector-alerts" element={<DetectorAlertsPage />} />
          <Route path="/demo" element={<DemoStreamPage />} />
          <Route path="/admin" element={<AdminPage />} />
          <Route path="/settings/alerts" element={<AlertSettingsPage />} />
          <Route path="/deployments" element={<DeploymentManagerPage />} />
        </Routes>
      </div>

      {/* Footer */}
      <footer className="py-4 text-center text-gray-500 text-sm border-t border-gray-800">
        Powered By 4wardmotion Solutions, Inc
      </footer>
    </div>
  );
}

export default App;