import { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import AnnotationEditor from '../components/AnnotationEditor';


const API_BASE = import.meta.env.DEV ? 'http://localhost:8000/api' : '/api';

function Admin() {
  const [feedbacks, setFeedbacks] = useState([]);
  const [stats, setStats] = useState(null);
  const [history, setHistory] = useState([]); // Database records
  const [activeTab, setActiveTab] = useState('dashboard');
  const [loading, setLoading] = useState(true);

  const [error, setError] = useState(null);
  
  // Annotation State
  const [annotationData, setAnnotationData] = useState(null); // { id, imageUrl, initialBoxes }

  const navigate = useNavigate();
  
  const getImageUrl = (id) => `${API_BASE}/feedback/image/${id}`;

  useEffect(() => {
    const token = localStorage.getItem('adminToken');
    if (!token) {
      navigate('/admin/login');
      return;
    }
    // Load initial data based on active tab
    if (activeTab === 'review') {
      loadFeedbacks(token);
    } else {
      loadStats(token);
    }
  }, []); 
  
  useEffect(() => {
    const token = localStorage.getItem('adminToken');
    if (!token) return;
    
    if (activeTab === 'dashboard') {
        loadStats(token);
    } else if (activeTab === 'database') {
        loadHistory(token);
    } else {
        loadFeedbacks(token);
    }
  }, [activeTab]);

  const loadHistory = async (token) => {
    try {
        setLoading(true);
        const res = await fetch(`${API_BASE}/admin/history`, {
            headers: { 'X-Admin-Token': token || localStorage.getItem('adminToken') }
        });
        if (res.status === 401) {
            navigate('/admin/login');
            return;
        }
        if (!res.ok) throw new Error('Failed to fetch history');
        const data = await res.json();
        setHistory(data);
    } catch (err) {
        setError(err.message);
    } finally {
        setLoading(false);
    }
  };

  const deleteHistoryEntry = async (id) => {
    if (!window.confirm('Are you sure you want to permanently delete this record?')) return;
    try {
        const res = await fetch(`${API_BASE}/admin/history/${id}`, {
            method: 'DELETE',
            headers: { 'X-Admin-Token': localStorage.getItem('adminToken') }
        });
        if (!res.ok) throw new Error('Failed to delete');
        setHistory(history.filter(h => h.id !== id));
    } catch (err) {
        alert(err.message);
    }
  };

  const loadStats = async (token) => {
    try {
        setLoading(true);
        const res = await fetch(`${API_BASE}/admin/stats`, {
            headers: { 'X-Admin-Token': token || localStorage.getItem('adminToken') }
        });
        if (res.status === 401) {
            navigate('/admin/login');
            return;
        }
        if (!res.ok) throw new Error('Failed to fetch stats');
        const data = await res.json();
        setStats(data);
    } catch (err) {
        setError(err.message);
    } finally {
        setLoading(false);
    }
  };

  const loadFeedbacks = async (token) => {
    try {
      setLoading(true);
      const res = await fetch(`${API_BASE}/feedback/list?status=pending`, {
        headers: { 'X-Admin-Token': token || localStorage.getItem('adminToken') }
      });
      if (res.status === 401) {
        localStorage.removeItem('adminToken');
        navigate('/admin/login');
        return;
      }
      if (!res.ok) throw new Error('Failed to fetch feedback');
      const data = await res.json();
      setFeedbacks(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // Handle Quick Approve (Directly approve without opening editor)
  const handleQuickApprove = async (id) => {
      try {
          const res = await fetch(`${API_BASE}/feedback/${id}/approve`, {
              method: 'POST',
              headers: { 
                  'X-Admin-Token': localStorage.getItem('adminToken')
              }
          });
          if (!res.ok) throw new Error('Failed to approve');
          setFeedbacks(feedbacks.filter(f => f.id !== id));
      } catch (err) {
          alert('Error approving feedback: ' + err.message);
      }
  };

  // Handle Annotate (Open Editor)
  const handleAnnotateClick = (item) => {
    setAnnotationData({
        id: item.id,
        imageUrl: getImageUrl(item.id),
        initialBoxes: [], 
    });
  };

  const handleAnnotationSave = async (boxes, imgSize, isDraft) => {
    const { id } = annotationData;
    
    // Normalize coordinates
    const labels = boxes.map(b => {
        const x_center = (b.x + b.w / 2) / imgSize.w;
        const y_center = (b.y + b.h / 2) / imgSize.h;
        const width = b.w / imgSize.w;
        const height = b.h / imgSize.h;
        
        // Map class name to ID properly
        const classMap = { 
            'B.subtilis':0, 'C.albicans':1, 'Contamination':2, 
            'Defect':3, 'E.coli':4, 'P.aeruginosa':5, 'S.aureus':6 
        };
        
        return {
            class_id: classMap[b.class] ?? 4, // Default to E.coli (4) if unknown
            x_center,
            y_center,
            width,
            height
        };
    });

    const endpoint = isDraft ? `/feedback/${id}/annotate` : `/feedback/${id}/approve`;

    try {
        const res = await fetch(`${API_BASE}${endpoint}`, { 
            method: 'POST',
            headers: { 
                'X-Admin-Token': localStorage.getItem('adminToken'),
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ labels })
        });
        if (!res.ok) throw new Error(isDraft ? 'Failed to save draft' : 'Failed to approve');
        
        if (!isDraft) {
            // Only remove from list if approved (moved to retraining)
            setFeedbacks(feedbacks.filter(f => f.id !== id));
            setAnnotationData(null); // Close editor
        } else {
            alert("Draft saved!");
            // Keep editor open for drafts
        }
    } catch (err) {
        alert(err.message);
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Delete this feedback entry?')) return;
    try {
        const res = await fetch(`${API_BASE}/feedback/${id}`, { 
            method: 'DELETE',
            headers: { 'X-Admin-Token': localStorage.getItem('adminToken') }
        });
        if (!res.ok) throw new Error('Failed to delete');
        setFeedbacks(feedbacks.filter(f => f.id !== id));
    } catch (err) {
        alert(err.message);
    }
  };



  if (loading && !stats && feedbacks.length === 0) return <div className="loading-overlay"><div className="spinner"></div></div>;

  return (
    <div className="admin-container">
      <div className="admin-header">
        <div className="admin-title">
            <h2>Admin Portal</h2>
            <p>Manage model performance and feedback.</p>
        </div>
        <div className="admin-tabs">
            <button 
                className={`tab-btn ${activeTab === 'dashboard' ? 'active' : ''}`}
                onClick={() => setActiveTab('dashboard')}
            >
                Dashboard
            </button>
            <button 
                className={`tab-btn ${activeTab === 'database' ? 'active' : ''}`}
                onClick={() => setActiveTab('database')}
            >
                Database
            </button>
            <button 
                className={`tab-btn ${activeTab === 'review' ? 'active' : ''}`}
                onClick={() => setActiveTab('review')}
            >
                Review Queue {feedbacks.length > 0 && <span className="history-badge" style={{display: 'inline-flex', verticalAlign: 'middle'}}>{feedbacks.length}</span>}
            </button>
        </div>
      </div>

      {activeTab === 'dashboard' ? (
        <div className="dashboard-view animate-fade-in">
            {stats && (
                <>
                <div className="dashboard-grid">
                    <div className="stat-card">
                        <div className="stat-header">Total Analyses</div>
                        <div className="stat-value">{stats.total_analyses}</div>
                    </div>
                    <div className="stat-card primary">
                        <div className="stat-header">Total Colonies</div>
                        <div className="stat-value">{stats.total_colonies.toLocaleString()}</div>
                    </div>
                    <div className="stat-card warning">
                        <div className="stat-header">Pending Feedback</div>
                        <div className="stat-value">{stats.pending_feedback}</div>
                    </div>
                </div>

                <div className="chart-container">
                    <h3 className="chart-header">Detected Organism Distribution</h3>
                    <div className="chart-content">
                        {Object.entries(stats.class_distribution)
                            .sort(([,a], [,b]) => b - a)
                            .map(([name, count]) => {
                                const max = Math.max(...Object.values(stats.class_distribution));
                                const percent = (count / max) * 100;
                                return (
                                    <div key={name} className="chart-row">
                                        <div className="chart-label">{name}</div>
                                        <div className="chart-bar-bg">
                                            <div className="chart-bar-fill" style={{ width: `${percent}%` }}></div>
                                        </div>
                                        <div className="chart-count">{count}</div>
                                    </div>
                                );
                            })}
                        {Object.keys(stats.class_distribution).length === 0 && <p style={{color: '#999', textAlign: 'center', padding: '2rem'}}>No analysis data available yet.</p>}
                    </div>
                </div>
                </>
            )}
        </div>
      ) : activeTab === 'database' ? (
        <div className="database-view animate-fade-in">
            <div className="card" style={{padding: '0', overflow: 'hidden'}}>
                <table style={{width: '100%', borderCollapse: 'collapse'}}>
                    <thead style={{background: '#f8fafc', borderBottom: '1px solid #e2e8f0'}}>
                        <tr>
                            <th style={{padding: '1rem', textAlign: 'left', fontSize: '0.85rem', color: '#64748b'}}>ID</th>
                            <th style={{padding: '1rem', textAlign: 'left', fontSize: '0.85rem', color: '#64748b'}}>DATE</th>
                            <th style={{padding: '1rem', textAlign: 'left', fontSize: '0.85rem', color: '#64748b'}}>MODEL</th>
                            <th style={{padding: '1rem', textAlign: 'left', fontSize: '0.85rem', color: '#64748b'}}>COUNT</th>
                            <th style={{padding: '1rem', textAlign: 'right', fontSize: '0.85rem', color: '#64748b'}}>ACTIONS</th>
                        </tr>
                    </thead>
                    <tbody>
                        {history.map(row => (
                            <tr key={row.id} style={{borderBottom: '1px solid #f1f5f9'}}>
                                <td style={{padding: '1rem', fontSize: '0.9rem', color: '#64748b'}}>#{row.id}</td>
                                <td style={{padding: '1rem', fontSize: '0.9rem'}}>{new Date(row.timestamp).toLocaleString()}</td>
                                <td style={{padding: '1rem', fontSize: '0.9rem'}}><span className="tag tag-gray">{row.model_used.toUpperCase()}</span></td>
                                <td style={{padding: '1rem', fontSize: '0.9rem', fontWeight: 'bold'}}>{row.total_count}</td>
                                <td style={{padding: '1rem', textAlign: 'right'}}>
                                    <button 
                                        className="btn btn-secondary" 
                                        style={{padding: '4px 8px', color: '#ef4444', borderColor: '#fee2e2', background: '#fef2f2'}}
                                        onClick={() => deleteHistoryEntry(row.id)}
                                    >
                                        Delete
                                    </button>
                                </td>
                            </tr>
                        ))}
                        {history.length === 0 && (
                            <tr>
                                <td colSpan="5" style={{padding: '2rem', textAlign: 'center', color: '#94a3b8'}}>No history records found.</td>
                            </tr>
                        )}
                    </tbody>
                </table>
            </div>
        </div>
      ) : (
        /* Review Queue View */
        <div className="review-view animate-fade-in">
        {error ? (
            <div className="error-message">{error}</div>
        ) : feedbacks.length === 0 ? (
            <div className="empty-state">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1" strokeLinecap="round" strokeLinejoin="round" style={{width: '64px', height: '64px', color: '#cbd5e1', marginBottom: '1rem'}}>
                    <circle cx="12" cy="12" r="10"></circle>
                    <polyline points="12 6 12 12 16 14"></polyline>
                </svg>
                <p>No pending feedback to review.</p>
                <p style={{fontSize: '0.9rem', color: '#94a3b8', marginTop: '0.5rem'}}>Great job keeping up!</p>
            </div>
        ) : (
            <div className="feedback-list">
            {feedbacks.map(item => (
                <div key={item.id} className="feedback-card">
                {/* Image Side */}
                <div className="feedback-image-col">
                    <img 
                        src={getImageUrl(item.id)} 
                        alt="Feedback Image" 
                        className="feedback-img"
                    />
                    <div style={{marginTop: '1rem', display: 'flex', gap: '8px', flexWrap: 'wrap'}}>
                        <span className="tag tag-blue">{item.feedback_type.toUpperCase()}</span>
                        <span className="tag tag-gray">{new Date(item.timestamp).toLocaleDateString()}</span>
                    </div>
                </div>

                {/* Data Side */}
                <div className="feedback-details">
                    <div className="feedback-comparison">
                        <div className="comparison-col">
                            <h4>Original Prediction</h4>
                            {(item.original_count || item.predicted_count) && <p><strong>Count:</strong> {item.original_count || item.predicted_count}</p>}
                            <p style={{marginTop: '8px'}}><strong>Notes:</strong> {item.notes || "None"}</p> 
                        </div>
                        <div className="comparison-col correction">
                            <h4>User Correction</h4>
                            {item.corrections.correct_count && (
                                <p><strong>Count:</strong> {item.corrections.correct_count}</p>
                            )}
                            {item.corrections.correct_class && (
                                <p><strong>Class:</strong> {item.corrections.correct_class}</p>
                            )}
                             {!item.corrections.correct_count && !item.corrections.correct_class && (
                                <p className="text-muted">No specific correction provided.</p>
                            )}
                        </div>
                    </div>

                    <div className="feedback-actions">
                        <button 
                            className="btn btn-secondary" 
                            onClick={() => handleAnnotateClick(item)}
                            title="Open Editor to Annotate"
                        >
                            <span style={{marginRight: '8px'}}>✎</span> Annotate
                        </button>
                        <button 
                            className="btn btn-approve" 
                            onClick={() => handleQuickApprove(item.id)}
                            title="Approve immediately"
                        >
                            <span style={{marginRight: '8px'}}>✓</span> Approve
                        </button>
                        <button 
                            className="btn btn-reject" 
                            onClick={() => handleDelete(item.id)}
                            title="Delete Feedback"
                        >
                            <span style={{marginRight: '8px'}}>✕</span> Reject
                        </button>
                    </div>
                </div>
                </div>
            ))}
            </div>
        )}
        </div>
      )}
      
      {/* Annotation Editor Modal */}
      {annotationData && (
        <AnnotationEditor 
            imageUrl={annotationData.imageUrl}
            initialBoxes={annotationData.initialBoxes}
            onSave={handleAnnotationSave}
            onCancel={() => setAnnotationData(null)}
        />
      )}
    </div>
  );
}

export default Admin;
