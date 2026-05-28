// State
let audioEnabled = false;
let currentNumber = 0;
let tenantBranding = null;

// Helper: Get query parameter
function getQueryParam(name) {
  const urlParams = new URLSearchParams(window.location.search);
  return urlParams.get(name);
}

const slug = getQueryParam('comercio') || getQueryParam('slug') || 'el-puntano';

// TV Clock
function updateClock() {
  const clockEl = document.getElementById('tv-clock');
  if (!clockEl) return;
  const now = new Date();
  const hours = String(now.getHours()).padStart(2, '0');
  const minutes = String(now.getMinutes()).padStart(2, '0');
  const seconds = String(now.getSeconds()).padStart(2, '0');
  clockEl.textContent = `${hours}:${minutes}:${seconds}`;
}
setInterval(updateClock, 1000);
updateClock();

// Fetch Branding Config & Apply Colors / Logo
async function loadBranding() {
  try {
    const response = await fetch(`/api/branding?slug=${slug}`);
    if (!response.ok) throw new Error("No se pudo cargar la configuración de branding.");
    tenantBranding = await response.json();
    
    // Set Shop Name
    document.getElementById('tv-shop-name').textContent = tenantBranding.nombre_comercio;
    
    // Set Logo
    if (tenantBranding.logo_url) {
      const logoImg = document.getElementById('tv-logo-img');
      logoImg.src = tenantBranding.logo_url;
      logoImg.style.display = 'block';
      document.getElementById('tv-logo-placeholder').style.display = 'none';
    }

    // Set Dynamic Colors
    const colors = tenantBranding.branding_colors;
    if (colors) {
      if (colors.primary) document.documentElement.style.setProperty('--primary-color', colors.primary);
      if (colors.secondary) document.documentElement.style.setProperty('--secondary-color', colors.secondary);
      if (colors.background) document.documentElement.style.setProperty('--bg-color', colors.background);
      if (colors.text) document.documentElement.style.setProperty('--text-color', colors.text);
    }
  } catch (e) {
    console.error("Error al cargar branding para TV:", e);
    document.getElementById('tv-shop-name').textContent = "Carnicería El Puntano";
  }
}

// Speech Synthesis function
function speakTurn(number) {
  if (!audioEnabled || !('speechSynthesis' in window)) return;

  // Stop any ongoing speech to avoid overlay
  window.speechSynthesis.cancel();

  // Create announcement text
  const shopName = tenantBranding ? tenantBranding.nombre_comercio : "Carnicería";
  const text = `Turno número ${number}. Por favor, acercarse al mostrador de ${shopName}.`;
  
  const utterance = new SpeechSynthesisUtterance(text);
  
  // Try to find a Spanish voice
  const voices = window.speechSynthesis.getVoices();
  const esVoice = voices.find(v => v.lang.startsWith('es-AR') || v.lang.startsWith('es-ES') || v.lang.startsWith('es'));
  
  if (esVoice) {
    utterance.voice = esVoice;
  }
  
  utterance.lang = 'es-ES';
  utterance.rate = 0.9; // Slightly slower for clarity in loudspeakers
  utterance.pitch = 1.0;

  window.speechSynthesis.speak(utterance);
}

// Visual cue: Flash the massive number
function animateNumber() {
  const numberEl = document.getElementById('huge-serving-number');
  if (!numberEl) return;
  numberEl.classList.remove('flash');
  // Trigger reflow
  void numberEl.offsetWidth;
  numberEl.classList.add('flash');
}

// Update UI
function updateDisplay(data) {
  currentNumber = data.current;
  document.getElementById('huge-serving-number').textContent = currentNumber || '0';
  
  // Render History List
  const historyList = document.getElementById('tv-history-list');
  if (!historyList) return;
  
  historyList.innerHTML = '';
  
  const historyData = data.history || [];
  // Sort history newest first, and show last 4
  const itemsToShow = [...historyData].reverse().slice(0, 4);
  
  if (itemsToShow.length === 0) {
    historyList.innerHTML = `<li style="text-align: center; color: var(--text-muted); grid-column: span 4; padding: 1rem 0;">Esperando llamados...</li>`;
  } else {
    itemsToShow.forEach(item => {
      const timeStr = item.called_at 
        ? new Date(item.called_at).toLocaleTimeString('es-AR', { hour: '2-digit', minute: '2-digit' }) 
        : '';
      const li = document.createElement('li');
      li.style.background = 'rgba(0, 0, 0, 0.3)';
      li.style.border = '1px solid rgba(255, 255, 255, 0.05)';
      li.style.borderRadius = '12px';
      li.style.padding = '0.75rem';
      li.style.textAlign = 'center';
      
      li.innerHTML = `
        <div style="font-size: 0.8rem; text-transform: uppercase; color: var(--text-muted);">Turno</div>
        <div style="font-size: 1.8rem; font-weight: 700; color: var(--accent-gold); margin: 0.25rem 0;">#${item.number}</div>
        <div style="font-size: 0.75rem; color: var(--text-muted);">${timeStr}</div>
      `;
      historyList.appendChild(li);
    });
  }

  // Trigger sound/animation if there is a new call event
  if (data.new_call) {
    animateNumber();
    speakTurn(data.new_call.number);
  }
}

// Init SSE connection
function initSSE() {
  const eventSource = new EventSource(`/api/turns/live?slug=${slug}`);
  
  eventSource.onmessage = (event) => {
    try {
      const payload = JSON.parse(event.data);
      if (payload.type === 'initial' || payload.type === 'update' || payload.type === 'new_call') {
        updateDisplay(payload.data);
      }
    } catch (e) {
      console.error("Error al procesar mensaje SSE en TV:", e);
    }
  };

  eventSource.onerror = (e) => {
    console.error("Error en conexión SSE de TV. Reconectando...", e);
  };
}

// Audio activation
document.getElementById('btn-activate-audio').addEventListener('click', () => {
  audioEnabled = true;
  document.getElementById('audio-activation-overlay').style.display = 'none';
  document.getElementById('sound-indicator').textContent = 'Audio Activo 🔊';
  
  // Unlocking voice audio engine on mobile/browsers with a greeting
  if ('speechSynthesis' in window) {
    const greetingText = tenantBranding 
      ? `Sonido activado. Bienvenidos a la pantalla de ${tenantBranding.nombre_comercio}.`
      : "Sonido activado. Bienvenidos.";
    const greeting = new SpeechSynthesisUtterance(greetingText);
    greeting.lang = 'es-ES';
    window.speechSynthesis.speak(greeting);
  }
});

// Setup Page
async function setupPage() {
  await loadBranding();
  initSSE();
  
  if (!('speechSynthesis' in window)) {
    document.getElementById('sound-indicator').textContent = 'Audio No Soportado ❌';
    document.getElementById('audio-activation-overlay').style.display = 'none';
  }
}

// Trigger voices load (some browsers need this event to load speech voices lists)
if ('speechSynthesis' in window) {
  window.speechSynthesis.onvoiceschanged = () => {};
}

setupPage();
