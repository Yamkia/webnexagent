import React from 'react';
import { motion } from 'framer-motion';

// Card data for easy mapping
const cardData = [
  {
    label: 'Resources',
    icon: '+',
    title: 'ECO-URBAN DEVELOPMENT',
    color: 'text-green-500',
  },
  {
    label: 'Management',
    icon: 'O',
    title: 'CONSERVATION TECHNOLOGIES',
    color: 'text-blue-500',
  },
  {
    label: 'Development',
    icon: 'X',
    title: 'RESTORE OUR OCEANS',
    color: 'text-indigo-500',
  },
];

// Framer Motion variants for animations
const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.2, // Stagger the animation of children
    },
  },
};

const itemVariants = {
  hidden: { y: 20, opacity: 0 },
  visible: {
    y: 0,
    opacity: 1,
    transition: {
      type: 'spring',
      stiffness: 100,
    },
  },
};

const cardHoverEffect = {
  scale: 1.05,
  boxShadow: '0px 10px 30px rgba(0, 0, 0, 0.1)',
  transition: {
    type: 'spring',
    stiffness: 300,
  },
};

/**
 * A single glassmorphic card component.
 */
const GlassCard = ({ card }) => (
  <motion.div
    variants={itemVariants}
    whileHover={cardHoverEffect}
    className="w-full md:w-72 h-96 rounded-3xl p-8 flex flex-col justify-between cursor-pointer
               bg-white/50 backdrop-blur-md shadow-lg border border-white/30"
  >
    <span className="text-sm font-medium text-gray-500">{card.label}</span>
    <div className={`text-7xl font-thin text-center ${card.color}`}>{card.icon}</div>
    <h3 className="text-xl font-bold text-gray-800 text-center">{card.title}</h3>
  </motion.div>
);

/**
 * The main GreenMotive component with a hero-style layout.
 */
const GreenMotive = () => {
  return (
    <div className="min-h-screen w-full flex flex-col font-sans text-gray-800 p-4 sm:p-6 lg:p-8">
      {/* Top Navigation Bar */}
      <motion.nav
        initial={{ y: -100, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ type: 'spring', stiffness: 120, delay: 0.2 }}
        className="w-full flex justify-between items-center"
      >
        <div className="flex items-center gap-4 sm:gap-6">
          <button className="flex items-center gap-2 font-semibold hover:text-green-600 transition-colors">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              className="h-6 w-6"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M4 6h16M4 12h16m-7 6h7"
              />
            </svg>
            <span className="hidden sm:inline">Menu</span>
          </button>
          <button className="font-semibold hover:text-green-600 transition-colors hidden md:block">
            Discover Innovations
          </button>
        </div>
        <button
          className="font-semibold border-2 border-gray-800 rounded-full px-4 py-2 
                     hover:bg-gray-800 hover:text-white transition-all duration-300"
        >
          Renewable Energy Solutions
        </button>
      </motion.nav>

      {/* Main Content */}
      <main className="flex-grow flex flex-col items-center justify-center text-center pt-16 pb-8">
        <motion.h1
          initial={{ y: 20, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ type: 'spring', stiffness: 100, delay: 0.5 }}
          className="text-6xl md:text-8xl font-bold tracking-tighter mb-16"
        >
          GreenMotive
        </motion.h1>

        {/* Glassmorphism Cards Section */}
        <motion.div
          variants={containerVariants}
          initial="hidden"
          animate="visible"
          className="flex flex-col md:flex-row items-center justify-center gap-8"
        >
          {cardData.map((card) => (
            <GlassCard key={card.title} card={card} />
          ))}
        </motion.div>
      </main>
    </div>
  );
};

export default GreenMotive;


/* To use this component, update your App.js:

import GreenMotive from './GreenMotive';

function App() {
  return (
    <div className="App">
      <GreenMotive />
    </div>
  );
}

export default App;

*/