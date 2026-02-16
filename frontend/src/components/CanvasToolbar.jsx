import { useEffect } from 'react';

/**
 * Toolbar for correction tools with keyboard shortcuts
 * Tools: select, add, remove, adjust, split
 * Undo/Redo: Ctrl+Z, Ctrl+Shift+Z
 */
export default function CanvasToolbar({
  activeTool = 'select',
  onToolChange,
  colonyCount = 0,
  correctionSummary = { added: 0, removed: 0, adjusted: 0, split: 0 },
  onUndo,
  onRedo,
  canUndo = false,
  canRedo = false,
}) {
  const tools = [
    {
      id: 'select',
      label: 'Select',
      icon: '↖',
      shortcut: 'S',
      description: 'Select and inspect boxes',
    },
    {
      id: 'add',
      label: 'Add',
      icon: '+',
      shortcut: 'A',
      description: 'Click to add colony',
    },
    {
      id: 'remove',
      label: 'Remove',
      icon: '×',
      shortcut: 'R',
      description: 'Click box to remove',
    },
    {
      id: 'adjust',
      label: 'Adjust',
      icon: '↔',
      shortcut: 'D',
      description: 'Drag box edges to resize',
    },
    {
      id: 'split',
      label: 'Split',
      icon: '✂',
      shortcut: 'X',
      description: 'Click box to split into two',
    },
  ];

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e) => {
      // Ignore if user is typing in an input field
      if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;

      // Undo/Redo shortcuts
      if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === 'Z') {
        e.preventDefault();
        onRedo?.();
        return;
      }
      if ((e.ctrlKey || e.metaKey) && e.key === 'z') {
        e.preventDefault();
        onUndo?.();
        return;
      }

      // Tool shortcuts
      const key = e.key.toUpperCase();
      const tool = tools.find((t) => t.shortcut === key);
      if (tool) {
        onToolChange?.(tool.id);
        e.preventDefault();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onToolChange, onUndo, onRedo]);

  const { added, removed, adjusted, split } = correctionSummary;
  const hasCorrections = added > 0 || removed > 0 || adjusted > 0 || split > 0;

  return (
    <div className="canvas-toolbar">
      {/* Tool buttons */}
      <div className="canvas-toolbar-tools">
        {tools.map((tool) => (
          <button
            key={tool.id}
            className={`canvas-toolbar-btn ${activeTool === tool.id ? 'active' : ''}`}
            onClick={() => onToolChange?.(tool.id)}
            title={`${tool.description} (${tool.shortcut})`}
          >
            <span className="canvas-toolbar-icon">{tool.icon}</span>
            <span className="canvas-toolbar-label">{tool.label}</span>
          </button>
        ))}
      </div>

      {/* Undo/Redo buttons */}
      <div className="canvas-toolbar-actions">
        <button
          className="canvas-toolbar-btn"
          onClick={onUndo}
          disabled={!canUndo}
          title="Undo (Ctrl+Z)"
        >
          <span className="canvas-toolbar-icon">↶</span>
          <span className="canvas-toolbar-label">Undo</span>
        </button>
        <button
          className="canvas-toolbar-btn"
          onClick={onRedo}
          disabled={!canRedo}
          title="Redo (Ctrl+Shift+Z)"
        >
          <span className="canvas-toolbar-icon">↷</span>
          <span className="canvas-toolbar-label">Redo</span>
        </button>
      </div>

      {/* Colony count display */}
      <div className="canvas-toolbar-count">
        <span className="canvas-toolbar-count-label">Colonies:</span>
        <span className="canvas-toolbar-count-value">{colonyCount}</span>
      </div>

      {/* Correction summary */}
      {hasCorrections && (
        <div className="canvas-toolbar-summary">
          {added > 0 && <span className="correction-badge added">+{added}</span>}
          {removed > 0 && <span className="correction-badge removed">-{removed}</span>}
          {adjusted > 0 && <span className="correction-badge adjusted">~{adjusted}</span>}
          {split > 0 && <span className="correction-badge split">÷{split}</span>}
        </div>
      )}
    </div>
  );
}
