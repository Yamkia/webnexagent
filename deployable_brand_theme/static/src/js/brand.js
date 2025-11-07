// Small JS enhancements for the White Label theme (optional)
document.addEventListener('DOMContentLoaded', () => {
  // Example: add a small accessibility toggle or adjust header on scroll
  const header = document.querySelector('.gm-header');
  if (!header) return;
  window.addEventListener('scroll', () => {
    if (window.scrollY > 20) header.classList.add('gm-header-scrolled');
    else header.classList.remove('gm-header-scrolled');
  });
});