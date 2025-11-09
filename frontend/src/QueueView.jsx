import { useEffect, useState } from "react";
import {
  generate,
  fetchLikedImages,
  fetchApprovedVideos,
  fetchVideoQueueStatus,
  processVideoQueue,
} from "./api";

export default function QueueView() {
  const [activeTab, setActiveTab] = useState("liked");
  const [likedImages, setLikedImages] = useState([]);
  const [approvedVideos, setApprovedVideos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [generating, setGenerating] = useState(false);
  const [batchSize, setBatchSize] = useState(10);
  const [queueStatus, setQueueStatus] = useState(null);
  const [processing, setProcessing] = useState(false);
  const [toast, setToast] = useState(null);

  // Show toast notification
  const showToast = (message, type = "success") => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 5000); // Auto-hide after 5 seconds
  };

  const loadQueues = async () => {
    setLoading(true);
    setError(null);
    try {
      const [liked, approved] = await Promise.all([
        fetchLikedImages(),
        fetchApprovedVideos(),
      ]);

      setLikedImages(liked.images || []);
      setApprovedVideos(approved.videos || []);
    } catch (e) {
      setError(e.message || "Failed to load queues");
    } finally {
      setLoading(false);
    }
  };

  const loadQueueStatus = async () => {
    try {
      const status = await fetchVideoQueueStatus();
      setQueueStatus(status);
    } catch (e) {
      console.error("Failed to load queue status:", e);
    }
  };

  useEffect(() => {
    loadQueues();
    loadQueueStatus();

    // Poll queue status every 5 seconds
    const interval = setInterval(loadQueueStatus, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleGenerateImages = async () => {
    setGenerating(true);
    setError(null);
    try {
      const result = await generate(batchSize);
      showToast(`Generated ${result.items?.length || 0} images`, "success");
      // Don't reload queues here - images go to ImageReview first
    } catch (e) {
      setError(e.message || "Image generation failed");
      showToast(e.message || "Image generation failed", "error");
    } finally {
      setGenerating(false);
    }
  };

  const handleProcessQueue = async () => {
    setProcessing(true);
    try {
      const result = await processVideoQueue();
      if (result.processed) {
        if (result.ok) {
          showToast(`Video generated: ${result.image_id}`, "success");
        } else {
          showToast(`Failed: ${result.error}`, "error");
        }
      } else {
        showToast("Queue is empty", "info");
      }
      loadQueueStatus(); // Refresh status
      loadQueues(); // Refresh queues
    } catch (e) {
      showToast(e.message || "Queue processing failed", "error");
    } finally {
      setProcessing(false);
    }
  };


  if (loading) {
    return (
      <div style={styles.container}>
        <div style={styles.header}>Loading queues...</div>
      </div>
    );
  }

  const tabs = [
    { id: "liked", label: "Liked Images", count: likedImages.length },
    { id: "approved", label: "Liked Videos", count: approvedVideos.length },
  ];

  let items = [];
  if (activeTab === "liked") items = likedImages;
  else if (activeTab === "approved") items = approvedVideos;

  return (
    <div style={styles.container}>
      <div style={styles.header}>Content Queues</div>

      {error && <div style={styles.error}>{error}</div>}

      {/* Video Queue Status */}
      {queueStatus && (queueStatus.pending > 0 || queueStatus.processing > 0 || queueStatus.failed > 0) && (
        <div style={styles.queueStatus}>
          <div style={styles.queueHeader}>
            📹 Video Generation Queue
          </div>
          <div style={styles.queueStats}>
            {queueStatus.pending > 0 && (
              <span style={styles.queueStat}>
                {queueStatus.pending} queued
              </span>
            )}
            {queueStatus.processing > 0 && (
              <span style={styles.queueStatProcessing}>
                {queueStatus.processing} processing
              </span>
            )}
            {queueStatus.failed > 0 && (
              <span style={styles.queueStatFailed}>
                {queueStatus.failed} failed
              </span>
            )}
          </div>
          <button
            onClick={handleProcessQueue}
            disabled={processing || queueStatus.pending === 0}
            style={processing || queueStatus.pending === 0 ? styles.buttonDisabled : styles.buttonSecondary}
          >
            {processing ? "Processing..." : "Process Next Video"}
          </button>
        </div>
      )}

      {/* Generate Images Section */}
      <div style={styles.generateSection}>
        <div style={styles.generateHeader}>Generate New Images</div>
        <div style={styles.generateControls}>
          <input
            type="number"
            min="1"
            max="20"
            value={batchSize}
            onChange={(e) => setBatchSize(parseInt(e.target.value) || 10)}
            style={styles.input}
            disabled={generating}
          />
          <button
            onClick={handleGenerateImages}
            disabled={generating}
            style={generating ? styles.buttonDisabled : styles.buttonPrimary}
          >
            {generating ? "Generating..." : `Generate ${batchSize} Images`}
          </button>
        </div>
        <div style={styles.generateHint}>
          Images will appear in Image Review for rating
        </div>
      </div>

      <div style={styles.tabs}>
        {tabs.map((tab) => (
          <button
            key={tab.id}
            style={activeTab === tab.id ? styles.tabActive : styles.tab}
            onClick={() => setActiveTab(tab.id)}
          >
            {tab.label} ({tab.count})
          </button>
        ))}
      </div>

      <div style={styles.grid}>
        {items.length === 0 && (
          <div style={styles.empty}>No items in this queue</div>
        )}

        {items.map((item) => (
          <div key={item.id} style={styles.card}>
            {activeTab === "approved" ? (
              <video
                src={`/${item.video_path}`}
                style={styles.thumbnail}
                muted
                loop
              />
            ) : (
              <img
                src={`/${item.image_path}`}
                alt={item.id}
                style={styles.thumbnail}
              />
            )}

            <div style={styles.cardMeta}>
              <div style={styles.cardId}>ID: {item.id?.slice(0, 8)}</div>

              {activeTab === "liked" && (
                <div style={styles.cardNote}>Liked (preview)</div>
              )}

              {activeTab === "approved" && (
                <div style={styles.cardNote}>Ready to post</div>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Toast notification */}
      {toast && (
        <div
          style={{
            ...styles.toast,
            ...(toast.type === "success" ? styles.toastSuccess : {}),
            ...(toast.type === "error" ? styles.toastError : {}),
            ...(toast.type === "info" ? styles.toastInfo : {}),
          }}
        >
          {toast.type === "success" && "✅ "}
          {toast.type === "error" && "❌ "}
          {toast.type === "info" && "ℹ️ "}
          {toast.message}
        </div>
      )}
    </div>
  );
}

const styles = {
  container: {
    maxWidth: "800px",
    margin: "0 auto",
    padding: "16px",
  },
  header: {
    fontSize: "20px",
    marginBottom: "16px",
    color: "#111",
    borderBottom: "1px solid #ddd",
    paddingBottom: "8px",
  },
  tabs: {
    display: "flex",
    gap: "0",
    marginBottom: "16px",
    borderBottom: "1px solid #ddd",
  },
  tab: {
    padding: "8px 16px",
    backgroundColor: "transparent",
    color: "#666",
    border: "none",
    borderBottom: "2px solid transparent",
    cursor: "pointer",
    fontSize: "14px",
    fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto",
  },
  tabActive: {
    padding: "8px 16px",
    backgroundColor: "transparent",
    color: "#111",
    border: "none",
    borderBottom: "2px solid #111",
    cursor: "pointer",
    fontSize: "14px",
    fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto",
    fontWeight: "500",
  },
  grid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))",
    gap: "16px",
  },
  card: {
    border: "1px solid #ddd",
    backgroundColor: "#fafafa",
  },
  thumbnail: {
    width: "100%",
    height: "200px",
    objectFit: "cover",
    display: "block",
    backgroundColor: "#000",
  },
  cardMeta: {
    padding: "8px",
  },
  cardId: {
    fontSize: "12px",
    color: "#666",
    marginBottom: "8px",
    fontFamily: "monospace",
  },
  cardButton: {
    width: "100%",
    padding: "8px",
    backgroundColor: "#333",
    color: "#fff",
    border: "none",
    cursor: "pointer",
    fontSize: "12px",
    fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto",
  },
  cardNote: {
    fontSize: "12px",
    color: "#999",
  },
  empty: {
    gridColumn: "1 / -1",
    textAlign: "center",
    padding: "32px",
    color: "#999",
    fontSize: "14px",
  },
  error: {
    padding: "8px",
    backgroundColor: "#f0f0f0",
    color: "#666",
    marginBottom: "16px",
    fontSize: "14px",
    border: "1px solid #ddd",
  },
  generateSection: {
    padding: "16px",
    backgroundColor: "#f9f9f9",
    border: "1px solid #ddd",
    marginBottom: "16px",
  },
  generateHeader: {
    fontSize: "16px",
    fontWeight: "500",
    marginBottom: "12px",
    color: "#111",
  },
  generateControls: {
    display: "flex",
    gap: "8px",
    alignItems: "center",
    marginBottom: "8px",
  },
  input: {
    padding: "8px 12px",
    border: "1px solid #ddd",
    fontSize: "14px",
    fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto",
    width: "80px",
    backgroundColor: "#fff",
  },
  buttonPrimary: {
    padding: "8px 16px",
    backgroundColor: "#111",
    color: "#fff",
    border: "none",
    cursor: "pointer",
    fontSize: "14px",
    fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto",
    fontWeight: "500",
  },
  buttonDisabled: {
    padding: "8px 16px",
    backgroundColor: "#999",
    color: "#fff",
    border: "none",
    cursor: "not-allowed",
    fontSize: "14px",
    fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto",
    fontWeight: "500",
    opacity: 0.5,
  },
  generateHint: {
    fontSize: "12px",
    color: "#666",
    fontStyle: "italic",
  },
  queueStatus: {
    padding: "16px",
    backgroundColor: "#f0f9ff",
    border: "1px solid #0ea5e9",
    marginBottom: "16px",
  },
  queueHeader: {
    fontSize: "16px",
    fontWeight: "500",
    marginBottom: "12px",
    color: "#111",
  },
  queueStats: {
    display: "flex",
    gap: "16px",
    marginBottom: "12px",
    fontSize: "14px",
  },
  queueStat: {
    color: "#666",
  },
  queueStatProcessing: {
    color: "#0ea5e9",
    fontWeight: "500",
  },
  queueStatFailed: {
    color: "#ef4444",
    fontWeight: "500",
  },
  buttonSecondary: {
    padding: "8px 16px",
    backgroundColor: "#0ea5e9",
    color: "#fff",
    border: "none",
    cursor: "pointer",
    fontSize: "14px",
    fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto",
    fontWeight: "500",
  },
  toast: {
    position: "fixed",
    bottom: "24px",
    left: "50%",
    transform: "translateX(-50%)",
    padding: "12px 24px",
    borderRadius: "6px",
    fontSize: "14px",
    fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto",
    fontWeight: "500",
    boxShadow: "0 4px 12px rgba(0, 0, 0, 0.15)",
    zIndex: 1000,
    maxWidth: "500px",
    textAlign: "center",
  },
  toastSuccess: {
    backgroundColor: "#10b981",
    color: "#fff",
  },
  toastError: {
    backgroundColor: "#ef4444",
    color: "#fff",
  },
  toastInfo: {
    backgroundColor: "#3b82f6",
    color: "#fff",
  },
};
