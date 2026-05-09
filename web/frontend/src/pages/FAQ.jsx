import { useState } from 'react';

function FAQ() {
  const [openIndex, setOpenIndex] = useState(null);

  const faqCategories = [
    {
      title: 'Getting Started',
      faqs: [
        {
          question: 'What image formats are supported?',
          answer: 'CFU-Counter supports JPEG, PNG, and BMP image formats. For best results, use high-resolution images (1000x1000 pixels or higher) with good lighting and minimal glare.'
        },
        {
          question: 'What is the ideal image for analysis?',
          answer: 'The best images are taken from directly above the petri dish with even lighting, no shadows or reflections, and the dish filling most of the frame. Avoid images where colonies are touching or overlapping heavily.'
        },
        {
          question: 'How do I get started?',
          answer: 'Simply navigate to the Analyzer page, upload your petri dish image, select your preferred model (YOLO for detection or CNN for quick counting), and click Analyze. Results appear within seconds.'
        },
      ]
    },
    {
      title: 'Models & Analysis',
      faqs: [
        {
          question: 'Which model should I use - YOLO or CNN?',
          answer: 'Use YOLO when you need to see individual colony locations, species classifications, and bounding boxes - ideal for mixed cultures or documentation. Use CNN for faster processing when you only need the total count - ideal for pure cultures and high-throughput screening.'
        },
        {
          question: 'How accurate is the detection?',
          answer: 'Our YOLO model achieves ~92% mAP on the AGAR validation set. Accuracy depends on image quality and colony density. The models perform best on well-separated colonies with clear contrast against the agar.'
        },
        {
          question: 'What does the confidence threshold do?',
          answer: 'The confidence threshold (default 40%) filters out detections below that confidence level. Lower thresholds detect more colonies but may include false positives. Higher thresholds are more conservative but may miss faint colonies. Adjust based on your needs.'
        },
        {
          question: 'Why are some colonies not detected?',
          answer: 'Colonies may be missed if they are: very small or faint, overlapping with other colonies, near the dish edge, or in areas with poor lighting. Try improving image quality or lowering the confidence threshold.'
        },
      ]
    },
    {
      title: 'Bacterial Classes',
      faqs: [
        {
          question: 'What bacterial species can be detected?',
          answer: 'The classifier identifies 7 classes: B.subtilis (Bacillus subtilis), C.albicans (Candida albicans), E.coli (Escherichia coli), P.aeruginosa (Pseudomonas aeruginosa), S.aureus (Staphylococcus aureus), plus Contamination and Defect categories.'
        },
        {
          question: 'Can it detect species not in the training set?',
          answer: 'The model will still detect colonies from unknown species, but may misclassify them as one of the 7 trained classes. For accurate species identification, the bacteria should match one of the supported classes.'
        },
        {
          question: 'What are "Contamination" and "Defect" classes?',
          answer: 'Contamination refers to environmental microorganisms that accidentally entered the plate. Defect refers to agar artifacts like bubbles, cracks, or scratches that might be mistaken for colonies.'
        },
      ]
    },
    {
      title: 'Data & Privacy',
      faqs: [
        {
          question: 'Is my data stored on your servers?',
          answer: 'Images are processed in real-time and are NOT permanently stored on our servers. After analysis, images are immediately discarded. Your analysis history is saved only in your browser\'s local storage.'
        },
        {
          question: 'Can I export my results?',
          answer: 'Yes! On the History page, you can export all your analyses to CSV format. The annotated images can be downloaded directly from the results panel after each analysis.'
        },
        {
          question: 'Will my history persist between devices?',
          answer: 'Currently, history is stored in your browser\'s local storage and does not sync between devices. Clearing your browser data will also clear your history. We recommend exporting important results.'
        },
      ]
    },
    {
      title: 'Technical & Deployment',
      faqs: [
        {
          question: 'Can I run this locally?',
          answer: 'Yes! CFU-Counter is open source and can be deployed locally using Docker. Clone the repository from GitHub, run docker-compose up, and access the application at localhost. This is ideal for air-gapped environments or high-security labs.'
        },
        {
          question: 'Can it run on a Raspberry Pi?',
          answer: 'Yes, the system is optimized for edge deployment. The CNN model runs well on Raspberry Pi 4 (4GB+ RAM). YOLO inference is slower on Pi but still functional. GPU-powered machines provide the best performance.'
        },
        {
          question: 'Is there an API for integration?',
          answer: 'Yes, the backend exposes a REST API at /predict endpoint. You can POST an image and receive JSON results. See the API documentation on GitHub for details on integrating with your existing pipelines.'
        },
      ]
    },
    {
      title: 'Troubleshooting',
      faqs: [
        {
          question: 'Why is the analysis taking too long?',
          answer: 'Analysis typically takes 2-5 seconds. Slow processing may be due to: large image files (try resizing to ~2000x2000), server load, or slow network connection. The CNN model is faster than YOLO if speed is critical.'
        },
        {
          question: 'The count seems wrong - what should I do?',
          answer: 'Try: 1) Improving image quality and lighting, 2) Ensuring the dish is centered and fills the frame, 3) Adjusting the confidence threshold, 4) Using the other model (YOLO vs CNN). For dense plates with overlapping colonies, manual adjustment may be needed.'
        },
        {
          question: 'Can I use this for production/clinical use?',
          answer: 'CFU-Counter is designed as a research and educational tool. For clinical or production use, validate results against manual counts per your lab\'s quality assurance protocols. The tool should augment, not replace, professional judgment.'
        },
      ]
    },
  ];

  const toggleFaq = (categoryIndex, faqIndex) => {
    const key = `${categoryIndex}-${faqIndex}`;
    setOpenIndex(openIndex === key ? null : key);
  };

  return (
    <div className="faq-page">
      <div className="page-header">
        <h1>Frequently Asked Questions</h1>
        <p>Everything you need to know about using CFU-Counter.</p>
      </div>

      <div className="faq-categories">
        {faqCategories.map((category, categoryIndex) => (
          <div key={categoryIndex} className="faq-category">
            <h2 className="faq-category-title">{category.title}</h2>
            <div className="faq-list">
              {category.faqs.map((faq, faqIndex) => {
                const key = `${categoryIndex}-${faqIndex}`;
                return (
                  <div 
                    key={faqIndex} 
                    className={`faq-item ${openIndex === key ? 'open' : ''}`}
                  >
                    <button 
                      className="faq-question"
                      onClick={() => toggleFaq(categoryIndex, faqIndex)}
                    >
                      <span>{faq.question}</span>
                      <svg 
                        className="faq-icon" 
                        viewBox="0 0 24 24" 
                        fill="none" 
                        stroke="currentColor" 
                        strokeWidth="2" 
                        strokeLinecap="round" 
                        strokeLinejoin="round"
                      >
                        <polyline points="6 9 12 15 18 9"></polyline>
                      </svg>
                    </button>
                    <div className="faq-answer">
                      <p>{faq.answer}</p>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        ))}
      </div>

      <div className="faq-contact">
        <h3>Still have questions?</h3>
        <p>
          Check out our <a href="https://github.com/RohanRajesh55/CFU-counter" target="_blank" rel="noopener noreferrer">GitHub repository</a> for 
          documentation, or open an issue for support.
        </p>
      </div>
    </div>
  );
}

export default FAQ;
