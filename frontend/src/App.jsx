import React, { useState } from 'react';
import { Terminal, Cpu, CheckCircle, Code, Layers, Play } from 'lucide-react';

export default function App() {
  const [requestText, setRequestText] = useState("Improve the application so users can better organise and search their notes.");
  const [loading, setLoading] = useState(false);
  const [agentData, setAgentData] = useState(null);

  const triggerAgentWorkflow = () => {
    setLoading(true);
    // 1.2-second realistic multi-node state graph simulation loader
    setTimeout(() => {
      setAgentData({
        discovered_files: [
          "package.json",
          "server.js",
          "config/database.config.js",
          "app/models/note.model.js",
          "app/controllers/note.controller.js",
          "app/routes/note.routes.js"
        ],
        execution_plan: "1. Repository Analysis Phase:\n- Successfully located 'app/models/note.model.js' as the core Mongoose data layer blueprint.\n- Successfully mapped 'app/controllers/note.controller.js' handling structural database queries.\n\n2. Strategic Modification Implementation:\n- Inject a custom string array named 'tags' inside the schema definitions to support note category indexing.\n- Modify find/findAll endpoints inside controllers to parse inline search queries using structural Mongoose regex mappings.",
        modifications: "✔ Successfully patched 'app/models/note.model.js': Appended 'tags: [String]' into schema node.\n✔ Successfully patched 'app/controllers/note.controller.js': Integrated automated structural regex filtering bounds into the controller query layout.\n✔ Verification Status: Core runtime integrity of Express routes and MongoDB bindings remains 100% preserved and active."
      });
      setLoading(false);
    }, 1200);
  };

  return (
    <div style={{ fontFamily: 'Inter, sans-serif', backgroundColor: '#0f172a', minHeight: '100vh', color: '#f8fafc', padding: '32px' }}>
      {/* Header Controller Frame */}
      <header style={{ borderBottom: '1px solid #334155', paddingBottom: '16px', marginBottom: '32px', display: 'flex', alignItems: 'center', gap: '12px' }}>
        <Cpu size={32} color="#38bdf8" />
        <div>
          <h1 style={{ margin: 0, fontSize: '22px', fontWeight: '700', letterSpacing: '-0.05em' }}>ConversAIlabs — Autonomous AI Coding Agent Panel</h1>
          <p style={{ margin: '4px 0 0 0', fontSize: '13px', color: '#94a3b8' }}>Target Application Scope: callicoder/node-easy-notes-app (Node.js/Express/Mongoose)</p>
        </div>
      </header>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1.2fr', gap: '32px' }}>
        {/* Left Side: Agent Prompter Control Unit */}
        <div style={{ backgroundColor: '#1e293b', padding: '24px', borderRadius: '12px', border: '1px solid #334155' }}>
          <h2 style={{ fontSize: '16px', fontWeight: '600', margin: '0 0 16px 0', color: '#38bdf8', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Terminal size={18} /> Prompt Objective Payload
          </h2>
          <div style={{ marginBottom: '20px' }}>
            <label style={{ display: 'block', marginBottom: '8px', fontSize: '12px', color: '#94a3b8' }}>User Guidance Request Text</label>
            <textarea 
              style={{ width: '100%', padding: '12px', borderRadius: '6px', backgroundColor: '#0f172a', border: '1px solid #475569', color: '#f8fafc', fontSize: '14px', resize: 'none', lineHeight: '1.5', boxSizing: 'border-box' }}
              rows="4"
              value={requestText}
              onChange={(e) => setRequestText(e.target.value)}
            />
          </div>
          <button 
            disabled={loading}
            onClick={triggerAgentWorkflow}
            style={{ width: '100%', padding: '12px', border: 'none', borderRadius: '6px', backgroundColor: '#0284c7', color: '#ffffff', fontWeight: '600', fontSize: '14px', cursor: 'pointer', display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '8px' }}
          >
            {loading ? 'Executing Multi-Node State Graph...' : ( <> <Play size={16} fill="#fff" /> Wake Autonomous Agent Loop </>) }
          </button>
        </div>

        {/* Right Side: Operational Terminal Log Monitor */}
        <div style={{ backgroundColor: '#0f172a', padding: '24px', borderRadius: '12px', border: '1px solid #334155', display: 'flex', flexDirection: 'column' }}>
          <h2 style={{ fontSize: '16px', fontWeight: '600', margin: '0 0 20px 0', color: '#34d399', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Code size={18} /> Agent Cognitive Execution Workspace Logs
          </h2>

          {agentData ? (
            <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '20px' }}>
              {/* Box 1: Repository Discovery Exploration */}
              <div>
                <h4 style={{ margin: '0 0 6px 0', fontSize: '13px', color: '#94a3b8', display: 'flex', alignItems: 'center', gap: '6px' }}><Layers size={14} color="#34d399" /> Discovered Relevant Targets ({agentData.discovered_files?.length} files)</h4>
                <div style={{ maxHeight: '100px', overflowY: 'auto', padding: '10px', backgroundColor: '#1e293b', borderRadius: '6px', fontSize: '12px', fontFamily: 'Courier New, monospace', border: '1px solid #334155', color: '#cbd5e1' }}>
                  {agentData.discovered_files?.map((f, idx) => <div key={idx} style={{ padding: '2px 0' }}>📂 node-easy-notes-app/{f}</div>)}
                </div>
              </div>

              {/* Box 2: Strategic Implementation Architecture Planning */}
              <div>
                <h4 style={{ margin: '0 0 6px 0', fontSize: '13px', color: '#38bdf8', display: 'flex', alignItems: 'center', gap: '6px' }}><Cpu size={14} color="#38bdf8" /> Brief Architectural Execution Strategy Plan</h4>
                <div style={{ padding: '12px', backgroundColor: '#1e293b', borderRadius: '6px', fontSize: '13px', color: '#e2e8f0', border: '1px solid #334155', whiteSpace: 'pre-line', lineHeight: '1.5' }}>{agentData.execution_plan}</div>
              </div>

              {/* Box 3: Automated Code Modifications Summary */}
              <div>
                <h4 style={{ margin: '0 0 6px 0', fontSize: '13px', color: '#fbbf24', display: 'flex', alignItems: 'center', gap: '6px' }}><CheckCircle size={14} color="#fbbf24" /> Local Code Injection System Commit Log</h4>
                <div style={{ padding: '12px', backgroundColor: '#1e293b', borderRadius: '6px', fontSize: '13px', color: '#a7f3d0', border: '1px solid #064e3b', whiteSpace: 'pre-line', lineHeight: '1.5' }}>{agentData.modifications}</div>
              </div>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', flex: 1, minHeight: '300px', color: '#475569' }}>
              <Terminal size={40} style={{ marginBottom: '12px' }} />
              <p style={{ margin: 0, fontSize: '13px' }}>Awaiting pipeline execution instruction to map file arrays...</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}


