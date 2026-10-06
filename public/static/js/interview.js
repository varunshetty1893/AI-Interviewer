/* InterviewQuest — dynamic conversation engine */
(function () {
  const iv          = window.__INTERVIEW__ || {};
  const interviewId = iv.id;
  const total       = iv.total_questions || 10;
  let   qNumber     = iv.current_index || 1;
  let   mode        = 'idle'; // 'idle' | 'sending' | 'done'

  const chatLog    = document.getElementById('chat-log');
  const inputWrap  = document.getElementById('chat-input-wrap');
  const finishWrap = document.getElementById('finish-wrap');
  const inputEl    = document.getElementById('answer-input');
  const sendBtn    = document.getElementById('send-btn');
  const skipBtn    = document.getElementById('skip-btn');
  const finishBtn  = document.getElementById('finish-btn');
  const progBar    = document.getElementById('progress-bar');
  const progText   = document.getElementById('progress-text');
  const catList    = document.getElementById('category-list');

  // Stage → display category name mapping
  const STAGE_LABELS = {
    intro:      'Introduction',
    project:    'Project',
    technical:  'Technical',
    behavioral: 'Behavioral',
    career:     'Career & Fit',
  };

  // ── Sidebar category counts ────────────────────────────────────────────────
  const stageCounts = {
    intro: 3, project: 3, technical: 2, behavioral: 1, career: 1
  };

  function renderCategories() {
    catList.innerHTML = Object.entries(stageCounts).map(([id, n]) =>
      `<div class="cat-row">
        <span class="cat-name">${STAGE_LABELS[id]}</span>
        <span class="cat-count">${n}</span>
      </div>`
    ).join('');
  }

  // ── Progress ───────────────────────────────────────────────────────────────
  function updateProgress(answered) {
    progText.textContent = `${answered} / ${total}`;
    progBar.style.width  = `${Math.round((answered / total) * 100)}%`;
  }

  // ── Bubbles ────────────────────────────────────────────────────────────────
  function bubble(role, text, meta) {
    const wrap = document.createElement('div');
    wrap.className = `bubble bubble-${role}`;
    if (meta) {
      const m = document.createElement('span');
      m.className   = 'bubble-meta';
      m.textContent = meta;
      wrap.appendChild(m);
    }
    const p = document.createElement('div');
    p.textContent = text;
    wrap.appendChild(p);
    chatLog.appendChild(wrap);
    chatLog.scrollTop = chatLog.scrollHeight;
    return wrap;
  }

  function addTyping() {
    const d = document.createElement('div');
    d.className = 'bubble bubble-ai bubble-typing';
    d.innerHTML = '<span class="dot"></span><span class="dot"></span><span class="dot"></span>';
    chatLog.appendChild(d);
    chatLog.scrollTop = chatLog.scrollHeight;
    return d;
  }

  function setLocked(locked) {
    sendBtn.disabled = locked;
    skipBtn.disabled = locked;
    inputEl.disabled = locked;
    sendBtn.querySelector('.label-default').classList.toggle('d-none', locked);
    sendBtn.querySelector('.label-loading').classList.toggle('d-none', !locked);
  }

  function showFinish() {
    mode = 'done';
    inputWrap.classList.add('d-none');
    finishWrap.classList.remove('d-none');
  }

  // ── Submit answer ──────────────────────────────────────────────────────────
  async function submitAnswer(text) {
    if (mode !== 'idle') return;
    mode = 'sending';
    setLocked(true);

    bubble('user', text || '(skipped)', 'You');
    inputEl.value = '';

    const typing = addTyping();

    try {
      const res  = await fetch(`/interview/${interviewId}/answer`, {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ answer: text }),
        credentials: 'include',
      });
      const data = await res.json();
      typing.remove();

      if (!res.ok) throw new Error(data.error || 'Request failed');

      updateProgress(qNumber);
      qNumber++;

      if (data.done) {
        showFinish();
        return;
      }

      // Show next AI question
      const stageLabel = STAGE_LABELS[data.stage_label] || data.stage_label || '';
      const meta = stageLabel ? `${stageLabel} · Q${data.q_number}` : `Q${data.q_number}`;
      bubble('ai', data.message, meta);

      mode = 'idle';
      setLocked(false);
      inputEl.focus();

    } catch (err) {
      typing.remove();
      bubble('ai', `Something went wrong: ${err.message}. Please try again.`, 'System');
      mode = 'idle';
      setLocked(false);
    }
  }

  // ── Event listeners ────────────────────────────────────────────────────────
  sendBtn.addEventListener('click', () => {
    if (mode !== 'idle') return;
    const text = inputEl.value.trim();
    if (!text) { inputEl.focus(); return; }
    submitAnswer(text);
  });

  skipBtn.addEventListener('click', () => {
    if (mode !== 'idle') return;
    submitAnswer('');
  });

  inputEl.addEventListener('keydown', e => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
      e.preventDefault();
      sendBtn.click();
    }
  });

  finishBtn.addEventListener('click', async () => {
    finishBtn.disabled = true;
    finishBtn.querySelector('.label-default').classList.add('d-none');
    finishBtn.querySelector('.label-loading').classList.remove('d-none');
    try {
      const res  = await fetch(`/interview/${interviewId}/finish`, {
        method: 'POST', credentials: 'include'
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || 'Evaluation failed');
      window.location.href = data.redirect;
    } catch (err) {
      finishBtn.disabled = false;
      finishBtn.querySelector('.label-default').classList.remove('d-none');
      finishBtn.querySelector('.label-loading').classList.add('d-none');
      alert(`Error: ${err.message}`);
    }
  });

  // ── Boot ──────────────────────────────────────────────────────────────────
  renderCategories();
  updateProgress(qNumber - 1);

  const conversation = iv.conversation || [];

  // Replay existing conversation (page reload / resume)
  // Each interviewer turn is shown ONCE — no duplicates
  let answeredCount = 0;
  for (const turn of conversation) {
    if (turn.role === 'interviewer') {
      const stageName = STAGE_LABELS[turn.stage] || (turn.stage || '');
      const qn        = turn.q_num;
      const meta      = (stageName && qn) ? `${stageName} · Q${qn}` : (qn ? `Q${qn}` : 'Interviewer');
      bubble('ai', turn.text, meta);
    } else if (turn.role === 'candidate') {
      bubble('user', turn.answer || '(skipped)', 'You');
      answeredCount++;
    }
  }

  updateProgress(answeredCount);

  // If last turn is a candidate answer and all answered → show finish
  const lastTurn = conversation[conversation.length - 1];
  if (lastTurn && lastTurn.role === 'candidate' && answeredCount >= total) {
    showFinish();
  } else {
    mode = 'idle';
    setLocked(false);
    inputEl.focus();
  }
})();
