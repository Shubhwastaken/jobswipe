import { useEffect, useState } from 'react';
import { getStudents, Student } from '../services/api';

export default function StudentsPage() {
  const [students, setStudents] = useState<Student[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [dept, setDept] = useState('');
  const [offset, setOffset] = useState(0);
  const LIMIT = 50;

  useEffect(() => {
    setLoading(true);
    getStudents({ department: dept || undefined, limit: LIMIT, offset })
      .then((res) => {
        setStudents(res.data.students);
        setTotal(res.data.total);
      })
      .catch((err) => console.error(err))
      .finally(() => setLoading(false));
  }, [dept, offset]);

  return (
    <div className="container animate-fade">
      <header className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end' }}>
        <div>
          <h1>Student Directory</h1>
          <p>Anonymized Student Profiles (Board Type/Gender Hidden for Bias Prevention)</p>
        </div>
        <div style={{ display: 'flex', gap: '10px' }}>
          <select 
             className="input" 
             style={{ width: '200px' }}
             value={dept}
             onChange={e => {
                setDept(e.target.value);
                setOffset(0);
             }}
          >
            <option value="">All Departments</option>
            <option value="CSE">CSE</option>
            <option value="IT">IT</option>
            <option value="AIML">AIML</option>
            <option value="AIDS">AIDS</option>
            <option value="ECE">ECE</option>
            <option value="EEE">EEE</option>
            <option value="MECH">MECH</option>
          </select>
        </div>
      </header>

      {loading ? (
        <div className="loading"><div className="spinner"></div>Loading Students...</div>
      ) : (
        <div className="table-container">
          <table>
            <thead>
              <tr>
                <th>ID & Name</th>
                <th>Department</th>
                <th>CGPA / Year</th>
                <th>Prior Academics</th>
                <th>Backlogs</th>
              </tr>
            </thead>
            <tbody>
              {students.map(s => (
                <tr key={s.student_id}>
                  <td>
                    <div style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{s.full_name}</div>
                    <div style={{ fontSize: '12px', color: 'var(--text-muted)', fontFamily: 'monospace' }}>{s.student_id}</div>
                  </td>
                  <td>
                    <span className="badge badge-info">{s.department}</span>
                  </td>
                  <td>
                    <div style={{ fontWeight: 600 }}>{s.cgpa.toFixed(2)}</div>
                    <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Year {s.year_of_study}</div>
                  </td>
                  <td>
                    <div style={{ fontSize: '13px' }}>
                      <span style={{ color: 'var(--text-secondary)' }}>12th:</span> {s['12th_marks'].toFixed(1)}%
                    </div>
                    <div style={{ fontSize: '13px' }}>
                      <span style={{ color: 'var(--text-secondary)' }}>10th:</span> {s['10th_marks'].toFixed(1)}%
                    </div>
                  </td>
                  <td>
                    {s.active_backlogs > 0 ? (
                      <span className="badge badge-danger" style={{ background: 'transparent', border: '1px solid currentColor' }}>
                         {s.active_backlogs} Active
                      </span>
                    ) : s.backlogs_history > 0 ? (
                      <span className="badge badge-warning" style={{ background: 'transparent', border: '1px solid currentColor' }}>
                         {s.backlogs_history} Cleared
                      </span>
                    ) : (
                      <span className="badge badge-success" style={{ background: 'transparent', border: '1px solid currentColor' }}>Clear</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          <div style={{ padding: '16px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderTop: '1px solid var(--border)', background: 'var(--bg-tertiary)' }}>
             <span style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
                Showing {offset + 1} to {Math.min(offset + LIMIT, total)} of {total}
             </span>
             <div style={{ display: 'flex', gap: '8px' }}>
                <button 
                  className="btn btn-ghost btn-sm" 
                  disabled={offset === 0}
                  onClick={() => setOffset(Math.max(0, offset - LIMIT))}
                >Previous</button>
                <button 
                  className="btn btn-ghost btn-sm" 
                  disabled={offset + LIMIT >= total}
                  onClick={() => setOffset(offset + LIMIT)}
                >Next</button>
             </div>
          </div>
        </div>
      )}
    </div>
  );
}
