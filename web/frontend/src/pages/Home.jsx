import { Link } from 'react-router-dom';

function Home() {
  const features = [
    {
      icon: (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
          <circle cx="8.5" cy="8.5" r="1.5"></circle>
          <polyline points="21 15 16 10 5 21"></polyline>
        </svg>
      ),
      title: 'YOLOv8 Object Detection',
      description: 'State-of-the-art detection that identifies and localizes each bacterial colony with precise bounding boxes and confidence scores.',
    },
    {
      icon: (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline>
        </svg>
      ),
      title: 'CNN Regression Counting',
      description: 'Fast regression-based model that predicts total colony count directly from image features - ideal for high-throughput screening.',
    },
    {
      icon: (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="12" cy="12" r="10"></circle>
          <path d="M12 6v6l4 2"></path>
        </svg>
      ),
      title: 'Results in Seconds',
      description: 'Upload your petri dish image and receive comprehensive analysis within 2-5 seconds, replacing hours of manual counting.',
    },
    {
      icon: (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path>
          <path d="m9 12 2 2 4-4"></path>
        </svg>
      ),
      title: '7 Bacterial Classes',
      description: 'Trained on the AGAR dataset to identify B.subtilis, C.albicans, E.coli, P.aeruginosa, S.aureus, plus contamination and defects.',
    },
  ];

  const stats = [
    { value: '18K+', label: 'Training Images' },
    { value: '92%', label: 'Detection Accuracy' },
    { value: '< 3s', label: 'Analysis Time' },
    { value: '7', label: 'Bacterial Classes' },
  ];

  const workflow = [
    {
      step: '01',
      title: 'Upload Image',
      description: 'Capture or upload a clear photo of your petri dish. We support JPEG, PNG, and BMP formats.',
    },
    {
      step: '02', 
      title: 'Select Model',
      description: 'Choose YOLOv8 for detailed detection with bounding boxes, or CNN for quick total count estimation.',
    },
    {
      step: '03',
      title: 'Analyze',
      description: 'Our AI processes the image through advanced preprocessing and deep learning inference.',
    },
    {
      step: '04',
      title: 'Get Results',
      description: 'Receive detailed colony counts, classifications, annotated images, and exportable data.',
    },
  ];

  return (
    <div className="home-page">
      {/* Hero Section */}
      <section className="hero">
        <div className="hero-content">
          <div className="hero-badge">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ width: 16, height: 16 }}>
              <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>
            </svg>
            AI-Powered Analysis
          </div>
          <h1 className="hero-title">
            Precision Microbiology at the <span className="gradient-text">Speed of AI</span>
          </h1>
          <p className="hero-subtitle">
            CFU-Counter automates bacterial colony counting with deep learning. 
            Replace hours of tedious manual counting with accurate, reproducible results in seconds.
          </p>
          <div className="hero-cta">
            <Link to="/analyzer" className="btn btn-primary btn-lg">
              <svg className="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline>
              </svg>
              Start Analyzing
            </Link>
            <Link to="/about" className="btn btn-secondary btn-lg">
              How It Works
            </Link>
          </div>
        </div>
        <div className="hero-visual">
          <div className="hero-image-container">
            <div className="hero-glow"></div>
            <div className="hero-placeholder">
              <svg 
                className="placeholder-icon" 
                viewBox="0 0 24 24" 
                fill="none" 
                stroke="currentColor" 
                strokeWidth="1" 
                strokeLinecap="round" 
                strokeLinejoin="round"
                style={{ width: 80, height: 80 }}
              >
                <circle cx="12" cy="12" r="10"></circle>
                <circle cx="12" cy="12" r="4"></circle>
                <line x1="21.17" y1="8" x2="12" y2="8"></line>
                <line x1="3.95" y1="6.06" x2="8.54" y2="14"></line>
                <line x1="10.88" y1="21.94" x2="15.46" y2="14"></line>
              </svg>
              <span className="placeholder-text">AI-Powered Detection</span>
            </div>
          </div>
        </div>
      </section>

      {/* Stats Section */}
      <section className="stats-section">
        <div className="stats-grid">
          {stats.map((stat, index) => (
            <div key={index} className="stat-card">
              <span className="stat-value">{stat.value}</span>
              <span className="stat-label">{stat.label}</span>
            </div>
          ))}
        </div>
      </section>

      {/* Features Section */}
      <section className="features-section">
        <div className="section-header">
          <h2>Why CFU-Counter?</h2>
          <p>Advanced deep learning models trained specifically for bacterial colony analysis.</p>
        </div>
        <div className="features-grid">
          {features.map((feature, index) => (
            <div key={index} className="feature-card">
              <div className="feature-icon">{feature.icon}</div>
              <h3>{feature.title}</h3>
              <p>{feature.description}</p>
            </div>
          ))}
        </div>
      </section>

      {/* How It Works Section */}
      <section className="workflow-section">
        <div className="section-header">
          <h2>How It Works</h2>
          <p>Four simple steps from petri dish to actionable data.</p>
        </div>
        <div className="workflow-grid">
          {workflow.map((item, index) => (
            <div key={index} className="workflow-card">
              <div className="workflow-step">{item.step}</div>
              <h3>{item.title}</h3>
              <p>{item.description}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Use Cases Section */}
      <section className="usecases-section">
        <div className="section-header">
          <h2>Who Uses CFU-Counter?</h2>
          <p>Designed for researchers and professionals across microbiology.</p>
        </div>
        <div className="usecases-grid">
          <div className="usecase-card">
            <div className="usecase-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M22 10v6M2 10l10-5 10 5-10 5z"/>
                <path d="M6 12v5c3 3 9 3 12 0v-5"/>
              </svg>
            </div>
            <h3>Research Labs</h3>
            <p>Accelerate microbiology research with consistent, reproducible colony counts for your experiments.</p>
          </div>
          <div className="usecase-card">
            <div className="usecase-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/>
                <circle cx="12" cy="7" r="4"/>
              </svg>
            </div>
            <h3>Students & Educators</h3>
            <p>Learn microbiology techniques with instant feedback and detailed classification breakdowns.</p>
          </div>
          <div className="usecase-card">
            <div className="usecase-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
              </svg>
            </div>
            <h3>Quality Control</h3>
            <p>Integrate rapid colony counting into your food safety and pharmaceutical QC workflows.</p>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="cta-section">
        <h2>Ready to Transform Your Colony Counting?</h2>
        <p>
          Stop spending hours on manual counting. Get accurate, AI-powered results 
          that are consistent, reproducible, and ready for your reports.
        </p>
        <Link to="/analyzer" className="btn btn-primary btn-lg">
          Try the Analyzer Free
        </Link>
      </section>

      {/* About Project Section */}
      <section className="about-project-section">
        <div className="section-header">
          <h2>About the Project</h2>
          <p>Open-source AI for microbiology research</p>
        </div>
        <div className="about-project-content">
          <p>
            CFU-Counter is an open-source project that brings state-of-the-art computer vision 
            to microbiology labs. Traditional CFU (Colony Forming Unit) counting is time-consuming, 
            subjective, and prone to human error. Our solution leverages deep learning trained on 
            over 18,000 images from the AGAR dataset to provide fast, accurate, and reproducible results.
          </p>
          <p>
            The platform uses a dual-model architecture: <strong>YOLOv8</strong> for precise object 
            detection with bounding boxes, and a custom <strong>CNN regressor</strong> for fast count 
            estimation. Both models are optimized for deployment on edge devices like Raspberry Pi, 
            making AI-powered colony counting accessible to any lab.
          </p>
          <div className="project-links">
            <a href="https://github.com/RohanRajesh55/CFU-counter" target="_blank" rel="noopener noreferrer" className="btn btn-secondary">
              <svg viewBox="0 0 24 24" fill="currentColor" style={{ width: 18, height: 18 }}>
                <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/>
              </svg>
              View on GitHub
            </a>
          </div>
        </div>
      </section>
    </div>
  );
}

export default Home;
