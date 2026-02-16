function ModelSelector({ modelType, onModelChange }) {
  return (
    <div className="model-selector">
      <div className="model-option selected">
        <h3>RT-DETR</h3>
        <p>Real-Time Detection Transformer<br/>Colony detection with bounding boxes</p>
      </div>
    </div>
  );
}

export default ModelSelector;
