// ============================================================================
// Image Generation
// ============================================================================

export async function generate(n = 3) {
  const r = await fetch("/api/cycle/generate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ n }),
  });
  return r.json();
}

// ============================================================================
// Image Rating & Queues
// ============================================================================

export async function fetchPendingImage() {
  const r = await fetch("/api/images/pending");
  return r.json();
}

export async function rateImage(id, rating) {
  const r = await fetch(`/api/images/${id}/rate`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ rating }),
  });
  return r.json();
}

export async function fetchLikedImages() {
  const r = await fetch("/api/images/liked");
  return r.json();
}

export async function fetchSuperlikedImages() {
  const r = await fetch("/api/images/superliked");
  return r.json();
}

// ============================================================================
// Video Rating & Queues
// ============================================================================

export async function fetchPendingVideo() {
  const r = await fetch("/api/videos/pending");
  return r.json();
}

export async function rateVideo(id, rating) {
  const r = await fetch(`/api/videos/${id}/rate`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ rating }),
  });
  return r.json();
}

export async function regenerateVideo(id) {
  const r = await fetch(`/api/videos/${id}/regenerate`, {
    method: "POST",
  });
  return r.json();
}

export async function fetchApprovedVideos() {
  const r = await fetch("/api/videos/approved");
  return r.json();
}

// ============================================================================
// Video Generation Queue
// ============================================================================

export async function fetchVideoQueueStatus() {
  const r = await fetch("/api/videos/queue/status");
  return r.json();
}

export async function processVideoQueue() {
  const r = await fetch("/api/videos/process-queue", {
    method: "POST",
  });
  return r.json();
}

// ============================================================================
// Music Review
// ============================================================================

export async function suggestMusic(videoId) {
  const r = await fetch(`/api/videos/${videoId}/music/suggest`, {
    method: "POST",
  });
  return r.json();
}

export async function generateMusic(videoId) {
  const r = await fetch(`/api/videos/${videoId}/music/generate`, {
    method: "POST",
  });
  return r.json();
}

export async function muxMusic(videoId) {
  const r = await fetch(`/api/videos/${videoId}/music/mux`, {
    method: "POST",
  });
  return r.json();
}

export async function rateMusic(videoId, rating) {
  const r = await fetch(`/api/videos/${videoId}/music/rate`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ rating }),
  });
  return r.json();
}

// ============================================================================
// Scheduler Control
// ============================================================================

export async function schedulerRunOnce() {
  const r = await fetch("/api/scheduler/run-once", {
    method: "POST",
  });
  return r.json();
}

export async function schedulerDryRun() {
  const r = await fetch("/api/scheduler/dry-run", {
    method: "POST",
  });
  return r.json();
}

// ============================================================================
// Health & Config
// ============================================================================

export async function fetchHealth() {
  const r = await fetch("/api/healthz");
  return r.json();
}

// ============================================================================
// Logs
// ============================================================================

export async function fetchLogs(lines = 100) {
  const r = await fetch(`/api/logs/tail?lines=${lines}`);
  return r.json();
}
