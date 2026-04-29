import { useEffect, useState } from 'react';
import { getCompanies, Company } from '../services/api';

export default function CompaniesPage() {
  const [companies, setCompanies] = useState<Company[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('');

  useEffect(() => {
    getCompanies()
      .then((res) => setCompanies(res.data.companies))
      .catch((err) => console.error(err))
      .finally(() => setLoading(false));
  }, []);

  const filtered = companies.filter(c => 
    c.company_name.toLowerCase().includes(filter.toLowerCase()) ||
    c.industry.toLowerCase().includes(filter.toLowerCase())
  );

  return (
    <div className="container animate-fade">
      <header className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end' }}>
        <div>
          <h1>Companies & Criteria</h1>
          <p>Transparent Rule Definitions for 50 Partner Organizations</p>
        </div>
        <input 
           type="text" 
           placeholder="Search companies or industry..." 
           className="input" 
           style={{ width: '300px' }}
           value={filter}
           onChange={e => setFilter(e.target.value)}
        />
      </header>

      {loading ? (
        <div className="loading"><div className="spinner"></div>Loading...</div>
      ) : (
        <div className="table-container">
          <table>
            <thead>
              <tr>
                <th>Company</th>
                <th>Industry & Tier</th>
                <th>Roles Offered</th>
                <th>Academic Min</th>
                <th>Allowed Depts</th>
                <th>Skills Required</th>
                <th>Package</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map(c => (
                <tr key={c.company_id}>
                  <td>
                    <div style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{c.company_name}</div>
                    <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>ID: {c.company_id}</div>
                  </td>
                  <td>
                    <div style={{ marginBottom: '4px' }}>{c.industry}</div>
                    <span className={`badge badge-${c.tier.toLowerCase()}`}>{c.tier}</span>
                  </td>
                  <td>{c.role_offered}</td>
                  <td>
                    <div style={{ fontSize: '13px' }}>
                      CGPA: <span style={{ color: 'white' }}>{c.min_cgpa.toFixed(1)}</span>
                    </div>
                    <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                      10th: {c.min_10th}% | 12th: {c.min_12th}%
                    </div>
                  </td>
                  <td style={{ maxWidth: '180px', fontSize: '12px', lineHeight: '1.4' }}>
                     {c.allowed_departments.replace(/,/g, ', ')}
                  </td>
                  <td style={{ maxWidth: '200px', fontSize: '12px', lineHeight: '1.4' }}>
                     <div style={{ color: 'var(--text-primary)' }}>{c.required_skills.replace(/,/g, ', ') || 'None'}</div>
                     {c.preferred_skills && <div style={{ color: 'var(--text-muted)', marginTop: '4px' }}>+ Pref: {c.preferred_skills.replace(/,/g, ', ')}</div>}
                  </td>
                  <td style={{ fontWeight: 600, color: 'var(--accent-success)' }}>
                    ₹{c.package_lpa.toFixed(1)} LPA
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {filtered.length === 0 && (
             <div className="empty-state">No companies found matching search.</div>
          )}
        </div>
      )}
    </div>
  );
}
