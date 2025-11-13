# Advanced Styling Strategy Guide

## 🎨 SCSS Architecture Best Practices

### Design Token System

Create a centralized token system for consistent theming:

```scss
// static/src/scss/_tokens.scss

// Spacing scale (8px base)
$space-1: 0.25rem;  // 4px
$space-2: 0.5rem;   // 8px
$space-3: 0.75rem;  // 12px
$space-4: 1rem;     // 16px
$space-6: 1.5rem;   // 24px
$space-8: 2rem;     // 32px
$space-12: 3rem;    // 48px

// Typography scale
$text-xs: 0.75rem;   // 12px
$text-sm: 0.875rem;  // 14px
$text-base: 1rem;    // 16px
$text-lg: 1.125rem;  // 18px
$text-xl: 1.25rem;   // 20px
$text-2xl: 1.5rem;   // 24px
$text-3xl: 1.875rem; // 30px

// Font weights
$font-normal: 400;
$font-medium: 500;
$font-semibold: 600;
$font-bold: 700;

// Border radius
$radius-sm: 4px;
$radius-md: 8px;
$radius-lg: 12px;
$radius-xl: 16px;
$radius-full: 9999px;

// Shadows
$shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
$shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
$shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
$shadow-xl: 0 20px 25px -5px rgba(0, 0, 0, 0.1);

// Transitions
$transition-fast: 150ms cubic-bezier(0.4, 0, 0.2, 1);
$transition-base: 200ms cubic-bezier(0.4, 0, 0.2, 1);
$transition-slow: 300ms cubic-bezier(0.4, 0, 0.2, 1);
```

### CSS Custom Properties Pattern

```scss
// static/src/scss/brand.scss

:root {
  // Brand colors (set by backend)
  --brand-primary: #34D399;
  --brand-secondary: #0f766e;
  
  // Derived colors
  --brand-primary-light: color-mix(in srgb, var(--brand-primary) 80%, white);
  --brand-primary-dark: color-mix(in srgb, var(--brand-primary) 80%, black);
  
  // Semantic colors
  --color-success: #10b981;
  --color-warning: #f59e0b;
  --color-error: #ef4444;
  --color-info: #3b82f6;
  
  // Neutral palette
  --gray-50: #f9fafb;
  --gray-100: #f3f4f6;
  --gray-200: #e5e7eb;
  --gray-300: #d1d5db;
  --gray-500: #6b7280;
  --gray-700: #374151;
  --gray-900: #111827;
  
  // Spacing (use tokens)
  --space-unit: 0.25rem;
}
```

---

## 🌓 Dark Mode Implementation

### Approach 1: Automatic Detection

```scss
@media (prefers-color-scheme: dark) {
  :root {
    --brand-bg: #0f172a;
    --brand-text: #f1f5f9;
    --gray-50: #1e293b;
    --gray-900: #f8fafc;
  }
  
  body {
    background: var(--brand-bg);
    color: var(--brand-text);
  }
}
```

### Approach 2: Manual Toggle

```scss
body[data-theme="dark"] {
  --brand-bg: #0f172a;
  --brand-text: #f1f5f9;
  
  .gm-header {
    background: rgba(15, 23, 42, 0.8);
    border-bottom-color: rgba(255, 255, 255, 0.1);
  }
}
```

**JavaScript toggle:**

```javascript
// static/src/js/theme-toggle.js
const themeToggle = document.querySelector('[data-theme-toggle]');
themeToggle?.addEventListener('click', () => {
  const current = document.body.dataset.theme || 'light';
  const next = current === 'light' ? 'dark' : 'light';
  document.body.dataset.theme = next;
  localStorage.setItem('theme', next);
});

// Restore on load
document.body.dataset.theme = localStorage.getItem('theme') || 'light';
```

---

## 🚀 Performance Optimizations

### 1. Critical CSS Extraction

Extract above-the-fold styles for faster FCP:

```xml
<!-- views/assets.xml -->
<template id="critical_css" inherit_id="web.layout">
  <xpath expr="//head" position="inside">
    <style>
      /* Inline critical styles here */
      body { margin: 0; font-family: system-ui; }
      .gm-header { background: white; padding: 1rem 0; }
    </style>
  </xpath>
</template>
```

### 2. Lazy Load Brand-Specific Assets

```xml
<template id="assets_frontend_lazy" inherit_id="website.assets_frontend">
  <xpath expr="." position="inside">
    <link rel="preload" href="/deployable_brand_theme/static/src/scss/brand.scss" as="style"/>
    <link rel="stylesheet" href="/deployable_brand_theme/static/src/scss/brand.scss" media="print" onload="this.media='all'"/>
  </xpath>
</template>
```

### 3. Asset Versioning

Add cache busting via query params:

```python
# models/website.py
def get_brand_asset_version(self):
    return self.brand_id.write_date.timestamp() if self.brand_id else '1.0'
```

```xml
<link t-attf-href="/deployable_brand_theme/static/src/scss/brand.scss?v={{ website.get_brand_asset_version() }}" rel="stylesheet"/>
```

---

## 🎯 Component Library Pattern

### Button Component

```scss
// static/src/scss/components/_button.scss

.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: $space-2 $space-4;
  font-weight: $font-semibold;
  border-radius: $radius-md;
  transition: all $transition-base;
  cursor: pointer;
  
  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
}

.btn-primary {
  background: linear-gradient(135deg, var(--brand-primary), var(--brand-secondary));
  color: white;
  border: none;
  
  &:hover:not(:disabled) {
    transform: translateY(-1px);
    box-shadow: $shadow-lg;
  }
}

.btn-secondary {
  background: transparent;
  color: var(--brand-primary);
  border: 2px solid var(--brand-primary);
  
  &:hover:not(:disabled) {
    background: var(--brand-primary);
    color: white;
  }
}

.btn-ghost {
  background: transparent;
  color: var(--brand-primary);
  border: none;
  
  &:hover:not(:disabled) {
    background: var(--brand-primary-light);
  }
}

// Size variants
.btn-sm { padding: $space-1 $space-3; font-size: $text-sm; }
.btn-lg { padding: $space-3 $space-6; font-size: $text-lg; }
```

### Card Component

```scss
// static/src/scss/components/_card.scss

.card {
  background: white;
  border-radius: $radius-lg;
  box-shadow: $shadow-md;
  overflow: hidden;
  transition: box-shadow $transition-base;
  
  &:hover {
    box-shadow: $shadow-xl;
  }
  
  &-header {
    padding: $space-4;
    border-bottom: 1px solid var(--gray-200);
    border-top: 3px solid var(--brand-primary);
  }
  
  &-body {
    padding: $space-4;
  }
  
  &-footer {
    padding: $space-4;
    background: var(--gray-50);
    border-top: 1px solid var(--gray-200);
  }
}

// Brand variant
.card-brand {
  border-top-width: 4px;
  
  .card-header {
    background: linear-gradient(135deg, var(--brand-primary), var(--brand-secondary));
    color: white;
    border-bottom: none;
  }
}
```

---

## 📐 Responsive Design Tokens

```scss
// static/src/scss/_breakpoints.scss

$breakpoint-sm: 640px;
$breakpoint-md: 768px;
$breakpoint-lg: 1024px;
$breakpoint-xl: 1280px;
$breakpoint-2xl: 1536px;

@mixin respond-above($breakpoint) {
  @media (min-width: $breakpoint) {
    @content;
  }
}

@mixin respond-below($breakpoint) {
  @media (max-width: $breakpoint - 1px) {
    @content;
  }
}

// Usage:
.container {
  padding: $space-4;
  
  @include respond-above($breakpoint-md) {
    padding: $space-8;
  }
  
  @include respond-above($breakpoint-lg) {
    padding: $space-12;
    max-width: 1200px;
    margin: 0 auto;
  }
}
```

---

## 🎨 Brand-Specific Advanced Overrides

### Example: Luxury Brand with Animations

```scss
// static/src/scss/brands/_luxe.scss

body.brand-luxe {
  // Gradient backgrounds
  background: linear-gradient(135deg, #faf5ff 0%, #f3e8ff 100%);
  
  .gm-header {
    backdrop-filter: blur(20px);
    border-bottom: 2px solid rgba(168, 85, 247, 0.2);
    
    &::after {
      content: '';
      position: absolute;
      bottom: 0;
      left: 0;
      right: 0;
      height: 2px;
      background: linear-gradient(90deg, 
        transparent 0%, 
        var(--brand-primary) 50%, 
        transparent 100%
      );
      opacity: 0;
      transition: opacity $transition-slow;
    }
    
    &.gm-header-scrolled::after {
      opacity: 1;
    }
  }
  
  .btn-brand {
    position: relative;
    overflow: hidden;
    
    &::before {
      content: '';
      position: absolute;
      inset: 0;
      background: linear-gradient(135deg, 
        rgba(255,255,255,0.2) 0%, 
        transparent 100%
      );
      transform: translateX(-100%);
      transition: transform $transition-slow;
    }
    
    &:hover::before {
      transform: translateX(100%);
    }
  }
  
  // Glassmorphism cards
  .card {
    background: rgba(255, 255, 255, 0.7);
    backdrop-filter: blur(10px);
    border: 1px solid rgba(168, 85, 247, 0.1);
  }
}
```

---

## 🔍 Accessibility Considerations

```scss
// Ensure sufficient color contrast
@function check-contrast($color1, $color2) {
  // Use a contrast checker library or implement WCAG formula
}

// Focus states
:focus-visible {
  outline: 2px solid var(--brand-primary);
  outline-offset: 2px;
}

// Reduced motion support
@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}

// High contrast mode
@media (prefers-contrast: high) {
  .btn-brand {
    border: 2px solid currentColor;
  }
}
```

---

## 📦 File Organization

```
static/src/scss/
├── brand.scss                  # Main entry (imports all)
├── _tokens.scss                # Design tokens
├── _breakpoints.scss           # Responsive mixins
├── _utilities.scss             # Utility classes
├── base/
│   ├── _reset.scss
│   ├── _typography.scss
│   └── _layout.scss
├── components/
│   ├── _button.scss
│   ├── _card.scss
│   ├── _form.scss
│   ├── _header.scss
│   └── _footer.scss
└── brands/
    ├── _greenmotive.scss
    ├── _techpro.scss
    └── _luxe.scss
```

**Import order in `brand.scss`:**

```scss
// 1. Tokens & config
@import 'tokens';
@import 'breakpoints';

// 2. Base styles
@import 'base/reset';
@import 'base/typography';
@import 'base/layout';

// 3. Components
@import 'components/button';
@import 'components/card';
@import 'components/form';

// 4. Brand overrides
@import 'brands/greenmotive';
@import 'brands/techpro';
@import 'brands/luxe';

// 5. Utilities (last to override)
@import 'utilities';
```

---

## 🎯 Summary

✅ Use design tokens for consistency  
✅ Leverage CSS custom properties for runtime theming  
✅ Support dark mode with media queries or manual toggle  
✅ Optimize performance with critical CSS and lazy loading  
✅ Build reusable component library  
✅ Implement responsive design with mixins  
✅ Ensure accessibility (contrast, focus, reduced motion)  
✅ Organize SCSS with clear file structure  
