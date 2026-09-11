/**
 * Workforce Studio Chrome Extension - Popup Controller
 */

const SERVER_BASE = "http://127.0.0.1:8765";

let currentTasks = [];
let selectedTask = null;
let currentCapability = "research";

// DOM Elements
const serverStatusBadge = document.getElementById("server-status-badge");
const statusDot = document.getElementById("status-dot");
const statusLabel = document.getElementById("status-label");
const taskSelect = document.getElementById("task-select");
const taskInfoCard = document.getElementById("task-info-card");
const taskCardPriority = document.getElementById("task-card-priority");
const taskCardType = document.getElementById("task-card-type");
const taskCardId = document.getElementById("task-card-id");
const taskCardTitle = document.getElementById("task-card-title");
const promptOutput = document.getElementById("gemini-prompt-output");
const btnCopyPrompt = document.getElementById("btn-copy-prompt");
const btnOpenGemini = document.getElementById("btn-open-gemini");
const btnSwitchToCapture = document.getElementById("btn-switch-to-capture");
const capabilityChips = document.querySelectorAll("#capability-chips .chip");

// Capture elements
const formCapture = document.getElementById("form-capture");
const captureTitle = document.getElementById("capture-title");
const captureType = document.getElementById("capture-type");
const captureTaskId = document.getElementById("capture-task-id");
const captureUrl = document.getElementById("capture-url");
const captureContent = document.getElementById("capture-content");
const captureAutoDispatch = document.getElementById("capture-auto-dispatch");
const btnGrabSelection = document.getElementById("btn-grab-selection");

// Inbox elements
const inboxCountBadge = document.getElementById("inbox-count-badge");
const inboxSummaryText = document.getElementById("inbox-summary-text");
const inboxItemsContainer = document.getElementById("inbox-items-container");
const btnRefreshInbox = document.getElementById("btn-refresh-inbox");
const btnOpenStudio = document.getElementById("btn-open-studio");
const toast = document.getElementById("toast");

// Tab switching
const tabButtons = document.querySelectorAll(".tab-btn");
const tabPanes = document.querySelectorAll(".tab-pane");

tabButtons.forEach(btn => {
  btn.addEventListener("click", () => {
    const targetTab = btn.getAttribute("data-tab");
    tabButtons.forEach(b => b.classList.remove("active"));
    tabPanes.forEach(p => p.classList.remove("active"));
    btn.classList.add("active");
    document.getElementById(`tab-${targetTab}`).classList.add("active");
    if (targetTab === "inbox") {
      loadInboxItems();
    }
  });
});

// Toast notification helper
function showToast(message, duration = 2500) {
  toast.textContent = message;
  toast.classList.remove("hidden");
  setTimeout(() => {
    toast.classList.add("hidden");
  }, duration);
}

// Check server status
async function checkServerStatus() {
  try {
    const res = await fetch(`${SERVER_BASE}/api/heartbeat`, { method: "GET", headers: { "Accept": "application/json" } });
    if (res.ok) {
      const data = await res.json();
      serverStatusBadge.className = "status-badge online";
      statusLabel.textContent = `Online (PID ${data.server_pid || "8765"})`;
      return true;
    }
  } catch (err) {
    // Offline
  }
  serverStatusBadge.className = "status-badge offline";
  statusLabel.textContent = "Server Offline";
  return false;
}

// Load active tasks from canvas server
async function loadTasks() {
  try {
    const res = await fetch(`${SERVER_BASE}/api/state`);
    if (res.ok) {
      const data = await res.json();
      currentTasks = data.tasks || [];
      inboxCountBadge.textContent = data.stats?.inbox_count || (data.inbox ? data.inbox.length : 0);

      // Populate select dropdown
      taskSelect.innerHTML = '<option value="">-- Choose an active task --</option>';
      currentTasks.forEach(task => {
        const opt = document.createElement("option");
        opt.value = task.id;
        opt.textContent = `[${task.priority}] [${task.team}] ${task.title}`;
        taskSelect.appendChild(opt);
      });

      if (currentTasks.length > 0) {
        taskSelect.selectedIndex = 1;
        onTaskSelected(currentTasks[0].id);
      }
    }
  } catch (err) {
    taskSelect.innerHTML = '<option value="">Error connecting to Workforce Canvas</option>';
  }
}

// Handle task selection
function onTaskSelected(taskId) {
  selectedTask = currentTasks.find(t => t.id === taskId) || null;
  if (selectedTask) {
    taskInfoCard.style.display = "block";
    taskCardPriority.textContent = selectedTask.priority;
    taskCardType.textContent = selectedTask.type || selectedTask.team;
    taskCardId.textContent = selectedTask.id;
    taskCardTitle.textContent = selectedTask.title;
    captureTaskId.value = selectedTask.id;
    generatePrompt();
  } else {
    taskInfoCard.style.display = "none";
    promptOutput.value = "";
  }
}

taskSelect.addEventListener("change", (e) => {
  onTaskSelected(e.target.value);
});

// Capability chips
capabilityChips.forEach(chip => {
  chip.addEventListener("click", () => {
    capabilityChips.forEach(c => c.classList.remove("active"));
    chip.classList.add("active");
    currentCapability = chip.getAttribute("data-type");
    generatePrompt();
  });
});

// Generate Gemini Prompt
function generatePrompt() {
  if (!selectedTask) {
    promptOutput.value = "Please select a task from the list above.";
    return;
  }

  const title = selectedTask.title;
  const id = selectedTask.id;
  const priority = selectedTask.priority;
  const type = selectedTask.type;
  const bodySnippet = (selectedTask.body || "").slice(0, 300).trim();

  let prompt = "";

  if (currentCapability === "research") {
    prompt = `Context: Workforce Project Task [ID: ${id}] (Priority: ${priority}, Type: ${type})
Task Title: "${title}"
Background: ${bodySnippet}

Instruction for Ask Gemini:
Please conduct targeted web research for this initiative. 
1. Identify 3-5 real-world benchmarks, competitor solutions, or market precedents.
2. Note key user pain points, pricing patterns, and technical trade-offs.
3. Provide high-signal findings formatted in concise markdown bullet points with source URLs so I can submit them back to the Workforce Studio Canvas.`;
  } else if (currentCapability === "outreach") {
    prompt = `Context: Workforce Project Task [ID: ${id}] (Priority: ${priority}, Type: ${type})
Task Title: "${title}"
Background: ${bodySnippet}

Instruction for Ask Gemini:
1. Identify high-fit prospective buyer personas or target community channels for this offer.
2. Draft 2 personalized, human-sounding outreach messages (one cold email under 100 words, one LinkedIn/X message under 50 words) focused strictly on customer value.
3. Zero buzzwords, zero generic AI flattery.`;
  } else if (currentCapability === "flow_video") {
    prompt = `Context: Workforce Task [ID: ${id}] - Google Flow Video Prompt Generator
Initiative: "${title}"
Details: ${bodySnippet}

Instruction for Google Flow:
Generate a structured 3-scene prompt sequence for generating a product video in Google Flow:
Scene 1 (Hook / 0-4s): High-contrast visual introducing the core problem. Camera motion: slow dolly-in. Lighting: editorial cinematic.
Scene 2 (Mechanism / 4-10s): Demonstration of the workflow solution and studio interface. Camera motion: steady pan.
Scene 3 (Call to Action / 10-15s): Clean product card and outcome. Camera motion: subtle zoom-out.`;
  } else if (currentCapability === "stitch_review") {
    prompt = `Context: Workforce Task [ID: ${id}] - Stitch UI Audit
Component / Page: "${title}"
Requirements: ${bodySnippet}

Instruction for Ask Gemini:
Audit the current Stitch with Google interface prototype (or current webpage).
1. Check typography hierarchy and contrast against WCAG AA accessibility.
2. Flag any cluttered elements, unnecessary telemetry, or generic AI patterns.
3. Suggest 3 concrete UI refinements to match Refero-grade aesthetic standards.`;
  }

  promptOutput.value = prompt;
}

// Copy prompt button
btnCopyPrompt.addEventListener("click", () => {
  if (!promptOutput.value) return;
  navigator.clipboard.writeText(promptOutput.value).then(() => {
    showToast("Prompt copied to clipboard!");
  }).catch(() => {
    promptOutput.select();
    document.execCommand("copy");
    showToast("Prompt copied to clipboard!");
  });
});

// Open Ask Gemini in a new tab
btnOpenGemini.addEventListener("click", () => {
  chrome.tabs.create({ url: "https://gemini.google.com/app" });
});

// Switch to capture tab with task ID filled
btnSwitchToCapture.addEventListener("click", () => {
  document.querySelector('[data-tab="capture"]').click();
});

// Grab selection from active tab
async function grabActiveTabInfo() {
  try {
    const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
    if (tabs && tabs[0]) {
      const activeTab = tabs[0];
      if (activeTab.url) {
        captureUrl.value = activeTab.url;
        // Detect Stitch prototypes
        if (activeTab.url.includes("stitch.withgoogle.com")) {
          captureType.value = "stitch_mockup";
          captureTitle.value = `Stitch Prototype: ${activeTab.title || "Project"}`;
        } else if (!captureTitle.value) {
          captureTitle.value = activeTab.title || "";
        }
      }

      // Query content script for highlighted text
      chrome.tabs.sendMessage(activeTab.id, { action: "getSelection" }, (response) => {
        if (chrome.runtime.lastError) {
          // Content script may not be injected on chrome:// or restricted pages
          return;
        }
        if (response && response.text) {
          captureContent.value = response.text;
          showToast("Captured text selection from active page!");
        }
      });
    }
  } catch (err) {
    console.error("Tab query error:", err);
  }
}

btnGrabSelection.addEventListener("click", () => {
  grabActiveTabInfo();
});

// Submit Quick Capture
formCapture.addEventListener("submit", async (e) => {
  e.preventDefault();

  const title = captureTitle.value.trim();
  const content = captureContent.value.trim();
  const type = captureType.value;
  const taskId = captureTaskId.value.trim();
  const sourceUrl = captureUrl.value.trim();
  const autoDispatch = captureAutoDispatch.checked;

  if (!title || !content) {
    showToast("Please provide both a title and notes/content.");
    return;
  }

  const payload = {
    title: title,
    content: content,
    type: type,
    source_url: sourceUrl,
    task_id: taskId,
    auto_dispatch: autoDispatch,
    requires_human: !autoDispatch,
    tags: [type, "chrome_extension"]
  };

  try {
    const res = await fetch(`${SERVER_BASE}/api/inbox/submit`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    if (res.ok) {
      const result = await res.json();
      showToast(autoDispatch ? "Dispatched task to agent!" : "Saved to Workforce Inbox!");
      captureContent.value = "";
      // Refresh inbox count and tab
      loadInboxItems();
      document.querySelector('[data-tab="inbox"]').click();
    } else {
      showToast("Server rejected submission.");
    }
  } catch (err) {
    showToast("Failed to connect to Workforce Canvas server.");
  }
});

// Load Inbox Items
async function loadInboxItems() {
  try {
    const res = await fetch(`${SERVER_BASE}/api/inbox`);
    if (res.ok) {
      const data = await res.json();
      const items = data.items || [];
      inboxCountBadge.textContent = items.length;
      inboxSummaryText.textContent = `${items.length} item${items.length === 1 ? '' : 's'} recorded`;

      if (items.length === 0) {
        inboxItemsContainer.innerHTML = '<div class="empty-state">No items in inbox yet. Use Quick Capture to save research, Stitch URLs, or notes.</div>';
        return;
      }

      inboxItemsContainer.innerHTML = "";
      items.forEach(item => {
        const itemEl = document.createElement("div");
        itemEl.className = "inbox-item";
        const dateStr = item.captured_at ? item.captured_at.slice(5, 16).replace("T", " ") : "";
        itemEl.innerHTML = `
          <div class="inbox-item-header">
            <span class="inbox-item-tag">${escapeHtml(item.type || item._folder || "item")}</span>
            <span class="inbox-item-date">${escapeHtml(dateStr)}</span>
          </div>
          <div class="inbox-item-title">${escapeHtml(item.title || "Untitled")}</div>
          <div class="inbox-item-content">${escapeHtml(item.content || item.selection || "")}</div>
        `;
        inboxItemsContainer.appendChild(itemEl);
      });
    }
  } catch (err) {
    console.warn("Could not load inbox items:", err);
    inboxItemsContainer.innerHTML = '<div class="empty-state">Unable to load inbox items. Server may be offline.</div>';
  }
}

btnRefreshInbox.addEventListener("click", () => {
  loadInboxItems();
});

btnOpenStudio.addEventListener("click", () => {
  chrome.tabs.create({ url: SERVER_BASE });
});

serverStatusBadge.addEventListener("click", async () => {
  const isOnline = await checkServerStatus();
  if (isOnline) {
    await loadTasks();
    showToast("Connected to Workforce Canvas server!");
  } else {
    showToast("Server offline. Run server.py to connect.");
  }
});

function escapeHtml(str) {
  return String(str || "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

// Initial bootstrap
document.addEventListener("DOMContentLoaded", async () => {
  const isOnline = await checkServerStatus();
  if (isOnline) {
    await loadTasks();
  }
  grabActiveTabInfo();
});
