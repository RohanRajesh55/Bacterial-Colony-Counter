
import { useEffect, useState } from 'react';
import { driver } from 'driver.js';
import 'driver.js/dist/driver.css';

const Tutorial = ({ isActive, onComplete }) => {
  const [driverObj, setDriverObj] = useState(null);

  useEffect(() => {
    const driverInstance = driver({
      showProgress: true,
      animate: true,
      doneBtnText: 'Finish',
      nextBtnText: 'Next',
      prevBtnText: 'Previous',
      onDestroyed: () => {
        if (onComplete) onComplete();
      },
      steps: [
        { 
          element: '.analyzer-header h1', 
          popover: { 
            title: 'Welcome to CFU-Counter', 
            description: 'This tool uses AI to count bacterial colonies in seconds. Let\'s take a quick tour.' 
          } 
        },
        { 
          element: '.upload-area', 
          popover: { 
            title: 'Upload Your Image', 
            description: 'Drag & drop your petri dish image here, or click to select a file. We support JPEG, PNG, and BMP.' 
          } 
        },
        { 
          element: '.settings-panel', 
          popover: { 
            title: 'Choose Your Model', 
            description: 'Select "YOLOv8" for detailed detection boxes, or "CNN" for a super-fast estimated count.' 
          } 
        },
        { 
          element: '.analyze-btn', 
          popover: { 
            title: 'Start Analysis', 
            description: 'Click here to let our AI process your image. Results will appear below automatically.' 
          } 
        },
        { 
          element: '.history-badge', 
          popover: { 
            title: 'View History', 
            description: 'Accidentally closed the page? Check your past results in the History tab.' 
          } 
        }
      ]
    });

    setDriverObj(driverInstance);
  }, [onComplete]);

  useEffect(() => {
    if (isActive && driverObj) {
      driverObj.drive();
    }
  }, [isActive, driverObj]);

  return null;
};

export default Tutorial;
