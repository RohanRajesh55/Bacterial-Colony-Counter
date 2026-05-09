function About() {
  const team = [
    {
      name: 'Research Team',
      role: 'Model Development',
      description: 'Deep learning researchers focused on computer vision and object detection for microbiology applications.'
    }
  ];

  return (
    <div className="about-page">
      <div className="page-header">
        <h1>About CFU-Counter</h1>
        <p>AI-powered bacterial colony detection and classification for modern microbiology.</p>
      </div>

      <section className="about-section">
        <h2>The Problem We Solve</h2>
        <p>
          Colony Forming Unit (CFU) counting is a fundamental technique in microbiology, used to 
          quantify viable bacteria in food safety testing, pharmaceutical quality control, and 
          research laboratories worldwide. However, traditional manual counting is:
        </p>
        <ul className="problem-list">
          <li><strong>Time-consuming:</strong> Manual counting can take 30+ minutes per plate</li>
          <li><strong>Subjective:</strong> Results vary between technicians by up to 20%</li>
          <li><strong>Error-prone:</strong> Fatigue leads to miscounts, especially at high densities</li>
          <li><strong>Unscalable:</strong> Bottleneck for high-throughput screening pipelines</li>
        </ul>
        <p>
          CFU-Counter addresses these challenges with deep learning models trained on over 18,000 
          annotated petri dish images, delivering consistent, accurate results in seconds.
        </p>
      </section>

      <section className="about-section">
        <h2>How It Works</h2>
        <div className="about-cards">
          <div className="about-card">
            <div className="about-card-number">1</div>
            <h3>Image Upload</h3>
            <p>Upload a clear photo of your petri dish. We support JPEG, PNG, and BMP formats up to 10MB.</p>
          </div>
          <div className="about-card">
            <div className="about-card-number">2</div>
            <h3>Preprocessing</h3>
            <p>Advanced image processing isolates the dish, removes rim artifacts, normalizes lighting, and enhances colony contrast.</p>
          </div>
          <div className="about-card">
            <div className="about-card-number">3</div>
            <h3>AI Detection</h3>
            <p>Deep learning models analyze the image to detect, count, and classify each bacterial colony by species.</p>
          </div>
          <div className="about-card">
            <div className="about-card-number">4</div>
            <h3>Results & Export</h3>
            <p>Get annotated images, detailed counts by class, confidence scores, and exportable data for your reports.</p>
          </div>
        </div>
      </section>

      <section className="about-section">
        <h2>Our Models</h2>
        <div className="model-cards">
          <div className="model-card">
            <h3>
              <svg style={{width: 20, height: 20, verticalAlign: 'middle', marginRight: 8}} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
                <circle cx="8.5" cy="8.5" r="1.5"></circle>
                <polyline points="21 15 16 10 5 21"></polyline>
              </svg>
              YOLOv8 Object Detection
            </h3>
            <p>
              State-of-the-art object detection model that identifies individual colonies and draws 
              bounding boxes around each one. Provides per-colony classification, confidence scores, 
              and spatial location data. Best for:
            </p>
            <ul>
              <li>Mixed cultures requiring species identification</li>
              <li>Quality assurance documentation</li>
              <li>Detailed colony morphology analysis</li>
            </ul>
          </div>
          <div className="model-card">
            <h3>
              <svg style={{width: 20, height: 20, verticalAlign: 'middle', marginRight: 8}} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline>
              </svg>
              CNN Regression Model
            </h3>
            <p>
              Custom convolutional neural network that predicts total colony count directly from 
              image features without individual detection. Faster inference time for high-throughput 
              scenarios. Best for:
            </p>
            <ul>
              <li>Pure culture single-species counts</li>
              <li>High-throughput screening pipelines</li>
              <li>Resource-constrained edge devices</li>
            </ul>
          </div>
        </div>
      </section>

      <section className="about-section">
        <h2>Supported Bacterial Classes</h2>
        <p>Our models are trained on the AGAR dataset to identify the following species and conditions:</p>
        <div className="class-grid">
          <div className="class-item" style={{ '--class-color': '#0ea5e9' }}>
            <strong>B.subtilis</strong>
            <span>Bacillus subtilis</span>
          </div>
          <div className="class-item" style={{ '--class-color': '#22c55e' }}>
            <strong>C.albicans</strong>
            <span>Candida albicans</span>
          </div>
          <div className="class-item" style={{ '--class-color': '#06b6d4' }}>
            <strong>E.coli</strong>
            <span>Escherichia coli</span>
          </div>
          <div className="class-item" style={{ '--class-color': '#8b5cf6' }}>
            <strong>P.aeruginosa</strong>
            <span>Pseudomonas aeruginosa</span>
          </div>
          <div className="class-item" style={{ '--class-color': '#f97316' }}>
            <strong>S.aureus</strong>
            <span>Staphylococcus aureus</span>
          </div>
          <div className="class-item" style={{ '--class-color': '#ef4444' }}>
            <strong>Contamination</strong>
            <span>Environmental contaminants</span>
          </div>
          <div className="class-item" style={{ '--class-color': '#71717a' }}>
            <strong>Defect</strong>
            <span>Agar defects, bubbles</span>
          </div>
        </div>
      </section>


    </div>
  );
}

export default About;
