import { useEffect, useState } from 'react';
import { getBiasReport, BiasReport } from '../services/api';

export default function BiasDetection() {
  const [biasReport, setBiasReport] = useState<BiasReport | null>(null);

  useEffect(() => {
    getBiasReport(false).then(r => setBiasReport(r.data)).catch(() => {});
  }, []);

  return (
    <div className="container animate-fade">
      <header className="page-header">
        <h1> Bias Detection</h1>
        <p>Fairness Audit and Disparate Impact Analysis</p>
      </header>

      {!biasReport ? (
        <div className="loading"><div className="spinner"></div> Loading bias report...</div>
      ) : (
        <>
          {/* Summary cards */}
          <div className="grid grid-4" style={{ marginBottom: '24px' }}>
            <div className="stat-card">
              <div className="stat-label">Companies Analysed</div>
              <div className="stat-value">{biasReport.summary.n_companies}</div>
            </div>
            <div className="stat-card" style={{ borderLeft: '4px solid var(--accent-danger)' }}>
              <div className="stat-label">Flagged for Bias</div>
              <div className="stat-value" style={{ color: biasReport.summary.n_flagged > 0 ? 'var(--accent-danger)' : 'var(--accent-success)' }}>
                {biasReport.summary.n_flagged}
              </div>
            </div>
            <div className="stat-card">
              <div className="stat-label">Flag Rate</div>
              <div className="stat-value">{(biasReport.summary.flag_rate * 100).toFixed(1)}%</div>
            </div>
            <div className="stat-card">
              <div className="stat-label">Test Used</div>
              <div className="stat-value" style={{ fontSize: '14px', marginTop: '6px' }}>Fisher's Exact<br/><span style={{fontSize:'11px', color:'var(--text-muted)'}}>p &lt; {biasReport.summary.significance}</span></div>
            </div>
          </div>

          {/* Flagged companies */}
          {biasReport.flagged_companies.length > 0 && (
            <div className="glass-card" style={{ marginBottom: '24px', borderColor: 'rgba(239,68,68,0.3)' }}>
              <h3 style={{ marginBottom: '4px', color: 'var(--accent-danger)' }}> Flagged Companies — Biased Criteria Detected</h3>
              <p style={{ color: 'var(--text-secondary)', fontSize: '13px', marginBottom: '16px' }}>
                These companies' hard placement rules produce statistically significant gender disparate impact (p &lt; {biasReport.summary.significance}, gap &gt; {(biasReport.summary.threshold * 100).toFixed(0)}%).
              </p>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                {biasReport.flagged_companies.map(f => (
                  <div key={f.company_id} style={{ padding: '14px 16px', background: 'rgba(239,68,68,0.06)', border: '1px solid rgba(239,68,68,0.2)', borderRadius: '10px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                      <div>
                        <span style={{ fontWeight: 700 }}>{f.company_name}</span>
                        <span className="badge badge-danger" style={{ marginLeft: '8px', fontSize: '11px' }}>{f.tier}</span>
                      </div>
                      <div style={{ display: 'flex', gap: '8px' }}>
                        <span className="badge badge-danger">Disparity: {(f.disparity * 100).toFixed(1)}%</span>
                        <span className="badge badge-ghost" style={{ fontSize: '11px' }}>p={f.p_value.toFixed(4)}</span>
                        <span className="badge badge-warning" style={{ fontSize: '11px' }}>Driver: {f.top_bias_criterion}</span>
                      </div>
                    </div>
                    <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                      {Object.entries(f.pass_rates).map(([g, r]) => (
                        <span key={g} style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
                          {g}: <strong>{((r as number) * 100).toFixed(0)}%</strong> pass rate
                        </span>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* All companies table */}
          <div className="glass-card">
            <h3 style={{ marginBottom: '16px', color: 'var(--text-accent)' }}>All Companies — Gender Disparity Ranking</h3>
            <div className="table-container">
              <table>
                <thead>
                  <tr>
                    <th>Company</th><th>Tier</th><th>Pool Pass Rate</th><th>Gender Disparity</th><th>p-value</th><th>Bias Driver</th><th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {(biasReport.all_companies ?? [])
                    .sort((a, b) => b.gender_disparity - a.gender_disparity)
                    .map(c => (
                      <tr key={c.company_id} style={{ background: c.gender_flagged ? 'rgba(239,68,68,0.04)' : undefined }}>
                        <td style={{ fontWeight: 600 }}>{c.company_name}</td>
                        <td><span className="badge badge-info">{c.tier}</span></td>
                        <td>{(c.pool_pass_rate * 100).toFixed(1)}%</td>
                        <td>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                            <div style={{ flex: 1, height: '6px', borderRadius: '3px', background: 'var(--bg-secondary)' }}>
                              <div style={{ height: '100%', borderRadius: '3px', width: `${Math.min(c.gender_disparity * 400, 100)}%`, background: c.gender_flagged ? 'var(--accent-danger)' : 'var(--accent-success)' }}></div>
                            </div>
                            <span style={{ fontSize: '12px', minWidth: '36px' }}>{(c.gender_disparity * 100).toFixed(1)}%</span>
                          </div>
                        </td>
                        <td style={{ fontSize: '12px', color: 'var(--text-muted)' }}>{c.gender_p_value.toFixed(4)}</td>
                        <td><span className="badge badge-ghost" style={{ fontSize: '11px' }}>{c.top_bias_criterion}</span></td>
                        <td>
                          {c.gender_flagged
                            ? <span className="badge badge-danger">Flagged</span>
                            : <span className="badge badge-success">Clean</span>}
                        </td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
