import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import Sidebar from "./components/Sidebar";
import Navbar from "./components/Navbar";
import Dashboard from "./pages/Dashboard";
import Portfolio from "./pages/Portfolio";
import CopyTrading from "./pages/CopyTrading";
import Analytics from "./pages/Analytics";
import Subscribers from "./pages/Subscribers";
import Settings from "./pages/Settings";
import Register from "./pages/onboarding/Register";
import Login from "./pages/onboarding/Login";
import Subscription from "./pages/onboarding/Subscription";
import ConnectMT5 from "./pages/onboarding/ConnectMT5";
import Success from "./pages/onboarding/Success";
import { isAuthenticated } from "./services/auth";
import "./App.css";


function Protected({ children }) {
  return isAuthenticated() ? children : <Navigate to="/login" replace />;
}


function PortalLayout() {
  return (
    <Protected>
      <div className="layout">
        <Sidebar />
        <div className="main">
          <Navbar />
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/portfolio" element={<Portfolio />} />
            <Route path="/copy-trading" element={<CopyTrading />} />
            <Route path="/analytics" element={<Analytics />} />
            <Route path="/subscribers" element={<Subscribers />} />
            <Route path="/settings" element={<Settings />} />
          </Routes>
        </div>
      </div>
    </Protected>
  );
}


export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route
          path="/subscription"
          element={<Protected><Subscription /></Protected>}
        />
        <Route
          path="/connect-mt5"
          element={<Protected><ConnectMT5 /></Protected>}
        />
        <Route
          path="/onboarding-success"
          element={<Protected><Success /></Protected>}
        />
        <Route path="/*" element={<PortalLayout />} />
      </Routes>
    </BrowserRouter>
  );
}
