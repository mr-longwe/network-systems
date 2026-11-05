/**
 * Edge Server REST API Client
 */

const API = {
  async getHealth() {
    const res = await fetch('/api/v1/health');
    if (!res.ok) throw new Error(`Health check failed: ${res.statusText}`);
    return res.json();
  },

  async getSystemStatus() {
    const res = await fetch('/api/v1/system/status');
    if (!res.ok) throw new Error(`System status fetch failed: ${res.statusText}`);
    return res.json();
  },

  async getCameras() {
    const res = await fetch('/api/v1/cameras');
    if (!res.ok) throw new Error(`Cameras fetch failed: ${res.statusText}`);
    return res.json();
  },

  async getCamera(id) {
    const res = await fetch(`/api/v1/cameras/${encodeURIComponent(id)}`);
    if (!res.ok) throw new Error(`Camera fetch failed: ${res.statusText}`);
    return res.json();
  },

  async registerCamera(data) {
    const res = await fetch('/api/v1/cameras', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || 'Registration failed');
    }
    return res.json();
  },

  async updateCamera(id, data) {
    const res = await fetch(`/api/v1/cameras/${encodeURIComponent(id)}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    if (!res.ok) throw new Error('Update failed');
    return res.json();
  },

  async deleteCamera(id) {
    const res = await fetch(`/api/v1/cameras/${encodeURIComponent(id)}`, {
      method: 'DELETE'
    });
    if (!res.ok) throw new Error('Delete failed');
    return res.json();
  },

  async startCamera(id) {
    const res = await fetch(`/api/v1/cameras/${encodeURIComponent(id)}/start`, { method: 'POST' });
    return res.json();
  },

  async stopCamera(id) {
    const res = await fetch(`/api/v1/cameras/${encodeURIComponent(id)}/stop`, { method: 'POST' });
    return res.json();
  },

  async getEvents(cameraId = null, limit = 50) {
    let url = `/api/v1/events?limit=${limit}`;
    if (cameraId) url += `&camera_id=${encodeURIComponent(cameraId)}`;
    const res = await fetch(url);
    if (!res.ok) throw new Error('Events fetch failed');
    return res.json();
  },

  async getRecordings(cameraId = null, limit = 50) {
    let url = `/api/v1/recordings?limit=${limit}`;
    if (cameraId) url += `&camera_id=${encodeURIComponent(cameraId)}`;
    const res = await fetch(url);
    if (!res.ok) throw new Error('Recordings fetch failed');
    return res.json();
  }
};

