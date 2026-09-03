/**
 * Workforce Command Canvas - Interactive Engine
 * Zero npm dependencies (Vanilla JS + SVG Bezier Splines)
 */

(function () {
  'use strict';

  // State Management
  const state = {
    viewMode: 'workstate', // 'workstate' | 'blast_radius'
    panX: 80,
    panY: 80,
    zoom: 0.95,
    isPanning: false,
    startX: 0,
    startY: 0,
    nodes: new Map(), // id -> { id, element, x, y, width, height, data }
    edges: [],        // [ { source, target, type, label, element } ]
    selectedNodeId: null,
    draggedNode: null,
    dragOffset: { x: 0, y: 0 },
    connectingFrom: null, // { nodeId, portType, element }
    tempCable: null,
    tasks: [],
    hypotheses: [],
    goals: [],
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
    await fetchWorkforceState();
    renderView();
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
      state.hypotheses = data.hypotheses || [];
      state.goals = data.goals || [];
      state.stats = data.stats || {};
      updateTopBarStats();
    } catch (err) {
      console.error('Fetch error:', err);
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
      renderView();
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
      renderView();
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
      // Pan when clicking background or holding space
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
      }
      if (state.connectingFrom) {
        if (state.tempCable) {
          state.tempCable.remove();
          state.tempCable = null;
        }
        state.connectingFrom = null;
      }
    });

    viewport.addEventListener('wheel', (e) => {
      e.preventDefault();
      const zoomFactor = 1.08;
      const oldZoom = state.zoom;
      let newZoom = e.deltaY < 0 ? oldZoom * zoomFactor : oldZoom / zoomFactor;
      newZoom = Math.max(0.2, Math.min(2.5, newZoom));

      // Zoom towards mouse position
      const rect = viewport.getBoundingClientRect();
      const mouseX = e.clientX - rect.left;
      const mouseY = e.clientY - rect.top;

      state.panX = mouseX - (mouseX - state.panX) * (newZoom / oldZoom);
      state.panY = mouseY - (mouseY - state.panY) * (newZoom / oldZoom);
      state.zoom = newZoom;

      applyTransform();
      document.getElementById('zoom-label').innerText = `${Math.round(state.zoom * 100)}%`;
    }, { passive: false });
  }

  // --- Rendering & Layouts ---

  function renderView() {
    nodesLayer.innerHTML = '';
    connectionsLayer.innerHTML = '';
    framesLayer.innerHTML = '';
    state.nodes.clear();
    state.edges = [];

    if (state.viewMode === 'workstate') {
      renderWorkstateLayout();
    } else {
      renderBlastRadiusLayout();
    }

    if (window.lucide) {
      window.lucide.createIcons();
    }
  }

  function renderWorkstateLayout() {
    // Column Groups: To Do, In Progress, Blocked, Done
    const columns = [
      { id: 'in_progress', label: 'In Progress (Active Focus)', status: 'in_progress', x: 400, color: 'var(--status-in-progress)' },
      { id: 'blocked', label: 'Blocked / Needs Unblocking', status: 'blocked', x: 800, color: 'var(--status-blocked)' },
      { id: 'todo', label: 'Ready Queue / Backlog', status: 'todo', x: 50, color: 'var(--status-todo)' },
      { id: 'done', label: 'Completed Deliverables', status: 'done', x: 1200, color: 'var(--status-done)' }
    ];

    // Render grouped frames
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

      // Render cards in column
      colTasks.forEach((task, index) => {
        const cardX = col.x;
        const cardY = 70 + index * 160;
        createTaskCard(task, cardX, cardY);
      });
    });

    // Build edges for blocked_by
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

  async function renderBlastRadiusLayout(symbolName) {
    const symbolToQuery = symbolName || 'setUp';
    const data = await fetchBlastRadius(symbolToQuery);

    if (!data || !data.found) {
      alert(`Symbol '${symbolToQuery}' not found in code-graph.json`);
      state.viewMode = 'workstate';
      renderView();
      return;
    }

    // Focal Node in Center
    const target = data.target;
    const centerX = 550;
    const centerY = 240;
    createSymbolCard(target, centerX, centerY, true);

    // Upstream callees on Left (what target calls)
    const callees = data.upstream_callees.slice(0, 6); // Cap at 6 to avoid noise
    callees.forEach((c, idx) => {
      const cx = 150;
      const cy = 100 + idx * 110;
      const cardId = `callee-${c.name}-${idx}`;
      createSymbolCard(c, cx, cy, false, cardId);
      createEdge(cardId, target.name, 'upstream');
    });

    // Downstream callers on Right (Blast Radius: who calls target)
    const callers = data.downstream_callers.slice(0, 6);
    if (callers.length === 0) {
      // Empty blast radius card
      createPlaceholderCard('No downstream callers detected (Isolated Leaf)', 950, centerY);
    } else {
      callers.forEach((c, idx) => {
        const cx = 950;
        const cy = 100 + idx * 110;
        const cardId = `caller-${c.name}-${idx}`;
        createSymbolCard(c, cx, cy, false, cardId);
        createEdge(target.name, cardId, 'blast');
      });
    }

    updateCables();
  }

  // --- Node & Card Factories ---

  function createTaskCard(task, x, y) {
    const card = document.createElement('div');
    card.className = 'canvas-card';
    card.id = `node-${task.id}`;
    card.style.transform = `translate3d(${x}px, ${y}px, 0)`;

    // Team Accent Border
    card.style.borderLeft = `3px solid var(--team-${task.team})`;

    // Header
    const header = document.createElement('div');
    header.className = 'card-header';
    header.innerHTML = `
      <div class="flex items-center gap-2">
        <span class="badge-team badge-${task.team}">${task.team}</span>
        <span class="text-xs text-muted font-mono font-medium">${task.priority}</span>
      </div>
      <div class="flex items-center gap-1.5">
        <span class="status-pill status-${task.status}" data-action="toggle-status">
          ${task.status.replace('_', ' ')}
        </span>
      </div>
    `;

    // Body
    const body = document.createElement('div');
    body.className = 'p-3 text-left';
    body.innerHTML = `
      <div class="card-title">${task.title}</div>
      <div class="mt-2 flex items-center justify-between text-xs text-muted">
        <span class="font-mono text-[11px] truncate max-w-[170px]">${task.file.split('/').pop()}</span>
        <button class="text-sky-400 hover:text-sky-300 font-medium text-[11px] flex items-center gap-1" data-action="inspect-impact">
          Code Trail &rarr;
        </button>
      </div>
    `;

    // Ports
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

    // Event Bindings
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
  }

  function createSymbolCard(symbol, x, y, isFocal, overrideId) {
    const cardId = overrideId || symbol.name;
    const card = document.createElement('div');
    card.className = `canvas-card ${isFocal ? 'is-target-focal' : ''}`;
    card.style.width = '280px';
    card.id = `node-${cardId}`;
    card.style.transform = `translate3d(${x}px, ${y}px, 0)`;

    card.innerHTML = `
      <div class="card-header">
        <span class="badge-team badge-dev font-mono">${symbol.kind || 'function'}</span>
        <span class="text-xs font-mono text-muted">L${symbol.line || 0}</span>
      </div>
      <div class="p-3 text-left">
        <div class="font-mono text-xs font-semibold text-white truncate">${symbol.name}()</div>
        <div class="mt-1 font-mono text-[11px] text-muted truncate">${symbol.file || 'internal'}</div>
        ${isFocal ? '<div class="mt-2 text-[10px] text-amber-400 font-semibold tracking-wide uppercase">Target Impact Focal Point</div>' : ''}
      </div>
    `;

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
      height: 90,
      inputPort,
      outputPort,
      data: symbol
    });

    setupCardDrag(card, cardId);
  }

  function createPlaceholderCard(text, x, y) {
    const card = document.createElement('div');
    card.className = 'canvas-card opacity-60 border-dashed';
    card.style.transform = `translate3d(${x}px, ${y}px, 0)`;
    card.innerHTML = `<div class="p-6 text-center text-xs text-muted font-mono">${text}</div>`;
    nodesLayer.appendChild(card);
  }

  // --- Interactions & Connectors ---

  function setupCardInteractions(card, task, x, y, inPort, outPort) {
    setupCardDrag(card, task.id);

    // Click handling
    card.addEventListener('click', (e) => {
      const toggleBtn = e.target.closest('[data-action="toggle-status"]');
      const impactBtn = e.target.closest('[data-action="inspect-impact"]');

      if (toggleBtn) {
        cycleTaskStatus(task);
        return;
      }
      if (impactBtn) {
        state.viewMode = 'blast_radius';
        document.getElementById('btn-mode-blast').click();
        renderBlastRadiusLayout('setUp');
        return;
      }

      openInspectDrawer(task);
    });

    // Port drag-to-connect
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
    const header = card.querySelector('.card-header') || card;
    header.addEventListener('mousedown', (e) => {
      if (e.target.closest('.port') || e.target.closest('button') || e.target.closest('[data-action]')) return;
      e.stopPropagation();
      const node = state.nodes.get(id);
      if (!node) return;
      state.draggedNode = node;
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
    document.getElementById('drawer-body').innerText = task.body || 'No task description available.';

    // Save button
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
  }

  function closeInspectDrawer() {
    inspectDrawer.classList.remove('is-open');
    document.getElementById('drawer-note-input').value = '';
  }

  // --- Controls & UI Setup ---

  function setupControls() {
    document.getElementById('btn-zoom-in').onclick = () => {
      state.zoom = Math.min(2.5, state.zoom * 1.15);
      applyTransform();
      document.getElementById('zoom-label').innerText = `${Math.round(state.zoom * 100)}%`;
    };

    document.getElementById('btn-zoom-out').onclick = () => {
      state.zoom = Math.max(0.2, state.zoom / 1.15);
      applyTransform();
      document.getElementById('zoom-label').innerText = `${Math.round(state.zoom * 100)}%`;
    };

    document.getElementById('btn-zoom-reset').onclick = () => {
      state.panX = 80;
      state.panY = 80;
      state.zoom = 0.95;
      applyTransform();
      document.getElementById('zoom-label').innerText = '95%';
    };

    // Mode Switchers
    const btnWorkstate = document.getElementById('btn-mode-workstate');
    const btnBlast = document.getElementById('btn-mode-blast');

    btnWorkstate.onclick = () => {
      state.viewMode = 'workstate';
      btnWorkstate.classList.add('bg-zinc-800', 'text-white');
      btnBlast.classList.remove('bg-zinc-800', 'text-white');
      btnBlast.classList.add('text-zinc-400');
      renderView();
    };

    btnBlast.onclick = () => {
      state.viewMode = 'blast_radius';
      btnBlast.classList.add('bg-zinc-800', 'text-white');
      btnWorkstate.classList.remove('bg-zinc-800', 'text-white');
      btnWorkstate.classList.add('text-zinc-400');
      renderBlastRadiusLayout('setUp');
    };

    document.getElementById('drawer-close-btn').onclick = closeInspectDrawer;

    // Keyboard Shortcuts
    window.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') closeInspectDrawer();
      if (e.key === 'r' && !e.target.matches('input, textarea')) {
        document.getElementById('btn-zoom-reset').click();
      }
    });
  }

  function setupSearch() {
    const searchInput = document.getElementById('global-search');
    searchInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        const query = searchInput.value.trim();
        if (!query) return;
        if (state.viewMode === 'blast_radius') {
          renderBlastRadiusLayout(query);
        } else {
          // Find task
          const match = state.tasks.find(t => t.title.toLowerCase().includes(query.toLowerCase()));
          if (match) {
            const node = state.nodes.get(match.id);
            if (node) {
              state.panX = viewport.clientWidth / 2 - node.x * state.zoom - 160;
              state.panY = viewport.clientHeight / 2 - node.y * state.zoom - 60;
              applyTransform();
              openInspectDrawer(match);
            }
          }
        }
      }
    });
  }

  function updateTopBarStats() {
    document.getElementById('stat-total-tasks').innerText = `${state.stats.total_tasks || 0} Tasks`;
    document.getElementById('stat-in-progress').innerText = `${state.stats.in_progress || 0} In Progress`;
    document.getElementById('stat-blocked').innerText = `${state.stats.blocked || 0} Blocked`;
  }

  // Self-start on DOM ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();
