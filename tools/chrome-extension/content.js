/**
 * Workforce Studio Chrome Extension - Content Script
 */

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === "getSelection") {
    const selectedText = window.getSelection() ? window.getSelection().toString().trim() : "";
    sendResponse({ text: selectedText });
    return true;
  }

  if (request.action === "showToast") {
    displayInPageToast(request.message);
    sendResponse({ success: true });
    return true;
  }
});

function displayInPageToast(message) {
  let toastEl = document.getElementById("workforce-inpage-toast");
  if (!toastEl) {
    toastEl = document.createElement("div");
    toastEl.id = "workforce-inpage-toast";
    toastEl.className = "workforce-toast-container";
    document.body.appendChild(toastEl);
  }

  toastEl.textContent = message;
  toastEl.classList.add("visible");

  setTimeout(() => {
    toastEl.classList.remove("visible");
  }, 2500);
}
