const triageForm = document.querySelector("#triageForm");
const triageButton = document.querySelector("#triageButton");
const triageResult = document.querySelector("#triageResult");
const messageInput = document.querySelector("#message");
const charCount = document.querySelector("#charCount");
const recordForm = document.querySelector("#recordForm");
const recordResult = document.querySelector("#recordResult");
const toast = document.querySelector("#toast");

document.querySelectorAll(".nav-item").forEach((item) => {
  item.addEventListener("click", () => {
    document.querySelectorAll(".nav-item").forEach((nav) => nav.classList.remove("active"));
    document.querySelectorAll(".section").forEach((section) => section.classList.remove("active"));
    item.classList.add("active");
    const sectionName = item.dataset.section;
    document.querySelector(sectionName === "triage" ? "#triageSection" : "#recordSection").classList.add("active");
    document.querySelector("#pageTitle").textContent = sectionName === "triage" ? "Ticket triage" : "Retained records";
  });
});

messageInput.addEventListener("input", () => {
  const count = messageInput.value.length;
  charCount.textContent = `${count} character${count === 1 ? "" : "s"}`;
});

triageForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const message = messageInput.value.trim();
  if (!message) {
    showToast("Enter a customer message.");
    return;
  }

  triageButton.disabled = true;
  triageButton.querySelector("span").textContent = "Analyzing...";
  triageResult.innerHTML = `<div class="empty-state"><div class="empty-icon">···</div><h2>Analyzing message</h2><p>Applying classification and safety rules.</p></div>`;

  try {
    const response = await fetch("/triage", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "The triage request failed.");

    const recordId = response.headers.get("X-Record-ID");
    triageResult.innerHTML = renderTriageResult(data, recordId);
    showToast("Triage completed and record retained.");
  } catch (error) {
    triageResult.innerHTML = renderError("Triage unavailable", error.message);
  } finally {
    triageButton.disabled = false;
    triageButton.querySelector("span").textContent = "Run triage";
  }
});

recordForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const recordId = document.querySelector("#recordId").value.trim();
  const token = document.querySelector("#reviewerToken").value.trim();
  if (!recordId || !token) {
    showToast("Record ID and reviewer token are required.");
    return;
  }

  recordResult.innerHTML = `<div class="empty-state"><div class="empty-icon">···</div><h2>Retrieving record</h2><p>Verifying reviewer access.</p></div>`;
  try {
    const response = await fetch(`/retained/${encodeURIComponent(recordId)}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "Record retrieval failed.");
    recordResult.innerHTML = `
      <div class="result-head"><h2>Retained record</h2><span class="record-id">${escapeHtml(data.record_id)}</span></div>
      <pre class="record-json">${escapeHtml(JSON.stringify(data, null, 2))}</pre>`;
  } catch (error) {
    recordResult.innerHTML = renderError("Unable to retrieve record", error.message);
  }
});

document.querySelector("#toggleToken").addEventListener("click", (event) => {
  const input = document.querySelector("#reviewerToken");
  const show = input.type === "password";
  input.type = show ? "text" : "password";
  event.currentTarget.textContent = show ? "Hide" : "Show";
  event.currentTarget.setAttribute("aria-label", show ? "Hide reviewer token" : "Show reviewer token");
});

function renderTriageResult(data, recordId) {
  const alerts = [];
  if (data.human_review_required) alerts.push(`<span class="badge alert">Human review</span>`);
  if (data.clarification_required) alerts.push(`<span class="badge">Clarification</span>`);
  return `
    <div class="result-head">
      <h2>Analysis result</h2>
      ${recordId ? `<button class="copy-button" type="button" data-copy="${escapeHtml(recordId)}">Copy record ID</button>` : ""}
    </div>
    <div class="badges">
      <span class="badge">${escapeHtml(data.category)}</span>
      <span class="badge priority-${escapeHtml(data.priority)}">${escapeHtml(data.priority)} priority</span>
      ${alerts.join("")}
    </div>
    <div class="detail-grid">
      <div class="detail-item"><span>Department</span><strong>${escapeHtml(data.department)}</strong></div>
      <div class="detail-item"><span>Sentiment</span><strong>${escapeHtml(data.sentiment)}</strong></div>
    </div>
    ${recordId ? `<div class="detail-item" style="margin-top:8px"><span>Record ID</span><strong class="record-id" style="max-width:none">${escapeHtml(recordId)}</strong></div>` : ""}
    <div class="response-box"><span>Suggested response</span><p>${escapeHtml(data.suggested_response)}</p></div>
    ${data.clarification_question ? `<div class="response-box"><span>Clarification</span><p>${escapeHtml(data.clarification_question)}</p></div>` : ""}
    <div class="response-box"><span>Rationale</span><p>${escapeHtml(data.rationale)}</p></div>`;
}

triageResult.addEventListener("click", async (event) => {
  const button = event.target.closest("[data-copy]");
  if (!button) return;
  await navigator.clipboard.writeText(button.dataset.copy);
  showToast("Record ID copied.");
});

function renderError(title, message) {
  return `<div class="error-state"><div><strong>${escapeHtml(title)}</strong><p>${escapeHtml(message)}</p></div></div>`;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

let toastTimer;
function showToast(message) {
  toast.textContent = message;
  toast.classList.add("visible");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toast.classList.remove("visible"), 2600);
}
