import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { useEffect } from 'react';
import AccessGate from './components/AccessGate';
import Header from './components/Header';
import Home from './pages/Home';
import Analyzer from './pages/Analyzer';
import About from './pages/About';
import FAQ from './pages/FAQ';
import History from './pages/History';
import Profile from './pages/Profile';
import Admin from './pages/Admin';
import AdminLogin from './pages/AdminLogin';

function App() {
  // Apply dark mode globally on mount and listen for changes
  useEffect(() => {
    const applyDarkMode = () => {
      try {
        const saved = localStorage.getItem('userSettings');
        if (saved) {
          const settings = JSON.parse(saved);
          if (settings.darkMode) {
            document.documentElement.setAttribute('data-theme', 'dark');
          } else {
            document.documentElement.removeAttribute('data-theme');
          }
        }
      } catch (e) {
        console.error('Error reading settings:', e);
      }
    };

    // Apply on mount
    applyDarkMode();

    // Listen for localStorage changes (from other tabs or settings page)
    const handleStorageChange = (e) => {
      if (e.key === 'userSettings') {
        applyDarkMode();
      }
    };

    // Also listen for custom event for same-tab updates
    const handleSettingsUpdate = () => applyDarkMode();

    window.addEventListener('storage', handleStorageChange);
    window.addEventListener('settingsUpdated', handleSettingsUpdate);

    return () => {
      window.removeEventListener('storage', handleStorageChange);
      window.removeEventListener('settingsUpdated', handleSettingsUpdate);
    };
  }, []);

  return (
    <AccessGate>
      <BrowserRouter>
        <div className="app-container">
          <Header />
          <main className="main-content">
            <Routes>
              <Route path="/" element={<Home />} />
              <Route path="/analyzer" element={<Analyzer />} />
              <Route path="/history" element={<History />} />
              <Route path="/about" element={<About />} />
              <Route path="/faq" element={<FAQ />} />
              <Route path="/profile" element={<Profile />} />
              <Route path="/admin" element={<Admin />} />
              <Route path="/admin/login" element={<AdminLogin />} />
            </Routes>
          </main>
          <footer className="site-footer">
            <p>CFU-Counter · AI-Powered Bacterial Colony Analysis</p>
          </footer>
        </div>
      </BrowserRouter>
    </AccessGate>
  );
}

export default App;
