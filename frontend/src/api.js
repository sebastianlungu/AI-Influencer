export async function generate(n = 3) {
  const r = await fetch("/api/cycle/generate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ n }),
  });
  return r.json();
}
