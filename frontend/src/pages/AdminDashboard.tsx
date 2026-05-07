import { useEffect, useState } from 'react';
import {
  getStats, getModelMetrics, getBiasReport, getRankedShortlist, getCompanies,
  getStudents, getSkillGap,
  Stats, ModelMetrics, BiasReport, RankedShortlist, SkillGapResult, Company, Student
} from '../services/api';

type Tab = 'overview' | 'ranking' | 'skillgap' | 'bias';

export default function AdminDashboard() {
  const [tab, setTab] = useState<Tab>('overview');
  const [stats, setStats] = useState<Stats | null>(null);
  const [metrics, setMetrics] = useState<ModelMetrics | null>(null);
  const [biasReport, setBiasReport] = useState<BiasReport | null>(null);
  const [companies, setCompanies] = useState<Company[]>([]);
  const [students, setStudents] = useState<Student[]>([]);
  const [selectedCompany, setSelectedCompany] = useState('');
  const [selectedStudent, setSelectedStudent] = useState('');
  const [shortlist, setShortlist] = useState<RankedShortlist | null>(null);
  const [skillGap, setSkillGap] = useState<SkillGapResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [mlLoading, setMlLoading] = useState(false);

  useEffect(() => {
    Promise.all([
      getStats().catch(() => null),
      getModelMetrics().catch(() => null),
      getCompanies({}).catch(() => null),
      getStudents({ limit: 100 }).catch(() => null),
    ]).then(([statsRes, metricsRes, compRes, studRes]) => {
      if (statsRes?.data) setStats(statsRes.data);
      if (metricsRes?.data) setMetrics(metricsRes.data);
      if (compRes?.data) setCompanies(compRes.data.companies);
      if (studRes?.data) setStudents(studRes.data.students);
      setLoading(false);
    });
  }, []);

  useEffect(() => {
    if (tab === 'bias' && !biasReport) {
      getBiasReport(false).then(r => setBiasReport(r.data)).catch(() => {});
    }
  }, [tab]);

  const runRanking = async () => {
    if (!selectedCompany) return;
    setMlLoading(true);
    try {
      const res = await getRankedShortlist(selectedCompany, 20);
      setShortlist(res.data);
    } catch { alert('Ranker not loaded or company not found.'); }
    finally { setMlLoading(false); }
  };

  const runSkillGap = async () => {
    if (!selectedStudent) return;
    setMlLoading(true);
    try {
      const res = await getSkillGap(selectedStudent, 5);
      setSkillGap(res.data);
    } catch { alert('Skill recommender not loaded or student not found.'); }
    finally { setMlLoading(false); }
  };

  if (loading) return <div className="loading"><div className="spinner"></div> Loading Dashboard...</div>;
  if (!stats) return <div className="empty-state"><div className="icon">⚠️</div><h3>Failed to load stats</h3></div>;

  const TABS: { id: Tab; label: string; icon: string }[] = [
    { id: 'overview', label: 'Overview', icon: '📊' },
    { id: 'ranking',  label: 'ML Ranked Shortlist', icon: '🏆' },
    { id: 'skillgap', label: 'Skill Gap AI',  icon: '🎯' },
    { id: 'bias',     label: 'Bias Detection', icon: '🔬' },
  ];
  return (
    <div className="container animate-fade">
      <header className="page-header">
        <h1>Overview Dashboard</h1>
        <p>Bias-Free AI Placement System — 3 ML Models Active</p>
      </header>

      {/* ML Status Badges */}
      <div style={{ display: 'flex', gap: '8px', marginBottom: '24px', flexWrap: 'wrap' }}>
        {[
          { label: 'Classifier', ok: stats.model_loaded },
          { label: 'LTR Ranker', ok: stats.ranker_loaded },
          { label: 'Skill Rec.', ok: stats.skill_rec_loaded },
          { label: 'Bias Report', ok: stats.bias_report_available },
        ].map(s => (
          <span key={s.label} className={`badge ${s.ok ? 'badge-success' : 'badge-danger'}`} style={{ fontSize: '13px', padding: '6px 12px' }}>
            {s.ok ? '🟢' : '🔴'} {s.label}
          </span>
        ))}
      </div>

      {/* Tabs */}
      <div style={{ display: 'flex', gap: '4px', marginBottom: '24px', borderBottom: '1px solid var(--border-color)', paddingBottom: '0' }}>
        {TABS.map(t => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`btn ${tab === t.id ? 'btn-primary' : 'btn-ghost'}`}
            style={{ borderRadius: '8px 8px 0 0', borderBottom: tab === t.id ? 'none' : undefined }}
          >
            {t.icon} {t.label}
          </button>
        ))}
      </div>

      {/* ── OVERVIEW TAB ──────────────────────────────────────── */}
      {tab === 'overview' && (
        <>
          <div className="grid grid-4" style={{ marginBottom: '24px' }}>
            <div className="stat-card animate-slide delay-100">
              <div className="stat-label">Total Students</div>
              <div className="stat-value">{stats.total_students}</div>
            </div>
            <div className="stat-card animate-slide delay-200">
              <div className="stat-label">Partner Companies</div>
              <div className="stat-value">{stats.total_companies}</div>
            </div>
            <div className="stat-card animate-slide delay-300">
              <div className="stat-label">Average CGPA</div>
              <div className="stat-value">{stats.avg_cgpa.toFixed(2)}</div>
            </div>
            <div className="stat-card animate-slide delay-400" style={{ borderLeft: '4px solid var(--accent-success)' }}>
              <div className="stat-label">Model Status</div>
              <div className="stat-value animate-pulse-glow" style={{ fontSize: '16px', marginTop: '8px', color: 'var(--accent-success)' }}>
                {stats.model_loaded ? '🟢 Active & Loaded' : '🔴 Offline'}
              </div>
            </div>
          </div>

          <div className="grid grid-2">
            <div className="glass-card animate-slide delay-500">
              <h3 style={{ marginBottom: '16px', color: 'var(--text-accent)' }}>AI Model Performance</h3>
              {metrics?.metrics ? (
                <div className="grid grid-2">
                  {[
                    { label: 'Accuracy', val: `${(metrics.metrics.accuracy * 100).toFixed(1)}%` },
                    { label: 'F1 Score', val: metrics.metrics.f1.toFixed(3) },
                    { label: 'Precision', val: `${(metrics.metrics.precision * 100).toFixed(1)}%` },
                    { label: 'Recall', val: `${(metrics.metrics.recall * 100).toFixed(1)}%` },
                  ].map(m => (
                    <div key={m.label} className="stat-card" style={{ background: 'var(--bg-tertiary)' }}>
                      <div className="stat-label">{m.label}</div>
                      <div className="stat-value" style={{ fontSize: '24px' }}>{m.val}</div>
                    </div>
                  ))}
                </div>
              ) : <p className="text-muted">Model metrics not available.</p>}

              <h3 style={{ marginTop: '32px', marginBottom: '16px', color: 'var(--text-accent)' }}>Fairness Audit</h3>
              {metrics?.fairness ? (
                <div>
                  {[
                    { label: 'Gender Parity Disparity', val: metrics.fairness.gender_parity?.disparity, fair: metrics.fairness.gender_parity?.fair },
                    { label: 'Department Parity Disparity', val: metrics.fairness.department_parity?.disparity, fair: metrics.fairness.department_parity?.fair },
                  ].map(f => (
                    <div key={f.label} style={{ marginBottom: '12px' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px', fontSize: '14px' }}>
                        <span>{f.label}</span>
                        <span style={{ color: f.fair ? 'var(--accent-success)' : 'var(--accent-danger)' }}>
                          {((f.val ?? 0) * 100).toFixed(1)}%
                        </span>
                      </div>
                      <div className="progress-bar">
                        <div className={`progress-fill ${f.fair ? 'success' : 'danger'}`}
                          style={{ width: `${Math.min((f.val ?? 0) * 100 * 5, 100)}%` }}></div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : <p className="text-muted">Fairness report pending.</p>}
            </div>

            <div className="glass-card animate-slide delay-500">
              <h3 style={{ marginBottom: '16px', color: 'var(--text-accent)' }}>Department Distribution</h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                {Object.entries(stats.departments).slice(0, 8).map(([dept, count]) => (
                  <div key={dept}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px', fontSize: '13px' }}>
                      <span>{dept}</span>
                      <span style={{ color: 'var(--text-secondary)' }}>{count} students</span>
                    </div>
                    <div className="progress-bar">
                      <div className="progress-fill primary" style={{ width: `${((count as number) / stats.total_students) * 100}%` }}></div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </>
      )}

      {/* ── RANKING TAB ──────────────────────────────────────── */}
      {tab === 'ranking' && (
        <div className="animate-fade">
          <div className="glass-card" style={{ marginBottom: '24px' }}>
            <h3 style={{ marginBottom: '4px', color: 'var(--text-accent)' }}>🏆 Option 1 — ML Ranked Shortlist</h3>
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
      )}

      {/* ── SKILL GAP TAB ─────────────────────────────────────── */}
      {tab === 'skillgap' && (
        <div className="animate-fade">
          <div className="glass-card" style={{ marginBottom: '24px' }}>
            <h3 style={{ marginBottom: '4px', color: 'var(--text-accent)' }}>🎯 Option 2 — Skill Gap AI</h3>
            <p style={{ color: 'var(--text-secondary)', fontSize: '13px', marginBottom: '16px' }}>
              Counterfactual surrogate model predicts which skills would most increase a student's eligibility across all 50 companies.
              <span className="badge badge-success" style={{ marginLeft: '8px' }}>Spearman ρ = 0.77</span>
            </p>
            <div style={{ display: 'flex', gap: '12px', alignItems: 'flex-end' }}>
              <div style={{ flex: 1 }}>
                <label style={{ display: 'block', marginBottom: '6px', fontSize: '13px', color: 'var(--text-secondary)' }}>Select Student</label>
                <select className="input" value={selectedStudent} onChange={e => setSelectedStudent(e.target.value)}>
                  <option value="">-- Choose Student --</option>
                  {students.map(s => (
                    <option key={s.student_id} value={s.student_id}>
                      {s.full_name} ({s.department}) — CGPA {s.cgpa}
                    </option>
                  ))}
                </select>
              </div>
              <button className="btn btn-primary" onClick={runSkillGap} disabled={mlLoading || !selectedStudent}>
                {mlLoading ? 'Analysing...' : 'Get Skill Recommendations'}
              </button>
            </div>
          </div>

          {skillGap && (
            <div className="glass-card animate-slide">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
                <div>
                  <h3 style={{ color: 'var(--text-accent)' }}>{skillGap.full_name}</h3>
                  <p style={{ color: 'var(--text-secondary)', fontSize: '13px' }}>
                    {skillGap.department} · {skillGap.current_skill_count} skills currently
                  </p>
                </div>
                <span className="badge badge-ghost" style={{ fontSize: '11px' }}>{skillGap.model}</span>
              </div>

              <h4 style={{ marginBottom: '16px', color: 'var(--text-secondary)', fontSize: '13px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                Top Skills to Learn (by predicted eligibility gain)
              </h4>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                {skillGap.recommendations.map((r, i) => (
                  <div key={r.skill} style={{ display: 'flex', alignItems: 'center', gap: '12px', padding: '12px 16px', background: 'var(--bg-secondary)', borderRadius: '10px', border: '1px solid var(--border-color)' }}>
                    <div style={{ width: '28px', height: '28px', borderRadius: '50%', background: i === 0 ? 'var(--accent-primary)' : 'var(--bg-tertiary)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 800, fontSize: '13px', color: i === 0 ? '#fff' : 'var(--text-muted)', flexShrink: 0 }}>
                      {i + 1}
                    </div>
                    <div style={{ flex: 1 }}>
                      <div style={{ fontWeight: 600, marginBottom: '4px' }}>{r.skill}</div>
                      <div style={{ height: '6px', borderRadius: '3px', background: 'var(--bg-tertiary)', overflow: 'hidden' }}>
                        <div style={{
                          height: '100%', borderRadius: '3px',
                          width: `${Math.max(r.predicted_gain * 1000, 4)}%`,
                          background: i === 0 ? 'var(--accent-primary)' : 'var(--accent-success)',
                          transition: 'width 0.6s ease',
                        }}></div>
                      </div>
                    </div>
                    <div style={{ textAlign: 'right', minWidth: '80px' }}>
                      <div style={{ fontWeight: 700, color: 'var(--accent-success)', fontSize: '14px' }}>
                        +{(r.predicted_gain * 100).toFixed(2)}%
                      </div>
                      <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>avg gain</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* ── BIAS DETECTION TAB ───────────────────────────────── */}
      {tab === 'bias' && (
        <div className="animate-fade">
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
                  <h3 style={{ marginBottom: '4px', color: 'var(--accent-danger)' }}>⚠️ Flagged Companies — Biased Criteria Detected</h3>
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
      )}
    </div>
  );
}
