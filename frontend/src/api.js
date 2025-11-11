// ============================================================================
// Prompt Lab API Client (Prompt Generation + Observability Only)
// ============================================================================

export async function generatePromptBundle({ setting, seed_words, count }) {
  const r = await fetch("/api/prompts/bundle", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ setting, seed_words, count }),
  });
  if (!r.ok) {
    const err = await r.json();
    throw new Error(err.detail || "Failed to generate prompt bundle");
  }
  return r.json();
}

export async function getRecentPrompts(limit = 20) {
  const r = await fetch(`/api/prompts?limit=${limit}`);
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
