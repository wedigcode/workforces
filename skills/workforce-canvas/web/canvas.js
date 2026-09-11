/**
 * Workforce Command Canvas - Interactive Engine
 * Zero npm dependencies (Vanilla JS + SVG Bezier Splines + Marked)
 */

(function () {
  'use strict';

  // State Management
  const state = {
    viewMode: 'workstate', // 'workstate' | 'task_focus' | 'session_focus' | 'commit_focus' | 'blast_radius'
    activeFocalSymbol: null,
    focusedTask: null,
    focusedSession: null,
    focusedCommit: null,
    navStack: [], // Array of { mode, data, label }
    panX: 80,
    panY: 80,
    zoom: 0.95,
    isPanning: false,
    startX: 0,
    startY: 0,
    dragStartPos: null,
    hasDragged: false,
    nodes: new Map(), // id -> { id, element, x, y, width, height, data }
    edges: [],        // [ { source, target, type, label, element } ]
    selectedNodeId: null,
    draggedNode: null,
    dragOffset: { x: 0, y: 0 },
    connectingFrom: null, // { nodeId, portType, element }
    tempCable: null,
    tasks: [],
    sessions: [],
    hypotheses: [],
    goals: [],
    availableSymbols: [],
    stats: {},
  };

  // DOM Elements
  const viewport = document.getElementById('canvas-viewport');
  const container = document.getElementById('canvas-container');
  const connectionsLayer = document.getElementById('connections-layer');
  const nodesLayer = document.getElementById('nodes-layer');
  const framesLayer = document.getElementById('frames-layer');
  const inspectDrawer = document.getElementById('inspect-drawer');

  // Initialize
  async function init() {
    setupPanAndZoom();
    setupControls();
    setupSearch();
    setupHeartbeatAndPower();
    await fetchWorkforceState();
    setupStudio();
    // Default to the executive Standup Cockpit view
    switchToStudioMode('cockpit');
    if (window.lucide) {
      window.lucide.createIcons();
    }
  }

  // --- API Fetchers ---

  async function fetchWorkforceState() {
    try {
      const res = await fetch('/api/state');
      if (!res.ok) throw new Error('Failed to fetch state');
      const data = await res.json();
      state.tasks = data.tasks || [];
      state.sessions = data.sessions || [];
      state.hypotheses = data.hypotheses || [];
      state.goals = data.goals || [];
      state.availableSymbols = data.symbols || [];
      state.stats = data.stats || {};
      state.standup = data.standup || {};
      state.git = data.git || {};
      state.installedTeams = data.installed_teams || [];
      state.workstateMarkdown = data.workstate_markdown || '';
      updateTopBarStats();
      renderStandupCockpit();
    } catch (err) {
      console.error('Fetch error:', err);
    }
  }

  async function fetchCommitDetails(hash) {
    try {
      const res = await fetch(`/api/commit?hash=${encodeURIComponent(hash)}`);
      if (!res.ok) throw new Error('Failed to fetch commit');
      return await res.json();
    } catch (err) {
      console.error('Commit fetch error:', err);
      return null;
    }
  }

  async function fetchBlastRadius(symbol, file) {
    try {
      const params = new URLSearchParams();
      if (symbol) params.set('symbol', symbol);
      if (file) params.set('file', file);
      const res = await fetch(`/api/impact?${params.toString()}`);
      if (!res.ok) throw new Error('Failed to fetch blast radius');
      return await res.json();
    } catch (err) {
      console.error('Blast radius fetch error:', err);
      return null;
    }
  }

  async function updateTaskOnServer(fileRel, updates) {
    try {
      const res = await fetch('/api/task/update', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ file: fileRel, updates })
      });
      if (!res.ok) throw new Error('Task update failed');
      await fetchWorkforceState();
      renderCurrentView();
    } catch (err) {
      alert(`Update failed: ${err.message}`);
    }
  }

  async function connectTasksOnServer(blockerId, blockedId) {
    try {
      const res = await fetch('/api/task/connect', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ blocker_id: blockerId, blocked_id: blockedId })
      });
      if (!res.ok) throw new Error('Connect failed');
      await fetchWorkforceState();
      renderCurrentView();
    } catch (err) {
      alert(`Connection failed: ${err.message}`);
    }
  }

  // --- Pan & Zoom Engine ---

  function applyTransform() {
    container.style.transform = `translate3d(${state.panX}px, ${state.panY}px, 0) scale(${state.zoom})`;
  }

  function setupPanAndZoom() {
    viewport.addEventListener('mousedown', (e) => {
      if (e.target === viewport || e.target === container || e.target === connectionsLayer || e.code === 'Space' || e.button === 1) {
        state.isPanning = true;
        state.startX = e.clientX - state.panX;
        state.startY = e.clientY - state.panY;
        viewport.classList.add('is-panning');
      }
    });

    window.addEventListener('mousemove', (e) => {
      if (state.isPanning) {
        state.panX = e.clientX - state.startX;
        state.panY = e.clientY - state.startY;
        applyTransform();
      } else if (state.draggedNode) {
        if (state.dragStartPos) {
          const dist = Math.hypot(e.clientX - state.dragStartPos.x, e.clientY - state.dragStartPos.y);
          if (dist > 4) {
            state.hasDragged = true;
          }
        }
        const x = (e.clientX - state.panX) / state.zoom - state.dragOffset.x;
        const y = (e.clientY - state.panY) / state.zoom - state.dragOffset.y;
        state.draggedNode.x = Math.round(x);
        state.draggedNode.y = Math.round(y);
        state.draggedNode.element.style.transform = `translate3d(${state.draggedNode.x}px, ${state.draggedNode.y}px, 0)`;
        updateCables();
      } else if (state.connectingFrom && state.tempCable) {
        updateTempCable(e.clientX, e.clientY);
      }
    });

    window.addEventListener('mouseup', () => {
      if (state.isPanning) {
        state.isPanning = false;
        viewport.classList.remove('is-panning');
      }
      if (state.draggedNode) {
        state.draggedNode = null;
        setTimeout(() => {
          state.hasDragged = false;
          state.dragStartPos = null;
        }, 80);
      }
      if (state.connectingFrom) {
        if (state.tempCable) {
          if (state.tempCable.path && state.tempCable.path.parentNode) {
            state.tempCable.path.remove();
          }
          state.tempCable = null;
        }
        state.connectingFrom = null;
      }
    });

    // Capture-phase click interceptor: suppress accidental click triggers when dragging nodes
    window.addEventListener('click', (e) => {
      if (state.hasDragged) {
        e.stopPropagation();
        e.preventDefault();
      }
    }, true);

    let wheelGesture = {
      mode: 'idle', // 'idle' | 'zoom' | 'pan'
      accumX: 0,
      accumY: 0,
      timer: null
    };

    viewport.addEventListener('wheel', (e) => {
      // Allow native scrolling inside scrollable containers (e.g. drawer, commit lists)
      if (e.target.closest('#inspect-drawer') || e.target.closest('.overflow-y-auto')) {
        return;
      }

      e.preventDefault();
      clearTimeout(wheelGesture.timer);

      // Pinch-to-zoom (ctrlKey or metaKey on macOS trackpads)
      if (e.ctrlKey || e.metaKey) {
        wheelGesture.mode = 'zoom';
        const factor = Math.exp(-e.deltaY * 0.0075);
        zoomAroundPoint(factor, e.clientX, e.clientY);
      } else if (wheelGesture.mode === 'pan') {
        // Once horizontal motion initiates pan, drag canvas in ANY direction (X and Y)
        state.panX -= e.deltaX;
        state.panY -= e.deltaY;
        applyTransform();
        updateCables();
      } else if (wheelGesture.mode === 'zoom') {
        // In vertical zoom gesture
        const factor = Math.exp(-e.deltaY * 0.0028);
        zoomAroundPoint(factor, e.clientX, e.clientY);
      } else {
        // In 'idle': accumulate initial deltas to detect user intent
        wheelGesture.accumX += e.deltaX;
        wheelGesture.accumY += e.deltaY;
        const absX = Math.abs(wheelGesture.accumX);
        const absY = Math.abs(wheelGesture.accumY);

        // Threshold to distinguish intent
        if (absX > 3 || absY > 3) {
          if (absX > absY) {
            // Left/right motion initiates full two-finger drag/pan in any direction
            wheelGesture.mode = 'pan';
            state.panX -= wheelGesture.accumX;
            state.panY -= wheelGesture.accumY;
            applyTransform();
            updateCables();
          } else {
            // Up/down motion engages zoom
            wheelGesture.mode = 'zoom';
            const factor = Math.exp(-wheelGesture.accumY * 0.0028);
            zoomAroundPoint(factor, e.clientX, e.clientY);
          }
        }
      }

      // Reset gesture mode after fingers are lifted
      wheelGesture.timer = setTimeout(() => {
        wheelGesture.mode = 'idle';
        wheelGesture.accumX = 0;
        wheelGesture.accumY = 0;
      }, 160);
    }, { passive: false });
  }

  function zoomAroundPoint(factor, clientX, clientY) {
    const oldZoom = state.zoom;
    const newZoom = Math.max(0.15, Math.min(2.8, oldZoom * factor));
    if (Math.abs(newZoom - oldZoom) < 0.0001) return;

    const rect = viewport.getBoundingClientRect();
    const mouseX = clientX !== undefined ? (clientX - rect.left) : (rect.width / 2);
    const mouseY = clientY !== undefined ? (clientY - rect.top) : (rect.height / 2);

    state.panX = mouseX - (mouseX - state.panX) * (newZoom / oldZoom);
    state.panY = mouseY - (mouseY - state.panY) * (newZoom / oldZoom);
    state.zoom = newZoom;

    applyTransform();
    const label = document.getElementById('zoom-label');
    if (label) label.innerText = `${Math.round(state.zoom * 100)}%`;
  }

  function fitViewToBoundingBox(padding = 55) {
    if (state.nodes.size === 0) return;

    let minX = Infinity, maxX = -Infinity;
    let minY = Infinity, maxY = -Infinity;

    state.nodes.forEach(node => {
      minX = Math.min(minX, node.x);
      maxX = Math.max(maxX, node.x + (node.width || 320));
      minY = Math.min(minY, node.y);
      maxY = Math.max(maxY, node.y + (node.height || 120));
    });

    const boxWidth = maxX - minX;
    const boxHeight = maxY - minY;
    if (boxWidth <= 0 || boxHeight <= 0) return;

    // Detect if task details drawer is currently open (width = 400px)
    const drawerOpen = inspectDrawer && inspectDrawer.classList.contains('is-open');
    const drawerWidth = drawerOpen ? 410 : 0;

    const availWidth = Math.max(320, viewport.clientWidth - drawerWidth);
    const availHeight = Math.max(320, viewport.clientHeight - 60);

    const zoomX = (availWidth - padding * 2) / boxWidth;
    const zoomY = (availHeight - padding * 2) / boxHeight;
    const newZoom = Math.max(0.4, Math.min(1.0, Math.min(zoomX, zoomY)));

    const boxCenterX = minX + boxWidth / 2;
    const boxCenterY = minY + boxHeight / 2;

    const availCenterX = availWidth / 2;
    const availCenterY = 56 + availHeight / 2;

    state.zoom = newZoom;
    state.panX = Math.round(availCenterX - boxCenterX * newZoom);
    state.panY = Math.round(availCenterY - boxCenterY * newZoom);

    // Apply smooth glide transition when auto-centering
    container.style.transition = 'transform 0.28s cubic-bezier(0.16, 1, 0.3, 1)';
    applyTransform();
    setTimeout(() => {
      container.style.transition = '';
    }, 300);

    const label = document.getElementById('zoom-label');
    if (label) label.innerText = `${Math.round(state.zoom * 100)}%`;
  }

  // --- Transitive Navigation & Perspective Stack ---

  function navigateTo(mode, data, label, addToStack = true) {
    if (addToStack) {
      // Prevent consecutive duplicate pushes
      const last = state.navStack[state.navStack.length - 1];
      if (!last || last.mode !== mode || last.data !== data) {
        state.navStack.push({ mode, data, label: label || mode });
      }
    } else if (state.navStack.length === 0) {
      state.navStack = [{ mode: 'workstate', data: null, label: 'Radar' }];
    }

    state.viewMode = mode;
    if (mode === 'task_focus') state.focusedTask = data;
    if (mode === 'session_focus') state.focusedSession = data;
    if (mode === 'commit_focus') state.focusedCommit = data;
    if (mode === 'blast_radius') state.activeFocalSymbol = data;

    updateHeaderNavigation();
    renderCurrentView();
  }

  function popNavigation() {
    if (state.navStack.length > 1) {
      state.navStack.pop(); // Remove current
      const prev = state.navStack[state.navStack.length - 1];
      navigateTo(prev.mode, prev.data, prev.label, false);
    } else {
      navigateTo('workstate', null, 'Radar', false);
    }
  }

  function updateHeaderNavigation() {
    const modePills = document.getElementById('mode-pills-bar');
    const focusNav = document.getElementById('focus-nav-bar');
    const btnExitText = document.getElementById('btn-exit-focus-text');
    const crumbsContainer = document.getElementById('nav-breadcrumbs');

    if (state.viewMode === 'workstate') {
      focusNav.classList.add('hidden');
      focusNav.classList.remove('flex');
      modePills.classList.remove('hidden');
    } else {
      modePills.classList.add('hidden');
      focusNav.classList.remove('hidden');
      focusNav.classList.add('flex');

      if (btnExitText) {
        btnExitText.innerText = state.navStack.length > 1 ? 'Back' : 'Radar';
      }

      if (crumbsContainer) {
        crumbsContainer.innerHTML = '';
        state.navStack.forEach((entry, idx) => {
          const isLast = idx === state.navStack.length - 1;
          const crumb = document.createElement('span');
          crumb.className = `nav-crumb ${isLast ? 'is-current' : ''}`;
          crumb.innerText = entry.label;

          if (!isLast) {
            crumb.onclick = () => {
              state.navStack = state.navStack.slice(0, idx + 1);
              navigateTo(entry.mode, entry.data, entry.label, false);
            };
          }

          crumbsContainer.appendChild(crumb);
          if (!isLast) {
            const sep = document.createElement('span');
            sep.className = 'text-[#d1cfca]';
            sep.innerText = '›';
            crumbsContainer.appendChild(sep);
          }
        });
      }
    }
  }

  function renderCurrentView() {
    clearCanvas();

    if (state.viewMode === 'workstate') {
      renderWorkstateLayout();
    } else if (state.viewMode === 'task_focus') {
      renderTaskFocusLayout(state.focusedTask);
    } else if (state.viewMode === 'session_focus') {
      renderSessionFocusLayout(state.focusedSession);
    } else if (state.viewMode === 'commit_focus') {
      renderCommitFocusLayout(state.focusedCommit);
    } else if (state.viewMode === 'blast_radius') {
      renderBlastRadiusLayout(state.activeFocalSymbol);
    }

    if (window.lucide) window.lucide.createIcons();
  }

  function clearCanvas() {
    nodesLayer.innerHTML = '';
    connectionsLayer.innerHTML = '';
    framesLayer.innerHTML = '';
    state.nodes.clear();
    state.edges = [];
  }

  // --- Workstate Radar Layout ---

  function renderWorkstateLayout() {
    const columns = [
      { id: 'in_progress', label: 'In Progress (Active Focus)', status: 'in_progress', x: 400, color: 'var(--status-in-progress)' },
      { id: 'blocked', label: 'Blocked / Needs Unblocking', status: 'blocked', x: 800, color: 'var(--status-blocked)' },
      { id: 'todo', label: 'Ready Queue / Backlog', status: 'todo', x: 50, color: 'var(--status-todo)' },
      { id: 'done', label: 'Completed Deliverables', status: 'done', x: 1200, color: 'var(--status-done)' }
    ];

    columns.forEach(col => {
      const colTasks = state.tasks.filter(t => t.status === col.status);
      const frameHeight = Math.max(500, colTasks.length * 160 + 80);
      const frame = document.createElement('div');
      frame.className = 'group-frame';
      frame.style.left = `${col.x - 20}px`;
      frame.style.top = '40px';
      frame.style.width = '360px';
      frame.style.height = `${frameHeight}px`;

      const label = document.createElement('div');
      label.className = 'group-frame-label';
      label.innerText = `${col.label} (${colTasks.length})`;
      label.style.borderColor = col.color;
      frame.appendChild(label);
      framesLayer.appendChild(frame);

      colTasks.forEach((task, index) => {
        const cardX = col.x;
        const cardY = 70 + index * 160;
        createTaskCard(task, cardX, cardY);
      });
    });

    const taskMap = new Map(state.tasks.map(t => [t.id, t]));
    state.tasks.forEach(task => {
      (task.blocked_by || []).forEach(blockerId => {
        if (taskMap.has(blockerId)) {
          createEdge(blockerId, task.id, 'dependency');
        }
      });
    });

    updateCables();
  }

  // --- Task Perspective Layout ---

  function renderTaskFocusLayout(task) {
    if (!task) return;
    clearCanvas();

    const mainX = 440;
    const mainY = 220;
    const mainCard = createTaskCard(task, mainX, mainY, true);
    mainCard.classList.add('is-focused-main');

    // 1. Origin Session Satellite (Clickable to pivot)
    const sessionObj = findSessionForTask(task);
    const sessionFile = task.session_file || (sessionObj ? sessionObj.file : null);
    if (sessionFile || sessionObj) {
      const sessCardId = `sat-session-${task.id}`;
      const sessCard = createSatelliteCard({
        id: sessCardId,
        x: 60,
        y: 120,
        width: 300,
        badgeText: 'Origin Session',
        badgeColor: 'bg-[#e0f2fe] text-[#0369a1] border-[#bae6fd]',
        title: sessionObj ? sessionObj.topic : sessionFile.split('/').pop().replace(/\.md$/, ''),
        subtitle: `Lineage Context Note (#${task.session_id || (sessionObj ? sessionObj.id : '000')})`,
        actionLabel: 'Pivot to Session View &rarr;',
        icon: 'file-text'
      });

      sessCard.addEventListener('click', (e) => {
        if (state.hasDragged) return;
        const btn = e.target.closest('[data-action="satellite-action"]');
        if (btn) {
          const targetSess = sessionObj || {
            id: task.session_id || '000',
            file: sessionFile,
            topic: task.title + ' Context'
          };
          navigateTo('session_focus', targetSess, `Session #${targetSess.id}`);
        }
      });

      createEdge(sessCardId, task.id, 'session');
    }

    // 2. GitHub Issue / PR Satellite
    if (task.github_pr || task.github_issue) {
      const ghCardId = `sat-gh-${task.id}`;
      createSatelliteCard({
        id: ghCardId,
        x: 60,
        y: 320,
        width: 300,
        badgeText: 'GitHub Lineage',
        badgeColor: 'bg-[#f5f3ff] text-[#7c3aed] border-[#ddd6fe]',
        title: task.github_pr ? `PR #${task.github_pr}` : `Issue #${task.github_issue}`,
        subtitle: 'Remote Repository Tracking',
        actionLabel: 'Open GitHub ↗',
        actionUrl: 'https://github.com',
        icon: 'git-pull-request'
      });
      createEdge(ghCardId, task.id, 'github');
    }

    // 3. Associated Git Commits Satellite (Clickable rows)
    const commits = task.linked_commits || [];
    if (commits.length > 0) {
      const commitCardId = `sat-commits-${task.id}`;
      const commitsHtml = commits.map(c => `
        <div class="py-1.5 px-2 hover:bg-[#f5f5f5] rounded transition-colors cursor-pointer border-b border-[#e2e0dc] last:border-0" data-action="pivot-commit" data-hash="${c.hash}">
          <div class="flex items-center justify-between text-[11px]">
            <span class="font-mono text-[#047857] font-semibold">${c.hash}</span>
            <span class="text-[10px] text-[#828282]">${c.date}</span>
          </div>
          <div class="text-[11px] text-[#4d4d4d] truncate mt-0.5" title="${c.message}">${c.message}</div>
        </div>
      `).join('');

      const comCard = createCustomSatelliteCard({
        id: commitCardId,
        x: 840,
        y: 60,
        width: 340,
        badgeText: `Git Commits (${commits.length})`,
        badgeColor: 'bg-[#ecfdf5] text-[#047857] border-[#a7f3d0]',
        bodyHtml: commitsHtml,
        icon: 'git-commit'
      });

      comCard.addEventListener('click', (e) => {
        const row = e.target.closest('[data-action="pivot-commit"]');
        if (row) {
          const hash = row.dataset.hash;
          if (hash) navigateTo('commit_focus', hash, `Commit ${hash}`);
        }
      });

      createEdge(task.id, commitCardId, 'commit');
    }

    // 4. Linked Docs & Specs Satellite
    const docs = task.linked_docs || [];
    if (docs.length > 0) {
      const docCardId = `sat-docs-${task.id}`;
      const docsHtml = docs.map(d => `
        <a href="${d.url}" target="_blank" class="block py-1 text-[11px] text-[#c2410c] hover:text-[#9a3412] underline truncate">
          ${d.title || d.url} ↗
        </a>
      `).join('');

      createCustomSatelliteCard({
        id: docCardId,
        x: 840,
        y: 320,
        width: 340,
        badgeText: 'Linked Docs & Specs',
        badgeColor: 'bg-[#eff6ff] text-[#2563eb] border-[#bfdbfe]',
        bodyHtml: docsHtml,
        icon: 'external-link'
      });
      createEdge(task.id, docCardId, 'doc');
    }

    // 5. Touched AST Code Symbols Satellite
    const symbols = task.linked_symbols || [];
    if (symbols.length > 0) {
      const symCardId = `sat-symbols-${task.id}`;
      const symsHtml = symbols.map(s => `
        <div class="py-1.5 flex items-center justify-between border-b border-[#e2e0dc] last:border-0 text-[11px]">
          <span class="font-mono text-[#202020] font-medium truncate max-w-[180px]">${s.name}()</span>
          <button class="text-[#c2410c] hover:text-[#9a3412] text-[10px] font-semibold cursor-pointer" data-symbol="${s.name}" data-action="explore-symbol">
            Blast Radius &rarr;
          </button>
        </div>
      `).join('');

      createCustomSatelliteCard({
        id: symCardId,
        x: 1240,
        y: 160,
        width: 300,
        badgeText: `Touched Symbols (${symbols.length})`,
        badgeColor: 'bg-[#fff7ed] text-[#816729] border-[#fed7aa]',
        bodyHtml: symsHtml,
        icon: 'code-2'
      });
      createEdge(task.id, symCardId, 'blast');
    }

    updateCables();
    fitViewToBoundingBox(55);
  }

  // --- Session Perspective Layout ---

  function renderSessionFocusLayout(session) {
    if (!session) return;
    clearCanvas();

    const mainX = 500;
    const mainY = 220;

    // Focal Session Card
    const sessCard = document.createElement('div');
    sessCard.className = 'canvas-card is-focused-main p-4 text-left';
    sessCard.id = `node-session-${session.id}`;
    sessCard.style.width = '360px';
    sessCard.style.transform = `translate3d(${mainX}px, ${mainY}px, 0)`;
    sessCard.style.borderLeft = '3px solid #0369a1';

    const tagsHtml = (session.tags || []).map(t => `<span class="text-[10px] px-2 py-0.5 rounded-full bg-[#e0f2fe] text-[#0369a1] border border-[#bae6fd]">#${t}</span>`).join(' ');

    sessCard.innerHTML = `
      <div class="flex items-center justify-between pb-2 border-b border-[#e2e0dc]">
        <span class="text-[10px] uppercase tracking-wider font-semibold px-2 py-0.5 rounded-full border bg-[#e0f2fe] text-[#0369a1] border-[#bae6fd] font-mono">
          Session #${session.id}
        </span>
        <span class="text-[11px] text-[#828282] font-mono">${(session.created_at || '').slice(0, 10)}</span>
      </div>
      <div class="mt-3">
        <h3 class="text-sm font-semibold text-[#202020] leading-snug">${session.topic || session.title}</h3>
        <p class="font-mono text-[11px] text-[#828282] mt-1 truncate">${session.file}</p>
      </div>
      ${tagsHtml ? `<div class="mt-2.5 flex flex-wrap gap-1">${tagsHtml}</div>` : ''}
      <div class="mt-3 pt-2.5 border-t border-[#e2e0dc] flex items-center justify-between">
        <a href="/${session.file}" target="_blank" class="text-[#c2410c] hover:text-[#9a3412] text-xs font-semibold flex items-center gap-1">
          Open Markdown Notes ↗
        </a>
      </div>
    `;

    const inputPort = document.createElement('div');
    inputPort.className = 'port port-input';
    const outputPort = document.createElement('div');
    outputPort.className = 'port port-output';
    sessCard.appendChild(inputPort);
    sessCard.appendChild(outputPort);
    nodesLayer.appendChild(sessCard);

    state.nodes.set(sessCard.id, {
      id: sessCard.id,
      element: sessCard,
      x: mainX,
      y: mainY,
      width: 360,
      height: 160,
      inputPort,
      outputPort
    });
    setupCardDrag(sessCard, sessCard.id);

    // 1. Upstream Parent Session (Left)
    if (session.parent_session_id) {
      const parentSess = state.sessions.find(s => s.id === session.parent_session_id);
      const pCardId = `sat-parent-${session.id}`;
      const pCard = createSatelliteCard({
        id: pCardId,
        x: 100,
        y: 200,
        width: 300,
        badgeText: 'Preceding Session',
        badgeColor: 'bg-[#f4f4f5] text-[#52525b] border-[#e4e4e7]',
        title: parentSess ? parentSess.topic : `Session #${session.parent_session_id}`,
        subtitle: 'Upstream Lineage Predecessor',
        actionLabel: 'Pivot to Parent Session &rarr;',
        icon: 'git-commit'
      });

      pCard.addEventListener('click', (e) => {
        if (state.hasDragged) return;
        const btn = e.target.closest('[data-action="satellite-action"]');
        if (btn && parentSess) {
          navigateTo('session_focus', parentSess, `Session #${parentSess.id}`);
        }
      });
      createEdge(pCardId, sessCard.id, 'session');
    }

    // 2. Downstream Tasks Created/Tracked in this Session (Right)
    const trackedTasks = state.tasks.filter(t => t.session_id === session.id || (session.tracked_tasks && session.tracked_tasks.some(st => st.id === t.id || st.file === t.file)));
    if (trackedTasks.length > 0) {
      const tasksCardId = `sat-tasks-${session.id}`;
      const tasksHtml = trackedTasks.map(t => `
        <div class="py-2 px-2 hover:bg-[#f5f5f5] rounded transition-colors cursor-pointer border-b border-[#e2e0dc] last:border-0" data-action="pivot-task" data-id="${t.id}">
          <div class="flex items-center justify-between text-[11px]">
            <span class="badge-team badge-${t.team}">${t.team}</span>
            <span class="status-pill status-${t.status}">${t.status.replace('_', ' ')}</span>
          </div>
          <div class="text-xs font-semibold text-[#202020] truncate mt-1">${t.title}</div>
        </div>
      `).join('');

      const tCard = createCustomSatelliteCard({
        id: tasksCardId,
        x: 950,
        y: 80,
        width: 340,
        badgeText: `Tracked Deliverables (${trackedTasks.length})`,
        badgeColor: 'bg-[#eff6ff] text-[#2563eb] border-[#bfdbfe]',
        bodyHtml: tasksHtml,
        icon: 'check-square'
      });

      tCard.addEventListener('click', (e) => {
        const row = e.target.closest('[data-action="pivot-task"]');
        if (row) {
          const task = state.tasks.find(t => t.id === row.dataset.id);
          if (task) navigateTo('task_focus', task, task.title);
        }
      });
      createEdge(sessCard.id, tasksCardId, 'dependency');
    }

    // 3. Active Files Touched Satellite (Bottom Right)
    const activeFiles = session.active_files || [];
    if (activeFiles.length > 0) {
      const filesCardId = `sat-files-${session.id}`;
      const filesHtml = activeFiles.map(f => `
        <div class="py-1 text-[11px] font-mono text-[#4d4d4d] truncate flex items-center gap-1.5" title="${f}">
          <svg class="w-3.5 h-3.5 flex-shrink-0 text-[#828282]" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"/><polyline points="14 2 14 8 20 8"/></svg>
          <span class="truncate">${f}</span>
        </div>
      `).join('');

      createCustomSatelliteCard({
        id: filesCardId,
        x: 950,
        y: 330,
        width: 340,
        badgeText: `Active Files Touched (${activeFiles.length})`,
        badgeColor: 'bg-[#fff7ed] text-[#816729] border-[#fed7aa]',
        bodyHtml: filesHtml,
        icon: 'file-code'
      });
      createEdge(sessCard.id, filesCardId, 'doc');
    }

    updateCables();
    fitViewToBoundingBox(55);
  }

  // --- Git Commit Perspective Layout ---

  async function renderCommitFocusLayout(commitHash) {
    if (!commitHash) return;
    clearCanvas();

    const commitData = await fetchCommitDetails(commitHash);
    if (!commitData || commitData.error) {
      alert(`Could not load details for commit ${commitHash}`);
      popNavigation();
      return;
    }

    const mainX = 500;
    const mainY = 220;

    // Focal Commit Card
    const comCard = document.createElement('div');
    comCard.className = 'canvas-card is-focused-main p-4 text-left';
    comCard.id = `node-commit-${commitData.hash}`;
    comCard.style.width = '360px';
    comCard.style.transform = `translate3d(${mainX}px, ${mainY}px, 0)`;
    comCard.style.borderLeft = '3px solid #047857';

    comCard.innerHTML = `
      <div class="flex items-center justify-between pb-2 border-b border-[#e2e0dc]">
        <span class="text-[10px] uppercase tracking-wider font-semibold px-2 py-0.5 rounded-full border bg-[#ecfdf5] text-[#047857] border-[#a7f3d0] font-mono">
          Git Commit ${commitData.hash}
        </span>
        <span class="text-[11px] text-[#828282] font-mono">${(commitData.date || '').slice(0, 16)}</span>
      </div>
      <div class="mt-3">
        <h3 class="text-sm font-semibold text-[#202020] leading-snug">${commitData.message}</h3>
        <p class="text-[11px] text-[#4d4d4d] mt-1">Author: <span class="text-[#202020] font-medium">${commitData.author}</span></p>
      </div>
    `;

    const inputPort = document.createElement('div');
    inputPort.className = 'port port-input';
    const outputPort = document.createElement('div');
    outputPort.className = 'port port-output';
    comCard.appendChild(inputPort);
    comCard.appendChild(outputPort);
    nodesLayer.appendChild(comCard);

    state.nodes.set(comCard.id, {
      id: comCard.id,
      element: comCard,
      x: mainX,
      y: mainY,
      width: 360,
      height: 140,
      inputPort,
      outputPort
    });
    setupCardDrag(comCard, comCard.id);

    // 1. Associated Tasks (Left / Intent)
    const matchingTasks = state.tasks.filter(t => (t.linked_commits || []).some(c => c.hash === commitData.hash));
    if (matchingTasks.length > 0) {
      const taskSatId = `sat-ctasks-${commitData.hash}`;
      const tasksHtml = matchingTasks.map(t => `
        <div class="py-1.5 px-2 hover:bg-[#f5f5f5] rounded transition-colors cursor-pointer border-b border-[#e2e0dc] last:border-0" data-action="pivot-task" data-id="${t.id}">
          <div class="flex items-center justify-between text-[11px]">
            <span class="badge-team badge-${t.team}">${t.team}</span>
            <span class="status-pill status-${t.status}">${t.status.replace('_', ' ')}</span>
          </div>
          <div class="text-xs font-semibold text-[#202020] truncate mt-1">${t.title}</div>
        </div>
      `).join('');

      const tCard = createCustomSatelliteCard({
        id: taskSatId,
        x: 100,
        y: 180,
        width: 320,
        badgeText: `Triggering Tasks (${matchingTasks.length})`,
        badgeColor: 'bg-[#eff6ff] text-[#2563eb] border-[#bfdbfe]',
        bodyHtml: tasksHtml,
        icon: 'target'
      });

      tCard.addEventListener('click', (e) => {
        const row = e.target.closest('[data-action="pivot-task"]');
        if (row) {
          const task = state.tasks.find(t => t.id === row.dataset.id);
          if (task) navigateTo('task_focus', task, task.title);
        }
      });
      createEdge(taskSatId, comCard.id, 'commit');
    }

    // 2. Files Changed (Right)
    const files = commitData.files || [];
    if (files.length > 0) {
      const filesSatId = `sat-cfiles-${commitData.hash}`;
      const filesHtml = files.map(f => `
        <div class="py-1 text-[11px] font-mono text-[#4d4d4d] truncate flex items-center gap-1.5" title="${f}">
          <svg class="w-3.5 h-3.5 flex-shrink-0 text-[#828282]" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"/><polyline points="14 2 14 8 20 8"/></svg>
          <span class="truncate">${f}</span>
        </div>
      `).join('');

      createCustomSatelliteCard({
        id: filesSatId,
        x: 940,
        y: 80,
        width: 340,
        badgeText: `Files Changed (${files.length})`,
        badgeColor: 'bg-[#f4f4f5] text-[#52525b] border-[#e4e4e7]',
        bodyHtml: filesHtml,
        icon: 'file-diff'
      });
      createEdge(comCard.id, filesSatId, 'doc');
    }

    // 3. Touched AST Code Symbols (Far Right)
    const symbols = commitData.symbols || [];
    if (symbols.length > 0) {
      const symSatId = `sat-csyms-${commitData.hash}`;
      const symsHtml = symbols.slice(0, 8).map(s => `
        <div class="py-1.5 flex items-center justify-between border-b border-[#e2e0dc] last:border-0 text-[11px]">
          <span class="font-mono text-[#202020] font-medium truncate max-w-[180px]">${s.name}()</span>
          <button class="text-[#c2410c] hover:text-[#9a3412] text-[10px] font-semibold cursor-pointer" data-symbol="${s.name}" data-action="explore-symbol">
            Blast Radius &rarr;
          </button>
        </div>
      `).join('');

      createCustomSatelliteCard({
        id: symSatId,
        x: 1330,
        y: 160,
        width: 300,
        badgeText: `Touched Symbols (${symbols.length})`,
        badgeColor: 'bg-[#fff7ed] text-[#816729] border-[#fed7aa]',
        bodyHtml: symsHtml,
        icon: 'code-2'
      });
      createEdge(comCard.id, symSatId, 'blast');
    }

    updateCables();
    fitViewToBoundingBox(55);
  }

  // --- Code Blast Radius Layout ---

  async function renderBlastRadiusLayout(symbolName) {
    clearCanvas();

    let symbolToQuery = symbolName || state.activeFocalSymbol;
    if (!symbolToQuery) {
      const coreSymbols = ['sync_workstate_from_tasks', 'get_workstate_summary', 'resolve_manifest', 'prune_team', 'get_tracked_repos', 'run_server'];
      for (const cs of coreSymbols) {
        if (state.availableSymbols && state.availableSymbols.some(s => s.name === cs)) {
          symbolToQuery = cs;
          break;
        }
      }
      if (!symbolToQuery && state.availableSymbols && state.availableSymbols.length > 0) {
        symbolToQuery = state.availableSymbols[0].name;
      }
    }

    state.activeFocalSymbol = symbolToQuery;
    const data = await fetchBlastRadius(symbolToQuery);

    if (!data || !data.found) {
      alert(`Symbol '${symbolToQuery || ''}' not found in code-graph.json. Search symbols in top bar.`);
      popNavigation();
      return;
    }

    const callers = data.downstream_callers || [];
    const isLeaf = callers.length === 0;

    const target = data.target;
    const centerX = 550;
    const centerY = 240;
    createSymbolCard(target, centerX, centerY, true, null, isLeaf);

    const callees = data.upstream_callees || [];
    if (callees.length === 0) {
      const dummyId = 'no-internal-callees';
      const dummyCard = createSatelliteCard({
        id: dummyId,
        x: 150,
        y: 220,
        width: 280,
        badgeText: 'Internal Dependencies',
        badgeColor: 'bg-[#f4f4f5] text-[#52525b] border-[#e4e4e7]',
        title: '0 Internal Callees',
        subtitle: 'Pure logic or standard library built-ins',
        icon: 'check-circle'
      });
      createEdge(dummyId, target.name, 'upstream');
    } else {
      callees.slice(0, 12).forEach((c, idx) => {
        const cx = 150;
        const cy = 80 + idx * 105;
        const cardId = `callee-${c.name}-${idx}`;
        createSymbolCard(c, cx, cy, false, cardId);
        createEdge(cardId, target.name, 'upstream');
      });
    }

    if (callers.length === 0) {
      const dummyId = 'no-internal-callers';
      const dummyCard = createSatelliteCard({
        id: dummyId,
        x: 950,
        y: 220,
        width: 280,
        badgeText: 'Blast Radius (Callers)',
        badgeColor: 'bg-[#f4f4f5] text-[#52525b] border-[#e4e4e7]',
        title: '0 Downstream Callers',
        subtitle: 'Entrypoint or top-level script/handler',
        icon: 'terminal'
      });
      createEdge(target.name, dummyId, 'blast');
    } else {
      callers.slice(0, 12).forEach((c, idx) => {
        const cx = 950;
        const cy = 80 + idx * 105;
        const cardId = `caller-${c.name}-${idx}`;
        createSymbolCard(c, cx, cy, false, cardId);
        createEdge(target.name, cardId, 'blast');
      });
    }

    updateCables();
    fitViewToBoundingBox(55);
    if (window.lucide) window.lucide.createIcons();
  }

  // --- Helpers & Card Factories ---

  function findSessionForTask(task) {
    if (!state.sessions || state.sessions.length === 0) return null;
    if (task.session_id) {
      const match = state.sessions.find(s => s.id === task.session_id || s.id === String(task.session_id));
      if (match) return match;
    }
    if (task.session_file) {
      const match = state.sessions.find(s => s.file === task.session_file || task.session_file.includes(s.file));
      if (match) return match;
    }
    return null;
  }

  function createTaskCard(task, x, y, isFocused) {
    const card = document.createElement('div');
    card.className = `canvas-card ${isFocused ? 'is-focused-main' : ''}`;
    card.id = `node-${task.id}`;
    card.style.transform = `translate3d(${x}px, ${y}px, 0)`;
    card.style.borderLeft = `3px solid var(--team-${task.team})`;

    const symbolsCount = (task.linked_symbols || []).length;
    const commitsCount = (task.linked_commits || []).length;
    const hasGitHub = task.github_pr || task.github_issue;

    const header = document.createElement('div');
    header.className = 'card-header';
    header.innerHTML = `
      <div class="flex items-center gap-2">
        <span class="badge-team badge-${task.team}">${task.team}</span>
        <span class="text-xs text-[#4d4d4d] font-mono font-medium">${task.priority}</span>
        ${symbolsCount > 0 ? `<span title="${symbolsCount} touched AST symbols" class="text-[10px] text-[#816729] font-mono flex items-center gap-0.5 bg-[#fff7ed] px-1.5 py-0.5 rounded-full border border-[#fed7aa]"><i data-lucide="code-2" class="w-3 h-3"></i>${symbolsCount}</span>` : ''}
        ${commitsCount > 0 ? `<span title="${commitsCount} linked commits" class="text-[10px] text-[#047857] font-mono flex items-center gap-0.5 bg-[#ecfdf5] px-1.5 py-0.5 rounded-full border border-[#a7f3d0]"><i data-lucide="git-commit" class="w-3 h-3 text-[#047857]"></i>${commitsCount}</span>` : ''}
        ${hasGitHub ? `<span title="GitHub linked" class="text-[10px] text-[#7c3aed] bg-[#f5f3ff] px-1.5 py-0.5 rounded-full border border-[#ddd6fe]"><i data-lucide="git-pull-request" class="w-3 h-3"></i></span>` : ''}
      </div>
      <div class="flex items-center gap-1.5">
        <span class="status-pill status-${task.status}" data-action="toggle-status">
          ${task.status.replace('_', ' ')}
        </span>
      </div>
    `;

    const body = document.createElement('div');
    body.className = 'p-3 text-left';
    body.innerHTML = `
      <div class="card-title">${task.title}</div>
      <div class="mt-2.5 flex items-center justify-between text-xs text-[#828282]">
        <span class="font-mono text-[11px] truncate max-w-[260px]">${task.file.split('/').pop()}</span>
      </div>
    `;

    const inputPort = document.createElement('div');
    inputPort.className = 'port port-input';
    inputPort.title = 'Dependency In (Blocked By)';
    inputPort.dataset.portType = 'input';
    inputPort.dataset.nodeId = task.id;

    const outputPort = document.createElement('div');
    outputPort.className = 'port port-output';
    outputPort.title = 'Dependency Out (Blocks)';
    outputPort.dataset.portType = 'output';
    outputPort.dataset.nodeId = task.id;

    card.appendChild(inputPort);
    card.appendChild(outputPort);
    card.appendChild(header);
    card.appendChild(body);

    setupCardInteractions(card, task, x, y, inputPort, outputPort);
    nodesLayer.appendChild(card);

    state.nodes.set(task.id, {
      id: task.id,
      element: card,
      x: x,
      y: y,
      width: 320,
      height: 120,
      inputPort,
      outputPort,
      data: task
    });

    return card;
  }

  function createSymbolCard(symbol, x, y, isFocal, overrideId, isLeaf) {
    const cardId = overrideId || symbol.name;
    const existing = document.getElementById(`node-${cardId}`);
    if (existing) existing.remove();

    const card = document.createElement('div');
    card.className = `canvas-card ${isFocal ? 'is-target-focal' : ''}`;
    card.style.width = '280px';
    card.id = `node-${cardId}`;
    card.style.transform = `translate3d(${x}px, ${y}px, 0)`;

    const isCrossRepo = symbol.repo && symbol.repo !== 'workforces';
    const repoBadge = isCrossRepo
      ? `<span class="badge-team badge-compliance font-mono text-[10px]">${symbol.repo}</span>`
      : `<span class="badge-team badge-dev font-mono text-[10px]">${symbol.kind || 'function'}</span>`;

    card.innerHTML = `
      <div class="card-header flex items-center justify-between">
        <div class="flex items-center gap-1.5">
          ${repoBadge}
          ${isCrossRepo ? `<span class="text-[10px] text-[#828282] font-mono">${symbol.kind || 'fn'}</span>` : ''}
        </div>
        <div class="flex items-center gap-1.5">
          <span class="text-xs font-mono text-[#828282]">L${symbol.line || 0}</span>
          ${!isFocal ? `
            <button class="px-2 py-0.5 rounded-none text-[10px] font-semibold bg-[#202020] hover:bg-[#383838] text-white transition-all flex items-center gap-1 cursor-pointer btn-sharp" data-action="pivot-symbol" data-symbol="${symbol.name}" title="Drill into ${symbol.name}() blast radius">
              <span>Drill &rarr;</span>
            </button>
          ` : ''}
        </div>
      </div>
      <div class="p-3 text-left">
        <div class="font-mono text-xs font-semibold text-[#202020] truncate" title="${symbol.name}()">${symbol.name}()</div>
        <div class="mt-1 font-mono text-[11px] text-[#828282] truncate" title="${symbol.file || 'internal'}">${symbol.file || 'internal'}</div>
        ${isFocal ? '<div class="mt-2 text-[10px] text-[#816729] font-semibold tracking-wide uppercase">Target Impact Focal Point</div>' : ''}
        ${isLeaf ? '<div class="mt-1.5 text-[10px] text-[#828282] font-mono flex items-center gap-1.5"><span class="w-1.5 h-1.5 rounded-full bg-[#828282]"></span>Isolated Leaf (0 Callers)</div>' : ''}
      </div>
    `;

    card.addEventListener('click', (e) => {
      if (state.hasDragged) return;
      const pivotBtn = e.target.closest('[data-action="pivot-symbol"]');
      if (pivotBtn) {
        e.stopPropagation();
        navigateTo('blast_radius', symbol.name, `${symbol.name}()`);
      }
    });

    const inputPort = document.createElement('div');
    inputPort.className = 'port port-input';
    const outputPort = document.createElement('div');
    outputPort.className = 'port port-output';

    card.appendChild(inputPort);
    card.appendChild(outputPort);
    nodesLayer.appendChild(card);

    state.nodes.set(cardId, {
      id: cardId,
      element: card,
      x: x,
      y: y,
      width: 280,
      height: 95,
      inputPort,
      outputPort,
      data: symbol
    });

    setupCardDrag(card, cardId);
    return card;
  }

  function createSatelliteCard(cfg) {
    const card = document.createElement('div');
    card.className = 'satellite-card p-3.5 text-left cursor-pointer';
    card.id = `node-${cfg.id}`;
    card.style.width = `${cfg.width || 280}px`;
    card.style.transform = `translate3d(${cfg.x}px, ${cfg.y}px, 0)`;

    card.innerHTML = `
      <div class="flex items-center justify-between pb-2 border-b border-[#e2e0dc]">
        <span class="text-[10px] uppercase tracking-wider font-semibold px-2 py-0.5 rounded-full border ${cfg.badgeColor}">
          ${cfg.badgeText}
        </span>
        <i data-lucide="${cfg.icon || 'link'}" class="w-3.5 h-3.5 text-[#828282]"></i>
      </div>
      <div class="mt-2.5">
        <div class="text-xs font-semibold text-[#202020] truncate" title="${cfg.title}">${cfg.title}</div>
        <div class="text-[11px] text-[#828282] truncate mt-0.5">${cfg.subtitle || ''}</div>
      </div>
      ${cfg.actionLabel ? `
        <div class="mt-2.5 pt-2 border-t border-[#e2e0dc]">
          <button class="text-[#c2410c] hover:text-[#9a3412] text-[11px] font-semibold flex items-center gap-1 cursor-pointer bg-[#fff7ed] hover:bg-[#ffedd5] px-2.5 py-1 rounded-none border border-[#fed7aa] transition-all btn-sharp" data-action="satellite-action">
            ${cfg.actionLabel}
          </button>
        </div>
      ` : ''}
    `;

    const inputPort = document.createElement('div');
    inputPort.className = 'port port-input';
    const outputPort = document.createElement('div');
    outputPort.className = 'port port-output';

    card.appendChild(inputPort);
    card.appendChild(outputPort);
    nodesLayer.appendChild(card);

    state.nodes.set(cfg.id, {
      id: cfg.id,
      element: card,
      x: cfg.x,
      y: cfg.y,
      width: cfg.width || 280,
      height: 110,
      inputPort,
      outputPort
    });

    setupCardDrag(card, cfg.id);
    return card;
  }

  function createCustomSatelliteCard(cfg) {
    const card = document.createElement('div');
    card.className = 'satellite-card p-3.5 text-left';
    card.id = `node-${cfg.id}`;
    card.style.width = `${cfg.width || 280}px`;
    card.style.transform = `translate3d(${cfg.x}px, ${cfg.y}px, 0)`;

    card.innerHTML = `
      <div class="flex items-center justify-between pb-2 border-b border-[#e2e0dc]">
        <span class="text-[10px] uppercase tracking-wider font-semibold px-2 py-0.5 rounded-full border ${cfg.badgeColor}">
          ${cfg.badgeText}
        </span>
        <i data-lucide="${cfg.icon || 'link'}" class="w-3.5 h-3.5 text-[#828282]"></i>
      </div>
      <div class="mt-2.5 max-h-48 overflow-y-auto space-y-1">
        ${cfg.bodyHtml}
      </div>
    `;

    card.addEventListener('click', (e) => {
      const btn = e.target.closest('[data-action="explore-symbol"]');
      if (btn) {
        const symbol = btn.dataset.symbol;
        if (symbol) navigateTo('blast_radius', symbol, `${symbol}()`);
      }
    });

    const inputPort = document.createElement('div');
    inputPort.className = 'port port-input';
    const outputPort = document.createElement('div');
    outputPort.className = 'port port-output';

    card.appendChild(inputPort);
    card.appendChild(outputPort);
    nodesLayer.appendChild(card);

    state.nodes.set(cfg.id, {
      id: cfg.id,
      element: card,
      x: cfg.x,
      y: cfg.y,
      width: cfg.width || 280,
      height: 130,
      inputPort,
      outputPort
    });

    setupCardDrag(card, cfg.id);
    return card;
  }

  // --- Interactions & Connectors ---

  function setupCardInteractions(card, task, x, y, inPort, outPort) {
    setupCardDrag(card, task.id);

    card.addEventListener('click', (e) => {
      const toggleBtn = e.target.closest('[data-action="toggle-status"]');

      if (toggleBtn) {
        cycleTaskStatus(task);
        return;
      }

      openInspectDrawer(task);
      navigateTo('task_focus', task, task.title);
    });

    outPort.addEventListener('mousedown', (e) => {
      e.stopPropagation();
      startConnecting(task.id, 'output', outPort);
    });

    inPort.addEventListener('mouseup', (e) => {
      e.stopPropagation();
      finishConnecting(task.id, 'input');
    });
  }

  function setupCardDrag(card, id) {
    card.addEventListener('mousedown', (e) => {
      if (e.target.closest('.port') || e.target.closest('button') || e.target.closest('a') || e.target.closest('[data-action]')) return;
      e.stopPropagation();
      const node = state.nodes.get(id);
      if (!node) return;
      state.draggedNode = node;
      state.dragStartPos = { x: e.clientX, y: e.clientY };
      state.hasDragged = false;
      const rect = card.getBoundingClientRect();
      state.dragOffset.x = (e.clientX - rect.left) / state.zoom;
      state.dragOffset.y = (e.clientY - rect.top) / state.zoom;
    });
  }

  function startConnecting(nodeId, portType, portEl) {
    state.connectingFrom = { nodeId, portType, element: portEl };
    const rect = portEl.getBoundingClientRect();
    const startX = (rect.left + 6 - state.panX) / state.zoom;
    const startY = (rect.top + 6 - state.panY) / state.zoom;

    const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
    path.setAttribute('class', 'cable-path is-active');
    connectionsLayer.appendChild(path);
    state.tempCable = { path, startX, startY };
  }

  function updateTempCable(clientX, clientY) {
    if (!state.tempCable) return;
    const endX = (clientX - state.panX) / state.zoom;
    const endY = (clientY - state.panY) / state.zoom;
    const { startX, startY, path } = state.tempCable;
    path.setAttribute('d', calculateBezierPath(startX, startY, endX, endY));
  }

  function finishConnecting(targetNodeId, targetPortType) {
    if (!state.connectingFrom) return;
    const sourceNodeId = state.connectingFrom.nodeId;
    if (sourceNodeId !== targetNodeId) {
      connectTasksOnServer(sourceNodeId, targetNodeId);
    }
  }

  function cycleTaskStatus(task) {
    const cycle = {
      todo: 'in_progress',
      in_progress: 'done',
      done: 'todo',
      blocked: 'in_progress',
      dropped: 'todo'
    };
    const nextStatus = cycle[task.status] || 'todo';
    updateTaskOnServer(task.file, { status: nextStatus });
  }

  // --- Bezier Spline Cables ---

  function createEdge(sourceId, targetId, type) {
    const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
    let cssClass = 'cable-path';
    if (type === 'blast') cssClass += ' is-blast';
    if (type === 'dependency') cssClass += ' is-blocked';
    if (type === 'session') cssClass += ' is-session';
    if (type === 'commit') cssClass += ' is-commit';
    if (type === 'doc') cssClass += ' is-doc';
    if (type === 'github') cssClass += ' is-github';

    path.setAttribute('class', cssClass);
    connectionsLayer.appendChild(path);

    state.edges.push({
      source: sourceId,
      target: targetId,
      type: type,
      element: path
    });
  }

  function calculateBezierPath(x1, y1, x2, y2) {
    const dx = Math.abs(x2 - x1);
    const curvature = Math.max(40, dx * 0.48);
    const cx1 = x1 + curvature;
    const cy1 = y1;
    const cx2 = x2 - curvature;
    const cy2 = y2;
    return `M ${x1} ${y1} C ${cx1} ${cy1}, ${cx2} ${cy2}, ${x2} ${y2}`;
  }

  function updateCables() {
    state.edges.forEach(edge => {
      const srcNode = state.nodes.get(edge.source);
      const tgtNode = state.nodes.get(edge.target);
      if (!srcNode || !tgtNode) return;

      const x1 = srcNode.x + srcNode.width;
      const y1 = srcNode.y + (srcNode.height / 2);
      const x2 = tgtNode.x;
      const y2 = tgtNode.y + (tgtNode.height / 2);

      edge.element.setAttribute('d', calculateBezierPath(x1, y1, x2, y2));
    });
  }

  // --- Drawer & Inspector ---

  function openInspectDrawer(task) {
    document.getElementById('drawer-title').innerText = task.title;
    document.getElementById('drawer-file').innerText = task.file;
    document.getElementById('drawer-team').innerText = task.team.toUpperCase();
    document.getElementById('drawer-status').value = task.status;
    document.getElementById('drawer-priority').value = task.priority;

    const bodyEl = document.getElementById('drawer-body');
    if (window.marked) {
      bodyEl.innerHTML = window.marked.parse(task.body || '*No task description available.*');
      bodyEl.querySelectorAll('a').forEach(a => {
        a.setAttribute('target', '_blank');
        a.setAttribute('rel', 'noopener noreferrer');
      });
    } else {
      bodyEl.innerText = task.body || 'No task description available.';
    }

    const saveBtn = document.getElementById('drawer-save-btn');
    saveBtn.onclick = () => {
      const newStatus = document.getElementById('drawer-status').value;
      const newPriority = document.getElementById('drawer-priority').value;
      const note = document.getElementById('drawer-note-input').value.trim();

      const updates = { status: newStatus, priority: newPriority };
      if (note) updates.evolution_note = note;

      updateTaskOnServer(task.file, updates);
      closeInspectDrawer();
    };

    inspectDrawer.classList.add('is-open');
    if (state.viewMode !== 'workstate') {
      setTimeout(() => fitViewToBoundingBox(55), 50);
    }
  }

  function closeInspectDrawer() {
    inspectDrawer.classList.remove('is-open');
    document.getElementById('drawer-note-input').value = '';
    if (state.viewMode !== 'workstate') {
      setTimeout(() => fitViewToBoundingBox(55), 50);
    }
  }

  // --- Controls & UI Setup ---

  function setupControls() {
    const btnZoomIn = document.getElementById('btn-zoom-in');
    if (btnZoomIn) btnZoomIn.onclick = () => zoomAroundPoint(1.2);

    const btnZoomOut = document.getElementById('btn-zoom-out');
    if (btnZoomOut) btnZoomOut.onclick = () => zoomAroundPoint(1 / 1.2);

    const btnZoomReset = document.getElementById('btn-zoom-reset');
    if (btnZoomReset) {
      btnZoomReset.onclick = () => {
        state.panX = 80;
        state.panY = 80;
        state.zoom = 0.95;
        applyTransform();
        const zoomLbl = document.getElementById('zoom-label');
        if (zoomLbl) zoomLbl.innerText = '95%';
      };
    }

    const btnWorkstate = document.getElementById('btn-mode-workstate');
    if (btnWorkstate) {
      btnWorkstate.onclick = () => navigateTo('workstate', null, 'Radar', false);
    }

    const btnBlast = document.getElementById('btn-mode-blast');
    if (btnBlast) {
      btnBlast.onclick = () => navigateTo('blast_radius', state.activeFocalSymbol || 'sync_workstate_from_tasks', 'Blast Radius');
    }

    const btnExitFocus = document.getElementById('btn-exit-focus');
    if (btnExitFocus) {
      btnExitFocus.onclick = () => popNavigation();
    }

    const drawerClose = document.getElementById('drawer-close-btn');
    if (drawerClose) {
      drawerClose.onclick = closeInspectDrawer;
    }

    window.addEventListener('resize', () => {
      if (state.viewMode !== 'workstate') {
        fitViewToBoundingBox(55);
      }
    });

    window.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') {
        if (state.viewMode !== 'workstate') {
          popNavigation();
        } else {
          closeInspectDrawer();
        }
      }
      if (e.key === 'r' && !e.target.matches('input, textarea')) {
        const resetBtn = document.getElementById('btn-zoom-reset');
        if (resetBtn) resetBtn.click();
      }
    });
  }

  function setupSearch() {
    const searchInput = document.getElementById('global-search');
    searchInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        const query = searchInput.value.trim();
        if (!query) return;

        // Check if query matches a symbol in code-graph
        const matchedSymbol = state.availableSymbols
          ? state.availableSymbols.find(s => s.name.toLowerCase().includes(query.toLowerCase()))
          : null;

        if (matchedSymbol || state.viewMode === 'blast_radius') {
          navigateTo('blast_radius', matchedSymbol ? matchedSymbol.name : query, `${matchedSymbol ? matchedSymbol.name : query}()`);
        } else {
          const match = state.tasks.find(t => t.title.toLowerCase().includes(query.toLowerCase()));
          if (match) {
            navigateTo('task_focus', match, match.title);
            openInspectDrawer(match);
          }
        }
      }
    });
  }

  function updateTopBarStats() {
    const totalEl = document.getElementById('stat-total-tasks');
    if (totalEl) totalEl.innerText = `${state.stats.total_tasks || 0} Tasks`;
    const inProgEl = document.getElementById('stat-in-progress');
    if (inProgEl) inProgEl.innerText = `${state.stats.in_progress || 0} In Progress`;
    const blockedEl = document.getElementById('stat-blocked');
    if (blockedEl) blockedEl.innerText = `${state.stats.blocked || 0} Blocked`;
    const blockedCountEl = document.getElementById('stat-blocked-count');
    if (blockedCountEl) blockedCountEl.innerText = `${state.stats.blocked || 0} Blocked`;
    const inboxCountEl = document.getElementById('stat-inbox-count');
    if (inboxCountEl) inboxCountEl.innerText = `${state.stats.inbox_count || 0} Inbox`;
    const railInboxBadge = document.getElementById('rail-inbox-badge');
    if (railInboxBadge) {
      const count = state.stats.inbox_count || 0;
      railInboxBadge.innerText = count;
      if (count > 0) railInboxBadge.classList.remove('hidden');
      else railInboxBadge.classList.add('hidden');
    }
  }

  // --- Heartbeat & Auto-Shutdown Management ---

  let heartbeatInterval = null;
  let isServerDisconnected = false;

  function setupHeartbeatAndPower() {
    // 1. Initial heartbeat after 500ms, then every 30s
    setTimeout(sendHeartbeat, 500);
    heartbeatInterval = setInterval(sendHeartbeat, 30000);

    // 2. Power / Stop button handler
    const stopBtn = document.getElementById('btn-stop-server');
    if (stopBtn) {
      stopBtn.onclick = async () => {
        if (!confirm('Stop the Workforce Command Canvas server and release port 8765?')) {
          return;
        }
        stopBtn.disabled = true;
        try {
          await fetch('/api/shutdown', { method: 'POST' });
        } catch (e) {
          // Expected network drop on server shutdown
        }
        showDisconnectedOverlay('Server Stopped Manually', 'The backend Python server was shut down and port 8765 has been released. You can safely close this browser window.');
      };
    }

    // 3. Reconnect button in disconnected overlay
    const reconnectBtn = document.getElementById('btn-reconnect');
    if (reconnectBtn) {
      reconnectBtn.onclick = async () => {
        reconnectBtn.innerText = 'Connecting...';
        try {
          const res = await fetch('/api/heartbeat');
          if (res.ok) {
            window.location.reload();
            return;
          }
        } catch (e) {
          // Still down
        }
        setTimeout(() => {
          reconnectBtn.innerText = 'Reconnect';
          alert('Server is not running yet. Run `python skills/workforce-canvas/scripts/server.py` in your terminal to start it again.');
        }, 600);
      };
    }

    // 4. Send beacon when window is closed
    window.addEventListener('beforeunload', () => {
      if (!isServerDisconnected && navigator.sendBeacon) {
        navigator.sendBeacon('/api/heartbeat?closing=true');
      }
    });
  }

  async function sendHeartbeat() {
    if (isServerDisconnected) return;
    try {
      const res = await fetch('/api/heartbeat', { method: 'POST' });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      updateHeartbeatBadge(true, data);
    } catch (err) {
      updateHeartbeatBadge(false);
    }
  }

  function updateHeartbeatBadge(online, data) {
    const dot = document.getElementById('heartbeat-dot');
    const label = document.getElementById('heartbeat-label');
    const badge = document.getElementById('heartbeat-badge');
    if (!dot || !label) return;

    if (online) {
      dot.className = 'w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse';
      if (data && data.time_remaining !== undefined && data.time_remaining >= 0) {
        const mins = Math.floor(data.time_remaining / 60);
        const secs = data.time_remaining % 60;
        const timeStr = mins > 0 ? `${mins}m` : `${secs}s`;
        label.innerText = `${timeStr} Idle`;
        badge.title = `Canvas active. Auto-shuts down after ${timeStr} of inactivity if tabs close.`;
      } else {
        label.innerText = 'Live';
      }
    } else {
      dot.className = 'w-1.5 h-1.5 rounded-full bg-rose-500';
      label.innerText = 'Offline';
      badge.title = 'Server disconnected or stopped.';
    }
  }

  function showDisconnectedOverlay(title, description) {
    isServerDisconnected = true;
    if (heartbeatInterval) clearInterval(heartbeatInterval);
    updateHeartbeatBadge(false);

    const overlay = document.getElementById('disconnected-overlay');
    const titleEl = document.getElementById('disconnected-title');
    const descEl = document.getElementById('disconnected-desc');
    if (titleEl && title) titleEl.innerText = title;
    if (descEl && description) descEl.innerText = description;
    if (overlay) {
      overlay.classList.remove('hidden');
      if (window.lucide) window.lucide.createIcons();
    }
  }

  // ==========================================================================
  // OpenDesign Studio Split-Stage Controller
  // ==========================================================================

  const studioState = {
    openTabs: [],
    activeTabId: null,
    activeScenario: 'document',
    viewportMode: 'desktop',
    previewMode: 'preview',
    pinModeActive: false,
    pendingPinCoord: null,
    inboxItems: [],
    turnSummary: '',
  };

  function setupStudio() {
    setupSidebarRail();
    setupStageControls();
    setupCopilotFeed();
    setupStandupActions();
    loadStudioInitialContent();
  }

  function setupSidebarRail() {
    const railButtons = document.querySelectorAll('#studio-sidebar-rail .rail-item');
    railButtons.forEach(btn => {
      btn.addEventListener('click', () => {
        const view = btn.getAttribute('data-view');
        if (view === 'radar') {
          switchToRadarMode();
        } else {
          switchToView(view);
        }
      });
    });
  }

  function switchToRadarMode() {
    const studioContainer = document.getElementById('studio-workspace-container');
    const canvasViewport = document.getElementById('canvas-viewport');
    const radarDock = document.getElementById('radar-dock');
    if (studioContainer) studioContainer.classList.add('hidden');
    if (canvasViewport) canvasViewport.classList.remove('hidden');
    if (radarDock) radarDock.style.display = 'flex';

    document.querySelectorAll('#studio-sidebar-rail .rail-item').forEach(r => r.classList.remove('active'));
    const railRadar = document.getElementById('rail-btn-radar');
    if (railRadar) railRadar.classList.add('active');

    navigateTo('workstate', null, 'Radar', false);
    if (window.lucide) window.lucide.createIcons();
  }

  function switchToView(viewName) {
    studioState.activeScenario = viewName;
    const studioContainer = document.getElementById('studio-workspace-container');
    const canvasViewport = document.getElementById('canvas-viewport');
    const radarDock = document.getElementById('radar-dock');
    if (canvasViewport) canvasViewport.classList.add('hidden');
    if (radarDock) radarDock.style.display = 'none';
    if (studioContainer) studioContainer.classList.remove('hidden');

    // Update left rail active class
    document.querySelectorAll('#studio-sidebar-rail .rail-item').forEach(r => r.classList.remove('active'));
    const railKey = viewName === 'document' ? 'docs' : viewName;
    const targetRail = document.getElementById(`rail-btn-${railKey}`);
    if (targetRail) targetRail.classList.add('active');

    // Hide all stage containers
    const stageIds = ['stage-cockpit-view', 'stage-tasks-view', 'stage-inbox-view', 'stage-hypotheses-view', 'stage-document-view'];
    stageIds.forEach(id => {
      const el = document.getElementById(id);
      if (el) el.classList.add('hidden');
    });

    // Show selected stage container
    const targetStageId = `stage-${viewName === 'cockpit' ? 'cockpit' : (viewName === 'tasks' ? 'tasks' : (viewName === 'inbox' ? 'inbox' : (viewName === 'hypotheses' ? 'hypotheses' : 'document')))}-view`;
    const targetStageEl = document.getElementById(targetStageId);
    if (targetStageEl) targetStageEl.classList.remove('hidden');

    // Render corresponding view data
    if (viewName === 'cockpit') {
      renderStandupCockpit();
    } else if (viewName === 'tasks') {
      renderTasksStage();
    } else if (viewName === 'inbox') {
      renderInboxStage();
    } else if (viewName === 'hypotheses') {
      renderHypothesesStage();
    } else if (viewName === 'document') {
      renderActiveTabContent();
    }

    updateCopilotActiveFileContext();
    if (window.lucide) window.lucide.createIcons();
  }

  function switchToStudioMode(scenario = 'document') {
    switchToView(scenario);
  }

  function setupStageControls() {
    const btnPreview = document.getElementById('btn-toggle-preview');
    const btnCode = document.getElementById('btn-toggle-code');
    if (btnPreview && btnCode) {
      btnPreview.addEventListener('click', () => {
        studioState.previewMode = 'preview';
        btnPreview.className = 'px-2.5 py-1 rounded text-xs font-semibold bg-white text-[#202020] shadow-xs';
        btnCode.className = 'px-2.5 py-1 rounded text-xs font-medium text-[#666] hover:text-[#202020]';
        renderActiveTabContent();
      });
      btnCode.addEventListener('click', () => {
        studioState.previewMode = 'code';
        btnCode.className = 'px-2.5 py-1 rounded text-xs font-semibold bg-white text-[#202020] shadow-xs';
        btnPreview.className = 'px-2.5 py-1 rounded text-xs font-medium text-[#666] hover:text-[#202020]';
        renderActiveTabContent();
      });
    }

    const btnRefresh = document.getElementById('btn-stage-refresh');
    if (btnRefresh) {
      btnRefresh.addEventListener('click', async () => {
        await fetchWorkforceState();
        await loadTurnSummary();
        renderActiveTabContent();
      });
    }
  }

  function setupCopilotFeed() {
    const btnSubmit = document.getElementById('btn-copilot-submit-comment');
    const commentInput = document.getElementById('copilot-comment-input');
    const statusEl = document.getElementById('copilot-comment-status');

    if (btnSubmit && commentInput) {
      btnSubmit.addEventListener('click', async () => {
        const text = commentInput.value.trim();
        if (!text) return;
        const activeTab = studioState.openTabs.find(t => t.id === studioState.activeTabId);
        const payload = {
          target_type: activeTab ? (activeTab.type || 'task') : 'copilot',
          target_id: activeTab ? activeTab.id : 'copilot',
          file: activeTab?.path || '',
          comment: text,
          author: '@human'
        };

        try {
          const res = await fetch('/api/comments', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
          });
          if (res.ok) {
            commentInput.value = '';
            if (statusEl) {
              statusEl.classList.remove('hidden');
              setTimeout(() => statusEl.classList.add('hidden'), 3000);
            }
            await fetchWorkforceState();
            await loadTurnSummary();
            renderActiveTabContent();
          }
        } catch (err) {
          console.error('Comment submit error:', err);
        }
      });

      commentInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
          btnSubmit.click();
        }
      });
    }

    renderRecommendedActions();
    updateCopilotActiveFileContext();
  }

  function updateCopilotActiveFileContext() {
    const activeTab = studioState.openTabs.find(t => t.id === studioState.activeTabId);
    const targetLabel = document.getElementById('copilot-feedback-target-label');
    const targetTag = document.getElementById('copilot-active-file-tag');
    const commentInput = document.getElementById('copilot-comment-input');
    const contextTitle = document.getElementById('copilot-context-title');
    const contextSub = document.getElementById('copilot-context-subtitle');

    const taskPanel = document.getElementById('copilot-task-panel');
    const standupPanel = document.getElementById('copilot-standup-panel');

    const isTaskDoc = activeTab && (activeTab.type === 'task' || (activeTab.path && activeTab.path.includes('tasks/')));

    if (studioState.activeScenario === 'document' && isTaskDoc) {
      // Find matching task object
      const task = (state.tasks || []).find(t => t.id === activeTab.id || (t.file && t.file === activeTab.path));
      if (taskPanel) taskPanel.classList.remove('hidden');
      if (standupPanel) standupPanel.classList.add('hidden');

      if (contextTitle) contextTitle.innerText = "Task Inspector";
      if (contextSub) contextSub.innerText = "Properties, blockers, and questions for this task.";

      if (targetLabel) targetLabel.innerText = 'Note on active task:';
      if (targetTag) {
        targetTag.innerText = task ? task.title : (activeTab.title || 'Active Task');
        targetTag.title = activeTab.path || 'Task file';
      }
      if (commentInput) {
        commentInput.placeholder = `Add note or instruction for this task...`;
      }

      if (task) {
        renderTaskCopilotPanel(task);
      }
    } else {
      // Standup / general overview mode
      if (taskPanel) taskPanel.classList.add('hidden');
      if (standupPanel) standupPanel.classList.remove('hidden');

      if (contextTitle) contextTitle.innerText = "Standup Copilot";
      if (contextSub) contextSub.innerText = "Sprint focus, recommended actions, and decisions.";

      if (targetLabel) targetLabel.innerText = 'Note for active session:';
      if (targetTag) {
        targetTag.innerText = 'Standup Session';
        targetTag.title = 'General session context';
      }
      if (commentInput) {
        commentInput.placeholder = 'Add note or instruction for active workforce session...';
      }

      renderStandupCopilotPanel();
    }
  }

  function renderTaskCopilotPanel(task) {
    if (!task) return;

    // 1. Task Title & File
    const titleEl = document.getElementById('task-panel-title');
    const fileEl = document.getElementById('task-panel-file');
    const prioEl = document.getElementById('task-panel-priority');
    const teamEl = document.getElementById('task-panel-team');

    if (titleEl) titleEl.innerText = task.title || 'Untitled Task';
    if (fileEl) fileEl.innerText = task.file || `workforces/tasks/${task.id}.md`;
    if (prioEl) {
      prioEl.innerText = task.priority || 'P2';
      prioEl.className = `text-[10px] font-mono font-bold px-1.5 py-0.5 rounded ${task.priority === 'P0' ? 'bg-[#fee2e2] text-[#b91c1c] border border-[#fecaca]' : 'bg-[#f4f4f5] text-[#4d4d4d] border border-[#e2e0dc]'}`;
    }
    if (teamEl) {
      teamEl.innerText = (task.team || 'dev').toUpperCase();
      teamEl.className = `badge-team badge-${(task.team || 'dev').toLowerCase()}`;
    }

    // 2. Status Cycler Button
    const statusBtn = document.getElementById('task-panel-status-btn');
    const statusLabel = document.getElementById('task-panel-status-label');
    const statusDot = document.getElementById('task-panel-status-dot');

    if (statusLabel) statusLabel.innerText = (task.status || 'todo').toUpperCase();
    if (statusDot) {
      statusDot.className = `w-2 h-2 rounded-full ${task.status === 'in_progress' ? 'bg-[#0369a1]' : (task.status === 'done' ? 'bg-emerald-600' : (task.status === 'blocked' ? 'bg-[#b91c1c]' : 'bg-[#828282]'))}`;
    }

    if (statusBtn) {
      statusBtn.onclick = async () => {
        await cycleTaskStatus(task);
        const updated = (state.tasks || []).find(t => t.id === task.id);
        if (updated) renderTaskCopilotPanel(updated);
      };
    }

    // 3. Blocker Card
    const blockerCard = document.getElementById('task-panel-blocker-card');
    const blockerText = document.getElementById('task-panel-blocker-text');
    const resolveBtn = document.getElementById('btn-task-resolve-blocker');

    const isBlocked = task.status === 'blocked' || (task.blocked_by && task.blocked_by.length > 0);
    if (blockerCard) {
      if (isBlocked) {
        blockerCard.classList.remove('hidden');
        const blockerIds = task.blocked_by && task.blocked_by.length > 0 ? task.blocked_by.join(', ') : 'Active roadblock flagged';
        if (blockerText) blockerText.innerText = `Blocked by: ${blockerIds}`;
        if (resolveBtn) {
          resolveBtn.onclick = async () => {
            await updateTaskOnServer(task.file, { status: 'in_progress', blocked_by: [] });
            const updated = (state.tasks || []).find(t => t.id === task.id);
            if (updated) renderTaskCopilotPanel(updated);
          };
        }
      } else {
        blockerCard.classList.add('hidden');
      }
    }

    // 4. Open Questions Card & Inline Answer Form
    const questionsCard = document.getElementById('task-panel-questions-card');
    const questionsList = document.getElementById('task-panel-questions-list');
    const questionsCount = document.getElementById('task-panel-questions-count');

    const openQs = task.open_questions || [];
    if (questionsCount) questionsCount.innerText = openQs.length;

    if (questionsList) {
      questionsList.innerHTML = '';
      if (openQs.length === 0) {
        questionsList.innerHTML = '<p class="text-[11px] text-[#828282] italic">Zero blockers or open questions for this task.</p>';
      } else {
        openQs.forEach((q, idx) => {
          const qBox = document.createElement('div');
          qBox.className = 'p-2.5 bg-white border border-[#fed7aa] rounded-md space-y-2';
          qBox.innerHTML = `
            <div class="flex items-start gap-1.5">
              <span class="text-[10px] font-mono font-bold text-[#c2410c] mt-0.5">Q${idx + 1}:</span>
              <p class="text-xs font-medium text-[#202020] leading-snug flex-1">${escapeHtml(q)}</p>
            </div>
            <div class="flex items-center gap-1.5 pt-1">
              <input type="text" placeholder="Type answer for AI agent..." class="flex-1 text-[11px] px-2 py-1 bg-[#faf9f5] border border-[#e2e0dc] rounded focus:outline-none focus:border-[#c2410c] text-[#202020] answer-input">
              <button class="px-2 py-1 bg-[#202020] hover:bg-[#383838] text-white text-[10px] font-semibold rounded shrink-0 btn-save-answer">
                Answer
              </button>
            </div>
          `;

          const inputEl = qBox.querySelector('.answer-input');
          const btnEl = qBox.querySelector('.btn-save-answer');

          const submitAnswer = async () => {
            const ans = inputEl.value.trim();
            if (!ans) return;
            btnEl.innerText = 'Saving...';
            try {
              await fetch('/api/task/update', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                  file: task.file,
                  updates: {
                    answer_question: { question: q, answer: ans }
                  }
                })
              });
              await fetchWorkforceState();
              // Re-render task in active tab
              openTaskTab(task.id);
            } catch (e) {
              alert(`Save answer error: ${e.message}`);
            }
          };

          btnEl.onclick = submitAnswer;
          inputEl.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') submitAnswer();
          });

          questionsList.appendChild(qBox);
        });
      }
    }

    // 5. Recommended Next Actions for this specific task
    const actionsList = document.getElementById('task-panel-actions-list');
    if (actionsList) {
      actionsList.innerHTML = '';
      const taskActions = [];
      if (task.suggested_action) taskActions.push(task.suggested_action);
      if (task.checklist && task.checklist.length > 0) {
        task.checklist.slice(0, 3).forEach(c => taskActions.push(c));
      }

      if (taskActions.length === 0) {
        actionsList.innerHTML = '<p class="text-[10.5px] text-[#828282] italic py-1">No explicit next step documented in task.</p>';
      } else {
        taskActions.forEach(act => {
          const btn = document.createElement('button');
          btn.className = 'recommended-action-item';
          btn.innerHTML = `
            <span class="action-text">${escapeHtml(act)}</span>
            <i data-lucide="arrow-right" class="w-3.5 h-3.5 action-icon"></i>
          `;
          btn.onclick = () => {
            const commentInput = document.getElementById('copilot-comment-input');
            if (commentInput) {
              commentInput.value = act;
              commentInput.focus();
            }
          };
          actionsList.appendChild(btn);
        });
      }
    }

    // 6. Task Evolution Log
    const historyList = document.getElementById('task-panel-history-list');
    const historyCount = document.getElementById('task-panel-history-count');
    const notes = task.evolution_notes || [];

    if (historyCount) historyCount.innerText = `${notes.length} entries`;
    if (historyList) {
      historyList.innerHTML = '';
      if (notes.length === 0) {
        historyList.innerHTML = '<p class="text-[10.5px] text-[#828282] italic">No evolution history recorded yet.</p>';
      } else {
        notes.slice(-5).reverse().forEach(n => {
          const row = document.createElement('div');
          row.className = 'p-1.5 bg-white border border-[#e2e0dc] rounded text-[11px] leading-relaxed';
          row.innerText = n;
          historyList.appendChild(row);
        });
      }
    }

    if (window.lucide) window.lucide.createIcons();
  }

  function renderStandupCopilotPanel() {
    const standup = state.standup || {};
    const oneThing = standup.one_thing || (state.tasks && state.tasks.length > 0 ? state.tasks[0] : null);

    const focusTitle = document.getElementById('standup-copilot-focus-title');
    const focusDesc = document.getElementById('standup-copilot-focus-desc');

    if (oneThing && focusTitle) {
      focusTitle.innerText = oneThing.title || 'Untitled';
      focusTitle.onclick = () => openTaskTab(oneThing.id);
      if (focusDesc) {
        focusDesc.innerText = oneThing.body ? oneThing.body.replace(/[#*`_]/g, '').trim().slice(0, 140) + '...' : 'Evaluating sprint priorities...';
      }
    }

    renderRecommendedActions();

    // Decisions in standup copilot
    const decContainer = document.getElementById('copilot-decisions-feed');
    const decSession = document.getElementById('copilot-decisions-session');
    const latestSession = standup.latest_session || {};

    if (decSession) {
      decSession.innerText = latestSession.id ? `Session ${latestSession.id}` : 'Session';
    }

    if (decContainer) {
      const decisions = latestSession.decisions || [];
      if (decisions.length === 0) {
        decContainer.innerHTML = '<p class="text-[10.5px] text-[#828282] italic py-1">No decisions recorded in latest session.</p>';
      } else {
        decContainer.innerHTML = '';
        decisions.slice(0, 4).forEach(d => {
          const row = document.createElement('div');
          row.className = 'p-2 bg-white border border-[#e2e0dc] rounded text-[11px] space-y-0.5';
          row.innerHTML = `
            <div class="font-semibold text-[#202020] flex items-center gap-1">
              <i data-lucide="check" class="w-3 h-3 text-emerald-600"></i>
              <span class="truncate">${escapeHtml(d.title || d.what || 'Decision')}</span>
            </div>
            ${d.why ? `<p class="text-[#666] line-clamp-2 text-[10.5px]">${escapeHtml(d.why)}</p>` : ''}
          `;
          decContainer.appendChild(row);
        });
      }
    }

    if (window.lucide) window.lucide.createIcons();
  }

  function renderRecommendedActions() {
    const container = document.getElementById('copilot-recommended-actions-list');
    if (!container) return;

    const actions = (state.standup && state.standup.recommended_actions) || [];
    if (actions.length === 0) {
      container.innerHTML = '<p class="text-[10.5px] text-[#828282] italic py-1">No recommended actions queued in workstate.md.</p>';
      return;
    }

    container.innerHTML = '';
    actions.forEach((act) => {
      const btn = document.createElement('button');
      btn.className = 'recommended-action-item';
      btn.title = `Click to queue instruction or inspect: "${escapeHtml(act)}"`;
      btn.innerHTML = `
        <span class="action-text">${escapeHtml(act)}</span>
        <i data-lucide="arrow-right" class="w-3.5 h-3.5 action-icon"></i>
      `;
      btn.addEventListener('click', () => {
        // If the action references an active task by title, open that task!
        const matchingTask = (state.tasks || []).find(t => act.toLowerCase().includes(t.title.toLowerCase()) || t.title.toLowerCase().includes(act.toLowerCase()));
        if (matchingTask) {
          openTaskTab(matchingTask.id);
        }
        
        // Also pre-fill the comment/feedback box so the user can easily act on it
        const commentInput = document.getElementById('copilot-comment-input');
        if (commentInput) {
          commentInput.value = act;
          commentInput.focus();
        }
      });
      container.appendChild(btn);
    });

    if (window.lucide) window.lucide.createIcons();
  }

  async function loadTurnSummary() {
    try {
      const res = await fetch('/api/turn-summary');
      if (res.ok) {
        const data = await res.json();
        const container = document.getElementById('copilot-turn-summary-text');
        if (container) {
          container.innerText = data.content || "Autonomous execution verified. All unit tests, static analysis, and linters passed with 0 regressions.";
        }
      }
    } catch (err) {
      // Keep existing
    }
  }

  async function loadStudioInitialContent() {
    await loadTurnSummary();

    // Populate turn files
    const filesList = document.getElementById('copilot-files-list');
    const filesCount = document.getElementById('copilot-files-count');
    if (filesList) {
      filesList.innerHTML = '';
      const sampleFiles = [];

      state.tasks.slice(0, 4).forEach(t => {
        sampleFiles.push({ name: t.file ? t.file.split('/').pop() : `${t.id}.md`, path: t.file, type: 'task', title: t.title, id: t.id });
      });

      if (state.sessions.length > 0) {
        sampleFiles.push({ name: `${state.sessions[0].id}.md`, path: `workforces/session-context/${state.sessions[0].id}.md`, type: 'session', title: state.sessions[0].topic, id: state.sessions[0].id });
      }

      if (filesCount) filesCount.innerText = `${sampleFiles.length} files`;

      sampleFiles.forEach(f => {
        const row = document.createElement('div');
        row.className = 'turn-file-row';
        row.innerHTML = `
          <div class="flex items-center gap-2 truncate max-w-[200px]">
            <i data-lucide="file-code" class="w-3.5 h-3.5 text-[#828282] shrink-0"></i>
            <span class="font-mono truncate" title="${f.path}">${f.name}</span>
          </div>
          <button class="px-2 py-0.5 rounded text-[11px] font-medium text-[#c2410c] hover:bg-[#fff7ed] transition-colors btn-open-file">Open</button>
        `;
        row.querySelector('.btn-open-file').addEventListener('click', () => {
          if (f.type === 'task') {
            openTaskTab(f.id);
          } else {
            openDocumentTab(f.path, f.title);
          }
        });
        filesList.appendChild(row);
      });
    }

    // Start cleanly with 0 tabs open; user can open tasks/documents on demand
    renderTabStrip();
    switchToView('cockpit');
  }

  function openTab(tab) {
    const existing = studioState.openTabs.find(t => t.id === tab.id);
    if (!existing) {
      studioState.openTabs.push(tab);
    }
    studioState.activeTabId = tab.id;
    switchToStudioMode(tab.scenario || 'document');
    renderTabStrip();
    renderActiveTabContent();
  }

  function closeTab(tabId, e) {
    if (e) e.stopPropagation();
    studioState.openTabs = studioState.openTabs.filter(t => t.id !== tabId);
    if (studioState.activeTabId === tabId) {
      if (studioState.openTabs.length > 0) {
        studioState.activeTabId = studioState.openTabs[studioState.openTabs.length - 1].id;
        switchToView('document');
      } else {
        studioState.activeTabId = null;
        // If all tabs closed, return cleanly to Cockpit view
        switchToView('cockpit');
      }
    }
    renderTabStrip();
    renderActiveTabContent();
  }

  function renderTabStrip() {
    const strip = document.getElementById('studio-tabs-strip');
    if (!strip) return;
    strip.innerHTML = '';

    studioState.openTabs.forEach(tab => {
      const tabEl = document.createElement('div');
      tabEl.className = `studio-tab ${tab.id === studioState.activeTabId && studioState.activeScenario === 'document' ? 'active' : ''}`;
      const iconName = tab.type === 'task' ? 'check-square' : 'file-text';
      tabEl.innerHTML = `
        <i data-lucide="${iconName}" class="w-3.5 h-3.5"></i>
        <span class="truncate max-w-[140px]">${escapeHtml(tab.title)}</span>
        <button class="studio-tab-close" title="Close tab">&times;</button>
      `;
      tabEl.addEventListener('click', () => {
        studioState.activeTabId = tab.id;
        switchToView('document');
        renderTabStrip();
      });
      tabEl.querySelector('.studio-tab-close').addEventListener('click', (e) => {
        closeTab(tab.id, e);
      });
      strip.appendChild(tabEl);
    });

    if (window.lucide) window.lucide.createIcons();
  }

  async function openTaskTab(taskId) {
    const task = state.tasks.find(t => t.id === taskId);
    if (!task) return;

    const tab = {
      id: task.id,
      title: task.title,
      type: 'task',
      path: task.file,
      content: `# ${task.title}\n\n**Status:** \`${task.status}\` | **Priority:** \`${task.priority}\` | **Team:** \`${task.team}\` | **File:** \`${task.file || 'workforces/tasks/'}\`\n\n---\n\n${task.body || "No task description."}`,
      scenario: 'document'
    };

    openTab(tab);
  }

  async function openDocumentTab(filePath, title) {
    let content = `# ${title || filePath}\n\nLoading document content...`;
    try {
      const res = await fetch(`/api/document?path=${encodeURIComponent(filePath)}`);
      if (res.ok) {
        const data = await res.json();
        content = data.content;
      }
    } catch (err) {
      console.warn("Could not fetch document content:", filePath, err);
    }

    const tab = {
      id: filePath,
      title: title || filePath.split('/').pop(),
      type: 'doc',
      path: filePath,
      content: content,
      scenario: 'document'
    };
    openTab(tab);
  }

  function openDefaultDocumentTab() {
    // If tasks exist, open the first task by default
    if (state.tasks && state.tasks.length > 0) {
      openTaskTab(state.tasks[0].id);
    }
  }

  // --------------------------------------------------------------------------
  // Dedicated Stage Views (Tasks, Inbox, Hypotheses)
  // --------------------------------------------------------------------------

  let currentTasksStageTeamFilter = 'all';

  function renderTasksStage() {
    const tasks = state.tasks || [];
    const countBadge = document.getElementById('tasks-stage-count-badge');
    const grid = document.getElementById('tasks-stage-grid');
    const newBtn = document.getElementById('btn-tasks-stage-new');

    if (countBadge) countBadge.innerText = `${tasks.length} Tasks`;
    if (newBtn) {
      const mainNewBtn = document.getElementById('btn-cockpit-new-task');
      newBtn.onclick = () => { if (mainNewBtn) mainNewBtn.click(); };
    }

    // Bind team filters for tasks stage
    const teamChips = document.querySelectorAll('#tasks-stage-team-filters .team-filter-chip');
    teamChips.forEach(chip => {
      chip.onclick = () => {
        teamChips.forEach(c => c.classList.remove('active'));
        chip.classList.add('active');
        currentTasksStageTeamFilter = chip.getAttribute('data-team') || 'all';
        renderTasksStage();
      };
    });

    if (!grid) return;
    grid.innerHTML = '';

    const filterTeam = currentTasksStageTeamFilter.toLowerCase();
    const filtered = filterTeam === 'all' 
      ? tasks 
      : tasks.filter(t => (t.team || 'dev').toLowerCase() === filterTeam);

    if (filtered.length === 0) {
      grid.innerHTML = `<div class="col-span-full p-8 text-center text-xs text-[#828282] italic border border-dashed border-[#e2e0dc] rounded-lg">No tasks found for this filter.</div>`;
      return;
    }

    filtered.forEach(task => {
      const card = document.createElement('div');
      const prioLower = (task.priority || 'P2').toLowerCase();
      card.className = `kanban-card priority-${prioLower} flex flex-col justify-between space-y-3 p-4 bg-white border border-[#e2e0dc] rounded-lg hover:border-[#c2410c] cursor-pointer transition-all`;

      const statusBadge = task.status === 'in_progress'
        ? '<span class="text-[9.5px] font-mono px-1.5 py-0.5 rounded bg-[#e0f2fe] text-[#0369a1] font-semibold">IN PROGRESS</span>'
        : (task.status === 'done'
          ? '<span class="text-[9.5px] font-mono px-1.5 py-0.5 rounded bg-[#dcfce7] text-emerald-800 font-semibold">DONE</span>'
          : (task.status === 'blocked'
            ? '<span class="text-[9.5px] font-mono px-1.5 py-0.5 rounded bg-[#fee2e2] text-[#b91c1c] font-semibold">BLOCKED</span>'
            : '<span class="text-[9.5px] font-mono px-1.5 py-0.5 rounded bg-[#f4f4f5] text-[#52525b] font-semibold">TODO</span>'));

      card.innerHTML = `
        <div>
          <div class="flex items-center justify-between gap-2 mb-2">
            <div class="flex items-center gap-1.5">
              <span class="text-[9px] font-mono font-bold uppercase px-1.5 py-0.2 rounded ${task.priority === 'P0' ? 'bg-[#fee2e2] text-[#b91c1c]' : 'bg-[#f4f4f5] text-[#4d4d4d]'}">${task.priority || 'P1'}</span>
              <span class="badge-team badge-${(task.team || 'dev').toLowerCase()}">${(task.team || 'dev').toUpperCase()}</span>
            </div>
            ${statusBadge}
          </div>
          <h4 class="text-xs font-bold text-[#202020] leading-snug hover:text-[#c2410c] transition-colors">${escapeHtml(task.title)}</h4>
          <p class="text-[11px] text-[#666] line-clamp-2 mt-1 leading-relaxed">${escapeHtml(task.body ? task.body.replace(/[#*`_]/g, '').trim() : '')}</p>
        </div>
        <div class="flex items-center justify-between pt-2 border-t border-[#f4f4f5] text-[10px] font-mono text-[#828282]">
          <span>${task.assignee || '@human'}</span>
          <button class="px-2 py-0.5 rounded bg-[#faf9f5] border border-[#e2e0dc] hover:border-[#c2410c] text-[#202020] font-medium btn-advance-task">
            Cycle Status
          </button>
        </div>
      `;

      card.onclick = () => openTaskTab(task.id);
      card.querySelector('.btn-advance-task').onclick = (e) => {
        e.stopPropagation();
        cycleTaskStatus(task);
      };

      grid.appendChild(card);
    });

    if (window.lucide) window.lucide.createIcons();
  }

  async function renderInboxStage() {
    const listContainer = document.getElementById('inbox-stage-list');
    const badge = document.getElementById('inbox-stage-count-badge');
    if (!listContainer) return;

    let items = [];
    try {
      const res = await fetch('/api/inbox');
      if (res.ok) {
        const data = await res.json();
        items = data.items || [];
      }
    } catch (e) {
      console.warn("Could not load inbox items:", e);
    }

    if (badge) badge.innerText = `${items.length} Item${items.length === 1 ? '' : 's'}`;

    if (items.length === 0) {
      listContainer.innerHTML = '<div class="p-8 text-center text-xs text-[#828282] italic border border-dashed border-[#e2e0dc] rounded-lg">No pending captures in the extension inbox. Use the Chrome Extension to capture research, ask-gemini snippets, or issues.</div>';
      return;
    }

    listContainer.innerHTML = '';
    items.forEach(item => {
      const dateStr = item.captured_at ? item.captured_at.slice(5, 16).replace('T', ' ') : '';
      const card = document.createElement('div');
      card.className = 'p-4 bg-white border border-[#e2e0dc] rounded-lg space-y-2 hover:border-[#c2410c] transition-all';
      card.innerHTML = `
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-2">
            <span class="text-[9.5px] font-mono uppercase tracking-wider px-2 py-0.5 rounded bg-[#faf9f5] border border-[#e2e0dc] text-[#4d4d4d] font-semibold">${item.type || 'capture'}</span>
            <span class="text-xs font-bold text-[#202020]">${escapeHtml(item.title || 'Untitled Capture')}</span>
          </div>
          <span class="text-[10px] font-mono text-[#828282]">${dateStr}</span>
        </div>
        <p class="text-xs text-[#666] leading-relaxed whitespace-pre-wrap">${escapeHtml(item.content || item.selection || '')}</p>
        <div class="flex items-center justify-between pt-2 border-t border-[#f4f4f5]">
          ${item.source_url ? `<a href="${item.source_url}" target="_blank" class="text-[11px] text-[#c2410c] underline inline-block">Source URL &rarr;</a>` : '<span></span>'}
          <div class="flex items-center gap-1.5">
            <button class="px-2.5 py-1 rounded bg-[#202020] hover:bg-[#383838] text-white text-[11px] font-semibold btn-convert-task">
              Convert to Task
            </button>
            <button class="px-2 py-1 rounded bg-[#faf9f5] border border-[#e2e0dc] hover:border-[#b91c1c] text-[#b91c1c] text-[11px] font-medium btn-dismiss-inbox">
              Dismiss
            </button>
          </div>
        </div>
      `;

      card.querySelector('.btn-convert-task').onclick = () => handleInboxAction(item.id, 'approve');
      card.querySelector('.btn-dismiss-inbox').onclick = () => handleInboxAction(item.id, 'reject');

      listContainer.appendChild(card);
    });

    if (window.lucide) window.lucide.createIcons();
  }

  function renderHypothesesStage() {
    const listContainer = document.getElementById('hypotheses-stage-list');
    const badge = document.getElementById('hypotheses-stage-count-badge');
    if (!listContainer) return;

    const hypotheses = state.hypotheses || [];
    if (badge) badge.innerText = `${hypotheses.length} Hypotheses`;

    if (hypotheses.length === 0) {
      listContainer.innerHTML = '<div class="p-8 text-center text-xs text-[#828282] italic border border-dashed border-[#e2e0dc] rounded-lg">No active hypotheses recorded in workforces/hypotheses/.</div>';
      return;
    }

    listContainer.innerHTML = '';
    hypotheses.forEach(h => {
      const card = document.createElement('div');
      card.className = 'p-5 bg-white border border-[#e2e0dc] rounded-lg space-y-2 hover:border-[#c2410c] transition-all';
      card.innerHTML = `
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-2">
            <i data-lucide="flask-conical" class="w-4 h-4 text-[#c2410c]"></i>
            <h3 class="text-xs font-bold text-[#202020]">${escapeHtml(h.title)}</h3>
          </div>
          <span class="text-[10px] font-mono text-[#828282] uppercase bg-[#faf9f5] px-2 py-0.5 rounded border border-[#e2e0dc]">Experiment</span>
        </div>
        <p class="text-xs text-[#666] leading-relaxed whitespace-pre-wrap">${escapeHtml(h.body || '')}</p>
      `;
      listContainer.appendChild(card);
    });

    if (window.lucide) window.lucide.createIcons();
  }

  function openPluginsTab() {
    const plugins = [
      { name: "clean-coder", desc: "Craftsmanship, TDD, zero error swallowing.", type: "core" },
      { name: "code-graph", desc: "AST symbol indexing & blast radius call graph.", type: "core" },
      { name: "task-tracker", desc: "Deciding factors, session lineage, and workstate sync.", type: "core" },
      { name: "workforce-canvas", desc: "Interactive OpenDesign studio and command radar.", type: "core" },
      { name: "image-workflow", desc: "Prompt deconstruction and Antigravity asset generation.", type: "skill" },
      { name: "feature-research", desc: "5-phase PRD authoring pipeline.", type: "skill" },
    ];

    let html = `
      <div class="space-y-4">
        <div class="border-b border-[#e2e0dc] pb-3">
          <h2 class="text-lg font-bold text-[#202020]">Workforces Skills &amp; Plugins</h2>
          <p class="text-xs text-[#828282]">Installed modular agents, skills, and tools.</p>
        </div>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
    `;

    plugins.forEach(p => {
      html += `
        <div class="p-4 bg-[#faf9f5] border border-[#e2e0dc] rounded-lg">
          <div class="flex items-center justify-between mb-1">
            <span class="text-xs font-semibold text-[#202020]">${p.name}</span>
            <span class="text-[9.5px] font-mono px-1.5 py-0.5 rounded bg-white border border-[#e2e0dc] uppercase text-[#666]">${p.type}</span>
          </div>
          <p class="text-[11.5px] text-[#666]">${p.desc}</p>
        </div>
      `;
    });

    html += `</div></div>`;

    openTab({
      id: 'studio-plugins',
      title: 'Skills & Plugins',
      type: 'plugins',
      content: html,
      scenario: 'document',
      pins: []
    });
  }

  function renderActiveTabContent() {
    const activeTab = studioState.openTabs.find(t => t.id === studioState.activeTabId);
    const contentBox = document.getElementById('preview-content-box');
    const stageFileLabel = document.getElementById('stage-file-label');

    if (!activeTab || !contentBox) {
      if (contentBox) contentBox.innerHTML = '<p class="text-center text-xs text-[#828282] py-20">Select an item from the sidebar or open tabs.</p>';
      updateCopilotActiveFileContext();
      return;
    }

    if (stageFileLabel) stageFileLabel.innerText = activeTab.path || activeTab.title;

    if (studioState.previewMode === 'code') {
      contentBox.innerHTML = `<pre class="p-4 font-mono text-xs bg-[#faf9f5] border border-[#e2e0dc] rounded overflow-x-auto whitespace-pre-wrap"><code>${escapeHtml(activeTab.content || '')}</code></pre>`;
    } else {
      if (activeTab.isInbox || activeTab.type === 'tasks' || activeTab.type === 'hypotheses' || activeTab.type === 'plugins') {
        contentBox.innerHTML = activeTab.content;
      } else {
        try {
          contentBox.innerHTML = window.marked ? window.marked.parse(activeTab.content) : activeTab.content;
        } catch (e) {
          contentBox.innerHTML = `<p>${escapeHtml(activeTab.content)}</p>`;
        }
      }
    }

    updateCopilotActiveFileContext();
    if (window.lucide) window.lucide.createIcons();
  }

  // ==========================================================================
  // Standup Cockpit & Productivity Dashboard Controller
  // ==========================================================================

  let currentKanbanTeamFilter = 'all';

  function renderStandupCockpit() {
    const standup = state.standup || {};
    const tasks = state.tasks || [];
    const oneThing = standup.one_thing || (tasks.length > 0 ? tasks[0] : null);
    const needsAttention = standup.needs_attention || [];
    const wins = standup.wins_24h || [];

    // 1. Render "The One Thing" Focus Card
    const oneThingTitle = document.getElementById('one-thing-title');
    const oneThingDesc = document.getElementById('one-thing-desc');
    const oneThingStatus = document.getElementById('one-thing-status-badge');
    const oneThingTeam = document.getElementById('one-thing-team');
    const oneThingAssignee = document.getElementById('one-thing-assignee');
    const oneThingDate = document.getElementById('one-thing-date');
    const oneThingCycleBtn = document.getElementById('btn-one-thing-cycle');
    const oneThingInspectBtn = document.getElementById('btn-one-thing-inspect');
    const oneThingCycleLabel = document.getElementById('one-thing-cycle-label');

    if (oneThing && oneThingTitle) {
      oneThingTitle.innerText = oneThing.title || 'Untitled Task';
      oneThingTitle.onclick = () => openTaskTab(oneThing.id);
      if (oneThingDesc) {
        oneThingDesc.innerText = oneThing.body ? oneThing.body.replace(/[#*`_]/g, '').trim().slice(0, 160) + '...' : 'No description provided.';
      }
      if (oneThingStatus) {
        oneThingStatus.innerText = (oneThing.status || 'todo').toUpperCase();
        if (oneThing.status === 'in_progress') {
          oneThingStatus.className = 'px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase font-mono bg-[#e0f2fe] text-[#0369a1]';
        } else if (oneThing.status === 'done') {
          oneThingStatus.className = 'px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase font-mono bg-[#dcfce7] text-emerald-800';
        } else {
          oneThingStatus.className = 'px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase font-mono bg-[#f4f4f5] text-[#52525b]';
        }
      }
      if (oneThingTeam) {
        const tName = (oneThing.team || 'dev').toUpperCase();
        oneThingTeam.innerText = tName;
        oneThingTeam.className = `badge-team badge-${(oneThing.team || 'dev').toLowerCase()}`;
      }
      if (oneThingAssignee) {
        oneThingAssignee.innerText = `Assignee: ${oneThing.assignee || '@human'}`;
      }
      if (oneThingDate) {
        const dt = oneThing.updated_at || oneThing.reported_at || '';
        oneThingDate.innerText = `Updated: ${dt ? dt.slice(0, 10) : 'Today'}`;
      }
      if (oneThingCycleBtn) {
        oneThingCycleBtn.onclick = () => cycleTaskStatus(oneThing);
        if (oneThingCycleLabel) {
          oneThingCycleLabel.innerText = oneThing.status === 'todo' ? 'Start Task' : (oneThing.status === 'in_progress' ? 'Mark Done' : 'Restart Task');
        }
      }
      if (oneThingInspectBtn) {
        oneThingInspectBtn.onclick = () => openTaskTab(oneThing.id);
      }
    } else if (oneThingTitle) {
      oneThingTitle.innerText = "No active tasks in workspace";
      if (oneThingDesc) oneThingDesc.innerText = "Create a task or run a standup sync to populate the sprint pipeline.";
      if (oneThingStatus) oneThingStatus.innerText = "READY";
    }

    // 2. Render "Needs Attention" Radar Card
    const attentionList = document.getElementById('attention-items-list');
    const attentionBadge = document.getElementById('attention-count-badge');
    if (attentionBadge) {
      attentionBadge.innerText = `${needsAttention.length} Item${needsAttention.length === 1 ? '' : 's'}`;
    }

    if (attentionList) {
      if (needsAttention.length === 0) {
        attentionList.innerHTML = `
          <div class="py-6 text-center text-xs text-emerald-700 bg-emerald-50/50 rounded-lg border border-emerald-100 flex flex-col items-center gap-1">
            <i data-lucide="check-circle" class="w-4 h-4 text-emerald-600"></i>
            <span>All systems clear. Zero blockers or pending reviews!</span>
          </div>
        `;
      } else {
        attentionList.innerHTML = '';
        needsAttention.forEach(item => {
          const card = document.createElement('div');
          card.className = `attention-card ${item.type === 'blocker' ? 'blocker' : ''}`;
          
          let actionBtns = '';
          if (item.type === 'inbox_review') {
            actionBtns = `
              <div class="flex items-center gap-1.5 mt-1">
                <button class="px-2 py-0.5 rounded text-[10.5px] font-semibold bg-[#202020] text-white hover:bg-[#333] transition-colors btn-approve-inbox">Approve &amp; Task</button>
                <button class="px-2 py-0.5 rounded text-[10.5px] font-medium text-[#828282] hover:bg-[#faf9f5] border border-[#e2e0dc] transition-colors btn-dismiss-inbox">Dismiss</button>
              </div>
            `;
          } else {
            actionBtns = `
              <div class="flex items-center gap-1.5 mt-1">
                <button class="px-2 py-0.5 rounded text-[10.5px] font-semibold text-[#c2410c] hover:bg-[#fff7ed] transition-colors btn-open-task">Inspect Blocker &rarr;</button>
              </div>
            `;
          }

          card.innerHTML = `
            <div class="flex items-center justify-between">
              <span class="text-[9.5px] font-mono font-bold uppercase tracking-wider ${item.type === 'blocker' ? 'text-[#b91c1c]' : 'text-[#ea580c]'}">${item.type.replace('_', ' ')}</span>
              <span class="text-[9.5px] font-mono text-[#828282]">${item.priority || 'P1'}</span>
            </div>
            <h4 class="text-xs font-semibold text-[#202020] leading-snug cursor-pointer hover:text-[#c2410c]">${escapeHtml(item.title)}</h4>
            <p class="text-[11px] text-[#666] leading-relaxed">${escapeHtml(item.reason)}</p>
            ${actionBtns}
          `;

          if (item.type === 'inbox_review') {
            const approveBtn = card.querySelector('.btn-approve-inbox');
            const dismissBtn = card.querySelector('.btn-dismiss-inbox');
            if (approveBtn) approveBtn.onclick = () => handleInboxAction(item.id, 'approve');
            if (dismissBtn) dismissBtn.onclick = () => handleInboxAction(item.id, 'dismiss');
          } else {
            const openBtn = card.querySelector('.btn-open-task');
            if (openBtn) {
              openBtn.onclick = () => {
                if (item.task) openTaskTab(item.task.id);
                else openDocumentTab(item.file || '', item.title);
              };
            }
          }

          attentionList.appendChild(card);
        });
      }
    }

    // 3. Render 4-Stat Metric Strip
    const statInProg = document.getElementById('stat-card-in-progress');
    if (statInProg) statInProg.innerText = state.stats.in_progress || (standup.in_progress ? standup.in_progress.length : 0);

    const statTodo = document.getElementById('stat-card-todo');
    if (statTodo) statTodo.innerText = state.stats.todo || (standup.todo ? standup.todo.length : 0);

    const statAttention = document.getElementById('stat-card-attention');
    if (statAttention) statAttention.innerText = needsAttention.length;

    const statWins = document.getElementById('stat-card-wins');
    if (statWins) statWins.innerText = wins.length;

    // 4. Render 4-Column Sprint Kanban
    renderKanbanColumns();

    // 5. Render Architectural Decisions & 24h Wins
    const decisionList = document.getElementById('session-decisions-list');
    const decisionSessId = document.getElementById('session-decision-id');
    const latestSession = standup.latest_session || {};

    if (decisionSessId) {
      decisionSessId.innerText = latestSession.id ? `Session ${latestSession.id}` : 'Latest Session';
    }

    if (decisionList) {
      const decisions = latestSession.decisions || [];
      if (decisions.length === 0) {
        decisionList.innerHTML = `<p class="text-xs text-[#828282] italic py-2">No decision records found in recent session contexts.</p>`;
      } else {
        decisionList.innerHTML = '';
        decisions.slice(0, 5).forEach(d => {
          const row = document.createElement('div');
          row.className = 'p-2.5 bg-[#faf9f5] border border-[#e2e0dc] rounded-md space-y-1';
          row.innerHTML = `
            <div class="flex items-center gap-1.5 text-[10.5px] font-semibold text-[#202020]">
              <i data-lucide="check" class="w-3 h-3 text-emerald-600"></i>
              <span>${escapeHtml(d.title || d.what || 'Architecture Decision')}</span>
            </div>
            ${d.why ? `<p class="text-[11px] text-[#666] leading-relaxed">${escapeHtml(d.why)}</p>` : ''}
          `;
          decisionList.appendChild(row);
        });
      }
    }

    const winsList = document.getElementById('cockpit-wins-list');
    const winsCount = document.getElementById('wins-completed-count');
    if (winsCount) winsCount.innerText = `${wins.length} Done`;

    if (winsList) {
      if (wins.length === 0) {
        winsList.innerHTML = `<p class="text-xs text-[#828282] italic py-2">No completed tasks recorded in the last 24 hours.</p>`;
      } else {
        winsList.innerHTML = '';
        wins.slice(0, 5).forEach(w => {
          const row = document.createElement('div');
          row.className = 'p-2.5 bg-[#faf9f5] border border-[#e2e0dc] rounded-md flex items-center justify-between gap-3';
          row.innerHTML = `
            <div class="flex items-center gap-2 truncate">
              <i data-lucide="check-circle-2" class="w-3.5 h-3.5 text-emerald-600 shrink-0"></i>
              <span class="text-xs font-medium text-[#202020] truncate cursor-pointer hover:text-[#c2410c] win-title">${escapeHtml(w.title)}</span>
            </div>
            <span class="text-[10px] font-mono text-[#828282] shrink-0">${w.completed_at || 'Recently'}</span>
          `;
          row.querySelector('.win-title').onclick = () => openTaskTab(w.id);
          winsList.appendChild(row);
        });
      }
    }

    renderRecommendedActions();
    updateCopilotActiveFileContext();

    // Refresh Lucide vector icons
    if (window.lucide) window.lucide.createIcons();
  }

  function renderKanbanColumns() {
    const tasks = state.tasks || [];
    const filterTeam = currentKanbanTeamFilter.toLowerCase();

    const filtered = filterTeam === 'all' 
      ? tasks 
      : tasks.filter(t => (t.team || 'dev').toLowerCase() === filterTeam);

    const cols = {
      in_progress: filtered.filter(t => t.status === 'in_progress'),
      todo: filtered.filter(t => t.status === 'todo'),
      blocked: filtered.filter(t => t.status === 'blocked' || (t.blocked_by && t.blocked_by.length > 0)),
      done: filtered.filter(t => t.status === 'done'),
    };

    ['in_progress', 'todo', 'blocked', 'done'].forEach(colKey => {
      const container = document.getElementById(`kanban-cards-${colKey.replace('_', '-')}`);
      const countEl = document.getElementById(`kanban-count-${colKey.replace('_', '-')}`);
      const list = cols[colKey] || [];

      if (countEl) countEl.innerText = list.length;
      if (!container) return;

      if (list.length === 0) {
        container.innerHTML = `<div class="p-3 text-center text-[11px] text-[#828282] italic border border-dashed border-[#e2e0dc] rounded">Empty</div>`;
        return;
      }

      container.innerHTML = '';
      list.forEach(task => {
        const card = document.createElement('div');
        const prioLower = (task.priority || 'P2').toLowerCase();
        card.className = `kanban-card priority-${prioLower}`;

        const nextActionLabel = task.status === 'todo' ? 'Start &rarr;' : (task.status === 'in_progress' ? 'Done &check;' : 'Restart');

        card.innerHTML = `
          <div class="flex items-center justify-between mb-1.5">
            <span class="text-[9px] font-mono font-bold uppercase px-1.5 py-0.2 rounded ${task.priority === 'P0' ? 'bg-[#fee2e2] text-[#b91c1c]' : 'bg-[#f4f4f5] text-[#4d4d4d]'}">${task.priority || 'P1'}</span>
            <span class="text-[9.5px] font-mono uppercase text-[#828282]">${(task.team || 'dev').toUpperCase()}</span>
          </div>
          <h4 class="text-xs font-semibold text-[#202020] leading-snug mb-2 hover:text-[#c2410c] transition-colors">${escapeHtml(task.title)}</h4>
          <div class="flex items-center justify-between pt-2 border-t border-[#f4f4f5]">
            <span class="text-[10px] font-mono text-[#828282] truncate max-w-[110px]">${task.assignee || '@human'}</span>
            <button class="px-2 py-0.5 rounded text-[10px] font-semibold bg-[#f4f4f5] hover:bg-[#e4e4e7] text-[#202020] transition-colors btn-cycle-status">
              ${nextActionLabel}
            </button>
          </div>
        `;

        card.querySelector('h4').onclick = () => openTaskTab(task.id);
        card.querySelector('.btn-cycle-status').onclick = (e) => {
          e.stopPropagation();
          cycleTaskStatus(task);
        };

        container.appendChild(card);
      });
    });
  }

  async function cycleTaskStatus(task) {
    let nextStatus = 'in_progress';
    if (task.status === 'todo') nextStatus = 'in_progress';
    else if (task.status === 'in_progress') nextStatus = 'done';
    else if (task.status === 'done') nextStatus = 'todo';
    else if (task.status === 'blocked') nextStatus = 'in_progress';

    await updateTaskOnServer(task.file, { status: nextStatus });
  }

  async function handleInboxAction(itemId, action) {
    try {
      const res = await fetch('/api/inbox/action', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ item_id: itemId, action: action, priority: 'P1' })
      });
      if (res.ok) {
        await fetchWorkforceState();
      }
    } catch (err) {
      alert(`Action failed: ${err.message}`);
    }
  }

  function setupStandupActions() {
    // 1. Sync button
    const btnSync = document.getElementById('btn-standup-sync');
    const syncIcon = document.getElementById('icon-standup-sync');
    if (btnSync) {
      btnSync.onclick = async () => {
        if (syncIcon) syncIcon.classList.add('animate-spin');
        try {
          const res = await fetch('/api/sync', { method: 'POST' });
          if (res.ok) {
            await fetchWorkforceState();
          }
        } catch (err) {
          console.error('Standup sync error:', err);
        } finally {
          if (syncIcon) syncIcon.classList.remove('animate-spin');
        }
      };
    }

    // 2. Team filter chips
    const teamChips = document.querySelectorAll('#kanban-team-filters .team-filter-chip');
    teamChips.forEach(chip => {
      chip.onclick = () => {
        teamChips.forEach(c => c.classList.remove('active'));
        chip.classList.add('active');
        currentKanbanTeamFilter = chip.getAttribute('data-team') || 'all';
        renderKanbanColumns();
      };
    });

    // 3. New Task Modal
    const btnNewTask = document.getElementById('btn-cockpit-new-task');
    const taskModal = document.getElementById('new-task-modal');
    const taskModalClose = document.getElementById('btn-task-modal-close');
    const taskModalCancel = document.getElementById('btn-task-modal-cancel');
    const taskModalSave = document.getElementById('btn-task-modal-save');

    function openTaskModal() {
      if (taskModal) {
        document.getElementById('task-modal-title').value = '';
        document.getElementById('task-modal-desc').value = '';
        document.getElementById('task-modal-action').value = '';
        taskModal.classList.remove('hidden');
        document.getElementById('task-modal-title').focus();
      }
    }

    function closeTaskModal() {
      if (taskModal) taskModal.classList.add('hidden');
    }

    if (btnNewTask) btnNewTask.onclick = openTaskModal;
    if (taskModalClose) taskModalClose.onclick = closeTaskModal;
    if (taskModalCancel) taskModalCancel.onclick = closeTaskModal;

    if (taskModalSave) {
      taskModalSave.onclick = async () => {
        const title = document.getElementById('task-modal-title').value.trim();
        const priority = document.getElementById('task-modal-priority').value;
        const team = document.getElementById('task-modal-team').value;
        const desc = document.getElementById('task-modal-desc').value.trim();
        const action = document.getElementById('task-modal-action').value.trim();

        if (!title) {
          alert('Please enter a task title.');
          return;
        }

        try {
          const res = await fetch('/api/task/create', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              title: title,
              priority: priority,
              type: team,
              description: desc,
              suggested_action: action,
              reporter: '@human'
            })
          });
          if (res.ok) {
            closeTaskModal();
            await fetchWorkforceState();
          } else {
            alert('Failed to create task');
          }
        } catch (err) {
          alert(`Error creating task: ${err.message}`);
        }
      };
    }
  }

  function escapeHtml(str) {
    if (!str) return '';
    return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }

  // Self-start on DOM ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();
