const chat = document.querySelector("#chat");
const form = document.querySelector("#command-form");
const input = document.querySelector("#command-input");
const mode = document.querySelector("#mode");
const platform = document.querySelector("#platform");
const memoryCount = document.querySelector("#memory-count");
const events = document.querySelector("#events");
const memories = document.querySelector("#memories");
const connectionDot = document.querySelector("#connection-dot");
const connectionLabel = document.querySelector("#connection-label");
const systemOs = document.querySelector("#system-os");
const systemPython = document.querySelector("#system-python");
const systemCore = document.querySelector("#system-core");
const systemBrain = document.querySelector("#system-brain");

function addMessage(role, text) {
  const item = document.createElement("div");
  item.className = `message ${role}`;
  item.textContent = text;
  chat.appendChild(item);
  chat.scrollTop = chat.scrollHeight;
}

function setMode(nextMode) {
  mode.textContent = nextMode;
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
  return response.json();
}

async function sendCommand(command) {
  const value = command.trim();
  if (!value) return;

  addMessage("user", value);
  input.value = "";
  setMode("Thinking");

  try {
    const data = await api("/api/chat", {
      method: "POST",
      body: JSON.stringify({ message: value }),
    });
    addMessage("aura", data.reply || "Command complete.");
    setMode("Idle");
    await refreshStatus();
  } catch (error) {
    addMessage("aura", "I could not reach the local AURA core.");
    setMode("Offline");
  }
}

function renderFeed(container, items, emptyText, titleKey, bodyKey) {
  container.innerHTML = "";
  if (!items.length) {
    const empty = document.createElement("div");
    empty.className = "feed-item";
    empty.textContent = emptyText;
    container.appendChild(empty);
    return;
  }

  for (const item of items) {
    const row = document.createElement("div");
    row.className = "feed-item";
    const title = document.createElement("strong");
    title.textContent = item[titleKey];
    const body = document.createElement("span");
    body.textContent = item[bodyKey];
    row.append(title, body);
    container.appendChild(row);
  }
}

async function refreshStatus() {
  try {
    const data = await api("/api/status");
    connectionDot.classList.add("online");
    connectionLabel.textContent = "AURA Core Online";
    platform.textContent = data.system.platform;
    memoryCount.textContent = data.memories.length;
    systemOs.textContent = `${data.system.platform} ${data.system.platform_release}`;
    systemPython.textContent = data.system.python;
    systemCore.textContent = "Local";
    if (data.system.ai_provider === "ollama") {
      systemBrain.textContent = `Local ${data.system.ai_model}`;
    } else if (data.system.ai_provider === "openai") {
      systemBrain.textContent = `OpenAI ${data.system.ai_model}`;
    } else {
      systemBrain.textContent = data.system.ai_enabled ? data.system.ai_model : "Offline";
    }
    renderFeed(events, data.events, "No activity yet.", "action", "detail");
    renderFeed(memories, data.memories, "No memories saved yet.", "kind", "content");
  } catch (error) {
    connectionDot.classList.remove("online");
    connectionLabel.textContent = "AURA Core Offline";
    setMode("Offline");
  }
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  sendCommand(input.value);
});

document.querySelectorAll("[data-command]").forEach((button) => {
  button.addEventListener("click", () => sendCommand(button.dataset.command || ""));
});

addMessage("aura", "AURA core standing by. Type 'status' or ask what I can do.");
refreshStatus();
setInterval(refreshStatus, 5000);
