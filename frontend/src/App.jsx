import React, { useState, useEffect, useRef } from 'react';
import './App.css';

const API_URL = 'http://localhost:5000'; // Make sure this matches your Flask port

export default function App() {
  const [view, setView] = useState('upload'); // 'upload' or 'result'
  const [albums, setAlbums] = useState(null);
  const [boxedImage, setBoxedImage] = useState(null);
  const [files, setFiles] = useState([]);
  const [isUploading, setIsUploading] = useState(false);
  const [flashMsg, setFlashMsg] = useState(null);
  const [isDragging, setIsDragging] = useState(false);
  
  const fileInputRef = useRef(null);

  // Check if session exists on load
  useEffect(() => {
    fetch(`${API_URL}/`, {
      credentials: 'include'
    })
      .then(res => res.json())
      .then(data => {
        if (data.has_session) {
          setAlbums(data.albums);
          setBoxedImage(data.boxed_image);
          setView('result');
        }
      })
      .catch(err => console.error("Error connecting to backend", err));
  }, []);

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files.length > 0) {
      setFiles(Array.from(e.target.files));
    }
  };

  const handleUpload = async (e) => {
    e.preventDefault();
    if (!files.length) return;
    
    setIsUploading(true);
    const formData = new FormData();
    files.forEach(file => formData.append('images', file));

    try {
      const res = await fetch(`${API_URL}/upload`, {
        method: 'POST',
        credentials: 'include',
        body: formData,
      });
      const data = await res.json();
      setAlbums(data.albums);
      setBoxedImage(data.boxed_image);
      setView('result');
    } catch (err) {
      console.error("Upload failed", err);
    } finally {
      setIsUploading(false);
    }
  };

  const handleReset = async () => {
    await fetch(`${API_URL}/reset`, { 
      method: 'POST',
      credentials: 'include' 
    });
    setAlbums(null);
    setBoxedImage(null);
    setFiles([]);
    setView('upload');
  };

  const handleCorrect = async (e, imagePath) => {
    e.preventDefault();
    const name = e.target.elements.name.value;
    
    try {
      const res = await fetch(`${API_URL}/add_person`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, image: imagePath })
      });
      const data = await res.json();
      
      if (data.success) {
        setFlashMsg(data.message);
        e.target.reset();
        setTimeout(() => setFlashMsg(null), 4000);
      }
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <>
      {/* Animated Background */}
      <div className="bg">
        <div className="orb orb1"></div>
        <div className="orb orb2"></div>
        <div className="orb orb3"></div>
        <div className="grid-lines"></div>
      </div>

      {/* Flash Messages */}
      {flashMsg && (
        <div className="flash-wrap">
          <div className="flash"><p>{flashMsg}</p></div>
        </div>
      )}

      <div className="page">
        
        {/* Upload View */}
        {view === 'upload' && (
          <>
            <header className="header">
              <div className="badge"><span className="badge-dot"></span>AI-Powered</div>
              <h1>Face Recognition</h1>
              <p className="subtitle">Upload your images and let our neural engine identify and analyse every face.</p>
            </header>

            <div className="card">
              <div className="card-shine"></div>
              <form onSubmit={handleUpload}>
                <label 
                  className={`dropzone-label ${isDragging ? 'active' : ''}`}
                  onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
                  onDragLeave={() => setIsDragging(false)}
                  onDrop={(e) => { e.preventDefault(); setIsDragging(false); setFiles(Array.from(e.dataTransfer.files)); }}
                >
                  <div className="drop-icon">📁</div>
                  <p className="drop-title">Drop images here</p>
                  <p className="drop-sub">or <span>browse files</span> from your device</p>
                  <input type="file" multiple accept="image/*" onChange={handleFileChange} ref={fileInputRef} style={{ display: 'none' }}/>
                </label>

                <div className="file-info">
                  <div className={`file-pill ${files.length > 0 ? 'visible' : ''}`}>
                    <span>{files.length} file{files.length !== 1 ? 's' : ''} selected</span>
                  </div>
                </div>

                <div className="divider">
                  <div className="divider-line"></div>
                  <span className="divider-text">Ready to analyse</span>
                  <div className="divider-line"></div>
                </div>

                <button type="submit" className="btn" disabled={isUploading || files.length === 0}>
                  {isUploading ? 'Processing...' : 'Analyse Faces'}
                </button>
              </form>
            </div>
          </>
        )}

        {/* Results View */}
        {view === 'result' && albums && (
          <>
            <div className="header">
              <div className="badge"><span className="badge-dot"></span>Recognition Results</div>
              <h1>Face Albums</h1>
            </div>

            <div className="top-bar">
              <button onClick={handleReset} className="btn-ghost btn-danger">Reset Session</button>
            </div>

            {boxedImage && (
              <>
                <div className="section-label">Annotated Preview</div>
                <div className="detected-card">
                  <img src={`${API_URL}/static/uploads/${boxedImage}`} alt="Annotated" />
                </div>
                <hr />
              </>
            )}

            <div className="section-label">Albums</div>
            {Object.entries(albums).map(([person, images], idx) => (
              <div className="album" key={person} style={{ animationDelay: `${idx * 0.07}s` }}>
                <div className="album-title">
                  <div className="album-icon">📁</div>
                  {person}
                </div>

                <div className="images">
                  {images.map((item, iIdx) => (
                    <div className="img-item" key={iIdx} style={{ animationDelay: `${iIdx * 0.06}s` }}>
                      <div className="img-wrapper">
                        <img src={`${API_URL}/static/uploads/${item.image}`} alt={person} />
                        <div className="face-box"></div>
                      </div>
                      <div className="confidence">{item.confidence}</div>

                      {(person === "Unknown" || item.confidence > 0.6) && (
                        <form className="correct-form" onSubmit={(e) => handleCorrect(e, item.image)}>
                          <input type="text" name="name" placeholder="Enter correct name" required />
                          <button type="submit" className="btn-add">Add / Correct</button>
                        </form>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </>
        )}
      </div>
    </>
  );
}