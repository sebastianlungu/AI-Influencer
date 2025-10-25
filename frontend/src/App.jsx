import { useState, useEffect } from "react";
import { generate } from "./api";

// Sanitize ID to prevent path traversal
function sanitizeId(id) {
  // Allow only alphanumeric characters (IDs are SHA256 hex, so this is safe)
  if (!/^[a-fA-F0-9]+$/.test(id)) {
    console.error(`Invalid ID format: ${id}`);
    return null;
  }
  return id;
}

export default function App() {
  const [items, setItems] = useState([]);
  const [i, setI] = useState(0);
  const [loading, setLoading] = useState(false);

  async function onGen() {
    setLoading(true);
    try {
      const r = await generate(1);
      setItems((p) => [...r.items, ...p]);
      setI(0);
    } catch (e) {
      alert(`Error: ${e.message}`);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    const h = (e) => {
      if (!items.length) return;
      const safeId = sanitizeId(items[i].id);
      if (!safeId) return;

      if (e.key === "k") {
        alert("POST " + safeId);
      }
      if (e.key === "j") {
        alert("DELETE " + safeId);
      }
    };
    window.addEventListener("keydown", h);
    return () => window.removeEventListener("keydown", h);
  }, [items, i]);

  const currentItem = items[i];
  const safeId = currentItem ? sanitizeId(currentItem.id) : null;

  return (
    <div style={{ padding: 20, maxWidth: 420, margin: "0 auto" }}>
      <h1>AI Influencer Review</h1>
      <button onClick={onGen} disabled={loading}>
        {loading ? "Generating..." : "Generate"}
      </button>
      {currentItem && safeId && (
        <div style={{ marginTop: 20 }}>
          <video
            src={`/media/generated/${safeId}.mp4`}
            controls
            autoPlay
            loop
            muted
            style={{ width: "100%", maxWidth: 360 }}
          />
          <div style={{ marginTop: 10, fontSize: 14, color: "#666" }}>
            <div>ID: {safeId}</div>
            <div>Seed: {currentItem.seed}</div>
          </div>
          <div style={{ marginTop: 10, fontSize: 14 }}>
            Use <b>K</b> to POST, <b>J</b> to DELETE
          </div>
        </div>
      )}
      {!items.length && (
        <div style={{ marginTop: 20, color: "#999" }}>
          No videos yet. Click Generate to create one.
        </div>
      )}
    </div>
  );
}
