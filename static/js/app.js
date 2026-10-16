// ---------------------------------------------------------------- Toasts
function showToast(message, opts = {}) {
  const container = document.getElementById('toast-container');
  if (!container) return;
  const icon = opts.icon || 'check-circle-2';
  const el = document.createElement('div');
  el.className = 'toast';
  el.innerHTML = `<i data-lucide="${icon}" class="w-4 h-4 text-mint shrink-0"></i><span>${message}</span>`;
  container.appendChild(el);
  if (window.lucide) lucide.createIcons({ nodes: [el] });
  setTimeout(() => {
    el.classList.add('leaving');
    setTimeout(() => el.remove(), 250);
  }, 3200);
}

// ---------------------------------------------------------------- Demo role
async function setDemoRole(role) {
  try {
    await fetch('/api/demo-role', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ role }),
    });
  } catch (e) { /* demo only */ }
  const destinations = {
    guest: '/',
    seeker: '/dashboard/seeker',
    employer: '/dashboard/employer',
    admin: '/admin',
  };
  window.location.href = destinations[role] || '/';
}

function toggleDemoMenu() {
  document.getElementById('demo-menu').classList.toggle('hidden');
}
document.addEventListener('click', (e) => {
  const menu = document.getElementById('demo-menu');
  const btn = document.getElementById('demo-switcher-btn');
  if (menu && !menu.classList.contains('hidden') && !menu.contains(e.target) && e.target !== btn && !btn.contains(e.target)) {
    menu.classList.add('hidden');
  }
});

// ---------------------------------------------------------------- Mobile nav
function openMobileNav() {
  document.getElementById('mobile-nav-overlay').classList.add('open');
  document.getElementById('mobile-nav-drawer').classList.add('open');
}
function closeMobileNav() {
  document.getElementById('mobile-nav-overlay').classList.remove('open');
  document.getElementById('mobile-nav-drawer').classList.remove('open');
}
document.getElementById('mobile-nav-btn')?.addEventListener('click', openMobileNav);

// ---------------------------------------------------------------- Modal / Drawer helpers
function openModal(id) {
  document.getElementById(id + '-overlay')?.classList.add('open');
  document.getElementById(id)?.classList.add('open');
}
function closeModal(id) {
  document.getElementById(id + '-overlay')?.classList.remove('open');
  document.getElementById(id)?.classList.remove('open');
}
function openDrawer(id) {
  document.getElementById(id + '-overlay')?.classList.add('open');
  document.getElementById(id)?.classList.add('open');
}
function closeDrawer(id) {
  document.getElementById(id + '-overlay')?.classList.remove('open');
  document.getElementById(id)?.classList.remove('open');
}

// ---------------------------------------------------------------- Save job (shared button behaviour)
async function toggleSaveJob(jobId, btn) {
  try {
    const res = await fetch(`/api/jobs/${jobId}/save`, { method: 'POST' });
    const data = await res.json();
    document.querySelectorAll(`[data-save-btn="${jobId}"]`).forEach((el) => {
      el.classList.toggle('is-saved', data.saved);
      const icon = el.querySelector('i');
      if (icon) icon.setAttribute('fill', data.saved ? 'currentColor' : 'none');
      const label = el.querySelector('[data-save-label]');
      if (label) label.textContent = data.saved ? 'Saved' : 'Save';
    });
    document.querySelectorAll('[data-saved-count]').forEach((el) => { el.textContent = data.saved_count; });
    showToast(data.saved ? 'Job saved to your list.' : 'Removed from saved jobs.', { icon: data.saved ? 'bookmark-check' : 'bookmark-minus' });
    if (window.lucide) lucide.createIcons();
  } catch (e) { /* demo only */ }
}

// Animated counters for dashboard metrics
function animateCounter(el, target, opts = {}) {
  const duration = opts.duration || 900;
  const prefix = opts.prefix || '';
  const suffix = opts.suffix || '';
  const start = 0;
  const startTime = performance.now();
  function tick(now) {
    const progress = Math.min((now - startTime) / duration, 1);
    const eased = 1 - Math.pow(1 - progress, 3);
    const value = Math.round(start + (target - start) * eased);
    el.textContent = prefix + value.toLocaleString() + suffix;
    if (progress < 1) requestAnimationFrame(tick);
  }
  requestAnimationFrame(tick);
}
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('[data-counter]').forEach((el) => {
    const target = parseInt(el.dataset.counter, 10) || 0;
    animateCounter(el, target, { prefix: el.dataset.prefix || '', suffix: el.dataset.suffix || '' });
  });
});
