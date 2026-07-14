"use client";

import { useState, useEffect } from 'react';

const CHATWOOT_SSO_URL = 'https://chat.hiep265.shop/auth/saml?account_id=1&RelayState=web';
const POSTIZ_SSO_URL = 'https://app.hiep265.shop/api/postiz-sso';
const OPENCLAW_URL = 'https://openclaw.hiep265.shop/?workspace_sso=1';

export default function Home() {
  const [activeTab, setActiveTab] = useState('dashboard'); // dashboard, chat, post, openclaw
  const [health, setHealth] = useState({
    chatwoot: 'checking',
    postiz: 'checking',
    openclaw: 'checking'
  });
  const [viewer, setViewer] = useState({ email: null, user: null });
  
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
            openclaw: data.openclaw
          });
        } else {
          setHealth({ chatwoot: 'offline', postiz: 'offline', openclaw: 'offline' });
        }
      } catch (err) {
        setHealth({ chatwoot: 'offline', postiz: 'offline', openclaw: 'offline' });
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



        </div>
      </main>
    </div>
  );
}
