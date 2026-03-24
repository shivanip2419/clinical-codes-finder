const APP_CONFIG = window.APP_CONFIG || {
  maxPerSystem: 5,
  supportedSystems: ["ICD-10-CM", "LOINC", "RxTerms", "HCPCS", "UCUM", "HPO"],
  sampleQueries: ["diabetes", "glucose test"],
};

const input = document.getElementById("query");
const button = document.getElementById("send");
const messages = document.getElementById("messages");
const hint = document.querySelector(".hint");

function buildWelcomeMessage() {
  return "Hi! Enter a clinical term and I will return relevant clinical codes.";
}

function buildHintText() {
  return `Try: ${APP_CONFIG.sampleQueries.join(", ")}`;
}

function scrollToBottom() {
  messages.scrollTop = messages.scrollHeight;
}

function addUserBubble(text) {
  const div = document.createElement("div");
  div.className = "bubble user";
  div.textContent = text;
  messages.appendChild(div);
  scrollToBottom();
}

function buildAssistantHtml(payload) {
  const systems =
    payload.trace && payload.trace.systems_selected
      ? payload.trace.systems_selected.join(", ")
      : "n/a";
  const calls =
    payload.trace && payload.trace.calls_made !== undefined
      ? payload.trace.calls_made
      : "n/a";
  const groups = payload.results_by_system || {};
  const lines = [];
  for (const [system, items] of Object.entries(groups)) {
    lines.push(`<div class="meta"><strong>${system}</strong></div>`);
    (items || []).slice(0, 5).forEach((it) => {
      lines.push(`<div>- <code>${it.code}</code> - ${it.display}</div>`);
    });
  }
  if (lines.length === 0) {
    lines.push("<div>No matches found.</div>");
  }
  return `
    <div class="summary">${payload.summary || "No summary available."}</div>
    <div class="meta">Systems: ${systems} | API calls: ${calls}</div>
    ${lines.join("")}
  `;
}

function addAssistantBubble(html) {
  const div = document.createElement("div");
  div.className = "bubble assistant";
  div.innerHTML = html;
  messages.appendChild(div);
  scrollToBottom();
}

async function runQuery() {
  const query = input.value.trim();
  if (!query) return;
  addUserBubble(query);
  input.value = "";
  button.disabled = true;
  addAssistantBubble("Thinking...");
  try {
    const response = await fetch("/find-codes", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query, max_per_system: APP_CONFIG.maxPerSystem }),
    });
    const payload = await response.json();
    messages.lastChild.remove();
    addAssistantBubble(buildAssistantHtml(payload));
  } catch (err) {
    messages.lastChild.remove();
    addAssistantBubble("Request failed: " + err);
  } finally {
    button.disabled = false;
    input.focus();
  }
}

button.addEventListener("click", runQuery);
input.addEventListener("keydown", (e) => {
  if (e.key === "Enter") runQuery();
});

hint.textContent = buildHintText();
addAssistantBubble(buildWelcomeMessage());
