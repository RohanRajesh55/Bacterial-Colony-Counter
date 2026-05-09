import { useCallback, useState } from 'react';

function ImageUpload({ onFileSelect, previewUrl }) {
  const [isDragOver, setIsDragOver] = useState(false);

  const handleDragOver = useCallback((e) => {
    e.preventDefault();
    setIsDragOver(true);
  }, []);

  const handleDragLeave = useCallback((e) => {
    e.preventDefault();
    setIsDragOver(false);
  }, []);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    setIsDragOver(false);
    
    const files = e.dataTransfer.files;
    if (files.length > 0) {
      // Filter for images
      const imageFiles = Array.from(files).filter(f => f.type.startsWith('image/'));
      if (imageFiles.length > 0) {
        onFileSelect(imageFiles);
      }
    }
  }, [onFileSelect]);

  const handleFileChange = useCallback((e) => {
    const files = e.target.files;
    if (files.length > 0) {
        onFileSelect(Array.from(files));
    }
  }, [onFileSelect]);

  const handleClick = useCallback(() => {
    document.getElementById('file-input').click();
  }, []);

  return (
    <div
      className={`upload-zone ${isDragOver ? 'drag-over' : ''} ${previewUrl ? 'has-image' : ''}`}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      onClick={!previewUrl ? handleClick : undefined}
    >
      <input
        id="file-input"
        type="file"
        multiple
        accept="image/jpeg,image/png,image/jpg"
        onChange={handleFileChange}
      />
      
      {previewUrl ? (
        <div style={{ position: 'relative' }}>
          <img 
            src={previewUrl} 
            alt="Preview" 
            className="preview-image"
          />
          <button
            className="btn btn-secondary"
            style={{
              position: 'absolute',
              top: 'var(--spacing-sm)',
              right: 'var(--spacing-sm)',
              width: 'auto',
              padding: 'var(--spacing-xs) var(--spacing-sm)',
              fontSize: '0.75rem'
            }}
            onClick={(e) => {
              e.stopPropagation();
              document.getElementById('file-input').click();
            }}
          >
            Change
          </button>
        </div>
      ) : (
        <>
          <svg className="upload-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} 
              d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
          </svg>
          <p className="upload-text">
            Drag and drop your petri dish image here
          </p>
          <p className="upload-hint">
            or click to browse (JPG, PNG)
          </p>
        </>
      )}
    </div>
  );
}

export default ImageUpload;
