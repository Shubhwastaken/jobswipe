import { Link, useLocation } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';

export default function Navbar() {
  const location = useLocation();
  const { userRole, logout } = useAuthStore();

  const isActive = (path: string) => location.pathname === path ? 'active' : '';

  return (
    <nav className="navbar">
      <div className="navbar-inner">
        <Link to="/" className="navbar-brand">
          <div className="brand-icon">✨</div>
          JobSwipe AI
        </Link>
        <div className="navbar-links">
          {userRole === 'admin' ? (
             <>
               <Link to="/" className={isActive('/')}>Dashboard</Link>
               <Link to="/students" className={isActive('/students')}>Students</Link>
               <Link to="/companies" className={isActive('/companies')}>Companies</Link>
               <Link to="/eligibility" className={isActive('/eligibility')}>Eligibility Engine</Link>
             </>
          ) : (
            <>
               <Link to="/" className={isActive('/')}>My Profile</Link>
               <Link to="/opportunities" className={isActive('/opportunities')}>Opportunities</Link>
               <Link to="/improvement" className={isActive('/improvement')}>Improvement Plan</Link>
            </>
          )}
          <button onClick={logout} className="btn btn-ghost btn-sm" style={{marginLeft: '16px'}}>
             Logout
          </button>
        </div>
      </div>
    </nav>
  );
}
