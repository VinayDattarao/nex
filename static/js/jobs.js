(function () {
  const jobs = window.NEXORA_JOBS || [];
  const opts = window.NEXORA_FILTER_OPTIONS || {};
  const savedIds = new Set(window.NEXORA_SAVED || []);

  const state = {
    keyword: '',
    location: '',
    industries: new Set(),
    jobTypes: new Set(),
    workModes: new Set(),
    experience: new Set(),
    minSalary: 0,
    datePosted: 'any',
    sort: 'relevance',
  };

  function daysLabel(d) {
    if (d === 0) return 'Today';
    if (d === 1) return '1 day ago';
    return `${d} days ago`;
  }

  function filterPanelHTML() {
    const chk = (name, value, groupSet) => `
      <label class="flex items-center gap-2.5 py-1.5 text-sm cursor-pointer">
        <input type="checkbox" data-group="${name}" value="${value}" class="w-4 h-4 rounded border-grey-line text-indigo focus:ring-indigo" ${groupSet.has(value) ? 'checked' : ''}>
        <span>${value}</span>
      </label>`;
    return `
      <div class="mb-6">
        <p class="text-xs font-semibold text-ink/40 mb-2">Job type</p>
        ${opts.jobTypes.map(v => chk('jobTypes', v, state.jobTypes)).join('')}
      </div>
      <div class="mb-6">
        <p class="text-xs font-semibold text-ink/40 mb-2">Work mode</p>
        ${opts.workModes.map(v => chk('workModes', v, state.workModes)).join('')}
      </div>
      <div class="mb-6">
        <p class="text-xs font-semibold text-ink/40 mb-2">Industry</p>
        <div class="max-h-40 overflow-y-auto scrollbar-thin pr-1">${opts.industries.map(v => chk('industries', v, state.industries)).join('')}</div>
      </div>
      <div class="mb-6">
        <p class="text-xs font-semibold text-ink/40 mb-2">Experience</p>
        ${opts.experienceLevels.map(v => chk('experience', v, state.experience)).join('')}
      </div>
      <div class="mb-6">
        <p class="text-xs font-semibold text-ink/40 mb-2">Minimum salary</p>
        <input type="range" min="0" max="150000" step="10000" value="${state.minSalary}" data-range="minSalary" class="w-full accent-indigo">
        <p class="text-xs text-ink/50 mt-1" id="min-salary-label">$${state.minSalary.toLocaleString()}+</p>
      </div>
      <div class="mb-2">
        <p class="text-xs font-semibold text-ink/40 mb-2">Date posted</p>
        <select data-select="datePosted" class="w-full text-sm border border-grey-line rounded-xl px-3 py-2">
          <option value="any" ${state.datePosted === 'any' ? 'selected' : ''}>Any time</option>
          <option value="1" ${state.datePosted === '1' ? 'selected' : ''}>Last 24 hours</option>
          <option value="7" ${state.datePosted === '7' ? 'selected' : ''}>Last 7 days</option>
          <option value="14" ${state.datePosted === '14' ? 'selected' : ''}>Last 14 days</option>
        </select>
      </div>
      <button onclick="clearFilters()" class="btn btn-outline btn-sm w-full mt-4">Clear all filters</button>
    `;
  }

  function bindPanel(root) {
    root.querySelectorAll('input[type=checkbox]').forEach((el) => {
      el.addEventListener('change', () => {
        const group = state[el.dataset.group];
        if (el.checked) group.add(el.value); else group.delete(el.value);
        applyFilters();
      });
    });
    root.querySelectorAll('input[type=range]').forEach((el) => {
      el.addEventListener('input', () => {
        state.minSalary = parseInt(el.value, 10);
        root.querySelector('#min-salary-label') && (root.querySelector('#min-salary-label').textContent = `$${state.minSalary.toLocaleString()}+`);
        document.querySelectorAll('#min-salary-label').forEach(l => l.textContent = `$${state.minSalary.toLocaleString()}+`);
        applyFilters();
      });
    });
    root.querySelectorAll('select[data-select]').forEach((el) => {
      el.addEventListener('change', () => { state.datePosted = el.value; applyFilters(); });
    });
  }

  function renderFilterPanels() {
    const desktop = document.getElementById('filters-panel-desktop');
    const mobile = document.getElementById('filters-panel-mobile');
    if (desktop) { desktop.innerHTML = filterPanelHTML(); bindPanel(desktop); }
    if (mobile) { mobile.innerHTML = filterPanelHTML(); bindPanel(mobile); }
  }

  function jobCard(job) {
    const isSaved = savedIds.has(job.id);
    const featuredBadge = job.featured ? '<span class="chip chip-indigo">Featured</span>' : '';
    const urgentBadge = job.urgent ? '<span class="chip chip-rose">Urgent hire</span>' : '';
    const tags = job.tags.slice(0, 4).map(t => `<span class="chip">${t}</span>`).join('');
    return `
    <div class="card card-hover p-5 ${job.featured ? 'ring-1 ring-indigo/20' : ''}">
      <div class="flex items-start gap-4">
        <span class="w-12 h-12 rounded-xl flex items-center justify-center text-white text-sm font-bold shrink-0" style="background:${job.company_color}">${job.company_initials}</span>
        <div class="flex-1 min-w-0">
          <div class="flex items-start justify-between gap-3">
            <div class="min-w-0">
              <a href="/jobs/${job.id}" class="font-display font-semibold text-navy hover:text-indigo leading-snug block truncate">${job.title}</a>
              <p class="text-sm text-ink/50">${job.company}</p>
            </div>
            <div class="flex gap-1.5 shrink-0">${featuredBadge}${urgentBadge}</div>
          </div>
          <div class="flex flex-wrap gap-x-4 gap-y-1.5 mt-3 text-xs text-ink/50">
            <span class="flex items-center gap-1"><i data-lucide="map-pin" class="w-3.5 h-3.5"></i>${job.location}</span>
            <span class="flex items-center gap-1"><i data-lucide="clock" class="w-3.5 h-3.5"></i>${job.type} · ${job.mode}</span>
            <span class="flex items-center gap-1"><i data-lucide="briefcase" class="w-3.5 h-3.5"></i>${job.experience}</span>
            <span class="flex items-center gap-1"><i data-lucide="calendar" class="w-3.5 h-3.5"></i>${daysLabel(job.posted_days_ago)}</span>
          </div>
          <div class="flex flex-wrap gap-1.5 mt-3">${tags}</div>
          <div class="flex items-center justify-between mt-4">
            <p class="font-display font-semibold text-navy">$${job.salary_min.toLocaleString()} - $${job.salary_max.toLocaleString()}</p>
            <div class="flex gap-2">
              <button data-save-btn="${job.id}" class="btn btn-outline btn-sm ${isSaved ? 'is-saved' : ''}" onclick="toggleSaveJob(${job.id}, this)">
                <i data-lucide="bookmark" class="w-3.5 h-3.5" ${isSaved ? "fill='currentColor'" : ''}></i><span data-save-label>${isSaved ? 'Saved' : 'Save'}</span>
              </button>
              <a href="/jobs/${job.id}" class="btn btn-outline btn-sm">Details</a>
              <button onclick="handleListApply(${job.id})" class="btn btn-primary btn-sm"><i data-lucide="send" class="w-3.5 h-3.5"></i>Apply Now</button>
            </div>
          </div>
        </div>
      </div>
    </div>`;
  }

  window.handleListApply = async function(jobId) {
    try {
      const res = await fetch(`/api/jobs/${jobId}/apply`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });
      const data = await res.json();
      if (!res.ok || data.requires_auth) {
        showToast("Oops! You are not logged in!", { icon: 'alert-circle' });
        setTimeout(() => {
          window.location.href = data.redirect || `/login?msg=not_logged_in&redirect=/jobs/${jobId}`;
        }, 750);
        return;
      }
      showToast("Application submitted successfully!", { icon: 'check-circle-2' });
    } catch(e) {
      showToast("Oops! You are not logged in!", { icon: 'alert-circle' });
      setTimeout(() => {
        window.location.href = `/login?msg=not_logged_in&redirect=/jobs/${jobId}`;
      }, 750);
    }
  };

  function matches(job) {
    const kw = state.keyword.trim().toLowerCase();
    if (kw && !(job.title.toLowerCase().includes(kw) || job.company.toLowerCase().includes(kw) || job.tags.join(' ').toLowerCase().includes(kw))) return false;
    const loc = state.location.trim().toLowerCase();
    if (loc && !job.location.toLowerCase().includes(loc)) return false;
    if (state.industries.size && !state.industries.has(job.industry)) return false;
    if (state.jobTypes.size && !state.jobTypes.has(job.type)) return false;
    if (state.workModes.size && !state.workModes.has(job.mode)) return false;
    if (state.experience.size && !state.experience.has(job.experience)) return false;
    if (job.salary_max < state.minSalary) return false;
    if (state.datePosted !== 'any' && job.posted_days_ago > parseInt(state.datePosted, 10)) return false;
    return true;
  }

  function sortJobs(list) {
    const arr = [...list];
    if (state.sort === 'newest') arr.sort((a, b) => a.posted_days_ago - b.posted_days_ago);
    else if (state.sort === 'salary') arr.sort((a, b) => b.salary_max - a.salary_max);
    else arr.sort((a, b) => (b.featured - a.featured) || (b.urgent - a.urgent) || (a.posted_days_ago - b.posted_days_ago));
    return arr;
  }

  window.applyFilters = function () {
    state.keyword = document.getElementById('filter-keyword')?.value || '';
    state.location = document.getElementById('filter-location')?.value || '';
    const filtered = sortJobs(jobs.filter(matches));
    const list = document.getElementById('job-list');
    const empty = document.getElementById('empty-state');
    document.getElementById('results-count').textContent = filtered.length;
    if (!filtered.length) {
      list.innerHTML = '';
      empty.classList.remove('hidden');
    } else {
      empty.classList.add('hidden');
      list.innerHTML = filtered.map(jobCard).join('');
    }
    if (window.lucide) lucide.createIcons();
  };

  window.clearFilters = function () {
    state.industries.clear(); state.jobTypes.clear(); state.workModes.clear(); state.experience.clear();
    state.minSalary = 0; state.datePosted = 'any'; state.keyword = ''; state.location = '';
    document.getElementById('filter-keyword').value = '';
    document.getElementById('filter-location').value = '';
    renderFilterPanels();
    applyFilters();
  };

  window.syncSort = function (value) {
    state.sort = value;
    document.getElementById('sort-select').value = value;
    document.getElementById('sort-select-mobile').value = value;
    applyFilters();
  };

  // Init from URL query params
  const params = new URLSearchParams(window.location.search);
  if (params.get('q')) state.keyword = params.get('q');
  if (params.get('location')) state.location = params.get('location');
  if (params.get('industry')) state.industries.add(params.get('industry'));

  document.getElementById('filter-keyword').value = state.keyword;
  document.getElementById('filter-location').value = state.location;
  renderFilterPanels();
  applyFilters();
})();
