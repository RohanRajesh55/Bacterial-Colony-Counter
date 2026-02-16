import { useState, useEffect, useRef, useCallback } from 'react';

/**
 * Custom hook for managing canvas viewport interactions:
 * - Zoom (scroll wheel)
 * - Pan (middle-click or space+click drag)
 * - Coordinate transformations between screen and canvas space
 */
export default function useCanvasInteraction(canvasRef) {
  const [scale, setScale] = useState(1.0);
  const [offset, setOffset] = useState({ x: 0, y: 0 });
  const [isPanning, setIsPanning] = useState(false);
  const lastPanPointRef = useRef({ x: 0, y: 0 });

  // Use refs for zoom calculation to avoid re-attaching wheel listener
  const scaleRef = useRef(scale);
  const offsetRef = useRef(offset);
  scaleRef.current = scale;
  offsetRef.current = offset;

  // Attach wheel listener with passive: false to prevent page scroll
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const handleWheel = (e) => {
      e.preventDefault();

      const rect = canvas.getBoundingClientRect();
      const mouseX = e.clientX - rect.left;
      const mouseY = e.clientY - rect.top;

      const currentScale = scaleRef.current;
      const currentOffset = offsetRef.current;

      const delta = e.deltaY > 0 ? 1 / 1.1 : 1.1;
      const newScale = Math.min(Math.max(currentScale * delta, 0.1), 10.0);

      const canvasX = (mouseX - currentOffset.x) / currentScale;
      const canvasY = (mouseY - currentOffset.y) / currentScale;

      const newOffsetX = mouseX - canvasX * newScale;
      const newOffsetY = mouseY - canvasY * newScale;

      setScale(newScale);
      setOffset({ x: newOffsetX, y: newOffsetY });
    };

    canvas.addEventListener('wheel', handleWheel, { passive: false });
    return () => canvas.removeEventListener('wheel', handleWheel);
  }, [canvasRef]);

  const handleMouseDown = useCallback((e) => {
    if (e.button === 1 || (e.button === 0 && e.code === 'Space')) {
      setIsPanning(true);
      lastPanPointRef.current = { x: e.clientX, y: e.clientY };
      e.preventDefault();
    }
  }, []);

  const handleMouseMove = useCallback((e) => {
    if (!isPanning) return;

    const deltaX = e.clientX - lastPanPointRef.current.x;
    const deltaY = e.clientY - lastPanPointRef.current.y;

    setOffset((prev) => ({
      x: prev.x + deltaX,
      y: prev.y + deltaY,
    }));

    lastPanPointRef.current = { x: e.clientX, y: e.clientY };
  }, [isPanning]);

  const handleMouseUp = useCallback(() => {
    setIsPanning(false);
  }, []);

  // Convert screen coordinates to canvas/image coordinates
  const screenToCanvas = useCallback((screenX, screenY) => {
    const canvas = canvasRef.current;
    if (!canvas) return { x: 0, y: 0 };

    const rect = canvas.getBoundingClientRect();
    const canvasScreenX = screenX - rect.left;
    const canvasScreenY = screenY - rect.top;

    return {
      x: (canvasScreenX - offsetRef.current.x) / scaleRef.current,
      y: (canvasScreenY - offsetRef.current.y) / scaleRef.current,
    };
  }, [canvasRef]);

  // Convert canvas coordinates to screen coordinates
  const canvasToScreen = useCallback((canvasX, canvasY) => {
    const canvas = canvasRef.current;
    if (!canvas) return { x: 0, y: 0 };

    const rect = canvas.getBoundingClientRect();

    return {
      x: canvasX * scaleRef.current + offsetRef.current.x + rect.left,
      y: canvasY * scaleRef.current + offsetRef.current.y + rect.top,
    };
  }, [canvasRef]);

  // Reset view to fit image
  const resetView = useCallback(() => {
    setScale(1.0);
    setOffset({ x: 0, y: 0 });
  }, []);

  // Calculate initial scale and offset to fit image in container
  const fitToView = useCallback((containerWidth, containerHeight, imageWidth, imageHeight) => {
    const scaleX = containerWidth / imageWidth;
    const scaleY = containerHeight / imageHeight;
    const fitScale = Math.min(scaleX, scaleY, 1.0);

    const scaledWidth = imageWidth * fitScale;
    const scaledHeight = imageHeight * fitScale;

    const newOffsetX = (containerWidth - scaledWidth) / 2;
    const newOffsetY = (containerHeight - scaledHeight) / 2;

    setScale(fitScale);
    setOffset({ x: newOffsetX, y: newOffsetY });

    return { scale: fitScale, offset: { x: newOffsetX, y: newOffsetY } };
  }, []);

  return {
    scale,
    offset,
    isPanning,
    handleMouseDown,
    handleMouseMove,
    handleMouseUp,
    screenToCanvas,
    canvasToScreen,
    resetView,
    fitToView,
  };
}
