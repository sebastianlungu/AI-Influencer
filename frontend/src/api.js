// ============================================================================
// Prompt Lab API Client (Prompt Generation + Observability Only)
// ============================================================================

export async function generatePromptBundle(payload) {
  const r = await fetch("/api/prompts/bundle", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!r.ok) {
    const err = await r.json();
    throw new Error(err.detail || "Failed to generate prompt bundle");
  }
  return r.json();
}

export async function getPrompts({
  status = "all",
  search = "",
  page = 1,
  page_size = 20,
  sort = "-created_at",
} = {}) {
  const params = new URLSearchParams({
    status,
    search,
    page: String(page),
    page_size: String(page_size),
    sort,
  });
  const r = await fetch(`/api/prompts?${params}`);
  if (!r.ok) {
    throw new Error("Failed to fetch prompts");
  }
  return r.json();
}

export async function getPromptBundle(bundleId) {
  const r = await fetch(`/api/prompts/${bundleId}`);
  if (!r.ok) {
    throw new Error("Failed to fetch prompt bundle");
  }
  return r.json();
}

export async function getLocations(refresh = false) {
  const url = refresh ? "/api/locations?refresh=1" : "/api/locations";
  const r = await fetch(url);
  if (!r.ok) {
    throw new Error("Failed to fetch locations");
  }
  return r.json();
}

export async function updatePromptState(bundleId, used) {
  const r = await fetch(`/api/prompts/${bundleId}/state`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ used }),
  });
  if (!r.ok) {
    const err = await r.json();
    throw new Error(err.detail || "Failed to update prompt state");
  }
  return r.json();
}

// ============================================================================
// Health & Logs
// ============================================================================

export async function fetchHealth() {
  const r = await fetch("/api/healthz");
  return r.json();
}

export async function fetchLogs(lines = 100) {
  const r = await fetch(`/api/logs/tail?lines=${lines}`);
  return r.json();
}
