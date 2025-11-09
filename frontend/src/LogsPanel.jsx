import { useState, useEffect, useRef } from "react";
import { fetchLogs } from "./api.js";

export default function LogsPanel() {
  const [logs, setLogs] = useState([]);
  const [filter, setFilter] = useState("");
  const [autoScroll, setAutoScroll] = useState(true);
  const [isUserScrolling, setIsUserScrolling] = useState(false);
  const [isCleared, setIsCleared] = useState(false);
  const logsContainerRef = useRef(null);

  // Load logs from backend
  async function loadLogs() {
    try {
      const data = await fetchLogs(10000);
      if (data.ok) {
        setLogs(data.logs || []);
      }
    } catch (err) {
      console.error("Failed to fetch logs:", err);
    }
  }

  // Poll every 2 seconds (but skip if manually cleared)
  useEffect(() => {
    if (!isCleared) {
      loadLogs();
    }
    const interval = setInterval(() => {
      if (!isCleared) {
        loadLogs();
      }
    }, 2000);
    return () => clearInterval(interval);
  }, [isCleared]);

  // Auto-scroll to bottom when new logs arrive (if not manually scrolling)
  useEffect(() => {
    if (autoScroll && !isUserScrolling && logsContainerRef.current) {
      logsContainerRef.current.scrollTop = logsContainerRef.current.scrollHeight;
    }
  }, [logs, autoScroll, isUserScrolling]);

  // Detect manual scrolling
  function handleScroll() {
    if (!logsContainerRef.current) return;
    const { scrollTop, scrollHeight, clientHeight } = logsContainerRef.current;
    const isAtBottom = Math.abs(scrollHeight - scrollTop - clientHeight) < 10;
    setIsUserScrolling(!isAtBottom);
  }

  // Clear logs (client-side only) and pause polling
  function handleClear() {
    setLogs([]);
    setIsCleared(true);
  }

  // Resume polling after clearing
  function handleResume() {
    setIsCleared(false);
    loadLogs();
  }

  // Filter logs by level
  function filterLogs(logLines) {
    if (!filter) return logLines;
    return logLines.filter(line => {
      const lower = line.toLowerCase();
      if (filter === "errors") return lower.includes("error");
      if (filter === "warnings") return lower.includes("warning") || lower.includes("warn");
      if (filter === "info") return lower.includes("info");
      return true;
    });
  }

  // Get color for log line based on level
  function getLogColor(line) {
    const lower = line.toLowerCase();
    if (lower.includes("error")) return "#ff4444";
    if (lower.includes("warning") || lower.includes("warn")) return "#ffaa00";
    if (lower.includes("info")) return "#4499ff";
    return "#cccccc";
  }

  const filteredLogs = filterLogs(logs);

  return (
    <div style={styles.panel}>
      {/* Header */}
      <div style={styles.header}>
        <div style={styles.title}>Logs</div>
        <div style={styles.controls}>
          <select
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            style={styles.select}
          >
            <option value="">All</option>
            <option value="errors">Errors</option>
            <option value="warnings">Warnings</option>
            <option value="info">Info</option>
          </select>
          <button
            onClick={() => setAutoScroll(!autoScroll)}
            style={{
              ...styles.button,
              ...(autoScroll ? styles.buttonActive : {}),
            }}
          >
            Auto-scroll: {autoScroll ? "ON" : "OFF"}
          </button>
          {isCleared ? (
            <button onClick={handleResume} style={{ ...styles.button, ...styles.buttonActive }}>
              Resume
            </button>
          ) : (
            <button onClick={handleClear} style={styles.button}>
              Clear
            </button>
          )}
        </div>
      </div>

      {/* Logs container */}
      <div
        ref={logsContainerRef}
        onScroll={handleScroll}
        style={styles.logsContainer}
      >
        {filteredLogs.length === 0 ? (
          <div style={styles.emptyMessage}>No logs yet...</div>
        ) : (
          filteredLogs.map((line, idx) => (
            <div key={idx} style={{ ...styles.logLine, color: getLogColor(line) }}>
              {line}
            </div>
          ))
        )}
      </div>

      {/* Footer */}
      <div style={styles.footer}>
        {filteredLogs.length} lines
        {filter && ` (filtered from ${logs.length})`}
      </div>
    </div>
  );
}

const styles = {
  panel: {
    display: "flex",
    flexDirection: "column",
    height: "100vh",
    backgroundColor: "#1e1e1e",
    color: "#d4d4d4",
    fontFamily: "'Consolas', 'Monaco', 'Courier New', monospace",
    fontSize: "12px",
    borderLeft: "1px solid #333",
  },
  header: {
    padding: "8px 12px",
    backgroundColor: "#2d2d30",
    borderBottom: "1px solid #333",
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
  },
  title: {
    fontWeight: "bold",
    fontSize: "13px",
    color: "#cccccc",
  },
  controls: {
    display: "flex",
    gap: "8px",
  },
  select: {
    backgroundColor: "#3c3c3c",
    color: "#d4d4d4",
    border: "1px solid #555",
    padding: "2px 6px",
    fontSize: "11px",
    borderRadius: "3px",
  },
  button: {
    backgroundColor: "#3c3c3c",
    color: "#d4d4d4",
    border: "1px solid #555",
    padding: "2px 8px",
    fontSize: "11px",
    cursor: "pointer",
    borderRadius: "3px",
  },
  buttonActive: {
    backgroundColor: "#0e639c",
    borderColor: "#0e639c",
  },
  logsContainer: {
    flex: 1,
    overflowY: "auto",
    padding: "8px",
    backgroundColor: "#1e1e1e",
  },
  logLine: {
    whiteSpace: "pre-wrap",
    wordBreak: "break-all",
    marginBottom: "2px",
    lineHeight: "1.4",
  },
  emptyMessage: {
    color: "#888",
    fontStyle: "italic",
    padding: "20px",
    textAlign: "center",
  },
  footer: {
    padding: "4px 12px",
    backgroundColor: "#2d2d30",
    borderTop: "1px solid #333",
    fontSize: "10px",
    color: "#888",
  },
};
