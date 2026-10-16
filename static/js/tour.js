// ============================================================
// WEBSITE TOUR — generic spotlight + tooltip walkthrough
// A page defines window.NEXORA_TOUR_STEPS = [{selector, title, text}, ...]
// If the current page has no steps defined, we redirect home and auto-start there.
// ============================================================
(function () {
  let steps = [];
  let idx = 0;
  let overlay, spotlight, tooltip;

  function build() {
    overlay = document.createElement('div');
    overlay.className = 'tour-overlay';
    spotlight = document.createElement('div');
    spotlight.className = 'tour-spotlight';
    tooltip = document.createElement('div');
    tooltip.className = 'tour-tooltip';
    overlay.appendChild(spotlight);
    overlay.appendChild(tooltip);
    document.body.appendChild(overlay);
    requestAnimationFrame(() => overlay.classList.add('open'));
  }

  function positionFor(el) {
    const r = el.getBoundingClientRect();
    const pad = 10;
    spotlight.style.top = (r.top - pad) + 'px';
    spotlight.style.left = (r.left - pad) + 'px';
    spotlight.style.width = (r.width + pad * 2) + 'px';
    spotlight.style.height = (r.height + pad * 2) + 'px';

    const tooltipWidth = Math.min(300, window.innerWidth - 40);
    let top = r.bottom + 18;
    let left = Math.min(Math.max(r.left, 16), window.innerWidth - tooltipWidth - 16);
    if (top + 190 > window.innerHeight) top = Math.max(r.top - 200, 16);
    tooltip.style.top = top + 'px';
    tooltip.style.left = left + 'px';
  }

  function render() {
    const step = steps[idx];
    const el = document.querySelector(step.selector);
    if (!el) { advance(1); return; }
    el.scrollIntoView({ behavior: 'smooth', block: 'center' });
    setTimeout(() => {
      positionFor(el);
      tooltip.innerHTML = `
        <p class="text-xs font-semibold mb-1" style="color:var(--mint)">Step ${idx + 1} of ${steps.length}</p>
        <p class="font-display font-semibold text-cream mb-1.5">${step.title}</p>
        <p class="text-sm text-cream/65 mb-4 leading-relaxed">${step.text}</p>
        <div class="flex items-center justify-between gap-2">
          <button onclick="window.__tourEnd()" class="text-xs text-cream/45 hover:text-cream transition-colors">Skip tour</button>
          <div class="flex gap-2">
            ${idx > 0 ? `<button onclick="window.__tourStep(-1)" class="btn btn-outline on-dark btn-sm">Back</button>` : ''}
            <button onclick="window.__tourStep(1)" class="btn btn-accent btn-sm">${idx === steps.length - 1 ? 'Finish' : 'Next'}</button>
          </div>
        </div>`;
      if (window.lucide) lucide.createIcons();
    }, 340);
  }

  function advance(delta) {
    idx += delta;
    if (idx < 0) idx = 0;
    if (idx >= steps.length) { end(); return; }
    render();
  }

  function end() {
    if (!overlay) return;
    overlay.classList.remove('open');
    setTimeout(() => { overlay.remove(); overlay = null; }, 250);
    showToast && showToast('Tour finished — explore at your own pace!', { icon: 'compass' });
  }

  window.__tourStep = advance;
  window.__tourEnd = end;

  window.startWebsiteTour = function () {
    if (window.NEXORA_TOUR_STEPS && window.NEXORA_TOUR_STEPS.length) {
      steps = window.NEXORA_TOUR_STEPS;
      idx = 0;
      build();
      render();
    } else {
      window.location.href = '/?tour=1';
    }
  };

  document.addEventListener('DOMContentLoaded', () => {
    const params = new URLSearchParams(window.location.search);
    if (params.get('tour') === '1' && window.NEXORA_TOUR_STEPS) {
      setTimeout(() => window.startWebsiteTour(), 500);
    }
  });
})();
