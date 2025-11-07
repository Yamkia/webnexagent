import React from 'react';
import { motion } from 'framer-motion';

const MagnettoDashboard = () => {
  return (
    <div className="magnetto-container" style={{ backgroundColor: 'red' }}>
      {/* Hero Section */}
      <section className="hero">
        <div className="hero-left">
          <motion.h1 
            className="magnetto-title"
            initial={{ opacity: 0, y: 50 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
          >
            MAGNETTO
          </motion.h1>
          <motion.h2 
            className="magnetto-subtitle"
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.2 }}
          >
            DESIGN STUDIO · LONDON
          </motion.h2>
        </div>
        <div className="hero-right">
          <motion.p 
            className="magnetto-description"
            initial={{ opacity: 0, x: 50 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.5, delay: 0.4 }}
          >
            We are a digital design studio based in London, creating innovative and impactful solutions for brands worldwide.
          </motion.p>
        </div>
      </section>

      {/* Navigation Bar */}
      <motion.nav 
        className="magnetto-nav"
        initial={{ opacity: 0, y: 50 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.6 }}
      >
        <img src="path/to/user-image.jpg" alt="User" className="user-image" />
        <ul className="nav-links">
          <li><a href="#">HOME</a></li>
          <li><a href="#">ABOUT</a></li>
          <li><a href="#">PROJECTS</a></li>
          <li><a href="#">JOURNAL</a></li>
        </ul>
        <button className="contact-button">CONTACT +</button>
      </motion.nav>
    </div>
  );
};

export default MagnettoDashboard;

/*
  To use this component, update your App.js:

  import MagnettoDashboard from './MagnettoDashboard';

  function App() {
    return (
      <div className="App">
        <MagnettoDashboard />
      </div>
    );
  }

  export default App;

*/