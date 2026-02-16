import { useRef, useEffect, useState, useCallback, useImperativeHandle, forwardRef } from 'react';
import useCanvasInteraction from '../hooks/useCanvasInteraction';
import useCorrectionState from '../hooks/useCorrectionState';

/**
 * Canvas-based editor for correction detection boxes
 * Features: zoom, pan, box selection, interactive tools (add/remove/adjust/split)
 */
const CorrectionCanvas = forwardRef(function CorrectionCanvas({
  imageUrl,
  initialDetections = [],
  activeTool = 'select',
  onCorrectionChange,
}, ref) {
  const canvasRef = useRef(null);
  const containerRef = useRef(null);
  const imageCache = useRef(null);
  const animationFrameId = useRef(null);

  const [selectedId, setSelectedId] = useState(null);
  const [hoveredBox, setHoveredBox] = useState(null);
  const [imageLoaded, setImageLoaded] = useState(false);
  const [dragState, setDragState] = useState(null); // For drag-to-draw and adjust modes

  // Use correction state hook
  const correctionState = useCorrectionState(initialDetections);
  const {
    detections,
    activeDetections,
    colonyCount,
    correctionSummary,
    addColony,
    removeColony,
    adjustColony,
    splitColony,
    undo,
    redo,
    canUndo,
    canRedo,
  } = correctionState;

  // Expose correction state to parent via ref
  useImperativeHandle(ref, () => ({
    correctionState,
    undo,
    redo,
    canUndo,
    canRedo,
  }), [correctionState, undo, redo, canUndo, canRedo]);

  // Notify parent of correction changes
  useEffect(() => {
    onCorrectionChange?.({
      colonyCount,
      correctionSummary,
      activeDetections,
      canUndo,
      canRedo,
    });
  }, [colonyCount, correctionSummary]); // eslint-disable-line react-hooks/exhaustive-deps

  const {
    scale,
    offset,
    isPanning,
    handleMouseDown: handlePanStart,
    handleMouseMove: handlePanMove,
    handleMouseUp: handlePanEnd,
    screenToCanvas,
    canvasToScreen,
    fitToView,
  } = useCanvasInteraction(canvasRef);

  // Load image on mount or when imageUrl changes
  useEffect(() => {
    if (!imageUrl) return;

    const img = new Image();
    img.onload = () => {
      imageCache.current = img;
      setImageLoaded(true);

      // Fit to view on initial load
      if (containerRef.current) {
        const container = containerRef.current;
        fitToView(container.clientWidth, container.clientHeight, img.width, img.height);
      }
    };
    img.src = imageUrl;

    return () => {
      imageCache.current = null;
      setImageLoaded(false);
    };
  }, [imageUrl, fitToView]);

  // Render canvas on state change
  const renderCanvas = useCallback(() => {
    const canvas = canvasRef.current;
    const ctx = canvas?.getContext('2d');
    if (!ctx || !imageCache.current || !imageLoaded) return;

    const img = imageCache.current;

    // Clear canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Apply transform
    ctx.save();
    ctx.translate(offset.x, offset.y);
    ctx.scale(scale, scale);

    // Draw image
    ctx.drawImage(img, 0, 0);

    // Draw detection boxes
    detections.forEach((detection) => {
      const { box, id, confidence, source = 'model', status = 'active' } = detection;
      if (!box || box.length < 4) return;

      // Use preview box if currently adjusting this detection
      let currentBox = box;
      if (dragState?.type === 'adjust' && id === selectedId && dragState.previewBox) {
        currentBox = dragState.previewBox;
      }

      const [x1, y1, x2, y2] = currentBox;
      const width = x2 - x1;
      const height = y2 - y1;

      // Determine box style based on source and status
      let strokeStyle = '#22c55e'; // Model-detected: green
      let lineWidth = 2;
      let lineDash = [];
      let fillStyle = null;

      if (source === 'user') {
        strokeStyle = '#3b82f6'; // User-added: blue
      }

      if (status === 'removed') {
        strokeStyle = '#ef4444'; // Removed: red
        lineDash = [5, 5];
        fillStyle = 'rgba(239, 68, 68, 0.1)'; // Semi-transparent red fill
      }

      if (id === selectedId && status === 'active') {
        strokeStyle = '#eab308'; // Selected: yellow
        lineWidth = 3;
      }

      // Draw box
      ctx.strokeStyle = strokeStyle;
      ctx.lineWidth = lineWidth / scale; // Maintain consistent line width regardless of zoom
      ctx.setLineDash(lineDash);

      if (fillStyle) {
        ctx.fillStyle = fillStyle;
        ctx.fillRect(x1, y1, width, height);
      }

      ctx.strokeRect(x1, y1, width, height);
      ctx.setLineDash([]); // Reset dash

      // Draw corner handles and edge handles for selected box in adjust mode
      if (id === selectedId && status === 'active' && activeTool === 'adjust') {
        const handleSize = 8 / scale;
        ctx.fillStyle = strokeStyle;

        // Corner handles
        // Top-left
        ctx.fillRect(x1 - handleSize / 2, y1 - handleSize / 2, handleSize, handleSize);
        // Top-right
        ctx.fillRect(x2 - handleSize / 2, y1 - handleSize / 2, handleSize, handleSize);
        // Bottom-left
        ctx.fillRect(x1 - handleSize / 2, y2 - handleSize / 2, handleSize, handleSize);
        // Bottom-right
        ctx.fillRect(x2 - handleSize / 2, y2 - handleSize / 2, handleSize, handleSize);

        // Edge handles (midpoints)
        const midX = (x1 + x2) / 2;
        const midY = (y1 + y2) / 2;
        // Top
        ctx.fillRect(midX - handleSize / 2, y1 - handleSize / 2, handleSize, handleSize);
        // Bottom
        ctx.fillRect(midX - handleSize / 2, y2 - handleSize / 2, handleSize, handleSize);
        // Left
        ctx.fillRect(x1 - handleSize / 2, midY - handleSize / 2, handleSize, handleSize);
        // Right
        ctx.fillRect(x2 - handleSize / 2, midY - handleSize / 2, handleSize, handleSize);
      } else if (id === selectedId && status === 'active') {
        // Just corner handles for other modes
        const handleSize = 8 / scale;
        ctx.fillStyle = strokeStyle;
        ctx.fillRect(x1 - handleSize / 2, y1 - handleSize / 2, handleSize, handleSize);
        ctx.fillRect(x2 - handleSize / 2, y1 - handleSize / 2, handleSize, handleSize);
        ctx.fillRect(x1 - handleSize / 2, y2 - handleSize / 2, handleSize, handleSize);
        ctx.fillRect(x2 - handleSize / 2, y2 - handleSize / 2, handleSize, handleSize);
      }

      // Draw confidence label on hover
      if (id === hoveredBox && confidence != null) {
        const label = `${(confidence * 100).toFixed(1)}%`;
        ctx.font = `${14 / scale}px Inter, sans-serif`;
        ctx.fillStyle = 'rgba(0, 0, 0, 0.7)';
        const metrics = ctx.measureText(label);
        const padding = 4 / scale;
        ctx.fillRect(x1, y1 - 20 / scale, metrics.width + padding * 2, 20 / scale);
        ctx.fillStyle = 'white';
        ctx.fillText(label, x1 + padding, y1 - 6 / scale);
      }
    });

    // Draw drag preview for add mode
    if (dragState?.type === 'add' && dragState.start && dragState.current) {
      const { start, current } = dragState;
      const width = current.x - start.x;
      const height = current.y - start.y;

      ctx.strokeStyle = '#3b82f6';
      ctx.lineWidth = 2 / scale;
      ctx.setLineDash([5 / scale, 5 / scale]);
      ctx.strokeRect(start.x, start.y, width, height);
      ctx.setLineDash([]);
    }

    // Draw split line preview
    if (activeTool === 'split' && hoveredBox) {
      const detection = detections.find((d) => d.id === hoveredBox);
      if (detection && detection.status === 'active' && detection.box) {
        const [x1, y1, x2, y2] = detection.box;
        const midX = (x1 + x2) / 2;

        ctx.strokeStyle = '#8b5cf6';
        ctx.lineWidth = 2 / scale;
        ctx.setLineDash([5 / scale, 5 / scale]);
        ctx.beginPath();
        ctx.moveTo(midX, y1);
        ctx.lineTo(midX, y2);
        ctx.stroke();
        ctx.setLineDash([]);
      }
    }

    ctx.restore();
  }, [detections, selectedId, hoveredBox, scale, offset, imageLoaded, activeTool, dragState]);

  // Trigger render on dependencies change
  useEffect(() => {
    renderCanvas();
  }, [renderCanvas]);

  // Handle window resize
  useEffect(() => {
    const updateCanvasSize = () => {
      const container = containerRef.current;
      const canvas = canvasRef.current;
      if (!container || !canvas) return;

      const dpr = window.devicePixelRatio || 1;
      const rect = container.getBoundingClientRect();

      canvas.width = rect.width * dpr;
      canvas.height = rect.height * dpr;
      canvas.style.width = `${rect.width}px`;
      canvas.style.height = `${rect.height}px`;

      const ctx = canvas.getContext('2d');
      ctx.scale(dpr, dpr);

      renderCanvas();
    };

    updateCanvasSize();
    window.addEventListener('resize', updateCanvasSize);
    return () => window.removeEventListener('resize', updateCanvasSize);
  }, [renderCanvas]);

  // Find box under cursor (only active boxes)
  const findBoxAtPoint = useCallback(
    (canvasX, canvasY, includeRemoved = false) => {
      for (let i = detections.length - 1; i >= 0; i--) {
        const { box, id, status } = detections[i];
        if (!box || box.length < 4) continue;
        if (!includeRemoved && status === 'removed') continue;

        const [x1, y1, x2, y2] = box;
        if (canvasX >= x1 && canvasX <= x2 && canvasY >= y1 && canvasY <= y2) {
          return id;
        }
      }
      return null;
    },
    [detections]
  );

  // Find which handle or edge is under cursor (for adjust mode)
  const findHandleAtPoint = useCallback(
    (canvasX, canvasY, boxId) => {
      const detection = detections.find((d) => d.id === boxId);
      if (!detection || !detection.box) return null;

      const [x1, y1, x2, y2] = detection.box;
      const handleSize = 8 / scale;
      const threshold = handleSize / 2;

      const midX = (x1 + x2) / 2;
      const midY = (y1 + y2) / 2;

      // Check corner handles
      if (Math.abs(canvasX - x1) <= threshold && Math.abs(canvasY - y1) <= threshold) {
        return { type: 'corner', corner: 'tl' };
      }
      if (Math.abs(canvasX - x2) <= threshold && Math.abs(canvasY - y1) <= threshold) {
        return { type: 'corner', corner: 'tr' };
      }
      if (Math.abs(canvasX - x1) <= threshold && Math.abs(canvasY - y2) <= threshold) {
        return { type: 'corner', corner: 'bl' };
      }
      if (Math.abs(canvasX - x2) <= threshold && Math.abs(canvasY - y2) <= threshold) {
        return { type: 'corner', corner: 'br' };
      }

      // Check edge handles
      if (Math.abs(canvasX - midX) <= threshold && Math.abs(canvasY - y1) <= threshold) {
        return { type: 'edge', edge: 'top' };
      }
      if (Math.abs(canvasX - midX) <= threshold && Math.abs(canvasY - y2) <= threshold) {
        return { type: 'edge', edge: 'bottom' };
      }
      if (Math.abs(canvasX - x1) <= threshold && Math.abs(canvasY - midY) <= threshold) {
        return { type: 'edge', edge: 'left' };
      }
      if (Math.abs(canvasX - x2) <= threshold && Math.abs(canvasY - midY) <= threshold) {
        return { type: 'edge', edge: 'right' };
      }

      // Check if inside box (for move)
      if (canvasX >= x1 && canvasX <= x2 && canvasY >= y1 && canvasY <= y2) {
        return { type: 'move' };
      }

      return null;
    },
    [detections, scale]
  );

  // Handle canvas mousedown
  const handleCanvasMouseDown = (e) => {
    // Handle panning first
    handlePanStart(e);

    // Don't start interactions during panning
    if (e.button === 1 || (e.button === 0 && e.code === 'Space')) {
      return;
    }

    const { x, y } = screenToCanvas(e.clientX, e.clientY);

    if (activeTool === 'add') {
      // Start drag-to-draw
      setDragState({ type: 'add', start: { x, y }, current: { x, y } });
    } else if (activeTool === 'adjust' && selectedId) {
      // Check if clicking on handle or box
      const handle = findHandleAtPoint(x, y, selectedId);
      if (handle) {
        const detection = detections.find((d) => d.id === selectedId);
        setDragState({
          type: 'adjust',
          handle,
          start: { x, y },
          originalBox: detection.box,
        });
      }
    }
  };

  // Handle canvas mousemove
  const handleCanvasMouseMove = (e) => {
    handlePanMove(e);

    const { x, y } = screenToCanvas(e.clientX, e.clientY);
    const boxId = findBoxAtPoint(x, y);
    setHoveredBox(boxId);

    // Handle drag states
    if (dragState) {
      if (dragState.type === 'add') {
        setDragState({ ...dragState, current: { x, y } });
      } else if (dragState.type === 'adjust') {
        const { handle, originalBox, start } = dragState;
        const [x1, y1, x2, y2] = originalBox;
        const dx = x - start.x;
        const dy = y - start.y;

        let newBox = [...originalBox];

        if (handle.type === 'corner') {
          if (handle.corner === 'tl') {
            newBox = [x1 + dx, y1 + dy, x2, y2];
          } else if (handle.corner === 'tr') {
            newBox = [x1, y1 + dy, x2 + dx, y2];
          } else if (handle.corner === 'bl') {
            newBox = [x1 + dx, y1, x2, y2 + dy];
          } else if (handle.corner === 'br') {
            newBox = [x1, y1, x2 + dx, y2 + dy];
          }
        } else if (handle.type === 'edge') {
          if (handle.edge === 'top') {
            newBox = [x1, y1 + dy, x2, y2];
          } else if (handle.edge === 'bottom') {
            newBox = [x1, y1, x2, y2 + dy];
          } else if (handle.edge === 'left') {
            newBox = [x1 + dx, y1, x2, y2];
          } else if (handle.edge === 'right') {
            newBox = [x1, y1, x2 + dx, y2];
          }
        } else if (handle.type === 'move') {
          newBox = [x1 + dx, y1 + dy, x2 + dx, y2 + dy];
        }

        // Update preview (store in dragState for live rendering)
        setDragState({ ...dragState, previewBox: newBox });
      }
    }
  };

  // Handle canvas mouseup
  const handleCanvasMouseUp = (e) => {
    handlePanEnd(e);

    const { x, y } = screenToCanvas(e.clientX, e.clientY);

    if (dragState) {
      if (dragState.type === 'add') {
        const { start, current } = dragState;
        const width = Math.abs(current.x - start.x);
        const height = Math.abs(current.y - start.y);

        if (width > 5 && height > 5) {
          // Drag-to-draw: use exact size
          const x1 = Math.min(start.x, current.x);
          const y1 = Math.min(start.y, current.y);
          const x2 = Math.max(start.x, current.x);
          const y2 = Math.max(start.y, current.y);
          const centerX = (x1 + x2) / 2;
          const centerY = (y1 + y2) / 2;

          addColony({ x: centerX, y: centerY }, { width: x2 - x1, height: y2 - y1 });
        } else {
          // Click-to-add: auto-size
          addColony({ x: start.x, y: start.y });
        }
      } else if (dragState.type === 'adjust' && dragState.previewBox) {
        // Commit the adjustment
        adjustColony(selectedId, dragState.previewBox);
      }

      setDragState(null);
      return;
    }

    // Handle clicks (no drag)
    if (activeTool === 'select') {
      const boxId = findBoxAtPoint(x, y);
      setSelectedId(boxId);
    } else if (activeTool === 'remove') {
      const boxId = findBoxAtPoint(x, y);
      if (boxId) {
        removeColony(boxId);
        if (selectedId === boxId) {
          setSelectedId(null);
        }
      }
    } else if (activeTool === 'split') {
      const boxId = findBoxAtPoint(x, y);
      if (boxId) {
        splitColony(boxId);
        if (selectedId === boxId) {
          setSelectedId(null);
        }
      }
    }
  };

  // Determine cursor style based on active tool and state
  const getCursorStyle = () => {
    if (isPanning) return 'grabbing';
    if (dragState) {
      if (dragState.type === 'add') return 'crosshair';
      if (dragState.type === 'adjust') {
        const { handle } = dragState;
        if (handle.type === 'corner') {
          if (handle.corner === 'tl' || handle.corner === 'br') return 'nwse-resize';
          if (handle.corner === 'tr' || handle.corner === 'bl') return 'nesw-resize';
        }
        if (handle.type === 'edge') {
          if (handle.edge === 'top' || handle.edge === 'bottom') return 'ns-resize';
          if (handle.edge === 'left' || handle.edge === 'right') return 'ew-resize';
        }
        if (handle.type === 'move') return 'move';
      }
    }

    if (activeTool === 'add') return 'crosshair';
    if (activeTool === 'remove' && hoveredBox) return 'pointer';
    if (activeTool === 'select' && hoveredBox) return 'pointer';
    if (activeTool === 'split' && hoveredBox) return 'crosshair';
    if (activeTool === 'adjust') {
      if (selectedId && hoveredBox === selectedId) {
        return 'move';
      }
    }
    return 'grab';
  };

  return (
    <div
      ref={containerRef}
      className="correction-canvas-container"
      style={{ cursor: getCursorStyle() }}
    >
      <canvas
        ref={canvasRef}
        className="correction-canvas"
        onMouseDown={handleCanvasMouseDown}
        onMouseMove={handleCanvasMouseMove}
        onMouseUp={handleCanvasMouseUp}
        onMouseLeave={handleCanvasMouseUp}
      />
    </div>
  );
});

export default CorrectionCanvas;
