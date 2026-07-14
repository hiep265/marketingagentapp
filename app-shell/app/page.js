"use client";

import { useState, useEffect } from 'react';

const CHATWOOT_SSO_URL = 'https://chat.hiep265.shop/auth/saml?account_id=1&RelayState=web';
const POSTIZ_SSO_URL = 'https://app.hiep265.shop/api/postiz-sso';
const OPENCLAW_URL = 'https://openclaw.hiep265.shop/?workspace_sso=1';

export default function Home() {
  const [activeTab, setActiveTab] = useState('dashboard'); // dashboard, chat, post, openclaw, bim
  const [health, setHealth] = useState({
    chatwoot: 'checking',
    postiz: 'checking',
    openclaw: 'checking',
    bim: 'checking'
  });
  const [viewer, setViewer] = useState({ email: null, user: null });
  const [bimProjectId, setBimProjectId] = useState('demo-office');
  const [bimFile, setBimFile] = useState(null);
  const [bimReplace, setBimReplace] = useState(true);
  const [bimUploadState, setBimUploadState] = useState({ status: 'idle', message: '' });
  const [bimUploadResult, setBimUploadResult] = useState(null);
  const [bimIngestJob, setBimIngestJob] = useState(null);
  const [bimQuestion, setBimQuestion] = useState('Tầng 3 có bao nhiêu cửa?');
  const [bimAskState, setBimAskState] = useState({ status: 'idle', message: '' });
  const [bimAnswer, setBimAnswer] = useState(null);
  
  // Interactive mock logs for OpenClaw orchestration
  const [orchestratorLogs, setOrchestratorLogs] = useState([
    { time: 'System initialization', text: 'All services mapped under reverse proxy.' },
    { time: 'OpenClaw Daemon', text: 'Listening for webhook events from Chatwoot.' }
  ]);
  
  const [autoRespond, setAutoRespond] = useState(true);
  const [autoPost, setAutoPost] = useState(false);

  // Poll health status from our custom API route
  useEffect(() => {
    const checkHealth = async () => {
      try {
        const res = await fetch('/api/health');
        if (res.ok) {
          const data = await res.json();
          setHealth({
            chatwoot: data.chatwoot,
            postiz: data.postiz,
            openclaw: data.openclaw,
            bim: data.bim
          });
        } else {
          setHealth({ chatwoot: 'offline', postiz: 'offline', openclaw: 'offline', bim: 'offline' });
        }
      } catch (err) {
        setHealth({ chatwoot: 'offline', postiz: 'offline', openclaw: 'offline', bim: 'offline' });
      }
    };

    checkHealth();
    const interval = setInterval(checkHealth, 8000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    const loadViewer = async () => {
      try {
        const res = await fetch('/api/me');
        if (!res.ok) return;
        const data = await res.json();
        setViewer({ email: data.email, user: data.user });
      } catch (err) {
        setViewer({ email: null, user: null });
      }
    };

    loadViewer();
  }, []);

  useEffect(() => {
    if (!bimIngestJob?.job_id || ['completed', 'failed'].includes(bimIngestJob.status)) return;

    const pollJob = async () => {
      try {
        const res = await fetch(`/api/bim/jobs/${encodeURIComponent(bimIngestJob.job_id)}`);
        const data = await res.json();
        if (!res.ok || !data.ok) throw new Error(data.error || data.detail || 'Could not read ingest job');
        setBimIngestJob(data);
        if (data.status === 'completed') {
          setBimUploadResult({ ingest: data.result });
          setBimUploadState({ status: 'success', message: 'BIM model ingested successfully.' });
        } else if (data.status === 'failed') {
          setBimUploadState({ status: 'error', message: data.error || data.message || 'BIM ingest failed.' });
        } else {
          setBimUploadState({ status: 'loading', message: data.message || `Ingest job ${data.status}...` });
        }
      } catch (err) {
        setBimUploadState({ status: 'error', message: err instanceof Error ? err.message : String(err) });
      }
    };

    pollJob();
    const interval = setInterval(pollJob, 2500);
    return () => clearInterval(interval);
  }, [bimIngestJob?.job_id, bimIngestJob?.status]);

  // Add random events to orchestrator logs to show activity
  useEffect(() => {
    if (!autoRespond && !autoPost) return;

    const interval = setInterval(() => {
      const timeStr = new Date().toLocaleTimeString();
      const events = [];
      
      if (autoRespond) {
        events.push({
          time: timeStr,
          text: `[Chatwoot Event] Received customer query -> OpenClaw analyzed and auto-responded via GPT-4o.`
        });
      }
      
      if (autoPost) {
        events.push({
          time: timeStr,
          text: `[Postiz Event] OpenClaw queued auto-generated marketing post for scheduled release.`
        });
      }

      if (events.length > 0) {
        const randomEvent = events[Math.floor(Math.random() * events.length)];
        setOrchestratorLogs(prev => [randomEvent, ...prev.slice(0, 8)]);
      }
    }, 15000);

    return () => clearInterval(interval);
  }, [autoRespond, autoPost]);

  const handleTabChange = (tabId) => {
    setActiveTab(tabId);
  };

  const uploadBimFile = async (event) => {
    event.preventDefault();
    if (!bimFile) {
      setBimUploadState({ status: 'error', message: 'Choose an IFC or IFCZIP file first.' });
      return;
    }

    setBimUploadState({ status: 'loading', message: 'Uploading and ingesting BIM model...' });
    setBimUploadResult(null);
    setBimIngestJob(null);

    try {
      const form = new FormData();
      form.set('project_id', bimProjectId);
      form.set('replace', String(bimReplace));
      form.set('file', bimFile);

      const res = await fetch('/api/bim/upload', { method: 'POST', body: form });
      const data = await res.json();
      if (!res.ok || !data.ok) {
        throw new Error(data.error || 'BIM upload failed');
      }

      setBimIngestJob(data.ingestJob);
      setBimUploadState({ status: 'loading', message: `Upload complete. Ingest job ${data.ingestJob?.job_id || ''} queued.` });
    } catch (err) {
      setBimUploadState({ status: 'error', message: err instanceof Error ? err.message : String(err) });
    }
  };

  const askBim = async (event) => {
    event.preventDefault();
    setBimAskState({ status: 'loading', message: 'Asking BIM graph...' });
    setBimAnswer(null);

    try {
      const res = await fetch('/api/bim/ask', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ project_id: bimProjectId, question: bimQuestion, top_k: 8 })
      });
      const data = await res.json();
      if (!res.ok || !data.ok) {
        throw new Error(data.error || data.detail || 'BIM question failed');
      }

      setBimAnswer(data);
      setBimAskState({ status: 'success', message: 'Answer ready.' });
    } catch (err) {
      setBimAskState({ status: 'error', message: err instanceof Error ? err.message : String(err) });
    }
  };

  return (
    <div className="app-container">
      {/* Sidebar */}
      <aside className="sidebar">
        <div className="sidebar-header">
          <div className="logo-icon">🪐</div>
          <div className="logo-text">AI Workspace</div>
        </div>
        
        <nav className="sidebar-nav">
          <div 
            onClick={() => handleTabChange('dashboard')} 
            className={`nav-item ${activeTab === 'dashboard' ? 'active' : ''}`}
          >
            <span className="nav-icon">📊</span>
            <span>Dashboard</span>
          </div>
          
          <div 
            onClick={() => handleTabChange('chat')} 
            className={`nav-item ${activeTab === 'chat' ? 'active' : ''}`}
          >
            <span className="nav-icon">💬</span>
            <span>Chatwoot (Inbox)</span>
          </div>
          
          <div 
            onClick={() => handleTabChange('post')} 
            className={`nav-item ${activeTab === 'post' ? 'active' : ''}`}
          >
            <span className="nav-icon">📅</span>
            <span>Postiz (Socials)</span>
          </div>
          
          <div 
            onClick={() => handleTabChange('openclaw')} 
            className={`nav-item ${activeTab === 'openclaw' ? 'active' : ''}`}
          >
            <span className="nav-icon">🦞</span>
            <span>OpenClaw (AI)</span>
          </div>

          <div 
            onClick={() => handleTabChange('bim')} 
            className={`nav-item ${activeTab === 'bim' ? 'active' : ''}`}
          >
            <span className="nav-icon">🏢</span>
            <span>BIM Files</span>
          </div>
        </nav>
        
        <div className="sidebar-footer">
          <div className="connection-status">
            <div className={`status-dot ${health.chatwoot === 'online' && health.postiz === 'online' && health.openclaw === 'online' ? '' : 'offline'}`}></div>
            <span>
              {health.chatwoot === 'online' && health.postiz === 'online' && health.openclaw === 'online' 
                ? 'All Services Operational' 
                : 'Some Services Offline'}
            </span>
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="main-content">
        {/* Topbar */}
        <header className="topbar">
          <h1 className="topbar-title">
            {activeTab === 'dashboard' && 'Workspace Control Center'}
            {activeTab === 'chat' && 'Omnichannel Communication'}
            {activeTab === 'post' && 'Social Media Scheduling'}
            {activeTab === 'openclaw' && 'AI Agent Orchestration'}
            {activeTab === 'bim' && 'BIM Model Ingestion'}
          </h1>
          <div className="topbar-actions">
            {viewer.email && <span className="viewer-badge">{viewer.email}</span>}
            <button className="btn" onClick={() => window.location.reload()}>🔄 Refresh Status</button>
            <a className="btn" href="https://app.hiep265.shop/realms/workspace/account/" target="_blank" rel="noreferrer">👤 Account</a>
            <a className="btn btn-primary" href="/oauth2/sign_out?rd=https://app.hiep265.shop">Sign out</a>
          </div>
        </header>

        {/* Portal Views */}
        <div className="portal-container">
          
          {/* TAB 1: Overview Dashboard */}
          {activeTab === 'dashboard' && (
            <div className="dashboard-view">
              <div className="welcome-section">
                <h2 className="welcome-title">Welcome back, Operator</h2>
                <p className="welcome-subtitle">Here is the status of your unified marketing and customer experience stack.</p>
              </div>

              {/* Service Cards Grid */}
              <div className="grid-container">
                {/* Chatwoot Card */}
                <div className="card">
                  <div className="card-header">
                    <h3 className="card-title">💬 Chatwoot</h3>
                    <span className={`card-status ${health.chatwoot === 'online' ? 'online' : 'offline'}`}>
                      {health.chatwoot}
                    </span>
                  </div>
                  <p className="card-description">
                    Manages customer communication across WhatsApp, Telegram, Email, and live chat inboxes.
                  </p>
                  <div className="card-stats">
                    <div className="card-stats-item">
                      <span>Internal Host</span>
                      <span className="card-stats-val">chatwoot-web</span>
                    </div>
                    <div className="card-stats-item">
                      <span>Virtual Port</span>
                      <span className="card-stats-val">3000</span>
                    </div>
                  </div>
                  <div className="card-actions">
                    <button className="btn btn-primary" onClick={() => handleTabChange('chat')}>Open Chatwoot</button>
                    <a href={CHATWOOT_SSO_URL} target="_blank" rel="noreferrer" className="btn" style={{textAlign:'center', textDecoration:'none'}}>External Open</a>
                  </div>
                </div>

                {/* Postiz Card */}
                <div className="card">
                  <div className="card-header">
                    <h3 className="card-title">📅 Postiz</h3>
                    <span className={`card-status ${health.postiz === 'online' ? 'online' : 'offline'}`}>
                      {health.postiz}
                    </span>
                  </div>
                  <p className="card-description">
                    Handles scheduling and publishing of social media posts to LinkedIn, X (Twitter), Facebook, etc.
                  </p>
                  <div className="card-stats">
                    <div className="card-stats-item">
                      <span>Internal Host</span>
                      <span className="card-stats-val">postiz-web</span>
                    </div>
                    <div className="card-stats-item">
                      <span>Virtual Port</span>
                      <span className="card-stats-val">5000</span>
                    </div>
                  </div>
                  <div className="card-actions">
                    <button className="btn btn-primary" onClick={() => handleTabChange('post')}>Open Postiz</button>
                    <a href={POSTIZ_SSO_URL} target="_blank" rel="noreferrer" className="btn" style={{textAlign:'center', textDecoration:'none'}}>External Open</a>
                  </div>
                </div>

                {/* OpenClaw Card */}
                <div className="card">
                  <div className="card-header">
                    <h3 className="card-title">🦞 OpenClaw</h3>
                    <span className={`card-status ${health.openclaw === 'online' ? 'online' : 'offline'}`}>
                      {health.openclaw}
                    </span>
                  </div>
                  <p className="card-description">
                    AI Agent Orchestrator connecting LLM APIs to automate workflows, parse messages, and execute commands.
                  </p>
                  <div className="card-stats">
                    <div className="card-stats-item">
                      <span>Internal Host</span>
                      <span className="card-stats-val">openclaw-gateway</span>
                    </div>
                    <div className="card-stats-item">
                      <span>Gateway Port</span>
                      <span className="card-stats-val">18789</span>
                    </div>
                  </div>
                  <div className="card-actions">
                    <button className="btn btn-primary" onClick={() => handleTabChange('openclaw')}>Open Control UI</button>
                    <a href={OPENCLAW_URL} target="_blank" rel="noreferrer" className="btn" style={{textAlign:'center', textDecoration:'none'}}>External Open</a>
                  </div>
                </div>

                {/* BIM Card */}
                <div className="card">
                  <div className="card-header">
                    <h3 className="card-title">🏢 BIM RAG</h3>
                    <span className={`card-status ${health.bim === 'online' ? 'online' : 'offline'}`}>
                      {health.bim}
                    </span>
                  </div>
                  <p className="card-description">
                    IFC ingestion pipeline backed by Neo4j graph queries and OpenClaw BIM tools.
                  </p>
                  <div className="card-stats">
                    <div className="card-stats-item">
                      <span>Demo Project</span>
                      <span className="card-stats-val">demo-office</span>
                    </div>
                    <div className="card-stats-item">
                      <span>Internal API</span>
                      <span className="card-stats-val">8095</span>
                    </div>
                  </div>
                  <div className="card-actions">
                    <button className="btn btn-primary" onClick={() => handleTabChange('bim')}>Open BIM Files</button>
                  </div>
                </div>
              </div>

              {/* Orchestrator Automation Panel */}
              <div className="orchestrator-panel">
                <h3 className="panel-title">🧠 OpenClaw Cross-App Orchestration</h3>
                
                <div className="grid-container" style={{gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))'}}>
                  <div className="workflow-status">
                    <div className="workflow-row">
                      <div className="workflow-info">
                        <span className="workflow-name">AI Auto-Responder</span>
                        <span className="workflow-desc">Auto-process Chatwoot incoming chats with OpenClaw LLM</span>
                      </div>
                      <div className="workflow-toggle">
                        <label className="switch">
                          <input 
                            type="checkbox" 
                            checked={autoRespond} 
                            onChange={(e) => setAutoRespond(e.target.checked)} 
                          />
                          <span className="slider"></span>
                        </label>
                      </div>
                    </div>

                    <div className="workflow-row" style={{borderLeftColor: 'var(--accent-pink)'}}>
                      <div className="workflow-info">
                        <span className="workflow-name">Smart Social Auto-Posting</span>
                        <span className="workflow-desc">Forward AI-curated campaign ideas to Postiz schedules</span>
                      </div>
                      <div className="workflow-toggle">
                        <label className="switch">
                          <input 
                            type="checkbox" 
                            checked={autoPost} 
                            onChange={(e) => setAutoPost(e.target.checked)} 
                          />
                          <span className="slider"></span>
                        </label>
                      </div>
                    </div>
                  </div>

                  {/* Logs Section */}
                  <div style={{ background: '#07080b', padding: '16px', borderRadius: '8px', border: '1px solid var(--border-subtle)', height: '200px', display: 'flex', flexDirection: 'column' }}>
                    <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '8px', fontWeight: 'bold', letterSpacing: '0.5px' }}>LIVE INTEGRATION HEARTBEAT</span>
                    <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '8px', fontFamily: 'var(--font-mono)', fontSize: '0.75rem' }}>
                      {orchestratorLogs.map((log, index) => (
                        <div key={index} style={{ color: log.text.includes('Chatwoot') ? '#8b5cf6' : log.text.includes('Postiz') ? '#ec4899' : 'var(--text-secondary)' }}>
                          <span style={{ color: 'var(--text-muted)', marginRight: '8px' }}>[{log.time}]</span>
                          {log.text}
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* TAB 2: Chatwoot */}
          <div style={{ display: activeTab === 'chat' ? 'block' : 'none', height: '100%', width: '100%' }}>
            <iframe 
              src={CHATWOOT_SSO_URL} 
              className="app-iframe" 
              title="Chatwoot Omnichannel Inbox"
              allow="camera; microphone; clipboard-write; geolocation"
            />
          </div>

          {/* TAB 3: Postiz */}
          <div style={{ display: activeTab === 'post' ? 'block' : 'none', height: '100%', width: '100%' }}>
            <iframe 
              src={POSTIZ_SSO_URL} 
              className="app-iframe" 
              title="Postiz Social Scheduler"
              allow="clipboard-write"
            />
          </div>

          {/* TAB 4: OpenClaw */}
          <div style={{ display: activeTab === 'openclaw' ? 'block' : 'none', height: '100%', width: '100%' }}>
            <iframe 
              src={OPENCLAW_URL} 
              className="app-iframe" 
              title="OpenClaw Control Board"
              allow="clipboard-write; read-clipboard"
            />
          </div>

          {/* TAB 5: BIM Upload */}
          {activeTab === 'bim' && (
            <div className="dashboard-view">
              <div className="welcome-section">
                <h2 className="welcome-title">BIM Files</h2>
                <p className="welcome-subtitle">Upload IFC models into the OpenClaw BIM graph and query them by project id.</p>
              </div>

              <div className="bim-layout">
                <section className="orchestrator-panel">
                  <h3 className="panel-title">📥 Upload IFC</h3>
                  <form className="bim-form" onSubmit={uploadBimFile}>
                    <label className="field-label" htmlFor="bim-project-id">Project ID</label>
                    <input
                      id="bim-project-id"
                      className="text-input"
                      value={bimProjectId}
                      onChange={(event) => setBimProjectId(event.target.value)}
                      placeholder="demo-office"
                    />

                    <label className="field-label" htmlFor="bim-file">IFC File</label>
                    <input
                      id="bim-file"
                      className="file-input"
                      type="file"
                      accept=".ifc,.ifczip"
                      onChange={(event) => setBimFile(event.target.files?.[0] || null)}
                    />

                    <label className="checkbox-row">
                      <input
                        type="checkbox"
                        checked={bimReplace}
                        onChange={(event) => setBimReplace(event.target.checked)}
                      />
                      <span>Replace existing project graph</span>
                    </label>

                    <div className="card-actions">
                      <button className="btn btn-primary" type="submit" disabled={bimUploadState.status === 'loading'}>
                        {bimUploadState.status === 'loading' ? 'Ingesting...' : 'Upload and Ingest'}
                      </button>
                    </div>
                  </form>

                  {bimUploadState.message && (
                    <div className={`status-box ${bimUploadState.status}`}>
                      {bimUploadState.message}
                    </div>
                  )}

                  {bimIngestJob?.job_id && (
                    <div className="status-box">
                      Job: {bimIngestJob.job_id} · {bimIngestJob.status}
                    </div>
                  )}

                  {bimUploadResult?.ingest?.counts && (
                    <div className="bim-result-grid">
                      <div className="metric-box">
                        <span>Nodes</span>
                        <strong>{bimUploadResult.ingest.counts.nodes}</strong>
                      </div>
                      <div className="metric-box">
                        <span>Relations</span>
                        <strong>{bimUploadResult.ingest.counts.relations}</strong>
                      </div>
                      <div className="metric-box">
                        <span>Chunks</span>
                        <strong>{bimUploadResult.ingest.counts.chunks}</strong>
                      </div>
                    </div>
                  )}
                </section>

                <section className="orchestrator-panel">
                  <h3 className="panel-title">🔎 Ask BIM</h3>
                  <form className="bim-form" onSubmit={askBim}>
                    <label className="field-label" htmlFor="bim-question">Question</label>
                    <textarea
                      id="bim-question"
                      className="text-area"
                      value={bimQuestion}
                      onChange={(event) => setBimQuestion(event.target.value)}
                      rows={4}
                    />
                    <div className="quick-question-row">
                      {['Tầng 3 có bao nhiêu cửa?', 'tường nào chống cháy 2h?', 'Tóm tắt model BIM này'].map((question) => (
                        <button className="btn" type="button" key={question} onClick={() => setBimQuestion(question)}>
                          {question}
                        </button>
                      ))}
                    </div>
                    <div className="card-actions">
                      <button className="btn btn-primary" type="submit" disabled={bimAskState.status === 'loading'}>
                        {bimAskState.status === 'loading' ? 'Asking...' : 'Ask'}
                      </button>
                      <button className="btn" type="button" onClick={() => handleTabChange('openclaw')}>
                        Open OpenClaw
                      </button>
                    </div>
                  </form>

                  {bimAnswer && (
                    <div className="answer-panel">
                      <div className="answer-route">{bimAnswer.route}</div>
                      <p>{bimAnswer.answer}</p>
                      <pre>{JSON.stringify(bimAnswer.facts, null, 2)}</pre>
                    </div>
                  )}
                </section>
              </div>
            </div>
          )}

        </div>
      </main>
    </div>
  );
}
