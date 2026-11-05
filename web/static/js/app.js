/**
 * Main Application Logic & UI View Controller
 */

const AppState = {
  activeView: 'overview',
  cameras: [],
  events: [],
  recordings: [],
  system: null,
  pollTimer: null,
  isPolling: false
};

// Formatting Utilities
function formatBytes(bytes) {
  if (bytes === 0 || !bytes) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function formatDuration(seconds) {
  if (!seconds) return '0s';
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return m > 0 ? `${m}m ${s}s` : `${s}s`;
}

function formatTime(isoStr) {
  if (!isoStr) return '--';
  const d = new Date(isoStr);
  return d.toLocaleTimeString([], { hour12: false }) + ' ' + d.toLocaleDateString([], { month: 'short', day: 'numeric' });
}

// Navigation & View Routing
function switchView(viewName) {
  AppState.activeView = viewName;
  
  // Update desktop links
  document.querySelectorAll('.nav-link').forEach(link => {
    link.classList.toggle('active', link.dataset.view === viewName);
  });

  // Update mobile bottom links
  document.querySelectorAll('.mobile-nav-item').forEach(link => {
    link.classList.toggle('active', link.dataset.view === viewName);
  });

  // Switch view sections
  document.querySelectorAll('.view-section').forEach(sec => {
    sec.classList.remove('active');
  });
  const target = document.getElementById(`view-${viewName}`);
  if (target) target.classList.add('active');

  // Update header title
  const titles = {
    overview: 'System Overview',
    live: 'Live Monitoring',
    events: 'Event Log',
    recordings: 'Video Recordings',
    cameras: 'Camera Configuration',
    system: 'Host Telemetry & Diagnostics'
  };
  const titleEl = document.getElementById('topbar-view-title');
  if (titleEl) titleEl.textContent = titles[viewName] || 'Dashboard';

  // Trigger immediate refresh for this view
  refreshCurrentView();
}

// Telemetry Polling Loop
async function pollTelemetry() {
  if (AppState.isPolling) return;
  AppState.isPolling = true;

  try {
    const [sys, cams] = await Promise.all([
      API.getSystemStatus(),
      API.getCameras()
    ]);
    AppState.system = sys;
    AppState.cameras = cams;

    // Update global status dot & topbar pill
    const uptimeMin = Math.floor(sys.uptime_seconds / 60);
    const uptimeStr = uptimeMin > 60 ? `${Math.floor(uptimeMin/60)}h ${uptimeMin%60}m` : `${uptimeMin}m`;
    const pill = document.getElementById('uptime-display');
    if (pill) pill.textContent = `UP: ${uptimeStr}`;

    // Render active view
    if (AppState.activeView === 'overview') {
      renderOverview(sys, cams);
    } else if (AppState.activeView === 'system') {
      renderSystem(sys);
    } else if (AppState.activeView === 'live') {
      updateLiveFeeds(cams);
    } else if (AppState.activeView === 'cameras') {
      renderCamerasTable(cams);
    }
  } catch (err) {
    console.warn('Telemetry poll error:', err);
  } finally {
    AppState.isPolling = false;
  }
}

// Overview View Renderer
async function renderOverview(sys, cams) {
  // Update KPI counters
  const onlineCount = cams.filter(c => c.status === 'online').length;
  document.getElementById('metric-cameras-online').textContent = `${onlineCount} / ${cams.length}`;
  
  // Storage metric
  const disk = sys.disk;
  document.getElementById('metric-storage-val').textContent = `${disk.used_gb} GB`;
  document.getElementById('metric-storage-sub').textContent = `${disk.free_gb} GB free of ${disk.total_gb} GB`;
  const storageBar = document.getElementById('metric-storage-bar');
  if (storageBar) {
    storageBar.style.width = `${disk.percent}%`;
    storageBar.className = 'progress-fill' + (disk.percent > 85 ? ' error' : (disk.percent > 70 ? ' warning' : ''));
  }

  // CPU metric
  const cpu = sys.cpu;
  document.getElementById('metric-cpu-val').textContent = `${cpu.percent}%`;
  document.getElementById('metric-cpu-sub').textContent = `${cpu.cores} Cores`;
  const cpuBar = document.getElementById('metric-cpu-bar');
  if (cpuBar) cpuBar.style.width = `${cpu.percent}%`;

  // Memory metric
  const mem = sys.memory;
  document.getElementById('metric-ram-val').textContent = `${mem.percent}%`;
  document.getElementById('metric-ram-sub').textContent = `${mem.used_mb} MB / ${mem.total_mb} MB`;
  const memBar = document.getElementById('metric-ram-bar');
  if (memBar) memBar.style.width = `${mem.percent}%`;

  // Network metric
  const net = sys.network;
  document.getElementById('metric-net-val').textContent = `${net.rx_kbps} kbps`;
  document.getElementById('metric-net-sub').textContent = `TX: ${net.tx_kbps} kbps`;

  // Render camera preview grid
  const previewGrid = document.getElementById('overview-camera-previews');
  if (previewGrid) {
    previewGrid.innerHTML = cams.map(cam => `
      <div class="camera-card ${cam.has_motion ? 'motion-active' : ''}">
        <div class="camera-header">
          <div class="camera-title-wrap">
            <span class="status-dot ${cam.status === 'online' ? 'pulse' : ''}" style="background-color: ${cam.status === 'online' ? 'var(--primary-green)' : 'var(--text-muted)'}"></span>
            <span class="camera-name">${cam.name}</span>
          </div>
          <span class="badge ${cam.status}">${cam.status}</span>
        </div>
        <div class="video-container">
          <img class="video-stream-img" src="/api/v1/cameras/${encodeURIComponent(cam.id)}/stream" alt="${cam.name}" loading="lazy" />
          ${cam.has_motion ? '<span class="stream-overlay-badge motion">● MOTION</span>' : ''}
        </div>
        <div class="camera-footer">
          <span>${cam.resolution} @ ${cam.fps_actual || cam.fps} FPS</span>
          <button class="btn btn-sm" onclick="switchView('live')">View Live</button>
        </div>
      </div>
    `).join('') || '<div style="color: var(--text-muted); padding: 16px;">No cameras registered.</div>';
  }

  // Load recent events
  try {
    const recentEvts = await API.getEvents(null, 5);
    const activeEvtCount = recentEvts.filter(e => e.status === 'active').length;
    document.getElementById('metric-events-val').textContent = activeEvtCount;
    document.getElementById('metric-events-sub').textContent = `${recentEvts.length} recent events`;

    const evtContainer = document.getElementById('overview-recent-events');
    if (evtContainer) {
      evtContainer.innerHTML = recentEvts.map(e => `
        <tr>
          <td><span class="badge ${e.event_type === 'motion' ? 'motion' : 'connecting'}">${e.event_type}</span></td>
          <td><code>${e.camera_id}</code></td>
          <td>${formatTime(e.start_time)}</td>
          <td>${e.status}</td>
        </tr>
      `).join('') || '<tr><td colspan="4" style="text-align: center; color: var(--text-muted);">No events recorded yet.</td></tr>';
    }
  } catch (e) {
    console.error('Failed to load overview events:', e);
  }
}

// Live Monitoring View Renderer
function updateLiveFeeds(cams) {
  const container = document.getElementById('live-cameras-grid');
  if (!container) return;

  // Render or update feed elements
  if (container.children.length !== cams.length) {
    container.innerHTML = cams.map(cam => `
      <div class="camera-card ${cam.has_motion ? 'motion-active' : ''}" id="live-card-${cam.id}">
        <div class="camera-header">
          <div class="camera-title-wrap">
            <span class="status-dot ${cam.status === 'online' ? 'pulse' : ''}" style="background-color: ${cam.status === 'online' ? 'var(--primary-green)' : 'var(--text-muted)'}"></span>
            <span class="camera-name">${cam.name}</span>
          </div>
          <div style="display: flex; gap: 6px;">
            ${cam.has_motion ? '<span class="badge motion">MOTION</span>' : ''}
            <span class="badge ${cam.status}">${cam.status}</span>
          </div>
        </div>
        <div class="video-container">
          <img class="video-stream-img" src="/api/v1/cameras/${encodeURIComponent(cam.id)}/stream" alt="${cam.name}" />
        </div>
        <div class="camera-footer">
          <span>Res: ${cam.resolution}</span>
          <span>Actual FPS: <strong>${cam.fps_actual || 0}</strong></span>
          <button class="btn btn-sm" onclick="openFullscreenStream('${cam.id}', '${cam.name}')">Expand</button>
        </div>
      </div>
    `).join('') || '<div style="color: var(--text-muted); padding: 16px;">No cameras configured.</div>';
  }
}

// Events View Renderer
async function loadEventsView() {
  try {
    const camFilter = document.getElementById('events-filter-cam').value;
    const events = await API.getEvents(camFilter || null, 100);
    const tbody = document.getElementById('events-table-body');
    if (!tbody) return;

    tbody.innerHTML = events.map(e => `
      <tr>
        <td><code>${e.id}</code></td>
        <td><code>${e.camera_id}</code></td>
        <td><span class="badge ${e.event_type === 'motion' ? 'motion' : 'connecting'}">${e.event_type}</span></td>
        <td>${formatTime(e.start_time)}</td>
        <td>${e.end_time ? formatTime(e.end_time) : '<span style="color: var(--primary-green)">Active...</span>'}</td>
        <td>${e.status}</td>
        <td><span style="font-size: 11px; color: var(--text-muted); font-family: var(--font-mono);">${e.details || ''}</span></td>
      </tr>
    `).join('') || '<tr><td colspan="7" style="text-align: center; color: var(--text-muted);">No events found.</td></tr>';
  } catch (err) {
    console.error('Failed to load events:', err);
  }
}

// Recordings View Renderer
async function loadRecordingsView() {
  try {
    const camFilter = document.getElementById('recordings-filter-cam').value;
    const recordings = await API.getRecordings(camFilter || null, 100);
    const tbody = document.getElementById('recordings-table-body');
    if (!tbody) return;

    tbody.innerHTML = recordings.map(r => `
      <tr>
        <td><code>${r.id}</code></td>
        <td><code>${r.camera_id}</code></td>
        <td>${formatTime(r.start_time)}</td>
        <td>${formatDuration(r.duration_seconds)}</td>
        <td>${formatBytes(r.file_size_bytes)}</td>
        <td><span class="badge ${r.status === 'completed' ? 'online' : 'connecting'}">${r.status}</span></td>
        <td>
          <button class="btn btn-sm btn-primary" onclick="openVideoPlayer('${r.id}', '${r.camera_id}')">Play</button>
        </td>
      </tr>
    `).join('') || '<tr><td colspan="7" style="text-align: center; color: var(--text-muted);">No recordings available yet. Motion events trigger automatic recordings.</td></tr>';
  } catch (err) {
    console.error('Failed to load recordings:', err);
  }
}

// Cameras View Renderer
function renderCamerasTable(cams) {
  const tbody = document.getElementById('cameras-table-body');
  if (!tbody) return;

  tbody.innerHTML = cams.map(cam => `
    <tr>
      <td><code>${cam.id}</code></td>
      <td><strong>${cam.name}</strong></td>
      <td><code>${cam.rtsp_url}</code></td>
      <td>${cam.resolution} @ ${cam.fps} FPS</td>
      <td><span class="badge ${cam.status}">${cam.status}</span></td>
      <td>
        <div style="display: flex; gap: 6px;">
          ${cam.enabled ? 
            `<button class="btn btn-sm btn-danger" onclick="toggleCameraState('${cam.id}', false)">Disable</button>` : 
            `<button class="btn btn-sm btn-primary" onclick="toggleCameraState('${cam.id}', true)">Enable</button>`
          }
          <button class="btn btn-sm btn-danger" onclick="deleteCameraEntry('${cam.id}')">Delete</button>
        </div>
      </td>
    </tr>
  `).join('') || '<tr><td colspan="6" style="text-align: center; color: var(--text-muted);">No cameras configured. Click "Register Camera" above to add one.</td></tr>';
}

// System View Renderer
function renderSystem(sys) {
  if (!sys) return;
  document.getElementById('sys-cpu-cores').textContent = sys.cpu.cores;
  document.getElementById('sys-cpu-percent').textContent = `${sys.cpu.percent}%`;
  document.getElementById('sys-mem-used').textContent = `${sys.memory.used_mb} MB`;
  document.getElementById('sys-mem-total').textContent = `${sys.memory.total_mb} MB (${sys.memory.percent}%)`;
  document.getElementById('sys-disk-drive').textContent = sys.disk.drive;
  document.getElementById('sys-disk-free').textContent = `${sys.disk.free_gb} GB`;
  document.getElementById('sys-disk-total').textContent = `${sys.disk.total_gb} GB (${sys.disk.percent}% used)`;
  document.getElementById('sys-net-rx').textContent = `${sys.network.rx_kbps} kbps (${sys.network.bytes_recv_mb} MB total)`;
  document.getElementById('sys-net-tx').textContent = `${sys.network.tx_kbps} kbps (${sys.network.bytes_sent_mb} MB total)`;
  document.getElementById('sys-proc-mem').textContent = `${sys.process.memory_mb} MB`;
  document.getElementById('sys-proc-threads').textContent = sys.process.threads;
  document.getElementById('sys-uptime').textContent = `${Math.floor(sys.uptime_seconds / 60)} minutes`;
}

// View Refresh Dispatcher
function refreshCurrentView() {
  pollTelemetry();
  if (AppState.activeView === 'events') {
    loadEventsView();
  } else if (AppState.activeView === 'recordings') {
    loadRecordingsView();
  }
}

// Camera Action Handlers
async function toggleCameraState(camId, enable) {
  try {
    await API.updateCamera(camId, { enabled: enable });
    if (enable) await API.startCamera(camId);
    else await API.stopCamera(camId);
    pollTelemetry();
  } catch (err) {
    alert(`Action failed: ${err.message}`);
  }
}

async function deleteCameraEntry(camId) {
  if (!confirm(`Are you sure you want to delete camera '${camId}'?`)) return;
  try {
    await API.deleteCamera(camId);
    pollTelemetry();
  } catch (err) {
    alert(`Failed to delete: ${err.message}`);
  }
}

// Modals Handling
function openModal(modalId) {
  const el = document.getElementById(modalId);
  if (el) el.classList.add('open');
}

function closeModal(modalId) {
  const el = document.getElementById(modalId);
  if (el) el.classList.remove('open');
}

function openFullscreenStream(camId, camName) {
  document.getElementById('stream-modal-title').textContent = `Live View: ${camName}`;
  const img = document.getElementById('fullscreen-stream-img');
  img.src = `/api/v1/cameras/${encodeURIComponent(camId)}/stream`;
  openModal('stream-modal');
}

function closeFullscreenStream() {
  const img = document.getElementById('fullscreen-stream-img');
  img.src = '';
  closeModal('stream-modal');
}

function openVideoPlayer(recId, camId) {
  document.getElementById('video-modal-title').textContent = `Playback: ${recId} (${camId})`;
  const video = document.getElementById('playback-video-el');
  video.src = `/api/v1/recordings/${encodeURIComponent(recId)}/stream`;
  openModal('video-modal');
  video.play().catch(e => console.log('Autoplay deferred:', e));
}

function closeVideoPlayer() {
  const video = document.getElementById('playback-video-el');
  video.pause();
  video.src = '';
  closeModal('video-modal');
}

// Camera Form Submission
document.addEventListener('DOMContentLoaded', () => {
  // Mobile sidebar drawer
  const navToggle = document.getElementById('mobile-nav-toggle');
  const sidebar = document.getElementById('sidebar');
  if (navToggle && sidebar) {
    navToggle.addEventListener('click', () => {
      sidebar.classList.toggle('mobile-open');
    });
  }

  // Camera Form
  const addCamForm = document.getElementById('add-camera-form');
  if (addCamForm) {
    addCamForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const payload = {
        id: document.getElementById('cam-id-input').value.trim(),
        name: document.getElementById('cam-name-input').value.trim(),
        rtsp_url: document.getElementById('cam-url-input').value.trim(),
        enabled: document.getElementById('cam-enabled-input').checked,
        fps: parseInt(document.getElementById('cam-fps-input').value, 10) || 10,
        resolution: document.getElementById('cam-res-input').value
      };

      try {
        await API.registerCamera(payload);
        closeModal('add-camera-modal');
        addCamForm.reset();
        pollTelemetry();
        alert('Camera registered successfully.');
      } catch (err) {
        alert(`Failed to register camera: ${err.message}`);
      }
    });
  }

  // Initial Poll & Schedule (every 2.5s)
  pollTelemetry();
  setInterval(pollTelemetry, 2500);
});

