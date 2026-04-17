import { useState, useEffect, useRef, useCallback } from 'react';

const API = 'http://localhost:5000';

function initials(name) {
  if (name === 'Unknown') return '?';
  return name.split(' ').map(w => w[0]).join('').slice(0, 2).toUpperCase();
}
function avgConf(entries) {
  if (!entries.length) return 0;
  return entries.reduce((s, e) => s + e.confidence, 0) / entries.length;
}
let _tid = 0;

export default function App() {
  const [view, setView]         = useState('upload');
  const [albums, setAlbums]     = useState(null);
  const [boxed, setBoxed]       = useState([]);
  const [files, setFiles]       = useState([]);
  const [previews, setPreviews] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(null);
  const [persons, setPersons]   = useState([]);
  const [toasts, setToasts]     = useState([]);
  const [isDragging, setIsDragging] = useState(false);
  const [addName, setAddName]   = useState('');
  const [addImg, setAddImg]     = useState('');
  const [thresh, setThresh]     = useState(0.8);
  const [margin, setMargin]     = useState(0.05);
  const [editingPerson, setEditingPerson] = useState(null);
  const [editName, setEditName] = useState('');
  const fileRef = useRef();

  const toast = useCallback((msg, type = 'success') => {
    const id = ++_tid;
    setToasts(t => [...t, { id, msg, type }]);
    setTimeout(() => setToasts(t => t.filter(x => x.id !== id)), 4000);
  }, []);

  useEffect(() => {
    fetch(`${API}/`, { credentials: 'include' })
      .then(r => r.json())
      .then(d => {
        if (d.has_session) {
          setAlbums(d.albums);
          setBoxed(d.boxed_images || []);
          setView('result');
        }
      }).catch(() => {});
    fetchPersons();
  }, []);

  function fetchPersons() {
    fetch(`${API}/persons`).then(r => r.json()).then(d => setPersons(d.persons || [])).catch(() => {});
  }

  function addFiles(newFiles) {
    const arr = Array.from(newFiles);
    setFiles(f => [...f, ...arr]);
    arr.forEach(f => {
      const reader = new FileReader();
      reader.onload = e => setPreviews(p => [...p, e.target.result]);
      reader.readAsDataURL(f);
    });
  }

  const onDrop = useCallback(e => {
    e.preventDefault(); setIsDragging(false);
    addFiles(e.dataTransfer.files);
  }, []);

  async function handleUpload(e) {
    e.preventDefault();
    if (!files.length) return;
    setUploading(true); setAlbums(null); setBoxed([]);
    setProgress({ step: 0, total: files.length, file: '', done: [] });
    const form = new FormData();
    files.forEach(f => form.append('images', f));
    try {
      const res = await fetch(`${API}/upload_stream`, { method: 'POST', body: form, credentials: 'include' });
      const reader = res.body.getReader();
      const dec = new TextDecoder();
      let buf = '';
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buf += dec.decode(value, { stream: true });
        const chunks = buf.split('\n\n'); buf = chunks.pop();
        for (const chunk of chunks) {
          if (!chunk.startsWith('data:')) continue;
          const ev = JSON.parse(chunk.slice(5));
          if (ev.type === 'progress') setProgress(p => ({ ...p, step: ev.step, total: ev.total, file: ev.file }));
          if (ev.type === 'file_done') setProgress(p => ({ ...p, done: [...p.done, ev.file] }));
          if (ev.type === 'done') {
            setAlbums(ev.albums); setBoxed(ev.boxed_images || []);
            setView('result'); fetchPersons();
            toast(`Scan complete — ${Object.keys(ev.albums).length} identit${Object.keys(ev.albums).length === 1 ? 'y' : 'ies'} found`);
          }
        }
      }
    } catch (err) { toast('Upload failed: ' + err.message, 'error'); }
    finally { setUploading(false); setProgress(null); }
  }

  async function handleReset() {
    await fetch(`${API}/reset`, { method: 'POST', credentials: 'include' });
    setAlbums(null); setBoxed([]); setFiles([]); setPreviews([]); setView('upload');
    toast('Session cleared');
  }

  async function handleCorrect(e, imagePath) {
    e.preventDefault();
    const name = e.target.elements.name.value.trim();
    if (!name) return;
    const res = await fetch(`${API}/add_person`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      credentials: 'include', body: JSON.stringify({ name, image: imagePath })
    });
    const d = await res.json();
    if (d.success) { toast(d.message); e.target.reset(); fetchPersons(); }
    else toast(d.error, 'error');
  }

  async function handleAddPerson(e) {
    e.preventDefault();
    if (!addName || !addImg) return;
    const res = await fetch(`${API}/add_person`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      credentials: 'include', body: JSON.stringify({ name: addName, image: addImg })
    });
    const d = await res.json();
    if (d.success) { toast(d.message); setAddName(''); setAddImg(''); fetchPersons(); }
    else toast(d.error, 'error');
  }

  async function handleDeletePerson(name) {
    const res = await fetch(`${API}/delete_person`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name })
    });
    const d = await res.json();
    if (d.success) { toast(`Deleted "${name}"`); fetchPersons(); }
    else toast(d.error, 'error');
  }

  async function handleRenamePerson(e, oldName) {
    e.preventDefault();
    const newName = editName.trim().toLowerCase();
    if (!newName || newName === oldName) { setEditingPerson(null); return; }
    const res = await fetch(`${API}/rename_person`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ old_name: oldName, new_name: newName })
    });
    const d = await res.json();
    if (d.success) { toast(`Renamed "${oldName}" → "${newName}"`); fetchPersons(); }
    else toast(d.error, 'error');
    setEditingPerson(null);
  }

  async function saveSettings() {
    await fetch(`${API}/settings`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ confidence_threshold: thresh, margin_threshold: margin })
    });
    toast('Recognition parameters updated');
  }

  const totalFaces = albums ? Object.values(albums).reduce((a, b) => a + b.length, 0) : 0;
  const knownCount = albums ? Object.keys(albums).filter(k => k !== 'Unknown').length : 0;

  return (
    <>
      <div className="bg">
        <div className="orb orb1"/><div className="orb orb2"/><div className="orb orb3"/>
        <div className="grid-lines"/>
      </div>

      <div className="toast-stack">
        {toasts.map(t => (
          <div key={t.id} className={`toast toast-${t.type}`}>
            <span className="toast-icon">{t.type === 'success' ? '✓' : '✕'}</span>
            {t.msg}
          </div>
        ))}
      </div>

      <nav className="topnav">
        <div className="nav-brand"><span className="nav-dot"/>FaceOS</div>
        <div className="nav-links">
          <button className={`nav-link ${view === 'upload' ? 'active' : ''}`} onClick={() => setView('upload')}>Scan</button>
          {albums && <button className={`nav-link ${view === 'result' ? 'active' : ''}`} onClick={() => setView('result')}>Results</button>}
          <button className={`nav-link ${view === 'persons' ? 'active' : ''}`} onClick={() => setView('persons')}>
            Persons {persons.length > 0 && <span className="nav-badge">{persons.length}</span>}
          </button>
        </div>
        {albums && (
          <div className="nav-stats">
            <span className="nav-stat"><span className="ns-val">{totalFaces}</span> faces</span>
            <span className="nav-stat"><span className="ns-val">{knownCount}</span> known</span>
          </div>
        )}
      </nav>

      <div className="page">
        {view === 'upload' && (
          <div className="view-upload">
            <header className="header">
              <div className="badge"><span className="badge-dot"/>AI-Powered</div>
              <h1>Face Recognition</h1>
              <p className="subtitle">Upload images and let the neural engine identify every face with precision.</p>
            </header>

            <div className="card">
              <div className="card-shine"/>
              <form onSubmit={handleUpload}>
                <label
                  className={`dropzone-label${isDragging ? ' active' : ''}`}
                  onClick={() => fileRef.current.click()}
                  onDragOver={e => { e.preventDefault(); setIsDragging(true); }}
                  onDragLeave={() => setIsDragging(false)}
                  onDrop={onDrop}
                >
                  <div className="drop-icon">
                    <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="url(#g1)" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                      <defs><linearGradient id="g1" x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" stopColor="#7efff5"/><stop offset="100%" stopColor="#a78bfa"/></linearGradient></defs>
                      <polyline points="16 16 12 12 8 16"/><line x1="12" y1="12" x2="12" y2="21"/>
                      <path d="M20.39 18.39A5 5 0 0 0 18 9h-1.26A8 8 0 1 0 3 16.3"/>
                    </svg>
                  </div>
                  <p className="drop-title">Drop images here</p>
                  <p className="drop-sub">or <span>browse files</span> from your device</p>
                  <p className="drop-formats">JPG · PNG · HEIC · WEBP</p>
                  <input ref={fileRef} type="file" multiple accept="image/*,.heic"
                    style={{ display:'none' }} onChange={e => addFiles(e.target.files)}/>
                </label>

                {previews.length > 0 && (
                  <div className="preview-strip">
                    {previews.map((src, i) => (
                      <div key={i} className="preview-thumb">
                        <img src={src} alt=""/>
                        <button className="preview-rm" type="button" onClick={e => {
                          e.stopPropagation();
                          setFiles(f => f.filter((_,j)=>j!==i));
                          setPreviews(p => p.filter((_,j)=>j!==i));
                        }}>✕</button>
                      </div>
                    ))}
                  </div>
                )}

                <div className="file-info">
                  <div className={`file-pill${files.length > 0 ? ' visible' : ''}`}>
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
                    {files.length} file{files.length !== 1 ? 's' : ''} selected
                  </div>
                </div>

                {progress && (
                  <div className="progress-block">
                    <div className="progress-header">
                      <span className="progress-label">Processing <em>{progress.file}</em></span>
                      <span className="progress-frac">{progress.step}/{progress.total}</span>
                    </div>
                    <div className="progress-track">
                      <div className="progress-fill" style={{ width:`${(progress.step/progress.total)*100}%` }}/>
                    </div>
                    <div className="progress-chips">
                      {files.map((f,i) => {
                        const done   = progress.done.includes(f.name);
                        const active = progress.file === f.name && !done;
                        return (
                          <span key={i} className={`pchip${done?' done':active?' active':''}`}>
                            {done?'✓ ':active?'◈ ':'○ '}{f.name.slice(0,18)}
                          </span>
                        );
                      })}
                    </div>
                  </div>
                )}

                <div className="divider">
                  <div className="divider-line"/><span className="divider-text">Ready to analyse</span><div className="divider-line"/>
                </div>

                <button type="submit" className="btn" disabled={uploading || !files.length}>
                  <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
                  {uploading ? 'Scanning…' : 'Analyse Faces'}
                </button>
              </form>
            </div>

            <div className="tuning-strip card" style={{ marginTop:20 }}>
              <div className="card-shine"/>
              <p className="tuning-title">Recognition parameters</p>
              <div className="tuning-row">
                <span className="tuning-label">Confidence threshold</span>
                <input type="range" min="0.3" max="1.5" step="0.05" value={thresh} onChange={e=>setThresh(+e.target.value)} className="tuning-range"/>
                <span className="tuning-val">{thresh.toFixed(2)}</span>
              </div>
              <div className="tuning-row">
                <span className="tuning-label">Match margin</span>
                <input type="range" min="0.01" max="0.3" step="0.01" value={margin} onChange={e=>setMargin(+e.target.value)} className="tuning-range"/>
                <span className="tuning-val">{margin.toFixed(2)}</span>
              </div>
              <button className="btn-ghost btn-sm" onClick={saveSettings}>Apply to backend</button>
            </div>
          </div>
        )}

        {view === 'result' && albums && (
          <div className="view-result">
            <div className="header">
              <div className="badge"><span className="badge-dot"/>Recognition Results</div>
              <h1>Face Albums</h1>
              <p className="subtitle">Grouped identities detected across your uploaded images</p>
            </div>
            <div className="top-bar">
              <button className="btn-ghost" onClick={() => setView('upload')}>
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><polyline points="15 18 9 12 15 6"/></svg>
                New Scan
              </button>
              <button className="btn-ghost btn-danger" onClick={handleReset}>
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><polyline points="1 4 1 10 7 10"/><path d="M3.51 15a9 9 0 1 0 .49-3.76"/></svg>
                Reset
              </button>
            </div>

            {boxed.length > 0 && (
              <>
                <div className="section-label">Annotated preview</div>
                <div className="detected-card"><BoxedViewer boxed={boxed}/></div>
                <hr className="section-hr"/>
              </>
            )}

            <div className="section-label">Albums</div>
            {Object.entries(albums).map(([person, images], idx) => (
              <AlbumCard key={person} person={person} images={images} idx={idx}
                onCorrect={handleCorrect}
                onTagAs={() => { setAddImg(images[0]?.image||''); setAddName(person==='Unknown'?'':person); setView('persons'); }}/>
            ))}
          </div>
        )}

        {view === 'persons' && (
          <div className="view-persons">
            <div className="header">
              <div className="badge"><span className="badge-dot"/>Database</div>
              <h1>Persons DB</h1>
              <p className="subtitle">Manage known identities and face embeddings</p>
            </div>

            <div className="card persons-add-card">
              <div className="card-shine"/>
              <p className="persons-add-title">Tag a face</p>
              <form className="persons-add-form" onSubmit={handleAddPerson}>
                <input type="text" placeholder="Person name" value={addName}
                  onChange={e=>setAddName(e.target.value)} className="glass-input"/>
                <input type="text" placeholder="Image filename (e.g. photo.jpg)" value={addImg}
                  onChange={e=>setAddImg(e.target.value)} className="glass-input"/>
                <button type="submit" className="btn btn-sm">Add face</button>
              </form>
            </div>

            <div className="section-label" style={{ marginTop:32 }}>Known persons ({persons.length})</div>

            {persons.length === 0 ? (
              <div className="empty-state">
                <p className="empty-icon">◉</p>
                <p className="empty-title">No persons in database</p>
                <p className="empty-sub">Add faces above to start recognizing people</p>
              </div>
            ) : (
              <div className="persons-list">
                {persons.map(p =>
                  <div key={p.name} className="person-row">
                    <div className="person-avatar">{initials(p.name)}</div>
                    <div className="person-info">
                      {editingPerson === p.name ? (
                        <form onSubmit={e => handleRenamePerson(e, p.name)} style={{display:'flex',gap:6,alignItems:'center'}}>
                          <input
                            autoFocus
                            className="glass-input glass-input-sm"
                            value={editName}
                            onChange={e => setEditName(e.target.value)}
                            placeholder="New name…"
                          />
                          <button type="submit" className="btn-add" title="Save">✓</button>
                          <button type="button" className="btn-ghost btn-sm" onClick={() => setEditingPerson(null)}>✕</button>
                        </form>
                      ) : (
                        <>
                          <span className="person-name">{p.name}</span>
                          <span className="person-meta">{p.face_count} embedding{p.face_count!==1?'s':''}</span>
                        </>
                      )}
                    </div>
                    <div style={{display:'flex',gap:6}}>
                      <button className="btn-ghost btn-sm" title="Rename" onClick={() => { setEditingPerson(p.name); setEditName(p.name); }}>✏️</button>
                      <button className="btn-ghost btn-danger btn-sm" onClick={() => handleDeletePerson(p.name)}>Delete</button>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>

      <p className="footer-note">Images processed locally · <a href="#">Privacy Policy</a></p>
    </>
  );
}

const IMAGES_PER_PAGE = 12;

function AlbumCard({ person, images, idx, onCorrect, onTagAs }) {
  const [page, setPage] = useState(0);
  const isUnknown = person.startsWith('Unknown');
  const avg     = avgConf(images);
  const confPct = isUnknown ? 0 : Math.max(0, Math.min(1, 1 - avg));
  const totalPages  = Math.ceil(images.length / IMAGES_PER_PAGE);
  const pageImages  = images.slice(page * IMAGES_PER_PAGE, (page + 1) * IMAGES_PER_PAGE);

  return (
    <div className="album" style={{ animationDelay:`${idx*0.07}s` }}>
      <div className="album-title">
        <div className="album-icon"><span style={{ fontSize:14 }}>{isUnknown ? '?' : initials(person)}</span></div>
        <span>{person}</span>
        {isUnknown
          ? <span className="pill pill-danger">unidentified</span>
          : <span className="pill pill-accent">{images.length} image{images.length!==1?'s':''}</span>
        }
      </div>
      {!isUnknown && (
        <div className="conf-row">
          <span className="conf-label">avg confidence</span>
          <div className="conf-track"><div className="conf-fill" style={{ width:`${confPct*100}%` }}/></div>
          <span className="conf-val">{(confPct*100).toFixed(0)}%</span>
        </div>
      )}
      <div className="images">
        {pageImages.map((item, iIdx) => (
          <div className="img-item" key={iIdx} style={{ animationDelay:`${iIdx*0.06}s` }}>
            <div className="img-wrapper">
              <img src={`${API}/static/uploads/${encodeURIComponent(item.image)}`} alt={person}/>
              <div className="face-box"/>
            </div>
            <div className="confidence">
              <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>
              {item.confidence.toFixed(3)}
            </div>
            {(isUnknown || item.confidence > 0.6) && (
              <form className="correct-form" onSubmit={e=>onCorrect(e,item.image)}>
                <input type="text" name="name" placeholder="Correct name…" className="glass-input glass-input-sm" required/>
                <button type="submit" className="btn-add">
                  <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
                  Tag
                </button>
              </form>
            )}
          </div>
        ))}
      </div>
      {totalPages > 1 && (
        <div style={{ display:'flex', alignItems:'center', justifyContent:'center', gap:12, marginTop:16 }}>
          <button className="btn-ghost btn-sm" disabled={page === 0} onClick={() => setPage(p => p - 1)}>← Prev</button>
          <span style={{ color:'var(--text-muted)', fontSize:13 }}>{page + 1} / {totalPages}</span>
          <button className="btn-ghost btn-sm" disabled={page >= totalPages - 1} onClick={() => setPage(p => p + 1)}>Next →</button>
        </div>
      )}
      {isUnknown && (
        <button className="btn-ghost btn-sm" style={{ marginTop:16 }} onClick={onTagAs}>
          Tag all as person →
        </button>
      )}
    </div>
  );
}

function BoxedViewer({ boxed }) {
  const [tab, setTab] = useState(0);
  const item = boxed[tab];
  return (
    <div>
      {boxed.length > 1 && (
        <div className="boxed-tabs">
          {boxed.map((b,i) => (
            <button key={i} className={`boxed-tab${tab===i?' active':''}`} onClick={()=>setTab(i)}>
              {b.original.slice(0,22)}
            </button>
          ))}
        </div>
      )}
      {item && (
        <div className="boxed-images">
          <div className="boxed-img-col">
            <span className="boxed-label">Original</span>
            <img src={`${API}/static/uploads/${encodeURIComponent(item.original)}`} />
          </div>
          <div className="boxed-img-col">
            <span className="boxed-label">Detected faces</span>
            <img src={`${API}/static/uploads/${item.boxed}`} alt="annotated"/>
          </div>
        </div>
      )}
    </div>
  );
}
