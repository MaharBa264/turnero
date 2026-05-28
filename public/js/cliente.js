// Client State
let myTicket = null;
let currentServingVal = 0;
let tenantBranding = null;
let userCoords = null;
let commerceCoords = null;
let travelTimeMinutes = 0;

// Helper: Get query parameter
function getQueryParam(name) {
  const urlParams = new URLSearchParams(window.location.search);
  return urlParams.get(name);
}

// 1. Resolve Tenant / Slug
const slug = getQueryParam('comercio') || getQueryParam('slug') || 'el-puntano';
let clientUuid = localStorage.getItem('cliente_uuid');
if (!clientUuid) {
  clientUuid = typeof crypto.randomUUID === 'function' ? crypto.randomUUID() : 'c-' + Math.random().toString(36).substr(2, 9);
  localStorage.setItem('cliente_uuid', clientUuid);
}

// 2. Fetch Branding & Apply Settings
async function loadBranding() {
  try {
    const response = await fetch(`/api/branding?slug=${slug}`);
    if (!response.ok) throw new Error("No se pudo cargar la configuración de branding.");
    tenantBranding = await response.json();
    
    // Set Shop Name
    document.getElementById('shop-name').textContent = tenantBranding.nombre_comercio;
    
    // Set Logo
    if (tenantBranding.logo_url) {
      const logoImg = document.getElementById('logo-img');
      logoImg.src = tenantBranding.logo_url;
      logoImg.style.display = 'block';
      document.getElementById('logo-placeholder').style.display = 'none';
    }

    // Set Dynamic Colors
    const colors = tenantBranding.branding_colors;
    if (colors) {
      if (colors.primary) document.documentElement.style.setProperty('--primary-color', colors.primary);
      if (colors.secondary) document.documentElement.style.setProperty('--secondary-color', colors.secondary);
      if (colors.background) document.documentElement.style.setProperty('--bg-color', colors.background);
      if (colors.text) document.documentElement.style.setProperty('--text-color', colors.text);
    }

    // Handle Banners
    renderBanners(tenantBranding.tipo_publicidad, tenantBranding.publicidad_banner_url);

    // Read commerce coordinates from branding response (nested or loaded via separate request if necessary,
    // but the backend API resolutions can expose coordinates)
    // For demo, we fallback to coordinates or read from branding if provided
    if (tenantBranding.latitud && tenantBranding.longitud) {
      commerceCoords = { lat: tenantBranding.latitud, lng: tenantBranding.longitud };
    }
  } catch (e) {
    console.error("Error al cargar branding:", e);
    document.getElementById('shop-name').textContent = "Carnicería El Puntano";
  }
}

// Render Advertisement Banners
function renderBanners(tipo, bannerUrl) {
  const adTop = document.getElementById('ad-top');
  const adBottom = document.getElementById('ad-bottom');
  
  const banners = [adTop, adBottom];
  
  banners.forEach((banner, idx) => {
    if (!banner) return;
    
    if (tipo === 'ninguna') {
      banner.style.display = 'none';
    } else if (tipo === 'propia' && bannerUrl) {
      banner.innerHTML = `<img src="${bannerUrl}" alt="Promoción Local" />`;
    } else if (tipo === 'google_ads') {
      banner.innerHTML = `
        <div style="background: #2b2b2b; color: #7f8c8d; font-family: monospace; width: 100%; height: 100%; display: flex; flex-direction: column; align-items: center; justify-content: center; font-size: 0.7rem; border: 1px solid #3a3a3a;">
          <span>Google Adsense Placeholder</span>
          <strong>Anuncio Relacionado</strong>
        </div>`;
    }
  });
}

// Calculate Distance (Haversine Formula)
function calculateDistance(lat1, lon1, lat2, lon2) {
  const R = 6371e3; // Earth radius in meters
  const phi1 = lat1 * Math.PI / 180;
  const phi2 = lat2 * Math.PI / 180;
  const deltaPhi = (lat2 - lat1) * Math.PI / 180;
  const deltaLambda = (lon2 - lon1) * Math.PI / 180;

  const a = Math.sin(deltaPhi / 2) * Math.sin(deltaPhi / 2) +
            Math.cos(phi1) * Math.cos(phi2) *
            Math.sin(deltaLambda / 2) * Math.sin(deltaLambda / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));

  return R * c; // In meters
}

// Request Location
function requestGeolocation() {
  return new Promise((resolve) => {
    if (!navigator.geolocation) {
      console.warn("Geolocalización no soportada en este navegador.");
      resolve(null);
    }
    navigator.geolocation.getCurrentPosition(
      (position) => {
        userCoords = {
          lat: position.coords.latitude,
          lng: position.coords.longitude
        };
        resolve(userCoords);
      },
      (error) => {
        console.warn("Permiso de geolocalización denegado o error de lectura.", error);
        resolve(null);
      },
      { enableHighAccuracy: true, timeout: 5000 }
    );
  });
}

// Load ticket from localStorage if exists
function loadTicket() {
  const stored = localStorage.getItem(`ticket_${slug}`);
  if (stored) {
    try {
      myTicket = JSON.parse(stored);
      document.getElementById('my-ticket-num').textContent = myTicket.number;
      showView('view-my-ticket');
      // Recalcular distancia si hay coordenadas guardadas/leídas
      updateDistanceUI();
    } catch (e) {
      localStorage.removeItem(`ticket_${slug}`);
    }
  } else {
    showView('view-request-ticket');
  }
}

// Switch views
function showView(viewId) {
  document.getElementById('view-request-ticket').style.display = viewId === 'view-request-ticket' ? 'block' : 'none';
  document.getElementById('view-my-ticket').style.display = viewId === 'view-my-ticket' ? 'block' : 'none';
}

// Calculate and show distance
function updateDistanceUI() {
  if (userCoords && commerceCoords) {
    const distMeters = calculateDistance(
      userCoords.lat, userCoords.lng,
      commerceCoords.lat, commerceCoords.lng
    );
    
    const distText = distMeters > 1000 
      ? (distMeters / 1000).toFixed(2) + " km" 
      : Math.round(distMeters) + " m";
      
    // Travel time walking at 5 km/h (1.39 m/s)
    const travelTimeSeconds = distMeters / 1.39;
    travelTimeMinutes = Math.ceil(travelTimeSeconds / 60);

    document.getElementById('val-distance').textContent = distText;
    document.getElementById('val-travel-time').textContent = `${travelTimeMinutes} min caminando`;
    document.getElementById('distance-info').style.display = 'block';
  } else {
    document.getElementById('distance-info').style.display = 'none';
  }
}

// Update UI based on active queue data
function updateQueueUI(data) {
  currentServingVal = data.current;
  document.getElementById('current-serving').textContent = data.current || '-';
  document.getElementById('total-waiting').textContent = data.total_waiting;

  if (myTicket) {
    const alertBox = document.getElementById('ticket-status-alert');
    const myNum = myTicket.number;

    if (currentServingVal === 0) {
      alertBox.className = 'status-alert wait';
      alertBox.innerHTML = `El local no ha iniciado la atención todavía.`;
    } else if (currentServingVal < myNum) {
      // Usar datos predictivos del backend si están disponibles, con fallback local
      const diff = (data.your_position !== undefined) ? data.your_position : (myNum - currentServingVal);
      const estTime = (data.estimated_wait_seconds !== undefined) 
        ? Math.ceil(data.estimated_wait_seconds / 60) 
        : (diff * 3);
      
      // Determinar si la alerta debe sonar
      // Alerta Inteligente: Si el tiempo estimado de espera es menor o igual al tiempo de regreso caminando (más 2 minutos de margen)
      const warningMargin = travelTimeMinutes + 2;

      if (estTime <= warningMargin || diff <= 2) {
        alertBox.className = 'status-alert soon';
        if (estTime <= travelTimeMinutes && travelTimeMinutes > 0) {
          alertBox.innerHTML = `⚠️ <strong>¡DEBES VOLVER YA!</strong><br>El tiempo estimado de espera (${estTime} min) es menor a tu tiempo de regreso (${travelTimeMinutes} min).`;
        } else {
          alertBox.innerHTML = `¡Tu turno está cerca! Acercate al mostrador. (Espera ~${estTime} min)`;
        }
        
        if (document.getElementById('chk-notify').checked) {
          triggerSimulatedNotification(myNum, diff, "¡Tu turno está cerca! Es hora de regresar al local.");
        }
      } else {
        alertBox.className = 'status-alert wait';
        alertBox.innerHTML = `Faltan <strong>${diff}</strong> números antes del tuyo.<br>Espera aprox: <strong>${estTime} min</strong>.`;
      }
    } else if (currentServingVal === myNum) {
      alertBox.className = 'status-alert now';
      alertBox.innerHTML = `🎉 <strong>¡ES TU TURNO!</strong><br>Pasá a ser atendido en el mostrador.`;
      triggerCallAlert();
    } else {
      alertBox.className = 'status-alert soon';
      alertBox.innerHTML = `🔴 Tu número ya pasó (fue el ${myNum}).`;
    }
  }
}

// Simulated notification (Vibration & OS alerts)
let hasNotifiedNear = false;
function triggerSimulatedNotification(num, diff, message) {
  if (hasNotifiedNear) return;
  hasNotifiedNear = true;

  if (navigator.vibrate) {
    navigator.vibrate([300, 100, 300]);
  }

  if (Notification.permission === 'granted') {
    new Notification(tenantBranding ? tenantBranding.nombre_comercio : 'Sistema de Turnos', {
      body: `${message} (Faltan ${diff} números)`,
      icon: '🥩'
    });
  }
}

let hasNotifiedNow = false;
function triggerCallAlert() {
  if (hasNotifiedNow) return;
  hasNotifiedNow = true;

  if (navigator.vibrate) {
    navigator.vibrate([500, 200, 500, 200, 500]);
  }

  // Beep sound
  try {
    const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    const oscillator = audioCtx.createOscillator();
    const gainNode = audioCtx.createGain();
    oscillator.connect(gainNode);
    gainNode.connect(audioCtx.destination);
    oscillator.type = 'sine';
    oscillator.frequency.value = 523.25; 
    gainNode.gain.setValueAtTime(0, audioCtx.currentTime);
    gainNode.gain.linearRampToValueAtTime(1, audioCtx.currentTime + 0.05);
    gainNode.gain.exponentialRampToValueAtTime(0.0001, audioCtx.currentTime + 1);
    oscillator.start(audioCtx.currentTime);
    oscillator.stop(audioCtx.currentTime + 1);
  } catch (e) {}

  if (Notification.permission === 'granted') {
    new Notification('¡Es tu Turno!', {
      body: `Pasá al mostrador con el número ${myTicket.number}.`,
      icon: '🥩'
    });
  }
}

// Initialize Realtime SSE connection
let eventSource = null;
function initSSE() {
  if (eventSource) {
    eventSource.close();
  }
  const ticketParam = myTicket ? `&ticket=${myTicket.number}` : '';
  eventSource = new EventSource(`/api/turns/live?slug=${slug}${ticketParam}`);
  
  eventSource.onmessage = (event) => {
    try {
      const payload = JSON.parse(event.data);
      if (payload.type === 'initial' || payload.type === 'update' || payload.type === 'new_call') {
        updateQueueUI(payload.data);
      }
      
      if (payload.reset) {
        abandonTurn();
      }
    } catch (e) {
      console.error("Error al procesar mensaje SSE:", e);
    }
  };

  eventSource.onerror = (e) => {
    console.error("Error en conexión SSE. Reconectando...", e);
  };
}

// Button Events
document.getElementById('btn-take-turn').addEventListener('click', async () => {
  try {
    // 1. Pedir geolocalización al cliente
    await requestGeolocation();

    // 2. Hacer llamada a la API para solicitar ticket
    const response = await fetch(`/api/turns/take?slug=${slug}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      }
    });

    if (!response.ok) throw new Error("Error al obtener turno");

    const data = await response.json();
    myTicket = data;
    localStorage.setItem(`ticket_${slug}`, JSON.stringify(myTicket));
    
    document.getElementById('my-ticket-num').textContent = myTicket.number;
    
    // Reset alert flags
    hasNotifiedNear = false;
    hasNotifiedNow = false;

    // Calcular distancia al comercio resuelto
    updateDistanceUI();
    showView('view-my-ticket');
    
    // Reestablecer SSE con datos de ticket para recibir estimaciones personalizadas
    initSSE();
    
    if (Notification.permission !== 'granted' && Notification.permission !== 'denied') {
      Notification.requestPermission();
    }
  } catch (err) {
    alert("Hubo un problema al solicitar el turno. Intente nuevamente.");
    console.error(err);
  }
});

document.getElementById('btn-cancel-turn').addEventListener('click', () => {
  if (confirm("¿Estás seguro de que querés abandonar tu turno? Perderás tu lugar en la fila.")) {
    abandonTurn();
  }
});

function abandonTurn() {
  myTicket = null;
  localStorage.removeItem(`ticket_${slug}`);
  showView('view-request-ticket');
  // Reestablecer SSE sin ticket para volver a modo anónimo
  initSSE();
}

// Main Bootstrapping
async function setupPage() {
  await loadBranding();
  loadTicket();
  initSSE();
}

setupPage();
