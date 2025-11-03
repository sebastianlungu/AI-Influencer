import { useState, useEffect } from "react";
import ImageReview from "./ImageReview";
import VideoReview from "./VideoReview";
import QueueView from "./QueueView";
import SchedulerSettings from "./SchedulerSettings";

export default function App() {
  const [currentView, setCurrentView] = useState("images");

  useEffect(() => {
    const handleKey = (e) => {
      // Only listen for uppercase or lowercase
      const key = e.key.toLowerCase();

      if (key === "i") setCurrentView("images");
      else if (key === "v") setCurrentView("videos");
      else if (key === "q") setCurrentView("queues");
      else if (key === "s") setCurrentView("scheduler");
    };

    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, []);

  return (
    <div style={styles.app}>
      <div style={styles.nav}>
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

      <div style={styles.content}>
        {currentView === "images" && <ImageReview />}
        {currentView === "videos" && <VideoReview />}
        {currentView === "queues" && <QueueView />}
        {currentView === "scheduler" && <SchedulerSettings />}
      </div>
    </div>
  );
}

const styles = {
  app: {
    minHeight: "100vh",
    backgroundColor: "#fafafa",
  },
  nav: {
    display: "flex",
    gap: "0",
    borderBottom: "2px solid #111",
    backgroundColor: "#fff",
    padding: "0",
  },
  navButton: {
    padding: "16px 24px",
    backgroundColor: "transparent",
    color: "#666",
    border: "none",
    borderBottom: "3px solid transparent",
    cursor: "pointer",
    fontSize: "14px",
    fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto",
    fontWeight: "400",
  },
  navButtonActive: {
    padding: "16px 24px",
    backgroundColor: "transparent",
    color: "#111",
    border: "none",
    borderBottom: "3px solid #111",
    cursor: "pointer",
    fontSize: "14px",
    fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto",
    fontWeight: "500",
  },
  content: {
    padding: "0",
  },
};
