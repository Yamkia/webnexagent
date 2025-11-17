// Dynamic Theme Switcher for Glassmorphism Theme
(function() {
    'use strict';

    // Add theme class to body
    document.addEventListener('DOMContentLoaded', function() {
        document.body.classList.add('glassmorphism-theme');
        
        // Animate cards on load
        animateCardsOnLoad();
        
        // Add particle effect
        createStarfield();
        
        // Enhanced glow on hover
        addInteractiveGlow();
    });

    function animateCardsOnLoad() {
        const cards = document.querySelectorAll('.o_kanban_record, .o_form_sheet');
        cards.forEach((card, index) => {
            setTimeout(() => {
                card.style.animation = 'fadeInUp 0.6s ease forwards';
            }, index * 100);
        });
    }

    function createStarfield() {
        // Create animated starfield background
        const starfield = document.createElement('div');
        starfield.className = 'starfield-background';
        starfield.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            z-index: -1;
            pointer-events: none;
        `;

        // Add shooting stars
        for (let i = 0; i < 5; i++) {
            setTimeout(() => {
                createShootingStar(starfield);
            }, Math.random() * 5000);
        }

        document.body.prepend(starfield);
    }

    function createShootingStar(container) {
        const star = document.createElement('div');
        star.className = 'shooting-star';
        star.style.cssText = `
            position: absolute;
            top: ${Math.random() * 50}%;
            left: ${Math.random() * 100}%;
            width: 2px;
            height: 2px;
            background: linear-gradient(90deg, #00d4ff, transparent);
            border-radius: 50%;
            box-shadow: 0 0 10px #00d4ff, 0 0 20px #00d4ff;
            animation: shoot 2s linear forwards;
        `;

        container.appendChild(star);
        setTimeout(() => star.remove(), 2000);

        // Repeat
        setTimeout(() => createShootingStar(container), Math.random() * 8000 + 5000);
    }

    function addInteractiveGlow() {
        document.addEventListener('mousemove', function(e) {
            const cards = document.querySelectorAll('.o_kanban_record, .o_form_sheet, .modal-content');
            
            cards.forEach(card => {
                const rect = card.getBoundingClientRect();
                const x = e.clientX - rect.left;
                const y = e.clientY - rect.top;
                
                if (x > 0 && x < rect.width && y > 0 && y < rect.height) {
                    const xPercent = (x / rect.width) * 100;
                    const yPercent = (y / rect.height) * 100;
                    
                    card.style.background = `
                        radial-gradient(circle at ${xPercent}% ${yPercent}%, 
                        rgba(0, 212, 255, 0.15) 0%, 
                        rgba(30, 33, 57, 0.6) 50%)
                    `;
                }
            });
        });
    }

    // Add CSS animations
    const style = document.createElement('style');
    style.textContent = `
        @keyframes fadeInUp {
            from {
                opacity: 0;
                transform: translateY(30px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }

        @keyframes shoot {
            0% {
                transform: translateX(0) translateY(0);
                opacity: 1;
            }
            100% {
                transform: translateX(300px) translateY(300px);
                opacity: 0;
            }
        }

        @keyframes pulse-glow {
            0%, 100% {
                box-shadow: 0 0 20px rgba(0, 212, 255, 0.5),
                           0 0 40px rgba(0, 212, 255, 0.3);
            }
            50% {
                box-shadow: 0 0 30px rgba(0, 212, 255, 0.8),
                           0 0 60px rgba(0, 212, 255, 0.5);
            }
        }

        .glassmorphism-theme .o_kanban_record,
        .glassmorphism-theme .btn-primary {
            animation: pulse-glow 3s ease-in-out infinite;
        }
    `;
    document.head.appendChild(style);

})();
