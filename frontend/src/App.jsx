import { Routes, Route, Link, useNavigate } from 'react-router';
import { useAuth } from './context/AuthContext';
import ProtectedRoute from './components/ProtectedRoute';
import HomePage from './pages/HomePage';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import HistoryPage from './pages/HistoryPage';
import AccountPage from './pages/AccountPage';
import CorrectionPage from './pages/CorrectionPage';

function App() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout();
    navigate('/');
  };

  return (
    <div className="app-container">
      <header className="header">
        <nav className="nav-bar">
          <Link to="/" className="nav-logo">
            Bacterial Colony Counter
          </Link>
          <div className="nav-links">
            {user ? (
              <>
                <span className="nav-user">{user.email}</span>
                <Link to="/history" className="nav-link">History</Link>
                <Link to="/account" className="nav-link">Account</Link>
                <button onClick={handleLogout} className="nav-link nav-logout">
                  Logout
                </button>
              </>
            ) : (
              <>
                <Link to="/login" className="nav-link">Login</Link>
                <Link to="/register" className="nav-link nav-register">Register</Link>
              </>
            )}
          </div>
        </nav>
        <p className="header-subtitle">Automated colony counting powered by RT-DETR</p>
      </header>

      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route path="/correct" element={<CorrectionPage />} />
        <Route
          path="/history"
          element={
            <ProtectedRoute>
              <HistoryPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/account"
          element={
            <ProtectedRoute>
              <AccountPage />
            </ProtectedRoute>
          }
        />
      </Routes>
    </div>
  );
}

export default App;
