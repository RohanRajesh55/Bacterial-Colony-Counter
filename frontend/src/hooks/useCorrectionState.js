import { useState, useCallback, useMemo } from 'react';

/**
 * Custom hook for managing correction state with undo/redo
 *
 * Manages detections array with add/remove/adjust/split actions.
 * All actions are tracked in an undo stack for full history.
 *
 * @param {Array} initialDetections - Initial detections from API
 * @returns {Object} State and action dispatchers
 */
export default function useCorrectionState(initialDetections = []) {
  // Counter for generating unique IDs
  const [nextId, setNextId] = useState(() => {
    const maxId = initialDetections.reduce((max, d) => {
      const id = typeof d.id === 'number' ? d.id : parseInt(d.id, 10);
      return isNaN(id) ? max : Math.max(max, id);
    }, 0);
    return maxId + 1;
  });

  // Normalize initial detections: ensure all have id, source, status
  const [detections, setDetections] = useState(() =>
    initialDetections.map((d, idx) => ({
      ...d,
      id: d.id ?? idx,
      source: d.source ?? 'model',
      status: d.status ?? 'active',
    }))
  );

  const [undoStack, setUndoStack] = useState([]);
  const [redoStack, setRedoStack] = useState([]);

  // Generate unique ID for new detections
  const generateId = useCallback(() => {
    const id = nextId;
    setNextId((prev) => prev + 1);
    return id;
  }, [nextId]);

  // Calculate median box size from active detections within radius
  const calculateAutoSize = useCallback(
    (position, radius = 200) => {
      const nearby = detections
        .filter((d) => d.status === 'active' && d.box?.length === 4)
        .filter((d) => {
          const [x1, y1, x2, y2] = d.box;
          const centerX = (x1 + x2) / 2;
          const centerY = (y1 + y2) / 2;
          const distance = Math.sqrt(
            Math.pow(centerX - position.x, 2) + Math.pow(centerY - position.y, 2)
          );
          return distance <= radius;
        })
        .map((d) => {
          const [x1, y1, x2, y2] = d.box;
          return {
            width: x2 - x1,
            height: y2 - y1,
          };
        });

      if (nearby.length === 0) {
        return { width: 30, height: 30 }; // Default size
      }

      // Calculate median width and height
      const widths = nearby.map((d) => d.width).sort((a, b) => a - b);
      const heights = nearby.map((d) => d.height).sort((a, b) => a - b);

      const medianWidth = widths[Math.floor(widths.length / 2)];
      const medianHeight = heights[Math.floor(heights.length / 2)];

      return { width: medianWidth, height: medianHeight };
    },
    [detections]
  );

  // Add colony action
  const addColony = useCallback(
    (position, size = null) => {
      const { width, height } = size ?? calculateAutoSize(position);

      const newId = generateId();
      const box = [
        position.x - width / 2,
        position.y - height / 2,
        position.x + width / 2,
        position.y + height / 2,
      ];

      const newDetection = {
        id: newId,
        box,
        confidence: null,
        source: 'user',
        status: 'active',
      };

      setDetections((prev) => [...prev, newDetection]);
      setUndoStack((prev) => [...prev, { type: 'add', detectionId: newId, box }]);
      setRedoStack([]); // Clear redo stack on new action
    },
    [generateId, calculateAutoSize]
  );

  // Remove colony action
  const removeColony = useCallback((detectionId) => {
    setDetections((prev) =>
      prev.map((d) => {
        if (d.id === detectionId) {
          setUndoStack((stack) => [
            ...stack,
            { type: 'remove', detectionId, previousBox: d.box },
          ]);
          return { ...d, status: 'removed' };
        }
        return d;
      })
    );
    setRedoStack([]);
  }, []);

  // Adjust colony action
  const adjustColony = useCallback((detectionId, newBox) => {
    setDetections((prev) =>
      prev.map((d) => {
        if (d.id === detectionId) {
          setUndoStack((stack) => [
            ...stack,
            { type: 'adjust', detectionId, previousBox: d.box, newBox },
          ]);
          return { ...d, box: newBox };
        }
        return d;
      })
    );
    setRedoStack([]);
  }, []);

  // Split colony action
  const splitColony = useCallback(
    (detectionId) => {
      const detection = detections.find((d) => d.id === detectionId);
      if (!detection || detection.status !== 'active' || !detection.box) return;

      const [x1, y1, x2, y2] = detection.box;
      const width = x2 - x1;
      const midX = x1 + width / 2;

      const newId1 = generateId();
      const newId2 = generateId();

      const box1 = [x1, y1, midX, y2];
      const box2 = [midX, y1, x2, y2];

      const newDetection1 = {
        id: newId1,
        box: box1,
        confidence: null,
        source: 'user',
        status: 'active',
      };

      const newDetection2 = {
        id: newId2,
        box: box2,
        confidence: null,
        source: 'user',
        status: 'active',
      };

      setDetections((prev) => [
        ...prev.map((d) => (d.id === detectionId ? { ...d, status: 'removed' } : d)),
        newDetection1,
        newDetection2,
      ]);

      setUndoStack((prev) => [
        ...prev,
        {
          type: 'split',
          originalId: detectionId,
          newIds: [newId1, newId2],
          originalBox: detection.box,
        },
      ]);

      setRedoStack([]);
    },
    [detections, generateId]
  );

  // Undo action
  const undo = useCallback(() => {
    if (undoStack.length === 0) return;

    const action = undoStack[undoStack.length - 1];
    const newUndoStack = undoStack.slice(0, -1);

    setUndoStack(newUndoStack);
    setRedoStack((prev) => [...prev, action]);

    switch (action.type) {
      case 'add':
        // Reverse add: mark as removed
        setDetections((prev) =>
          prev.map((d) =>
            d.id === action.detectionId ? { ...d, status: 'removed' } : d
          )
        );
        break;

      case 'remove':
        // Reverse remove: mark as active
        setDetections((prev) =>
          prev.map((d) =>
            d.id === action.detectionId ? { ...d, status: 'active' } : d
          )
        );
        break;

      case 'adjust':
        // Reverse adjust: restore previous box
        setDetections((prev) =>
          prev.map((d) =>
            d.id === action.detectionId ? { ...d, box: action.previousBox } : d
          )
        );
        break;

      case 'split':
        // Reverse split: restore original, remove new ones
        setDetections((prev) =>
          prev.map((d) => {
            if (d.id === action.originalId) {
              return { ...d, status: 'active' };
            }
            if (action.newIds.includes(d.id)) {
              return { ...d, status: 'removed' };
            }
            return d;
          })
        );
        break;

      default:
        break;
    }
  }, [undoStack]);

  // Redo action
  const redo = useCallback(() => {
    if (redoStack.length === 0) return;

    const action = redoStack[redoStack.length - 1];
    const newRedoStack = redoStack.slice(0, -1);

    setRedoStack(newRedoStack);
    setUndoStack((prev) => [...prev, action]);

    switch (action.type) {
      case 'add':
        // Re-apply add: mark as active
        setDetections((prev) =>
          prev.map((d) =>
            d.id === action.detectionId ? { ...d, status: 'active' } : d
          )
        );
        break;

      case 'remove':
        // Re-apply remove: mark as removed
        setDetections((prev) =>
          prev.map((d) =>
            d.id === action.detectionId ? { ...d, status: 'removed' } : d
          )
        );
        break;

      case 'adjust':
        // Re-apply adjust: restore new box
        setDetections((prev) =>
          prev.map((d) =>
            d.id === action.detectionId ? { ...d, box: action.newBox } : d
          )
        );
        break;

      case 'split':
        // Re-apply split: remove original, restore new ones
        setDetections((prev) =>
          prev.map((d) => {
            if (d.id === action.originalId) {
              return { ...d, status: 'removed' };
            }
            if (action.newIds.includes(d.id)) {
              return { ...d, status: 'active' };
            }
            return d;
          })
        );
        break;

      default:
        break;
    }
  }, [redoStack]);

  // Computed values
  const activeDetections = useMemo(
    () => detections.filter((d) => d.status === 'active'),
    [detections]
  );

  const colonyCount = useMemo(() => activeDetections.length, [activeDetections]);

  const correctionSummary = useMemo(() => {
    const summary = {
      added: 0,
      removed: 0,
      adjusted: 0,
      split: 0,
    };

    undoStack.forEach((action) => {
      if (action.type === 'add') summary.added++;
      else if (action.type === 'remove') summary.removed++;
      else if (action.type === 'adjust') summary.adjusted++;
      else if (action.type === 'split') summary.split++;
    });

    return summary;
  }, [undoStack]);

  const canUndo = undoStack.length > 0;
  const canRedo = redoStack.length > 0;

  return {
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
  };
}
