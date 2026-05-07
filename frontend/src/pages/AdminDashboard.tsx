import { useEffect, useState } from 'react';
import {
  getStats, getModelMetrics,
  Stats, ModelMetrics
} from '../services/api';

export default function AdminDashboard() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [metrics, setMetrics] = useState<ModelMetrics | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      getStats().catch(() => null),
      getModelMetrics().catch(() => null),
    ]).then(([statsRes, metricsRes]) => {
      if (statsRes?.data) setStats(statsRes.data);
      if (metricsRes?.data) setMetrics(metricsRes.data);
      setLoading(false);
    });
  }, []);

  if (loading) return <div className="loading"><div className="spinner"></div> Loading Dashboard...</div>;
  if (!stats) return <div className="empty-state"><div className="icon">⚠️</div><h3>Failed to load stats</h3></div>;

  return (
    <div className="container animate-fade">
      <header className="page-header">
        <h1>Overview Dashboard</h1>
      </header>


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
    </div>
  );
}
