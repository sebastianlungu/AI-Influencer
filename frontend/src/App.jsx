import { useState, useEffect } from "react";
import ImageReview from "./ImageReview";
import VideoReview from "./VideoReview";
import QueueView from "./QueueView";
import SchedulerSettings from "./SchedulerSettings";
import PromptLab from "./PromptLab";
import LogsPanel from "./LogsPanel";

export default function App() {
  const [currentView, setCurrentView] = useState("prompts");
  const [showLogs, setShowLogs] = useState(true);

  useEffect(() => {
    const handleKey = (e) => {
      // Only listen for uppercase or lowercase
      const key = e.key.toLowerCase();

      if (key === "p") setCurrentView("prompts");
      else if (key === "i") setCurrentView("images");
      else if (key === "v") setCurrentView("videos");
      else if (key === "q") setCurrentView("queues");
      else if (key === "s") setCurrentView("scheduler");
      else if (key === "l") setShowLogs(!showLogs);
    };

    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [showLogs]);

  return (
    <div style={styles.container}>
      <div style={styles.mainArea}>
        <div style={styles.nav}>
          <div style={styles.navLeft}>
            <button
              style={currentView === "prompts" ? styles.navButtonActive : styles.navButton}
              onClick={() => setCurrentView("prompts")}
            >
              [P] Prompt Lab
            </button>
            <button
              style={currentView === "images" ? styles.navButtonActive : styles.navButton}
              onClick={() => setCurrentView("images")}
            >
              [I] Images
            </button>
            <button
              style={currentView === "videos" ? styles.navButtonActive : styles.navButton}
              onClick={() => setCurrentView("videos")}
            >
              [V] Videos
            </button>
            <button
              style={currentView === "queues" ? styles.navButtonActive : styles.navButton}
              onClick={() => setCurrentView("queues")}
            >
              [Q] Queues
            </button>
            <button
              style={currentView === "scheduler" ? styles.navButtonActive : styles.navButton}
              onClick={() => setCurrentView("scheduler")}
            >
              [S] Scheduler
            </button>
          </div>
          <button
            style={showLogs ? styles.logsButtonActive : styles.logsButton}
            onClick={() => setShowLogs(!showLogs)}
          >
            [L] Logs
          </button>
        </div>

        <div style={styles.content}>
          {currentView === "prompts" && <PromptLab />}
          {currentView === "images" && <ImageReview />}
          {currentView === "videos" && <VideoReview />}
          {currentView === "queues" && <QueueView />}
          {currentView === "scheduler" && <SchedulerSettings />}
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
    minWidth: 0, // Allow flex shrinking
  },
  nav: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    gap: "0",
    borderBottom: "2px solid #111",
    backgroundColor: "#fff",
    padding: "0",
  },
  navLeft: {
    display: "flex",
    gap: "0",
  },
  navButton: {
    padding: "10px 16px",
    backgroundColor: "transparent",
    color: "#666",
    border: "none",
    borderBottom: "3px solid transparent",
    cursor: "pointer",
    fontSize: "13px",
    fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto",
    fontWeight: "400",
  },
  navButtonActive: {
    padding: "10px 16px",
    backgroundColor: "transparent",
    color: "#111",
    border: "none",
    borderBottom: "3px solid #111",
    cursor: "pointer",
    fontSize: "13px",
    fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto",
    fontWeight: "500",
  },
  logsButton: {
    padding: "10px 16px",
    backgroundColor: "transparent",
    color: "#666",
    border: "none",
    borderBottom: "3px solid transparent",
    cursor: "pointer",
    fontSize: "13px",
    fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto",
    fontWeight: "400",
  },
  logsButtonActive: {
    padding: "10px 16px",
    backgroundColor: "#2d2d30",
    color: "#fff",
    border: "none",
    borderBottom: "3px solid #0e639c",
    cursor: "pointer",
    fontSize: "13px",
    fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto",
    fontWeight: "500",
  },
  content: {
    padding: "0",
    flex: 1,
  },
  logsPanel: {
    width: "400px",
    flexShrink: 0,
  },
};
