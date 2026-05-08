import { useState, useEffect } from 'react';
import { getCompanies, getRankedShortlist, Company, RankedShortlist } from '../services/api';
import { recordActivity } from '../services/activityLog';

export default function MLRankedShortlist() {
  const [companies, setCompanies] = useState<Company[]>([]);
  const [selectedCompany, setSelectedCompany] = useState('');
  const [shortlist, setShortlist] = useState<RankedShortlist | null>(null);
  const [mlLoading, setMlLoading] = useState(false);

  useEffect(() => {
    getCompanies({}).then(res => setCompanies(res.data.companies)).catch(() => null);
  }, []);

  const runRanking = async () => {
    if (!selectedCompany) return;
    setMlLoading(true);
    try {
      const res = await getRankedShortlist(selectedCompany, 20);
      setShortlist(res.data);
      recordActivity({
        kind: 'ranking',
        tone: 'success',
        title: 'ML shortlist generated',
        detail: `${res.data.company_name} ranked ${res.data.total_students} students; top ${res.data.top_k} shown`,
        actor: 'Ranking Pipeline',
        status: 'Generated',
      });
    } catch { alert('Ranker not loaded or company not found.'); }
    finally { setMlLoading(false); }
  };

  return (
    <div className="container animate-fade">
      <header className="page-header">
        <h1> ML Ranked Shortlist</h1>
        <p>XGBoost LTR ranker scores candidates by placement fitness.</p>
      </header>

      <div className="glass-card" style={{ marginBottom: '24px' }}>
        <h3 style={{ marginBottom: '4px', color: 'var(--text-accent)' }}>ML Ranked Shortlist</h3>
        <p style={{ color: 'var(--text-secondary)', fontSize: '13px', marginBottom: '16px' }}>
          XGBoost LTR ranker (rank:ndcg) scores all 800 students for any company and returns them ranked by placement fitness.
          <span className="badge badge-success" style={{ marginLeft: '8px' }}>NDCG@10 = 0.9915</span>
        </p>
        <div style={{ display: 'flex', gap: '12px', alignItems: 'flex-end' }}>
          <div style={{ flex: 1 }}>
            <label style={{ display: 'block', marginBottom: '6px', fontSize: '13px', color: 'var(--text-secondary)' }}>Select Company</label>
            <select className="input" value={selectedCompany} onChange={e => setSelectedCompany(e.target.value)}>
              <option value="">-- Choose Company --</option>
              {companies.map(c => (
                <option key={c.company_id} value={c.company_id}>{c.company_name} ({c.tier})</option>
              ))}
            </select>
          </div>
          <button className="btn btn-primary" onClick={runRanking} disabled={mlLoading || !selectedCompany}>
            {mlLoading ? 'Running Ranker...' : 'Get ML Shortlist'}
          </button>
        </div>
      </div>

      {shortlist && (
        <div className="glass-card animate-slide">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
            <h3 style={{ color: 'var(--text-accent)' }}>
              {shortlist.company_name}
              <span className="badge badge-info" style={{ marginLeft: '8px' }}>{shortlist.tier}</span>
            </h3>
            <div style={{ display: 'flex', gap: '8px' }}>
              <span className="badge badge-ghost">{shortlist.total_students} total students</span>
              <span className="badge badge-success">Top {shortlist.top_k} shown</span>
            </div>
          </div>
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>Rank</th><th>Student</th><th>Dept</th><th>CGPA</th><th>Rank Score</th><th>Dept Eligible</th>
                </tr>
              </thead>
              <tbody>
                {shortlist.shortlist.map(r => (
                  <tr key={r.student_id} style={{ background: r.rank <= 3 ? 'rgba(99,102,241,0.06)' : undefined }}>
                    <td style={{ fontWeight: 800, color: r.rank <= 3 ? 'var(--accent-warning)' : 'var(--text-muted)' }}>
                      #{r.rank}
                    </td>
                    <td>
                      <div style={{ fontWeight: 600 }}>{r.full_name}</div>
                      <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>{r.student_id}</div>
                    </td>
                    <td><span className="badge badge-info">{r.department}</span></td>
                    <td style={{ fontWeight: 600 }}>{r.cgpa.toFixed(2)}</td>
                    <td>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <div style={{ flex: 1, height: '6px', borderRadius: '3px', background: 'var(--bg-secondary)' }}>
                          <div style={{ height: '100%', borderRadius: '3px', width: `${r.rank_score * 100}%`, background: 'var(--accent-primary)' }}></div>
                        </div>
                        <span style={{ fontSize: '12px', minWidth: '40px' }}>{r.rank_score.toFixed(3)}</span>
                      </div>
                    </td>
                    <td>
                      <span className={`badge ${r.dept_eligible ? 'badge-success' : 'badge-danger'}`}>
                        {r.dept_eligible ? 'Yes' : 'No'}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
