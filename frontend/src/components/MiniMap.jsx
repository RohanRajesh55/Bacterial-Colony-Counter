import { useRef, useEffect, useState } from 'react';

/**
 * Mini-map thumbnail showing full image overview with viewport indicator
 * Features: click to pan, color-coded detection markers
 */
export default function MiniMap({ imageUrl, detections = [], canvasRef }) {
  const miniCanvasRef = useRef(null);
  const [imageLoaded, setImageLoaded] = useState(false);
  const imageCache = useRef(null);

  // Load image
  useEffect(() => {
    if (!imageUrl) return;

    const img = new Image();
    img.onload = () => {
      imageCache.current = img;
      setImageLoaded(true);
    };
    img.src = imageUrl;

    return () => {
      imageCache.current = null;
      setImageLoaded(false);
    };
  }, [imageUrl]);

  // Render mini-map
  useEffect(() => {
    const canvas = miniCanvasRef.current;
    const ctx = canvas?.getContext('2d');
    if (!ctx || !imageCache.current || !imageLoaded) return;

    const img = imageCache.current;
    const miniSize = 200;

    // Calculate scale to fit image in mini-map
    const scale = Math.min(miniSize / img.width, miniSize / img.height);
    const scaledWidth = img.width * scale;
    const scaledHeight = img.height * scale;

    // Clear and draw image
    ctx.clearRect(0, 0, miniSize, miniSize);
    ctx.drawImage(img, 0, 0, scaledWidth, scaledHeight);

    // Draw detection markers
    if (detections && detections.length > 0) {
      detections.forEach((detection) => {
        const { box, status = 'active', source = 'model' } = detection;
        if (!box || box.length < 4) return;

        const [x1, y1, x2, y2] = box;
        const centerX = ((x1 + x2) / 2) * scale;
        const centerY = ((y1 + y2) / 2) * scale;

        // Color-coded dots
        let color = '#22c55e'; // Active model: green
        if (source === 'user') {
          color = '#3b82f6'; // User-added: blue
        }
        if (status === 'removed') {
          color = '#ef4444'; // Removed: red
        }

        ctx.fillStyle = color;
        ctx.beginPath();
        ctx.arc(centerX, centerY, 2, 0, 2 * Math.PI);
        ctx.fill();
      });
    }

    // Draw viewport rectangle (if canvas ref available)
    if (canvasRef?.current) {
      const mainCanvas = canvasRef.current;
      const { scale: viewScale, offset } = mainCanvas;

      // Get viewport bounds in image coordinates
      const viewportWidth = (canvas.width / viewScale);
      const viewportHeight = (canvas.height / viewScale);
      const viewportX = -offset.x / viewScale;
      const viewportY = -offset.y / viewScale;

      // Scale to mini-map coordinates
      const miniX = viewportX * scale;
      const miniY = viewportY * scale;
      const miniW = viewportWidth * scale;
      const miniH = viewportHeight * scale;

      ctx.strokeStyle = '#3b82f6';
      ctx.lineWidth = 2;
      ctx.strokeRect(miniX, miniY, miniW, miniH);
    }
  }, [imageLoaded, detections, canvasRef]);

  // Handle click to pan main canvas
  const handleMiniMapClick = (e) => {
    if (!canvasRef?.current || !imageCache.current) return;

    const canvas = miniCanvasRef.current;
    const rect = canvas.getBoundingClientRect();
    const clickX = e.clientX - rect.left;
    const clickY = e.clientY - rect.top;

    const img = imageCache.current;
    const miniSize = 200;
    const scale = Math.min(miniSize / img.width, miniSize / img.height);

    // Convert click to image coordinates
    const imageX = clickX / scale;
    const imageY = clickY / scale;

    // Pan main canvas to center on clicked position
    const mainCanvas = canvasRef.current;
    const { scale: viewScale } = mainCanvas;

    // Calculate new offset to center viewport on clicked position
    const newOffsetX = -(imageX * viewScale) + (canvas.width / 2);
    const newOffsetY = -(imageY * viewScale) + (canvas.height / 2);

    // Update main canvas offset (this requires exposing offset setter in useCanvasInteraction)
    // For now, this is a placeholder - full implementation would require updating the hook
    console.log('Mini-map clicked:', { imageX, imageY, newOffsetX, newOffsetY });
  };

  return (
    <div className="mini-map" onClick={handleMiniMapClick}>
      <canvas
        ref={miniCanvasRef}
        width={200}
        height={200}
        className="mini-map-canvas"
      />
    </div>
  );
}
