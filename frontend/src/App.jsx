import { useState, useEffect } from "react";
import PromptLab from "./PromptLab";
import LogsPanel from "./LogsPanel";

export default function App() {
  const [showLogs, setShowLogs] = useState(true);

  useEffect(() => {
    const handleKey = (e) => {
      // Ctrl+P → Prompt Lab (currently the only view, so this is a no-op)
      if (e.ctrlKey && e.key.toLowerCase() === "p") {
        e.preventDefault();
        // Prompt Lab is always visible, so this doesn't do anything
        // But we keep it for consistency and future expansion
      }
      // Ctrl+L → Toggle Logs
      else if (e.ctrlKey && e.key.toLowerCase() === "l") {
        e.preventDefault();
        setShowLogs(!showLogs);
      }
    };

    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [showLogs]);

  return (
    <div style={styles.container}>
      <div style={styles.mainArea}>
        <div style={styles.nav}>
          <div style={styles.navLeft}>
            <div style={styles.navTitle}>Prompt Lab</div>
            <div style={styles.navHint}>Ctrl+P: Prompt Lab | Ctrl+L: Toggle Logs</div>
          </div>
          <button
            style={showLogs ? styles.logsButtonActive : styles.logsButton}
            onClick={() => setShowLogs(!showLogs)}
          >
            {showLogs ? "Hide Logs [Ctrl+L]" : "Show Logs [Ctrl+L]"}
          </button>
        </div>

        <div style={styles.content}>
          <PromptLab onShowLogs={() => setShowLogs(true)} />
        </div>
      </div>

      {showLogs && (
        <div style={styles.logsPanel}>
          <LogsPanel />
        </div>
      )}
    </div>
  );
}

const styles = {
  container: {
    display: "flex",
    minHeight: "100vh",
    backgroundColor: "#fafafa",
  },
  mainArea: {
    flex: 1,
    display: "flex",
    flexDirection: "column",
    minWidth: 0,
  },
  nav: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    padding: "12px 16px",
    borderBottom: "2px solid #111",
    backgroundColor: "#fff",
  },
  navLeft: {
    display: "flex",
    flexDirection: "column",
    gap: "4px",
  },
  navTitle: {
    fontSize: "18px",
    fontWeight: "600",
    color: "#111",
    fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto",
  },
  navHint: {
    fontSize: "11px",
    color: "#666",
    fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto",
  },
  logsButton: {
    padding: "8px 16px",
    backgroundColor: "#f5f5f5",
    color: "#666",
    border: "1px solid #ddd",
    borderRadius: "4px",
    cursor: "pointer",
    fontSize: "13px",
    fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto",
    fontWeight: "500",
  },
  logsButtonActive: {
    padding: "8px 16px",
    backgroundColor: "#2d2d30",
    color: "#fff",
    border: "1px solid #0e639c",
    borderRadius: "4px",
    cursor: "pointer",
    fontSize: "13px",
    fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto",
    fontWeight: "500",
  },
  content: {
    padding: "0",
    flex: 1,
    overflowY: "auto",
  },
  logsPanel: {
    width: "400px",
    flexShrink: 0,
    borderLeft: "1px solid #ddd",
  },
};
