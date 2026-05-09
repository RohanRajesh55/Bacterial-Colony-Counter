function ModelSelector({ modelType, onModelChange }) {
  return (
    <div className="model-selector">
      <div
        className={`model-option ${modelType === "cnn" ? "selected" : ""}`}
        onClick={() => onModelChange("cnn")}
      >
        <h3>CNN</h3>
        <p>
          Multi-task classification
          <br />
          Count + Class prediction
        </p>
      </div>

      <div
        className={`model-option ${modelType === "yolo" ? "selected" : ""}`}
        onClick={() => onModelChange("yolo")}
      >
        <h3>YOLO</h3>
        <p>
          Object detection
          <br />
          Bounding boxes + Classes
        </p>
      </div>
    </div>
  );
}

export default ModelSelector;
