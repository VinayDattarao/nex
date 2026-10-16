(function () {
  const candidates = window.NEXORA_CANDIDATES || [];

  function findCandidate(id) {
    return candidates.find((c) => c.id === id);
  }

  function actionsHTML(candidate) {
    const stage = candidate.stage;
    let advance = '';
    if (stage === 'New') advance = `<button class="btn btn-accent btn-sm !py-1.5" onclick="moveStage(${candidate.id}, 'Shortlisted')">Shortlist</button>`;
    else if (stage === 'Shortlisted') advance = `<button class="btn btn-accent btn-sm !py-1.5" onclick="moveStage(${candidate.id}, 'Interview')">Move to Interview</button>`;
    else if (stage === 'Interview') advance = `<button class="btn btn-accent btn-sm !py-1.5" onclick="moveStage(${candidate.id}, 'Hired')">Mark Hired</button>`;
    return `
      <button class="btn btn-outline btn-sm !py-1.5" onclick='viewProfile(${candidate.id})'>View Profile</button>
      ${advance}
      <button class="btn btn-ghost btn-sm !py-1.5" onclick='contactCandidate(${JSON.stringify(candidate.name)})'>Contact</button>
    `;
  }

  function updateCounts() {
    document.querySelectorAll('[data-column-body]').forEach((body) => {
      const stage = body.dataset.columnBody;
      const count = body.querySelectorAll('[data-candidate-card]').length;
      const countEl = document.querySelector(`[data-column-count="${stage}"]`);
      if (countEl) countEl.textContent = count;
      const emptyLabel = body.querySelector(`[data-empty-label="${stage}"]`);
      if (count === 0 && !emptyLabel) {
        body.insertAdjacentHTML('beforeend', `<p class="text-xs text-cream/30 text-center py-6" data-empty-label="${stage}">No candidates here yet.</p>`);
      } else if (count > 0 && emptyLabel) {
        emptyLabel.remove();
      }
    });
  }

  window.moveStage = async function (id, newStage) {
    const card = document.querySelector(`[data-candidate-card="${id}"]`);
    const candidate = findCandidate(id);
    if (!card || !candidate) return;
    try {
      await fetch(`/api/applicants/${id}/stage`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ stage: newStage }),
      });
    } catch (e) {}
    candidate.stage = newStage;
    card.dataset.stage = newStage;
    const actionsRow = card.querySelector('.flex.flex-wrap.gap-1\\.5');
    if (actionsRow) actionsRow.innerHTML = actionsHTML(candidate);
    const destColumn = document.querySelector(`[data-column-body="${newStage}"]`);
    if (destColumn) {
      const emptyLabel = destColumn.querySelector(`[data-empty-label="${newStage}"]`);
      if (emptyLabel) destColumn.insertBefore(card, emptyLabel);
      else destColumn.appendChild(card);
    }
    updateCounts();
    if (window.lucide) lucide.createIcons();
    showToast(`${candidate.name} moved to ${newStage}.`, { icon: 'move-right' });
  };

  window.viewProfile = function (id) {
    const c = findCandidate(id);
    if (!c) return;
    document.getElementById('profile-modal-body').innerHTML = `
      <div class="flex items-center gap-3 mb-4">
        <span class="w-14 h-14 rounded-full bg-cream-dim text-navy flex items-center justify-center font-display font-bold">${c.avatar_initials}</span>
        <div>
          <p class="font-display font-semibold text-navy">${c.name}</p>
          <p class="text-xs text-ink/50">${c.title}</p>
        </div>
      </div>
      <div class="space-y-3">
        <div class="flex justify-between"><span class="text-ink/50">Applied for</span><span class="font-medium text-navy">${c.job_title}</span></div>
        <div class="flex justify-between"><span class="text-ink/50">Experience</span><span class="font-medium text-navy">${c.experience}</span></div>
        <div class="flex justify-between"><span class="text-ink/50">Applied on</span><span class="font-medium text-navy">${c.applied_date}</span></div>
        <div class="flex justify-between"><span class="text-ink/50">Current stage</span><span class="chip">${c.stage}</span></div>
        <div>
          <span class="text-ink/50 block mb-1.5">Skills</span>
          <div class="flex flex-wrap gap-1.5">${c.skills.map(s => `<span class="chip">${s}</span>`).join('')}</div>
        </div>
      </div>`;
    openModal('profile-modal');
    if (window.lucide) lucide.createIcons();
  };

  window.contactCandidate = function (name) {
    showToast(`Message sent to ${name}.`, { icon: 'mail' });
  };
})();
