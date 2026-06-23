const chat = document.querySelector("#chat");
const form = document.querySelector("#command-form");
const input = document.querySelector("#command-input");
const voiceButton = document.querySelector("#voice-button");
const voiceLabel = document.querySelector("#voice-label");
const hudState = document.querySelector("#hud-state");
const globeCanvas = document.querySelector("#globe-canvas");
const globeContext = globeCanvas.getContext("2d");
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
const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
const recognition = SpeechRecognition ? new SpeechRecognition() : null;
let voiceEnabled = false;
let isListening = false;
let globeTick = 0;

const globePoints = Array.from({ length: 95 }, (_, index) => {
  const offset = 2 / 95;
  const y = index * offset - 1 + offset / 2;
  const radius = Math.sqrt(1 - y * y);
  const theta = index * Math.PI * (3 - Math.sqrt(5));
  return {
    x: Math.cos(theta) * radius,
    y,
    z: Math.sin(theta) * radius,
    pulse: Math.random() * Math.PI * 2,
  };
});

const signalRoutes = [
  [-0.64, -0.22, 0.76, -0.1],
  [-0.34, 0.42, 0.48, -0.48],
  [-0.78, 0.2, 0.18, 0.58],
  [-0.04, -0.58, 0.7, 0.34],
];

function addMessage(role, text) {
  const item = document.createElement("div");
  item.className = `message ${role}`;
  item.textContent = text;
  chat.appendChild(item);
  chat.scrollTop = chat.scrollHeight;
}

function setMode(nextMode) {
  mode.textContent = nextMode;
  hudState.textContent = nextMode;
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
    speak(data.reply || "Command complete.");
    setMode("Idle");
    await refreshStatus();
  } catch (error) {
    addMessage("aura", "I could not reach the local AURA core.");
    setMode("Offline");
  }
}

function speak(text) {
  if (!voiceEnabled || !("speechSynthesis" in window) || !text) return;
  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.rate = 0.95;
  utterance.pitch = 0.86;
  utterance.volume = 0.9;
  utterance.onstart = () => {
    document.body.classList.add("speaking");
    setMode("Speaking");
    voiceLabel.textContent = "Speaking";
  };
  utterance.onend = () => {
    document.body.classList.remove("speaking");
    setMode("Idle");
    voiceLabel.textContent = voiceEnabled ? "Voice enabled" : "Voice standby";
  };
  utterance.onerror = utterance.onend;
  window.speechSynthesis.speak(utterance);
}

function setupVoice() {
  if (!recognition) {
    voiceLabel.textContent = "Voice unavailable";
    voiceButton.disabled = true;
    voiceButton.title = "Voice input is not supported in this browser";
    return;
  }

  recognition.continuous = false;
  recognition.interimResults = false;
  recognition.lang = "en-US";

  recognition.onstart = () => {
    isListening = true;
    voiceEnabled = true;
    document.body.classList.add("listening");
    voiceButton.classList.add("listening");
    setMode("Listening");
    voiceLabel.textContent = "Listening";
  };

  recognition.onresult = (event) => {
    const transcript = Array.from(event.results)
      .map((result) => result[0].transcript)
      .join(" ")
      .trim();
    if (transcript) {
      input.value = transcript;
      sendCommand(transcript);
    }
  };

  recognition.onerror = () => {
    voiceLabel.textContent = "Voice retry";
  };

  recognition.onend = () => {
    isListening = false;
    document.body.classList.remove("listening");
    voiceButton.classList.remove("listening");
    if (mode.textContent === "Listening") setMode("Idle");
    voiceLabel.textContent = voiceEnabled ? "Voice enabled" : "Voice standby";
  };
}

function toggleVoice() {
  if (!recognition) return;
  voiceEnabled = true;
  if (isListening) {
    recognition.stop();
  } else {
    window.speechSynthesis?.cancel();
    recognition.start();
  }
}

function resizeGlobeCanvas() {
  const rect = globeCanvas.getBoundingClientRect();
  const scale = window.devicePixelRatio || 1;
  globeCanvas.width = Math.max(1, Math.floor(rect.width * scale));
  globeCanvas.height = Math.max(1, Math.floor(rect.height * scale));
  globeContext.setTransform(scale, 0, 0, scale, 0, 0);
}

function projectPoint(point, angle, centerX, centerY, radius) {
  const cos = Math.cos(angle);
  const sin = Math.sin(angle);
  const x = point.x * cos - point.z * sin;
  const z = point.x * sin + point.z * cos;
  const depth = (z + 1.8) / 2.8;
  return {
    x: centerX + x * radius,
    y: centerY + point.y * radius * 0.72,
    z,
    depth,
  };
}

function drawGlobe() {
  const width = globeCanvas.clientWidth;
  const height = globeCanvas.clientHeight;
  const centerX = width / 2;
  const centerY = height / 2;
  const radius = Math.min(width, height) * 0.34;
  globeTick += 0.006;

  globeContext.clearRect(0, 0, width, height);

  const glow = globeContext.createRadialGradient(centerX, centerY, radius * 0.08, centerX, centerY, radius * 1.22);
  glow.addColorStop(0, "rgba(88, 231, 255, 0.2)");
  glow.addColorStop(0.42, "rgba(61, 124, 255, 0.08)");
  glow.addColorStop(1, "rgba(5, 7, 13, 0)");
  globeContext.fillStyle = glow;
  globeContext.beginPath();
  globeContext.arc(centerX, centerY, radius * 1.28, 0, Math.PI * 2);
  globeContext.fill();

  globeContext.strokeStyle = "rgba(88, 231, 255, 0.22)";
  globeContext.lineWidth = 1;
  for (let i = -2; i <= 2; i += 1) {
    globeContext.beginPath();
    globeContext.ellipse(centerX, centerY, radius, radius * (0.18 + Math.abs(i) * 0.1), globeTick + i * 0.22, 0, Math.PI * 2);
    globeContext.stroke();
  }

  for (let i = -3; i <= 3; i += 1) {
    globeContext.beginPath();
    globeContext.ellipse(centerX, centerY, radius * (0.2 + Math.abs(i) * 0.13), radius * 0.72, globeTick * 0.4, 0, Math.PI * 2);
    globeContext.stroke();
  }

  for (const route of signalRoutes) {
    const start = projectPoint({ x: route[0], y: route[1], z: 0.45 }, globeTick, centerX, centerY, radius);
    const end = projectPoint({ x: route[2], y: route[3], z: 0.45 }, globeTick, centerX, centerY, radius);
    globeContext.strokeStyle = "rgba(255, 207, 106, 0.22)";
    globeContext.beginPath();
    globeContext.moveTo(start.x, start.y);
    globeContext.quadraticCurveTo(centerX, centerY - radius * 0.72, end.x, end.y);
    globeContext.stroke();
  }

  for (const point of globePoints) {
    const projected = projectPoint(point, globeTick, centerX, centerY, radius);
    if (projected.z < -0.88) continue;
    const pulse = 0.5 + Math.sin(globeTick * 5 + point.pulse) * 0.5;
    globeContext.fillStyle = `rgba(102, 255, 194, ${0.24 + projected.depth * 0.5})`;
    globeContext.beginPath();
    globeContext.arc(projected.x, projected.y, 1.4 + pulse * 1.2, 0, Math.PI * 2);
    globeContext.fill();
  }

  requestAnimationFrame(drawGlobe);
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
    hudState.textContent = "Offline";
  }
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  sendCommand(input.value);
});

document.querySelectorAll("[data-command]").forEach((button) => {
  button.addEventListener("click", () => sendCommand(button.dataset.command || ""));
});

voiceButton.addEventListener("click", toggleVoice);
window.addEventListener("resize", resizeGlobeCanvas);

setupVoice();
resizeGlobeCanvas();
drawGlobe();
addMessage("aura", "AURA core standing by. Type 'status' or ask what I can do.");
refreshStatus();
setInterval(refreshStatus, 5000);
