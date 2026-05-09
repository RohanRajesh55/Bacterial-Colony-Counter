import { NavLink, Link } from 'react-router-dom';
import { useState, useRef, useEffect } from 'react';

function Header() {
  const [menuOpen, setMenuOpen] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);
  const profileRef = useRef(null);

  // Close profile dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event) {
      if (profileRef.current && !profileRef.current.contains(event.target)) {
        setProfileOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  return (
    <header className="header">
      <div className="header-inner">
        {/* Left: Logo */}
        <div className="header-section-left">
          <Link to="/" className="header-logo">
            {/* Logo image temporarily removed */}
            {/* <img src="/logo.jpeg" alt="CFU-Counter Logo" className="logo-image" /> */}
            <span className="logo-text">CFU-Counter</span>
          </Link>
        </div>

        {/* Center/Right: Navigation + Account */}
        <div className="header-section-right">
          <nav className={`header-nav ${menuOpen ? 'open' : ''}`}>
            <NavLink to="/" className={({isActive}) => isActive ? 'nav-link active' : 'nav-link'} onClick={() => setMenuOpen(false)}>
              Home
            </NavLink>
            <NavLink to="/analyzer" className={({isActive}) => isActive ? 'nav-link active' : 'nav-link'} onClick={() => setMenuOpen(false)}>
              Analyzer
            </NavLink>
            <NavLink to="/history" className={({isActive}) => isActive ? 'nav-link active' : 'nav-link'} onClick={() => setMenuOpen(false)}>
              History
            </NavLink>
            <NavLink to="/faq" className={({isActive}) => isActive ? 'nav-link active' : 'nav-link'} onClick={() => setMenuOpen(false)}>
              FAQ
            </NavLink>
            <NavLink to="/about" className={({isActive}) => isActive ? 'nav-link active' : 'nav-link'} onClick={() => setMenuOpen(false)}>
              About
            </NavLink>
          </nav>

          {/* Account Dropdown - Far Right (Acts as main menu on mobile) */}
          <div className="profile-dropdown" ref={profileRef}>
            <button 
              className="menu-icon-btn"
              onClick={() => setProfileOpen(!profileOpen)}
              aria-label="Menu"
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <line x1="3" y1="12" x2="21" y2="12"></line>
                <line x1="3" y1="6" x2="21" y2="6"></line>
                <line x1="3" y1="18" x2="21" y2="18"></line>
              </svg>
            </button>
            
            {profileOpen && (
              <div className="dropdown-menu dropdown-menu-right">
                {/* Mobile Navigation Links (Hidden on Desktop via CSS) */}
                <div className="mobile-nav-section">
                  <div className="dropdown-header">
                    <span className="dropdown-label">Navigation</span>
                  </div>
                  <Link to="/" className="dropdown-item" onClick={() => setProfileOpen(false)}>
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"></path><polyline points="9 22 9 12 15 12 15 22"></polyline></svg>
                    Home
                  </Link>
                  <Link to="/analyzer" className="dropdown-item" onClick={() => setProfileOpen(false)}>
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>
                    Analyzer
                  </Link>
                  <Link to="/history" className="dropdown-item" onClick={() => setProfileOpen(false)}>
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline></svg>
                    History
                  </Link>
                  <Link to="/faq" className="dropdown-item" onClick={() => setProfileOpen(false)}>
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10"></circle><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"></path><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>
                    FAQ
                  </Link>
                  <div className="dropdown-divider"></div>
                </div>

                {/* Account Links */}
                <div className="dropdown-header">
                  <span className="dropdown-label">Account</span>
                </div>
                <Link to="/profile" className="dropdown-item" onClick={() => setProfileOpen(false)}>
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
                    <circle cx="12" cy="7" r="4"></circle>
                  </svg>
                  Profile
                </Link>
                <Link to="/profile" className="dropdown-item" onClick={() => setProfileOpen(false)}>
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <circle cx="12" cy="12" r="3"></circle>
                    <path d="M12 1v2m0 18v2M4.22 4.22l1.42 1.42m12.72 12.72l1.42 1.42M1 12h2m18 0h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"></path>
                  </svg>
                  Settings
                </Link>
                <div className="dropdown-divider"></div>
                <Link to="/admin" className="dropdown-item" onClick={() => setProfileOpen(false)}>
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path>
                  </svg>
                  Admin Panel
                </Link>
              </div>
            )}
          </div>
        </div>
      </div>
    </header>
  );
}

export default Header;
