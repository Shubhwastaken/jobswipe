import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';

const LoginPage: React.FC = () => {
  const navigate = useNavigate();
  const setRole = useAuthStore((state) => state.setRole);

  const handleLogin = () => {
    setRole('admin');
    navigate('/dashboard');
  };

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      height: '100vh',
      backgroundColor: '#f5f7fa',
      fontFamily: 'Inter, sans-serif'
    }}>
      <div style={{
        background: 'white',
        padding: '40px',
        borderRadius: '12px',
        boxShadow: '0 10px 25px rgba(0, 0, 0, 0.05)',
        textAlign: 'center',
        maxWidth: '400px',
        width: '100%'
      }}>
        <h1 style={{ marginBottom: '10px', color: '#1a202c', fontSize: '24px' }}>JobSwipe Admin</h1>
        <p style={{ marginBottom: '30px', color: '#718096', fontSize: '14px' }}>
          Welcome back! Please login to continue.
        </p>
        <button
          onClick={handleLogin}
          style={{
            background: '#3182ce',
            color: 'white',
            border: 'none',
            padding: '12px 24px',
            borderRadius: '6px',
            fontSize: '16px',
            fontWeight: '600',
            cursor: 'pointer',
            width: '100%',
            transition: 'background 0.2s'
          }}
          onMouseOver={(e) => e.currentTarget.style.background = '#2b6cb0'}
          onMouseOut={(e) => e.currentTarget.style.background = '#3182ce'}
        >
          Login as Admin
        </button>
      </div>
    </div>
  );
};

export default LoginPage;
