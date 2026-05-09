import { useState, useRef, useEffect } from 'react';

// Default classes if none provided
const DEFAULT_CLASSES = [
  'B.subtilis',
  'C.albicans',
  'Contamination',
  'Defect',
  'E.coli',
  'P.aeruginosa',
  'S.aureus'
];

// Color mapping matching index.css/backend
const CLASS_COLORS = {
  'B.subtilis': '#0ea5e9',      // Sky Blue
  'C.albicans': '#22c55e',      // Green
  'Contamination': '#ef4444',   // Red
  'Defect': '#71717a',          // Zinc
  'E.coli': '#06b6d4',          // Cyan
  'P.aeruginosa': '#8b5cf6',    // Violet
  'S.aureus': '#f97316'         // Orange
};

function AnnotationEditor({ imageUrl, initialBoxes = [], onSave, onCancel }) {
  const [boxes, setBoxes] = useState(initialBoxes.map(b => ({ 
    ...b, 
    id: Math.random(),
    class: b.class || 'E.coli' // Default if missing
  })));
  
  const [selectedClass, setSelectedClass] = useState('E.coli');
  const [selectedBoxId, setSelectedBoxId] = useState(null);
  const [isDrawing, setIsDrawing] = useState(false);
  const [startPoint, setStartPoint] = useState(null);
  const [currentBox, setCurrentBox] = useState(null);
  const [imgSize, setImgSize] = useState({ w: 0, h: 0 });
  
  const containerRef = useRef(null);
  const imgRef = useRef(null);

  // Load image to get natural dimensions
  const onImgLoad = (e) => {
    setImgSize({ w: e.target.naturalWidth, h: e.target.naturalHeight });
  };

  const getRelativeCoords = (e) => {
    if (!containerRef.current) return { x: 0, y: 0 };
    const rect = containerRef.current.getBoundingClientRect();
    const scaleX = imgSize.w / rect.width;
    const scaleY = imgSize.h / rect.height;
    
    return {
      x: (e.clientX - rect.left) * scaleX,
      y: (e.clientY - rect.top) * scaleY
    };
  };

  // Zoom & Pan State
  const [scale, setScale] = useState(1);
  const [position, setPosition] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const [mode, setMode] = useState('view'); // 'view' | 'draw'

  // Fit image to container on load or reset
  const fitImage = () => {
    if (!containerRef.current || !imgSize.w || !imgSize.h) return;
    
    const container = containerRef.current.getBoundingClientRect();
    const containerAspect = container.width / container.height;
    const imgAspect = imgSize.w / imgSize.h;
    
    let newScale;
    if (containerAspect > imgAspect) {
        // Container is wider than image -> fit by height
        newScale = container.height / imgSize.h;
    } else {
        // Container is taller than image -> fit by width
        newScale = container.width / imgSize.w;
    }
    
    // Slight padding (95%)
    newScale = newScale * 0.95; 

    // Center the image
    const newX = (container.width - imgSize.w * newScale) / 2;
    const newY = (container.height - imgSize.h * newScale) / 2;
    
    setScale(newScale);
    setPosition({ x: newX, y: newY });
  };

  // Auto-fit when image loads
  useEffect(() => {
    if (imgSize.w && imgSize.h) {
        fitImage();
    }
  }, [imgSize]);

  // Handle Wheel Zoom (centered on cursor)
  const handleWheel = (e) => {
    e.preventDefault();
    if (mode === 'draw') return;

    const zoomSensitivity = 0.001;
    const delta = -e.deltaY * zoomSensitivity;
    const newScale = Math.min(Math.max(0.1, scale + delta), 5);
    
    // Zoom towards mouse pointer logic
    if (containerRef.current) {
        const rect = containerRef.current.getBoundingClientRect();
        const cursorX = e.clientX - rect.left;
        const cursorY = e.clientY - rect.top;

        // Calculate offset based on scale change to keep cursor point stable
        // (cursorX - oldX) / oldScale = (cursorX - newX) / newScale
        const scaleRatio = newScale / scale;
        const newX = cursorX - (cursorX - position.x) * scaleRatio;
        const newY = cursorY - (cursorY - position.y) * scaleRatio;

        setPosition({ x: newX, y: newY });
    }

    setScale(newScale);
  };

  // Interaction State
  const [interaction, setInteraction] = useState({ type: 'idle', id: null, handle: null, startPos: null, startBox: null });
  const [hoveredIds, setHoveredIds] = useState([]);

  // Helper to update specific box
  const updateBox = (id, updates) => {
    setBoxes(prev => prev.map(b => b.id === id ? { ...b, ...updates } : b));
  };

  const handleMouseDown = (e) => {
    // 1. Check for resize handle click (highest priority)
    if (e.target.dataset.handle && selectedBoxId) {
        e.stopPropagation();
        const startMouse = getRelativeCoords(e);
        const box = boxes.find(b => b.id === selectedBoxId);
        setInteraction({
            type: 'resizing',
            id: selectedBoxId,
            handle: e.target.dataset.handle,
            startPos: startMouse,
            startBox: { ...box }
        });
        return;
    }

    // 2. Check for box body move click
    const boxId = e.target.dataset.boxId;
    if (boxId && mode === 'view') {
        e.stopPropagation();
        const startMouse = getRelativeCoords(e);
        const box = boxes.find(b => b.id === parseFloat(boxId));
        setSelectedBoxId(parseFloat(boxId));
        if(box) setSelectedClass(box.class);
        
        setInteraction({
            type: 'moving',
            id: parseFloat(boxId),
            startPos: startMouse,
            startBox: { ...box }
        });
        return;
    }

    // 3. Background Panning (View Mode)
    if (mode === 'view') {
       if (!e.target.closest('.bounding-box')) {
           setIsDragging(true);
           setDragStart({ x: e.clientX - position.x, y: e.clientY - position.y });
           // Deselect if clicking empty space
           setSelectedBoxId(null);
       }
    } 
    // 4. Drawing Mode
    else if (mode === 'draw') {
       if (!imgRef.current) return;
       const rect = imgRef.current.getBoundingClientRect();
       // Normalized coords 0-1
       const x = (e.clientX - rect.left) / rect.width;
       const y = (e.clientY - rect.top) / rect.height;
       
       setIsDrawing(true);
       setStartPoint({ x, y });
       setCurrentBox({ x, y, w: 0, h: 0 });
    }
  };

  const handleMouseMove = (e) => {
    const currentMouse = getRelativeCoords(e);

    // Resizing Logic
    if (interaction.type === 'resizing' && interaction.startBox) {
        const { startBox, startPos, handle } = interaction;
        const dx = currentMouse.x - startPos.x;
        const dy = currentMouse.y - startPos.y;
        
        let newBox = { ...startBox };

        // Handle logic (simple version)
        if (handle.includes('e')) newBox.w = Math.max(5, startBox.w + dx);
        if (handle.includes('s')) newBox.h = Math.max(5, startBox.h + dy);
        if (handle.includes('w')) {
            newBox.x = Math.min(startBox.x + startBox.w - 5, startBox.x + dx);
            newBox.w = Math.max(5, startBox.w - dx);
        }
        if (handle.includes('n')) {
            newBox.y = Math.min(startBox.y + startBox.h - 5, startBox.y + dy);
            newBox.h = Math.max(5, startBox.h - dy);
        }

        updateBox(interaction.id, { x: newBox.x, y: newBox.y, w: newBox.w, h: newBox.h });
    } 
    // Moving Logic
    else if (interaction.type === 'moving' && interaction.startBox) {
        const dx = currentMouse.x - interaction.startPos.x;
        const dy = currentMouse.y - interaction.startPos.y;
        updateBox(interaction.id, {
            x: interaction.startBox.x + dx,
            y: interaction.startBox.y + dy
        });
    }
    // Panning/Hovering
    else if (mode === 'view') {
      if (isDragging) {
        setPosition({
            x: e.clientX - dragStart.x,
            y: e.clientY - dragStart.y
        });
      } else {
        // Hover Detection
        const mouseX = (e.clientX - rect.left) / rect.width * imgSize.w;
        const mouseY = (e.clientY - rect.top) / rect.height * imgSize.h;
        
        const hits = boxes.filter(b => 
            mouseX >= b.x && mouseX <= b.x + b.w &&
            mouseY >= b.y && mouseY <= b.y + b.h
        ).map(b => b.id);

        // Only update if changed (shallow compare)
        if (hits.length !== hoveredIds.length || !hits.every((val, index) => val === hoveredIds[index])) {
            setHoveredIds(hits);
        }
      }
    } 
    // Drawing
    else if (mode === 'draw' && isDrawing) {
       const rect = imgRef.current.getBoundingClientRect();
       const currentX = (e.clientX - rect.left) / rect.width;
       const currentY = (e.clientY - rect.top) / rect.height;
       
       const x = Math.min(startPoint.x, currentX);
       const y = Math.min(startPoint.y, currentY);
       const w = Math.abs(currentX - startPoint.x);
       const h = Math.abs(currentY - startPoint.y);
       
       setCurrentBox({ x, y, w, h });
    }
  };

  const handleMouseUp = () => {
    if (interaction.type !== 'idle') {
        setInteraction({ type: 'idle', id: null });
    }
    
    if (mode === 'view') {
      setIsDragging(false);
    } else if (mode === 'draw' && isDrawing) {
       setIsDrawing(false);
       if (currentBox && currentBox.w > 0.01 && currentBox.h > 0.01) { 
           const newId = Math.random();
           const pixelBox = {
               x: currentBox.x * imgSize.w,
               y: currentBox.y * imgSize.h,
               w: currentBox.w * imgSize.w,
               h: currentBox.h * imgSize.h,
               id: newId,
               class: selectedClass
           };
           setBoxes([...boxes, pixelBox]);
           setSelectedBoxId(newId);
       }
       setCurrentBox(null);
    }
  };

  const handleDelete = (id, e) => {
    e.stopPropagation();
    setBoxes(boxes.filter(b => b.id !== id));
    if (selectedBoxId === id) setSelectedBoxId(null);
  };

  const handleBoxClick = (id, e) => {
    e.stopPropagation();
    if (mode === 'draw') return;
    setSelectedBoxId(id);
    const box = boxes.find(b => b.id === id);
    if (box) setSelectedClass(box.class);
  };

  const handleClassChange = (cls) => {
    setSelectedClass(cls);
    if (selectedBoxId) {
        setBoxes(boxes.map(b => 
            b.id === selectedBoxId ? { ...b, class: cls } : b
        ));
    }
  };

  // Keyboard Shortcuts
  useEffect(() => {
    const handleKeyDown = (e) => {
        if ((e.key === 'Delete' || e.key === 'Backspace') && selectedBoxId) {
            setBoxes(prev => prev.filter(b => b.id !== selectedBoxId));
            setSelectedBoxId(null);
        }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [selectedBoxId]);

  return (
    <div className="annotation-modal">
      <div className="annotation-layout">
        {/* Left Sidebar - Toolbar */}
        <div className="annotation-sidebar">
            <div className="sidebar-header">
                <h3>Classes</h3>
                <p className="sidebar-subtitle">Select class to draw</p>
            </div>
            
            <div className="class-list">
                {DEFAULT_CLASSES.map(cls => (
                    <div 
                        key={cls}
                        className={`class-item ${selectedClass === cls ? 'active' : ''}`}
                        onClick={() => handleClassChange(cls)}
                        style={{
                            '--class-color': CLASS_COLORS[cls] || '#ccc'
                        }}
                    >
                        <div className="class-indicator" style={{ background: CLASS_COLORS[cls] || '#ccc' }} />
                        <span className="class-name">{cls}</span>
                        {selectedClass === cls && <span className="class-check">✓</span>}
                    </div>
                ))}
            </div>

            <div className="sidebar-footer">
                <div className="stats-panel">
                    <div className="stat-row">
                        <span>Total Colonies:</span>
                        <strong>{boxes.length}</strong>
                    </div>
                    <div className="stat-row">
                        <span>Selected:</span>
                        <strong>{selectedBoxId ? 1 : 0}</strong>
                    </div>
                </div>

                <div className="action-buttons">
                    <button className="btn btn-secondary full-width" onClick={() => setBoxes(initialBoxes.map(b => ({ ...b, id: Math.random(), class: b.class || 'E.coli' })))}>Reset Boxes</button>
                    <button className="btn btn-secondary full-width" onClick={onCancel}>Cancel</button>
                    <button className="btn btn-outline full-width" onClick={() => onSave(boxes, imgSize, true)}>Save Draft</button>
                    <button className="btn btn-primary full-width" onClick={() => onSave(boxes, imgSize, false)}>Approve</button>
                </div>

                {/* JSON Preview Toggle (Restored) */}
                <div style={{marginTop: '1rem', borderTop: '1px solid #27272a', paddingTop: '1rem'}}>
                    <details>
                        <summary style={{color:'#71717a', cursor:'pointer', fontSize:'0.75rem', userSelect:'none'}}>Show Raw JSON</summary>
                        <pre style={{
                            marginTop:'8px', 
                            background:'#09090b', 
                            padding:'8px', 
                            fontSize:'0.7rem', 
                            color:'#4ade80', 
                            overflow:'auto', 
                            maxHeight:'150px',
                            borderRadius:'4px',
                            border: '1px solid #27272a'
                        }}>
                            {JSON.stringify({
                                total_count: boxes.length,
                                classes_present: [...new Set(boxes.map(b => b.class))],
                                boxes: boxes.map(b => {
                                    const xc = ((b.x + b.w/2)/imgSize.w).toFixed(4);
                                    const yc = ((b.y + b.h/2)/imgSize.h).toFixed(4);
                                    const w = (b.w/imgSize.w).toFixed(4);
                                    const h = (b.h/imgSize.h).toFixed(4);
                                    return { cls: b.class, x: xc, y: yc, w, h };
                                })
                            }, null, 2)}
                        </pre>
                    </details>
                </div>
            </div>
        </div>

        {/* Main Canvas Area */}
        <div className="annotation-main">
            <div className="annotation-toolbar-header" style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                <div className="toolbar-group">
                    <button 
                        className={`btn-tool ${mode === 'view' ? 'active' : ''}`}
                        onClick={() => setMode('view')}
                        title="Pan & Zoom Mode"
                    >
                        ✋ View
                    </button>
                    <button 
                        className={`btn-tool ${mode === 'draw' ? 'active' : ''}`}
                        onClick={() => setMode('draw')}
                        title="Draw Box Mode"
                    >
                        ✏️ Draw
                    </button>
                </div>
                <div className="toolbar-divider"></div>
                <div className="zoom-controls">
                     <button onClick={() => setScale(Math.max(0.1, scale - 0.2))}>-</button>
                     <span>{Math.round(scale * 100)}%</span>
                     <button onClick={() => setScale(Math.min(5, scale + 0.2))}>+</button>
                     <button onClick={fitImage} title="Fit to Screen">⤢ Fit</button>
                </div>
            </div>

            <div 
            className="canvas-container" 
            ref={containerRef}
            onMouseDown={handleMouseDown}
            onMouseMove={handleMouseMove}
            onMouseUp={handleMouseUp}
            onMouseLeave={handleMouseUp}
            onWheel={handleWheel}
            style={{ 
                cursor: mode === 'view' ? (isDragging ? 'grabbing' : 'grab') : 'crosshair',
                overflow: 'hidden',
                position: 'relative'
            }}
            >
             <div 
                 style={{ 
                     transform: `translate(${position.x}px, ${position.y}px) scale(${scale})`, 
                     transformOrigin: '0 0',
                     transition: isDragging || isDrawing ? 'none' : 'transform 0.1s ease-out',
                     position: 'absolute',
                     left: 0, top: 0
                 }}
              >
                <img 
                    ref={imgRef}
                    src={imageUrl} 
                    onLoad={onImgLoad}
                    alt="Annotation target"
                    draggable="false"
                    style={{ display: 'block', maxWidth: 'none', pointerEvents: 'none', userSelect: 'none' }}
                />
                
                {/* Existing Boxes */}
                {boxes.map((box, idx) => {
                    const isSelected = selectedBoxId === box.id;
                    const isHovered = hoveredIds.includes(box.id);
                    const color = CLASS_COLORS[box.class] || '#22c55e';
                    
                    return (
                        <div
                        key={box.id}
                        className={`bounding-box ${isSelected ? 'selected' : ''} ${isHovered ? 'hovered' : ''}`}
                        data-box-id={box.id}
                        onMouseDown={(e) => handleBoxClick(box.id, e)}
                        style={{
                            left: `${box.x}px`,
                            top: `${box.y}px`,
                            width: `${box.w}px`,
                            height: `${box.h}px`,
                            borderColor: color,
                            backgroundColor: isHovered ? `${color}4d` : `${color}1a`, // Darker bg on hover
                            zIndex: isSelected ? 100 : (isHovered ? 50 : 10),
                            position: 'absolute',
                            boxShadow: isHovered ? `0 0 8px ${color}` : 'none',
                            transition: 'background-color 0.1s, box-shadow 0.1s'
                        }}
                        >
                            {/* Number Badge */}
                            <div 
                                className="box-badge"
                                style={{
                                    position: 'absolute',
                                    top: '-18px',
                                    left: '-2px',
                                    background: color,
                                    color: '#fff',
                                    fontSize: '10px',
                                    padding: '1px 4px',
                                    borderRadius: '3px',
                                    fontWeight: 'bold',
                                    zIndex: 101,
                                    pointerEvents: 'none' // Click through to background/box
                                }}
                            >
                                {idx + 1}
                            </div>

                            {/* Resize Handles (Only when selected) */}
                            {isSelected && (
                                <>
                                    <div className="resize-handle nw" data-handle="nw" />
                                    <div className="resize-handle ne" data-handle="ne" />
                                    <div className="resize-handle sw" data-handle="sw" />
                                    <div className="resize-handle se" data-handle="se" />
                                    
                                    <div className="box-control delete-control">
                                        <button onClick={(e) => handleDelete(box.id, e)}>×</button>
                                    </div>
                                </>
                            )}
                            
                            {scale > 0.8 && (
                                <div className="box-coord-tooltip">
                                    {box.class}
                                </div>
                            )}
                        </div>
                    );
                })}

                {/* Drawing Box */}
                {currentBox && (
                    <div
                    className="bounding-box drawing"
                    style={{
                        left: `${currentBox.x * imgSize.w}px`,
                        top: `${currentBox.y * imgSize.h}px`,
                        width: `${currentBox.w * imgSize.w}px`,
                        height: `${currentBox.h * imgSize.h}px`,
                        borderColor: CLASS_COLORS[selectedClass] || 'white',
                        position: 'absolute'
                    }}
                    />
                )}
                {/* Overlap Tooltip */}
                {hoveredIds.length > 1 && !isDragging && mode === 'view' && (
                    <div style={{
                        position: 'absolute',
                        top: '10px',
                        left: '50%',
                        transform: 'translateX(-50%)',
                        background: 'rgba(0,0,0,0.8)',
                        color: 'white',
                        padding: '4px 8px',
                        borderRadius: '4px',
                        fontSize: '12px',
                        zIndex: 200,
                        pointerEvents: 'none'
                    }}>
                        {hoveredIds.length} items detected here
                    </div>
                )}
             </div>
            </div>
        </div>
      </div>
    </div>
  );
}

export default AnnotationEditor;
