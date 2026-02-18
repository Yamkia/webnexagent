// Dev-only overlay helper. Run in console: window.__cssProbe.toggle()
(function () {
  if (window.__cssProbe) return;
  const state = { active: false, layers: [] };

  function clear() {
    state.layers.forEach((el) => el.remove());
    state.layers = [];
  }

  function overlaySelector(sel) {
    const nodes = document.querySelectorAll(sel);
    nodes.forEach((node, idx) => {
      const rect = node.getBoundingClientRect();
      const layer = document.createElement('div');
      layer.style.position = 'fixed';
      layer.style.left = `${rect.left}px`;
      layer.style.top = `${rect.top}px`;
      layer.style.width = `${rect.width}px`;
      layer.style.height = `${rect.height}px`;
      layer.style.border = '1px solid rgba(56,189,248,0.8)';
      layer.style.background = 'rgba(56,189,248,0.08)';
      layer.style.zIndex = 99999;
      layer.style.pointerEvents = 'none';
      layer.style.borderRadius = '6px';
      layer.style.boxShadow = '0 0 0 1px rgba(14,165,233,0.3)';

      const label = document.createElement('div');
      label.textContent = `${sel}#${idx}`;
      label.style.position = 'absolute';
      label.style.left = '0';
      label.style.top = '-18px';
      label.style.padding = '2px 6px';
      label.style.fontSize = '11px';
      label.style.fontFamily = 'monospace';
      label.style.background = 'rgba(15,23,42,0.9)';
      label.style.color = '#e0f2fe';
      label.style.borderRadius = '4px';
      label.style.border = '1px solid rgba(56,189,248,0.6)';
      label.style.pointerEvents = 'none';
      layer.appendChild(label);

      state.layers.push(layer);
      document.body.appendChild(layer);
    });
  }

  function toggle(selectors = ['header', '.o_main_navbar', '.o_action_manager', '.o_app', '.o_kanban_record']) {
    if (state.active) {
      clear();
      state.active = false;
      console.log('[css-probe] overlay off');
      return;
    }
    clear();
    selectors.forEach(overlaySelector);
    state.active = true;
    console.log('[css-probe] overlay on for selectors:', selectors);
  }

  window.__cssProbe = { toggle };
})();
