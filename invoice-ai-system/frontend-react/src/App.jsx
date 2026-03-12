import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Plus, Upload, FileText, CheckCircle, Clock, 
  ChevronRight, ArrowRight, Download, Search, RefreshCw,
  LayoutDashboard, ShieldCheck, Mail, Settings, DollarSign,
  AlertTriangle, XCircle, HardDrive, Inbox, Save, Trash2
} from 'lucide-react';

// --- CONFIG ---
axios.defaults.baseURL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const App = () => {
  const [invoices, setInvoices] = useState([]);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('Overview');
  const [selectedInvoice, setSelectedInvoice] = useState(null);
  const [config, setConfig] = useState({ groq_key: '', email: '', password: '' });
  const [ingestionMode, setIngestionMode] = useState('Manual');
  const [toast, setToast] = useState(null);
  const [extracting, setExtracting] = useState(false);

  const showToast = (message, type = 'success') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 4000);
  };

  useEffect(() => {
    fetchInvoices();
    fetchConfig();
  }, []);

  const fetchInvoices = async () => {
    try {
      const resp = await axios.get('/api/invoices');
      const data = Array.isArray(resp.data) ? resp.data : [];
      setInvoices(data);
      
      // Auto-poll if any invoice is still processing
      const hasProcessing = data.some(inv => inv.status === 'Processing');
      setExtracting(hasProcessing);
      if (hasProcessing) {
        setTimeout(fetchInvoices, 3000);
      }
    } catch (err) { 
      console.error(err); 
      setInvoices([]);
      setExtracting(false);
    }
  };

  const fetchConfig = async () => {
    try {
      const resp = await axios.get('/api/config');
      setConfig(resp.data);
    } catch (err) { console.error(err); }
  };

  const saveConfig = async () => {
    try {
      await axios.post('/api/config', config);
      showToast("Security settings updated successfully");
    } catch (err) { 
      console.error(err); 
      showToast("Failed to save settings", "error");
    }
  };

  const handleUpload = async (e) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;

    // We don't set global loading here because we process in background
    try {
      for (const file of files) {
        const formData = new FormData();
        formData.append('file', file);
        try {
          await axios.post('/api/extract', formData);
        } catch (fileErr) {
          console.error(`Failed to trigger background extraction for ${file.name}`, fileErr);
          showToast(`Extraction failed for ${file.name}`, "error");
        }
      }
      showToast(`Triggered extraction for ${files.length} document(s)`);
      setExtracting(true);
      // Start polling immediately
      fetchInvoices();
    } catch (err) {
      console.error("Batch upload orchestration error", err);
    }
  };

  const approveInvoice = async (id) => {
    try {
      await axios.post(`/api/approve/${id}`);
      fetchInvoices();
      setSelectedInvoice(null);
    } catch (err) { console.error(err); }
  };

  const rejectInvoice = async (id) => {
    try {
      await axios.post(`/api/reject/${id}`);
      fetchInvoices();
      setSelectedInvoice(null);
    } catch (err) { console.error(err); }
  };

  const payInvoice = async (id) => {
    try {
      await axios.post(`/api/pay/${id}`);
      fetchInvoices();
      setSelectedInvoice(null);
    } catch (err) { console.error(err); }
  };

  const deleteInvoice = async (e, id) => {
    e.stopPropagation(); // Don't open the modal
    if (!window.confirm("Purge this invoice from registry?")) return;
    try {
      await axios.delete(`/api/invoices/${id}`);
      fetchInvoices();
    } catch (err) { console.error(err); }
  };

  const syncLocal = async () => {
    setLoading(true);
    try { await axios.post('/api/sync/local'); fetchInvoices(); }
    catch (err) { console.error(err); }
    finally { setLoading(false); }
  };

  const syncEmail = async () => {
    setLoading(true);
    try { await axios.post('/api/sync/email'); fetchInvoices(); }
    catch (err) { console.error(err); }
    finally { setLoading(false); }
  };

  const clearRegistry = async () => {
    if (!window.confirm("CRITICAL: This will purge ALL data from the registry. Proceed?")) return;
    try {
      await axios.delete('/api/invoices');
      fetchInvoices();
      showToast("Registry cleared successfully");
    } catch (err) { console.error(err); }
  };

  const [xmlContent, setXmlContent] = useState(null);

  const downloadZip = async () => {
    try {
      const baseUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      window.open(`${baseUrl}/api/export/zip`, '_blank');
    } catch (err) { console.error(err); }
  };

  const downloadExcel = async () => {
    try {
      const resp = await axios.get('/api/export/excel');
      const baseUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      window.open(`${baseUrl}/${resp.data.file_url}`, '_blank');
    } catch (err) { console.error(err); }
  };

  const generateXml = async (id) => {
    try {
      const resp = await axios.get(`/api/export/xml/${id}`);
      setXmlContent(resp.data.xml);
    } catch (err) { console.error(err); }
  };

  const assignHod = async (id, hod) => {
    try {
      // In parity with Streamlit, we update status to Pending when assigned
      setInvoices(invoices.map(inv => inv.id === id ? { ...inv, assigned_hod: hod, status: 'Pending' } : inv));
    } catch (err) { console.error(err); }
  };

  // --- SUB-RENDERERS ---
  const renderOverview = () => (
    <div className="tab-pane">
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '24px', marginBottom: '40px' }}>
        {[
          { label: 'Ingested Documents', val: invoices.length, icon: FileText, color: 'var(--ios-teal)' },
          { label: 'Pending Audit', val: (Array.isArray(invoices) ? invoices : []).filter(i => i.status === 'Uploaded' || i.status === 'Pending').length, icon: Clock, color: '#FF9500' },
          { label: 'Verified Integrity', val: '100%', icon: CheckCircle, color: '#34C759' },
          { label: 'Total Ascribed Revenue', val: `₹${(Array.isArray(invoices) ? invoices : []).reduce((acc, i) => acc + (parseFloat(i.total) || 0), 0).toLocaleString()}`, icon: DollarSign, color: 'var(--ios-cyan)' },
        ].map((stat, i) => (
          <div key={i} className="glass squircle" style={{ padding: '24px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '16px' }}>
              <div style={{ padding: '8px', borderRadius: '10px', background: `${stat.color}15`, color: stat.color }}>
                <stat.icon size={18} />
              </div>
              <span style={{ color: 'var(--ios-secondary-label)', fontSize: '14px', fontWeight: '500' }}>{stat.label}</span>
            </div>
            <h2 style={{ fontSize: '28px' }}>{stat.val}</h2>
          </div>
        ))}
      </div>

      <div className="glass squircle" style={{ padding: '24px', marginBottom: '40px' }}>
        <h3 style={{ marginBottom: '20px' }}>Revenue Ingestion Console</h3>
        <div style={{ display: 'flex', gap: '20px', marginBottom: '20px' }}>
          {['Manual', 'Local Scan', 'Email Sync'].map(mode => (
            <div 
              key={mode} 
              onClick={() => setIngestionMode(mode)}
              style={{ 
                padding: '8px 16px', borderRadius: '100px', cursor: 'pointer',
                background: ingestionMode === mode ? 'var(--ios-teal)' : 'rgba(0,0,0,0.05)',
                color: ingestionMode === mode ? 'white' : 'var(--ios-secondary-label)',
                fontSize: '13px', fontWeight: '600'
              }}
            >{mode}</div>
          ))}
        </div>
        
        {ingestionMode === 'Manual' && (
          <div style={{ border: '2px dashed #E2E8F0', borderRadius: '16px', padding: '40px', textAlign: 'center' }}>
            <Upload size={40} color="var(--ios-secondary-label)" style={{ marginBottom: '16px' }} />
            <p style={{ color: 'var(--ios-secondary-label)', marginBottom: '20px' }}>Select multiple AP invoices for AI Omni-Vision synthesis</p>
            <label className="ios-button" style={{ cursor: 'pointer', display: 'inline-flex', alignItems: 'center', gap: '8px' }}>
              <Plus size={20} />
              <span>Ingest Invoices</span>
              <input type="file" multiple hidden onChange={handleUpload} />
            </label>
          </div>
        )}
        {ingestionMode === 'Local Scan' && (
          <div style={{ padding: '20px', background: 'rgba(0,0,0,0.02)', borderRadius: '12px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div>
              <p style={{ fontWeight: '600' }}>Network Folder Monitor</p>
              <p style={{ fontSize: '13px', color: 'var(--ios-secondary-label)' }}>Watching: data/local_import</p>
            </div>
            <button className="ios-button" onClick={syncLocal}>Trigger Bulk Ingestion</button>
          </div>
        )}
        {ingestionMode === 'Email Sync' && (
          <div style={{ padding: '20px', background: 'rgba(0,0,0,0.02)', borderRadius: '12px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div>
              <p style={{ fontWeight: '600' }}>Outlook Synchronizer</p>
              <p style={{ fontSize: '13px', color: 'var(--ios-secondary-label)' }}>Monitoring attachments on: {config.email}</p>
            </div>
            <button className="ios-button" onClick={syncEmail}>Sync Now</button>
          </div>
        )}
      </div>

      <VerificationTable invoices={(Array.isArray(invoices) ? invoices : []).filter(i => i.status === 'Uploaded')} />

      <InvoiceRegistry 
        invoices={invoices} 
        onSelect={setSelectedInvoice} 
        onClear={clearRegistry}
        onDelete={deleteInvoice}
      />
    </div>
  );

  const VerificationTable = ({ invoices }) => (
    <div className="glass squircle" style={{ padding: '24px', marginBottom: '40px' }}>
      <h3 style={{ marginBottom: '20px' }}>Review & Verify Extraction</h3>
      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid var(--ios-border)', color: 'var(--ios-secondary-label)', fontSize: '11px' }}>
              <th style={{ padding: '12px' }}>FILENAME</th>
              <th style={{ padding: '12px' }}>VENDOR</th>
              <th style={{ padding: '12px' }}>GSTIN</th>
              <th style={{ padding: '12px' }}>DATE</th>
              <th style={{ padding: '12px' }}>AMOUNT</th>
              <th style={{ padding: '12px' }}>HEALTH</th>
            </tr>
          </thead>
          <tbody>
            {invoices.map((inv) => {
              const hasVendor = inv.vendor && inv.vendor !== 'Unknown';
              const hasGst = inv.vendor_gst && inv.vendor_gst !== 'N/A';
              const hasDate = inv.date && inv.date !== 'N/A';
              const hasAmount = parseFloat(inv.total) > 0;
              const taxMatch = Math.abs((parseFloat(inv.raw_data?.subtotal) || 0) + (parseFloat(inv.raw_data?.total_tax) || 0) - (parseFloat(inv.total) || 0)) < 1;
              
              const renderValue = (val, ok) => (
                <span style={{ color: ok ? 'inherit' : '#FF9500', fontWeight: ok ? '500' : 'bold' }}>
                  {val || 'N/A'}
                </span>
              );

              return (
                <tr key={inv.id} style={{ borderBottom: '1px solid var(--ios-border)', fontSize: '12px' }}>
                  <td style={{ padding: '12px', whiteSpace: 'nowrap', fontWeight: 'bold' }}>{inv.filename}</td>
                  <td style={{ padding: '12px' }}>{renderValue(inv.vendor, hasVendor)}</td>
                  <td style={{ padding: '12px', fontFamily: 'monospace' }}>{renderValue(inv.vendor_gst, hasGst)}</td>
                  <td style={{ padding: '12px' }}>{renderValue(inv.date, hasDate)}</td>
                  <td style={{ padding: '12px', fontWeight: 'bold' }}>{renderValue(`₹${parseFloat(inv.total).toLocaleString()}`, hasAmount)}</td>
                  <td style={{ padding: '12px' }}>
                    <span style={{ fontSize: '10px', background: taxMatch && hasVendor ? '#34C75920' : '#FF950020', color: taxMatch && hasVendor ? '#34C759' : '#FF9500', padding: '2px 8px', borderRadius: '4px', fontWeight: 'bold' }}>
                      {taxMatch && hasVendor ? 'VERIFIED' : 'REVIEW'}
                    </span>
                  </td>
                </tr>
              );
            })}
            {invoices.length === 0 && (
              <tr><td colSpan="7" style={{ textAlign: 'center', padding: '40px', color: 'var(--ios-secondary-label)' }}>No documents in queue.</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );

  const [hodFilter, setHodFilter] = useState('All');

  const renderAudit = () => (
    <div className="tab-pane">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '25px' }}>
        <h3>Auditor Workspace</h3>
        <select 
          className="glass"
          style={{ padding: '10px 20px', borderRadius: '12px', border: '1px solid var(--ios-border)' }}
          value={hodFilter}
          onChange={(e) => setHodFilter(e.target.value)}
        >
          <option value="All">All Auditors</option>
          <option value="HOD 1">HOD 1</option>
          <option value="HOD 2">HOD 2</option>
          <option value="HOD 3">HOD 3</option>
        </select>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(360px, 1fr))', gap: '24px' }}>
        {invoices.filter(i => (i.status === 'Pending' || i.status === 'Uploaded') && (hodFilter === 'All' || i.assigned_hod === hodFilter)).map(inv => (
          <div key={inv.id} className="glass squircle" style={{ padding: '24px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '20px' }}>
               <div>
                  <h4 style={{ fontSize: '18px' }}>{inv.vendor}</h4>
                  <p style={{ color: 'var(--ios-secondary-label)', fontSize: '13px' }}>INV: {inv.invoice_no}</p>
               </div>
               <div style={{ textAlign: 'right' }}>
                  <h4 style={{ color: 'var(--ios-teal)' }}>₹{parseFloat(inv.total).toLocaleString()}</h4>
                  <p style={{ fontSize: '11px', color: 'var(--ios-secondary-label)' }}>HOD: {inv.assigned_hod}</p>
               </div>
            </div>
            <div style={{ display: 'flex', gap: '10px' }}>
              <button className="ios-button" style={{ flex: 1 }} onClick={() => approveInvoice(inv.id)}>Approve</button>
              <button className="ios-secondary-button" style={{ flex: 1, border: '1px solid #FF3B30', color: '#FF3B30' }} onClick={() => rejectInvoice(inv.id)}>Reject</button>
            </div>
            <button 
              onClick={() => setSelectedInvoice(inv)}
              style={{ width: '100%', marginTop: '10px', background: 'transparent', border: 'none', color: 'var(--ios-secondary-label)', fontSize: '12px', cursor: 'pointer' }}
            >Deep Audit Details</button>
          </div>
        ))}
        {invoices.filter(i => (i.status === 'Pending' || i.status === 'Uploaded') && (hodFilter === 'All' || i.assigned_hod === hodFilter)).length === 0 && <p style={{ color: 'var(--ios-secondary-label)' }}>No pending audits for this selection.</p>}
      </div>
    </div>
  );

  const renderPayments = () => (
    <div className="tab-pane">
      <h3 style={{ marginBottom: '25px' }}>Approved Disbursement Queue</h3>
      <div className="glass squircle" style={{ padding: '20px' }}>
        {invoices.filter(i => i.status === 'Approved').map(inv => (
          <div key={inv.id} style={{ display: 'flex', alignItems: 'center', padding: '16px', borderBottom: '1px solid var(--ios-border)' }}>
             <div style={{ flex: 2 }}>
                <div style={{ fontWeight: '600' }}>{inv.vendor}</div>
                <div style={{ fontSize: '12px' }}>Voucher Ref: {inv.invoice_no}</div>
             </div>
             <div style={{ flex: 1, fontWeight: 'bold', color: 'var(--ios-teal)' }}>₹{parseFloat(inv.total).toLocaleString()}</div>
             <div style={{ flex: 1, fontSize: '12px', color: 'var(--ios-secondary-label)' }}>{inv.assigned_hod} Approved</div>
             <div style={{ flex: 1, textAlign: 'right' }}>
                <button className="ios-button" onClick={() => payInvoice(inv.id)}>Execute Payment</button>
             </div>
          </div>
        ))}
        {invoices.filter(i => i.status === 'Approved').length === 0 && <p style={{ textAlign: 'center', padding: '40px', color: 'var(--ios-secondary-label)' }}>Queue empty. Synchronize with Audit Hub.</p>}
      </div>
    </div>
  );

  const renderExports = () => (
    <div className="tab-pane">
       <h3 style={{ marginBottom: '25px' }}>Accounting Statements & Reconciliation</h3>
       <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px', marginBottom: '40px' }}>
          <div className="glass squircle" style={{ padding: '30px' }}>
              <div style={{ marginBottom: '20px', color: 'var(--ios-teal)' }}><FileText size={40} /></div>
              <h4>Consolidated Excel Statement</h4>
              <p style={{ color: 'var(--ios-secondary-label)', fontSize: '14px', margin: '10px 0 20px' }}>Generate a complete ledger report of all processed AP activities for your accounting team.</p>
              <button className="ios-button" onClick={downloadExcel}>Download Statement (.xlsx)</button>
          </div>
          <div className="glass squircle" style={{ padding: '30px' }}>
              <div style={{ marginBottom: '20px', color: 'var(--ios-teal)' }}><Inbox size={40} /></div>
              <h4>Full Documentation Bundle</h4>
              <p style={{ color: 'var(--ios-secondary-label)', fontSize: '14px', margin: '10px 0 20px' }}>Archive all processed invoice documents into a single high-fidelity ZIP package.</p>
              <button className="ios-button" onClick={downloadZip}>Download Archive (.zip)</button>
          </div>
       </div>

       <div className="glass squircle" style={{ padding: '24px' }}>
          <h4 style={{ marginBottom: '20px' }}>Tally ERP / SAP XML Generation</h4>
          <p style={{ color: 'var(--ios-secondary-label)', fontSize: '13px', marginBottom: '20px' }}>Select an approved invoice to generate the Purchase Voucher XML for ERP import.</p>
          <div style={{ maxHeight: '300px', overflowY: 'auto' }}>
            {invoices.filter(i => i.status === 'Approved' || i.status === 'Paid').map(inv => (
              <div key={inv.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '12px', borderBottom: '1px solid var(--ios-border)' }}>
                <span>{inv.vendor} - {inv.invoice_no}</span>
                <button className="ios-secondary-button" style={{ padding: '6px 12px', fontSize: '12px' }} onClick={() => generateXml(inv.id)}>View XML</button>
              </div>
            ))}
          </div>
       </div>

       <AnimatePresence>
          {xmlContent && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} 
              style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(0,0,0,0.5)', zIndex: 1000, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
               <div className="glass squircle" style={{ background: 'white', width: '80%', height: '80%', padding: '40px', display: 'flex', flexDirection: 'column' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '20px' }}>
                    <h3>XML Purchase Voucher</h3>
                    <button onClick={() => setXmlContent(null)} className="ios-secondary-button">Close</button>
                  </div>
                  <pre style={{ flex: 1, background: '#F2F2F7', padding: '20px', borderRadius: '12px', overflow: 'auto', fontSize: '12px', fontFamily: 'monospace' }}>
                    {xmlContent}
                  </pre>
                  <button className="ios-button" style={{ marginTop: '20px' }} onClick={() => { navigator.clipboard.writeText(xmlContent); showToast("XML copied to clipboard"); }}>Copy to Clipboard</button>
               </div>
            </motion.div>
          )}
       </AnimatePresence>

       {/* Toast System */}
       <AnimatePresence>
          {toast && (
            <motion.div 
              initial={{ opacity: 0, y: 50, scale: 0.9 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, scale: 0.9 }}
              style={{
                position: 'fixed', bottom: '40px', left: '50%', transform: 'translateX(-50%)',
                background: toast.type === 'error' ? '#FF3B30' : 'rgba(0,0,0,0.8)',
                color: 'white', padding: '12px 24px', borderRadius: '100px',
                backdropFilter: 'blur(10px)', zIndex: 3000, display: 'flex', alignItems: 'center', gap: '10px',
                boxShadow: '0 8px 32px rgba(0,0,0,0.2)', pointerEvents: 'none', fontSize: '14px', fontWeight: '500'
              }}
            >
              {toast.type === 'error' ? <AlertTriangle size={18} /> : <CheckCircle size={18} color="#34C759" />}
              {toast.message}
            </motion.div>
          )}
       </AnimatePresence>
    </div>
  );

  const renderSettings = () => (
    <div className="tab-pane" style={{ maxWidth: '600px' }}>
       <h3 style={{ marginBottom: '25px' }}>System Configuration</h3>
       <div className="glass squircle" style={{ padding: '32px', display: 'flex', flexDirection: 'column', gap: '24px' }}>
          <div>
            <label style={{ display: 'block', fontSize: '12px', color: 'var(--ios-secondary-label)', marginBottom: '8px', fontWeight: 'bold' }}>GROQ API KEY</label>
            <input 
              type="password" 
              className="glass" 
              style={{ width: '100%', padding: '14px', borderRadius: '12px', border: '1px solid var(--ios-border)' }} 
              value={config.groq_key}
              onChange={e => setConfig({...config, groq_key: e.target.value})}
            />
          </div>
          <div>
            <label style={{ display: 'block', fontSize: '12px', color: 'var(--ios-secondary-label)', marginBottom: '8px', fontWeight: 'bold' }}>OUTLOOK EMAIL</label>
            <input 
              type="text" 
              className="glass" 
              style={{ width: '100%', padding: '14px', borderRadius: '12px', border: '1px solid var(--ios-border)' }} 
              value={config.email}
              onChange={e => setConfig({...config, email: e.target.value})}
            />
          </div>
          <button className="ios-button" onClick={saveConfig} style={{ marginTop: '10px' }}>Save Changes</button>
       </div>
    </div>
  );

  return (
    <div style={{ display: 'flex', height: '100vh', width: '100vw', overflow: 'hidden' }}>
      {/* iOS Sidebar */}
      <div className="glass" style={{ width: '280px', height: '100%', padding: '40px 20px', display: 'flex', flexDirection: 'column', zIndex: 10 }}>
        <div style={{ padding: '0 20px 40px', textAlign: 'center' }}>
          <h2 style={{ color: 'var(--ios-teal)', fontSize: '24px' }}>Infinx</h2>
          <span style={{ fontSize: '12px', color: 'var(--ios-cyan)', letterSpacing: '2px', fontWeight: 'bold' }}>AP TRACKER</span>
        </div>

        <nav style={{ flex: 1 }}>
          {[
            { name: 'Overview', icon: LayoutDashboard },
            { name: 'Audit Hub', icon: ShieldCheck },
            { name: 'Payments', icon: DollarSign },
            { name: 'Exports', icon: Download },
            { name: 'Settings', icon: Settings },
          ].map((tab) => (
            <div 
              key={tab.name}
              onClick={() => setActiveTab(tab.name)}
              style={{ 
                padding: '14px 20px', borderRadius: '14px', display: 'flex', alignItems: 'center', gap: '12px',
                cursor: 'pointer', marginBottom: '8px',
                background: activeTab === tab.name ? 'rgba(0, 90, 100, 0.1)' : 'transparent',
                color: activeTab === tab.name ? 'var(--ios-teal)' : 'var(--ios-secondary-label)',
                transition: 'all 0.3s'
              }}
            >
              <tab.icon size={20} />
              <span style={{ fontWeight: activeTab === tab.name ? '600' : '500' }}>{tab.name}</span>
            </div>
          ))}
        </nav>
      </div>

      {/* Main Content Area */}
      <main style={{ flex: 1, padding: '40px 60px', overflowY: 'auto', position: 'relative' }}>
        <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '40px' }}>
          <div>
            <h1 style={{ fontSize: '34px', marginBottom: '8px' }}>{activeTab === 'Overview' ? 'AP Overview' : activeTab}</h1>
            <p style={{ color: 'var(--ios-secondary-label)' }}>Managed Revenue Ingestion OS</p>
          </div>
          <div style={{ display: 'flex', gap: '12px' }}>
             <label className="ios-button" style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}>
               <Plus size={20} />
               <span>Ingest Invoices</span>
               <input type="file" multiple hidden onChange={handleUpload} />
             </label>
             <button className="ios-secondary-button" onClick={fetchInvoices}><RefreshCw size={18} /></button>
          </div>
        </header>

        <AnimatePresence mode="wait">
          <motion.div 
            key={activeTab}
            initial={{ opacity: 0, x: 10 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -10 }}
            transition={{ duration: 0.2 }}
          >
            {activeTab === 'Overview' && renderOverview()}
            {activeTab === 'Audit Hub' && renderAudit()}
            {activeTab === 'Payments' && renderPayments()}
            {activeTab === 'Exports' && renderExports()}
            {activeTab === 'Settings' && renderSettings()}
          </motion.div>
        </AnimatePresence>

        {/* Loading Overlay */}
        <AnimatePresence>
          {(loading || extracting) && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} style={{
                position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
                background: 'rgba(255,255,255,0.85)', backdropFilter: 'blur(20px)',
                display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
                zIndex: 2000
              }}>
              <div style={{ position: 'relative', width: '80px', height: '80px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <motion.div 
                  animate={{ rotate: 360 }} 
                  transition={{ repeat: Infinity, duration: 1.5, ease: 'linear' }}
                  style={{ position: 'absolute', width: '100%', height: '100%', border: '4px solid var(--ios-border)', borderTop: '4px solid var(--ios-teal)', borderRadius: '50%' }}
                />
                <motion.div 
                  animate={{ scale: [1, 1.2, 1] }} 
                  transition={{ repeat: Infinity, duration: 2 }}
                >
                  <FileText size={32} color="var(--ios-teal)" />
                </motion.div>
              </div>
              <h3 style={{ marginTop: '30px', color: 'var(--ios-teal)', letterSpacing: '0.5px' }}>
                {extracting ? 'AI synthesis in progress...' : 'Syncing with Server...'}
              </h3>
              <p style={{ marginTop: '10px', color: 'var(--ios-secondary-label)', fontSize: '14px' }}>
                {extracting ? 'Our Omni-Vision models are itemizing your documents.' : 'Please wait a moment.'}
              </p>
            </motion.div>
          )}
        </AnimatePresence>

        <DetailModal 
          invoice={selectedInvoice} 
          onClose={() => setSelectedInvoice(null)} 
          onApprove={() => approveInvoice(selectedInvoice.id)} 
          onReject={() => rejectInvoice(selectedInvoice.id)} 
          onPay={() => payInvoice(selectedInvoice.id)} 
          onAssign={assignHod}
          onDelete={(id) => {
            setSelectedInvoice(null);
            fetchInvoices();
          }}
        />
      </main>
    </div>
  );
};

const InvoiceRegistry = ({ invoices, onSelect, onClear, onDelete }) => {
  const [search, setSearch] = useState('');
  const filtered = (invoices || []).filter(inv => {
    const v = (inv.vendor || '').toLowerCase();
    const n = (inv.invoice_no || '').toLowerCase();
    const p = (inv.po_number || '').toLowerCase();
    const s = search.toLowerCase();
    return v.includes(s) || n.includes(s) || p.includes(s);
  });

  return (
    <div className="glass squircle" style={{ padding: '24px', minHeight: '400px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '20px' }}>
          <h3>Unified Registry</h3>
          <button 
            onClick={onClear}
            style={{ 
              background: 'transparent', border: '1px solid #FF3B30', color: '#FF3B30', 
              fontSize: '11px', padding: '4px 12px', borderRadius: '100px', cursor: 'pointer',
              fontWeight: '600', opacity: 0.7
            }}
          >Clear Registry</button>
        </div>
        <div style={{ background: 'rgba(0,0,0,0.03)', padding: '8px 16px', borderRadius: '10px', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Search size={16} color="var(--ios-secondary-label)" />
          <input 
            type="text" 
            placeholder="Search vendor, INV, or PO..." 
            style={{ border: 'none', background: 'transparent', outline: 'none', fontSize: '14px' }} 
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
      </div>
      <div style={{ width: '100%' }}>
        <div style={{ display: 'flex', color: 'var(--ios-secondary-label)', fontSize: '12px', padding: '12px 20px', fontWeight: '600', textTransform: 'uppercase', letterSpacing: '1px' }}>
          <div style={{ flex: 2 }}>Vendor / Invoice</div>
          <div style={{ flex: 1 }}>PO Number</div>
          <div style={{ flex: 1 }}>Amount</div>
          <div style={{ flex: 1 }}>Status</div>
          <div style={{ width: '60px' }}></div>
        </div>
        {filtered.map((inv) => (
          <div key={inv.id} onClick={() => onSelect(inv)} style={{ display: 'flex', alignItems: 'center', padding: '16px 20px', borderTop: '1px solid var(--ios-border)', cursor: 'pointer' }}>
            <div style={{ flex: 2 }}>
              <div style={{ fontWeight: '600' }}>{inv.vendor}</div>
              <div style={{ fontSize: '12px', color: 'var(--ios-secondary-label)' }}>{inv.invoice_no}</div>
            </div>
            <div style={{ flex: 1 }}><span style={{ padding: '4px 10px', borderRadius: '100px', background: 'rgba(0, 90, 100, 0.05)', color: 'var(--ios-teal)', fontSize: '12px', fontWeight: '600' }}>{inv.po_number}</span></div>
            <div style={{ flex: 1, fontWeight: '600' }}>₹{parseFloat(inv.total || 0).toLocaleString()}</div>
            <div style={{ flex: 1 }}>
              <span style={{ 
                fontSize: '12px', fontWeight: 'bold', 
                color: inv.status === 'Approved' ? '#34C759' : 
                       inv.status === 'Paid' ? 'var(--ios-teal)' : 
                       inv.status === 'Processing' ? 'var(--ios-cyan)' :
                       inv.status === 'Failed' ? '#FF3B30' : '#FF9500' 
              }}>
                {inv.status === 'Processing' ? (
                  <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <RefreshCw size={12} className="spin" /> Processing
                  </span>
                ) : (
                  <>● {inv.status}</>
                )}
              </span>
            </div>
            <div style={{ width: '60px', display: 'flex', gap: '8px', alignItems: 'center', color: 'var(--ios-secondary-label)' }}>
              <button 
                onClick={(e) => onDelete(e, inv.id)} 
                style={{ background: 'transparent', border: 'none', color: '#FF3B30', cursor: 'pointer', padding: '4px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}
              >
                <Trash2 size={16} />
              </button>
              <ChevronRight size={18} />
            </div>
          </div>
        ))}
        {filtered.length === 0 && <p style={{ textAlign: 'center', padding: '100px', color: 'var(--ios-secondary-label)' }}>No matching results.</p>}
      </div>
    </div>
  );
};

const DetailModal = ({ invoice, onClose, onApprove, onReject, onPay, onAssign, onDelete }) => (
  <AnimatePresence>
    {invoice && (
      <motion.div initial={{ y: '100%' }} animate={{ y: 0 }} exit={{ y: '100%' }} transition={{ type: 'spring', damping: 25, stiffness: 200 }}
        style={{ position: 'fixed', bottom: 0, left: 0, right: 0, height: '90%', background: 'white', borderTopLeftRadius: '32px', borderTopRightRadius: '32px', boxShadow: '0 -10px 40px rgba(0,0,0,0.1)', padding: '40px 60px', zIndex: 200, overflowY: 'auto' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '40px' }}>
          <div>
            <h1 style={{ fontSize: '38px' }}>{invoice.vendor}</h1>
            <span style={{ color: 'var(--ios-secondary-label)' }}>INV #{invoice.invoice_no} | PO #{invoice.po_number || 'N/A'}</span>
          </div>
          <button onClick={onClose} style={{ background: 'rgba(0,0,0,0.05)', border: 'none', padding: '10px 24px', borderRadius: '100px', cursor: 'pointer', fontWeight: 'bold' }}>Close</button>
        </div>
        
        {invoice.raw_data?._validation_warnings?.length > 0 && (
          <div style={{ padding: '16px', borderRadius: '14px', background: '#FFF2F2', border: '1px solid #FFCDCD', color: '#B91C1C', marginBottom: '30px', display: 'flex', gap: '12px', alignItems: 'center' }}>
            <AlertTriangle size={20} />
            <div>
              <p style={{ fontWeight: 'bold', fontSize: '14px' }}>Validation Attention Required</p>
              <p style={{ fontSize: '13px' }}>{invoice.raw_data._validation_warnings.join(', ')}</p>
            </div>
          </div>
        )}

        <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '60px' }}>
          <div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '40px', marginBottom: '60px' }}>
               <div>
                  <h4 className="meta-label">Audit Control</h4>
                  <div style={{ padding: '16px', background: '#F2F2F7', borderRadius: '12px' }}>
                    <p style={{ fontSize: '13px' }}>Status: <b style={{ color: 'var(--ios-teal)' }}>{invoice.status.toUpperCase()}</b></p>
                    <p style={{ fontSize: '13px', color: 'var(--ios-secondary-label)' }}>HOD: {invoice.assigned_hod || 'Unassigned'}</p>
                    <p style={{ fontSize: '13px', color: 'var(--ios-secondary-label)' }}>Processed: {invoice.processed_at}</p>
                  </div>
               </div>
               <div>
                  <h4 className="meta-label">Tax Identities</h4>
                  <p style={{ fontSize: '20px', fontWeight: 'bold', color: 'var(--ios-teal)' }}>{invoice.vendor_gst}</p>
                  <p style={{ fontSize: '12px', color: 'var(--ios-secondary-label)' }}>Vendor Adr: {invoice.raw_data.vendor_address}</p>
                  <div style={{ marginTop: '10px', fontSize: '11px', color: 'var(--ios-secondary-label)' }}>
                    Customer GST: {invoice.raw_data.customer_tax_id || 'N/A'}
                  </div>
               </div>
            </div>
            
            <h3 style={{ marginBottom: '20px' }}>Financial Itemization</h3>
            <div className="glass squircle" style={{ overflow: 'hidden', border: '1px solid var(--ios-border)', marginBottom: '40px' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead style={{ background: 'rgba(0,0,0,0.02)', textAlign: 'left' }}>
                  <tr>
                    <th style={{ padding: '15px 20px', fontSize: '12px', color: 'var(--ios-secondary-label)' }}>DESCRIPTION</th>
                    <th style={{ padding: '15px 20px', fontSize: '12px', color: 'var(--ios-secondary-label)', textAlign: 'right' }}>BASE AMOUNT</th>
                  </tr>
                </thead>
                <tbody>
                  {invoice.raw_data.line_items?.map((item, idx) => (
                    <tr key={idx} style={{ borderBottom: '1px solid var(--ios-border)' }}>
                      <td style={{ padding: '15px 20px', fontSize: '14px' }}>{item.description}</td>
                      <td style={{ padding: '15px 20px', textAlign: 'right', fontWeight: 'bold' }}>₹{parseFloat(item.amount || 0).toLocaleString()}</td>
                    </tr>
                  ))}
                  {(!invoice.raw_data.line_items || invoice.raw_data.line_items.length === 0) && (
                    <tr><td colSpan="2" style={{ padding: '20px', textAlign: 'center', color: 'var(--ios-secondary-label)' }}>No line items detected</td></tr>
                  )}
                </tbody>
              </table>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '16px', marginBottom: '40px' }}>
               {[
                 { label: 'CGST', val: invoice.raw_data.cgst_amount },
                 { label: 'SGST', val: invoice.raw_data.sgst_amount },
                 { label: 'IGST', val: invoice.raw_data.igst_amount },
                 { label: 'TOTAL TAX', val: invoice.raw_data.total_tax },
               ].map((tax, i) => (
                 <div key={i} className="glass" style={{ padding: '16px', borderRadius: '12px' }}>
                    <span style={{ fontSize: '11px', color: 'var(--ios-secondary-label)' }}>{tax.label}</span>
                    <div style={{ fontWeight: 'bold' }}>₹{parseFloat(tax.val || 0).toLocaleString()}</div>
                 </div>
               ))}
            </div>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '30px' }}>
              <div className="glass squircle" style={{ padding: '30px', background: 'var(--ios-teal)', color: 'white' }}>
                 <p style={{ fontSize: '14px', opacity: 0.8, marginBottom: '10px' }}>Net Disbursement Value</p>
                 <h1 style={{ color: 'white', fontSize: '44px' }}>₹{parseFloat(invoice.total || 0).toLocaleString()}</h1>
                 <hr style={{ margin: '20px 0', opacity: 0.2 }} />
                 <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13px' }}>
                    <span>Subtotal</span>
                    <span>₹{parseFloat(invoice.raw_data.subtotal || 0).toLocaleString()}</span>
                 </div>
              </div>

              <div className="glass squircle" style={{ padding: '24px' }}>
                 <p className="meta-label">Payment & Banking</p>
                 <div style={{ display: 'flex', gap: '12px', alignItems: 'center', marginBottom: '16px' }}>
                    <div style={{ padding: '10px', background: 'rgba(0, 90, 100, 0.05)', borderRadius: '10px', color: 'var(--ios-teal)' }}><DollarSign size={20} /></div>
                    <div style={{ flex: 1 }}>
                      <div style={{ fontSize: '13px', fontWeight: 'bold' }}>{invoice.raw_data.bank_details || 'N/A'}</div>
                      <div style={{ fontSize: '11px', color: 'var(--ios-secondary-label)' }}>UPI ID: {invoice.raw_data.upi_id || 'N/A'}</div>
                    </div>
                 </div>
                 {invoice.raw_data.vehicle_number && (
                   <div style={{ fontSize: '12px', padding: '8px 12px', background: '#F2F2F7', borderRadius: '8px', color: 'var(--ios-teal)', fontWeight: '600' }}>
                     🚛 Vehicle: {invoice.raw_data.vehicle_number}
                   </div>
                 )}
              </div>

              <div className="glass squircle" style={{ padding: '24px' }}>
                 <p className="meta-label">Internal Controls</p>
                 {invoice.status === 'Uploaded' && (
                   <div style={{ marginBottom: '20px' }}>
                      <label style={{ fontSize: '11px', display: 'block', marginBottom: '8px' }}>Assign for HOD Approval</label>
                      <select 
                        className="glass"
                        style={{ width: '100%', padding: '12px', borderRadius: '10px', border: '1px solid var(--ios-border)' }}
                        value={invoice.assigned_hod || ''}
                        onChange={(e) => onAssign(invoice.id, e.target.value)}
                      >
                        <option value="">Select Auditor</option>
                        <option value="HOD 1">Global Head (HOD 1)</option>
                        <option value="HOD 2">Finance Lead (HOD 2)</option>
                        <option value="HOD 3">Operations Dir (HOD 3)</option>
                      </select>
                   </div>
                 )}
                 <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                  {invoice.status === 'Pending' && (
                    <>
                    <button className="ios-button" onClick={onApprove} style={{ height: '56px' }}>Approve Voucher</button>
                    <button className="ios-secondary-button" onClick={onReject} style={{ height: '56px', borderColor: '#FF3B30', color: '#FF3B30' }}>Return for Correction</button>
                    <button 
                      className="ios-secondary-button" 
                      onClick={async () => {
                        if(window.confirm("Purge this document?")) {
                          try {
                            await axios.delete(`/api/invoices/${invoice.id}`);
                            onDelete(invoice.id);
                          } catch (err) { console.error(err); }
                        }
                      }}
                      style={{ height: '40px', marginTop: '10px', fontSize: '12px', borderColor: '#FF3B30', color: '#FF3B30', opacity: 0.6 }}
                    >
                      Permanent Delete
                    </button>
                    </>
                  )}
                  {invoice.status === 'Approved' && (
                    <button className="ios-button" onClick={onPay} style={{ height: '56px' }}>Execute Payment</button>
                  )}
                  {invoice.status === 'Paid' && (
                    <div style={{ textAlign: 'center', padding: '20px', color: '#34C759', fontWeight: 'bold' }}>
                      <CheckCircle size={32} style={{ margin: '0 auto 10px' }} />
                      <p>Payment Completed</p>
                    </div>
                  )}
                </div>
              </div>
          </div>
        </div>
      </motion.div>
    )}
  </AnimatePresence>
);

export default App;
