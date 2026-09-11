/**
 * Workforce Studio Chrome Extension - Background Service Worker
 */

const SERVER_BASE = "http://127.0.0.1:8765";

chrome.runtime.onInstalled.addListener(() => {
  // Setup context menu options
  chrome.contextMenus.create({
    id: "workforce-capture-selection",
    title: "Push selection to Workforce Inbox",
    contexts: ["selection"]
  });

  chrome.contextMenus.create({
    id: "workforce-capture-stitch",
    title: "Capture Stitch / Prototype URL to Workforce",
    contexts: ["page", "link"]
  });

  chrome.contextMenus.create({
    id: "workforce-open-canvas",
    title: "Open Workforce Command Canvas",
    contexts: ["all"]
  });
});

chrome.contextMenus.onClicked.addListener(async (info, tab) => {
  if (info.menuItemId === "workforce-open-canvas") {
    chrome.tabs.create({ url: SERVER_BASE });
    return;
  }

  if (info.menuItemId === "workforce-capture-selection") {
    const selectedText = info.selectionText || "";
    const pageUrl = tab?.url || "";
    const pageTitle = tab?.title || "Web Capture";

    const payload = {
      title: `Selection: ${pageTitle.slice(0, 40)}`,
      content: selectedText,
      selection: selectedText,
      type: "research",
      source_url: pageUrl,
      auto_dispatch: false,
      requires_human: true,
      tags: ["selection", "web_research"]
    };

    try {
      const res = await fetch(`${SERVER_BASE}/api/inbox/submit`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });

      if (res.ok && tab?.id) {
        chrome.tabs.sendMessage(tab.id, {
          action: "showToast",
          message: "Captured selection to Workforce Studio Inbox!"
        });
      }
    } catch (err) {
      if (tab?.id) {
        chrome.tabs.sendMessage(tab.id, {
          action: "showToast",
          message: "Canvas server offline. Could not submit selection."
        });
      }
    }
  }

  if (info.menuItemId === "workforce-capture-stitch") {
    const targetUrl = info.linkUrl || tab?.url || "";
    const pageTitle = tab?.title || "Prototype";

    const payload = {
      title: `Stitch / Prototype: ${pageTitle.slice(0, 40)}`,
      content: `Captured prototype URL from Chrome:\n\n[Prototype Link](${targetUrl})`,
      type: "stitch_mockup",
      source_url: targetUrl,
      auto_dispatch: false,
      requires_human: true,
      tags: ["stitch", "prototype", "ui_review"]
    };

    try {
      const res = await fetch(`${SERVER_BASE}/api/inbox/submit`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });

      if (res.ok && tab?.id) {
        chrome.tabs.sendMessage(tab.id, {
          action: "showToast",
          message: "Saved prototype link to Workforce Studio!"
        });
      }
    } catch (err) {
      if (tab?.id) {
        chrome.tabs.sendMessage(tab.id, {
          action: "showToast",
          message: "Canvas server offline. Could not submit prototype."
        });
      }
    }
  }
});
