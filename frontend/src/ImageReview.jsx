import { useEffect, useState } from "react";
import { fetchPendingImage, rateImage } from "./api";

export default function ImageReview() {
  const [image, setImage] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [pendingCount, setPendingCount] = useState(0);
  const [aspectView, setAspectView] = useState("4x5"); // "9x16" or "4x5"
  const [showOverlay, setShowOverlay] = useState(true);

  const loadNext = async () => {
    setLoading(true);
    setError(null);
    setAspectView("4x5"); // Reset to 4:5 view on load
    try {
      const res = await fetchPendingImage();
      if (res.ok && res.image) {
        setImage(res.image);
        // Count is implicit - we just show "reviewing" if exists
      } else {
        setImage(null);
        setError(res.message || "No pending images");
      }
    } catch (e) {
      setError(e.message || "Failed to load image");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadNext();
  }, []);

  useEffect(() => {
    const handleKey = async (e) => {
      if (!image || loading) return;

      // Aspect toggle: T key
      if (e.key === "t" || e.key === "T") {
        setAspectView((prev) => (prev === "9x16" ? "4x5" : "9x16"));
        return;
      }

      // Overlay toggle: O key
      if (e.key === "o" || e.key === "O") {
        setShowOverlay((prev) => !prev);
        return;
      }

      let rating = null;
      if (e.key === "1") rating = "dislike";
      else if (e.key === "2") rating = "like";
      else if (e.key === "3") rating = "superlike";

      if (!rating) return;

      try {
        await rateImage(image.id, rating);
        loadNext();
      } catch (e) {
        setError(e.message || "Rating failed");
      }
    };

    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [image, loading, aspectView]);

  if (loading) {
    return (
      <div style={styles.container}>
        <div style={styles.header}>Loading...</div>
      </div>
    );
  }

  if (error || !image) {
    return (
      <div style={styles.container}>
        <div style={styles.header}>Image Review</div>
        <div style={styles.error}>{error || "No images available"}</div>
      </div>
    );
  }

  // Get the appropriate image path based on view mode
  const getImagePath = () => {
    if (!image?.exports) return image?.image_path; // Fallback for old format

    if (aspectView === "9x16") {
      return image.exports.video_9x16_1080x1920;
    } else {
      return image.exports.feed_4x5_1080x1350;
    }
  };

  const imagePath = getImagePath();
  const hasCompositionWarning = image?.composition?.warning;

  return (
    <div style={styles.container}>
      <div style={styles.header}>Image Review - Mobile-First Dual Export</div>

      {/* Aspect Toggle */}
      <div style={styles.aspectToggle}>
        <button
          style={{
            ...styles.aspectButton,
            ...(aspectView === "4x5" ? styles.aspectButtonActive : {}),
          }}
          onClick={() => setAspectView("4x5")}
        >
          4:5 Feed (1080×1350)
        </button>
        <button
          style={{
            ...styles.aspectButton,
            ...(aspectView === "9x16" ? styles.aspectButtonActive : {}),
          }}
          onClick={() => setAspectView("9x16")}
        >
          9:16 Video (1080×1920)
        </button>
        <button
          style={styles.overlayToggleButton}
          onClick={() => setShowOverlay(!showOverlay)}
          title="Toggle 4:5 safe area overlay (O key)"
        >
          {showOverlay ? "Hide" : "Show"} Overlay
        </button>
      </div>

      {/* Composition Warning */}
      {hasCompositionWarning && (
        <div style={styles.warning}>
          ⚠️ Composition Warning: {image.composition.reason || "Subject may be cropped in 4:5 view"}
        </div>
      )}

      {/* Image Container with Overlay */}
      <div style={styles.imageContainer}>
        <div style={styles.imageWrapper}>
          <img
            src={`/${imagePath}`}
            alt="Review"
            style={styles.image}
          />
          {/* 4:5 Safe Area Overlay (only on 9:16 view) */}
          {aspectView === "9x16" && showOverlay && (
            <div style={styles.safeAreaOverlay}>
              <div style={styles.safeAreaBox}>
                4:5 Safe Area
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Export Usage Hint */}
      <div style={styles.hint}>
        📱 <strong>Like (2)</strong> → Uses 4:5 Feed • <strong>Superlike (3)</strong> → Uses 9:16 Video
      </div>

      <div style={styles.controls}>
        <button style={styles.button} onClick={() => rateImage(image.id, "dislike").then(loadNext)}>
          [1] Dislike
        </button>
        <button style={styles.button} onClick={() => rateImage(image.id, "like").then(loadNext)}>
          [2] 👍 Like (4:5)
        </button>
        <button style={styles.button} onClick={() => rateImage(image.id, "superlike").then(loadNext)}>
          [3] ⭐ Superlike (9:16)
        </button>
      </div>

      <div style={styles.meta}>
        <div style={styles.metaLine}>
          <strong>Viewing:</strong> {aspectView === "9x16" ? "9:16 Video (1080×1920)" : "4:5 Feed (1080×1350)"}
        </div>
        <div style={styles.metaLine}>
          <strong>Variation:</strong> {image.prompt?.variation || "N/A"}
        </div>
        <div style={styles.metaLine}>
          <strong>ID:</strong> {image.id?.slice(0, 8) || "N/A"}
        </div>
        <div style={styles.metaLine}>
          <strong>Seed:</strong> {image.prompt?.seed || "N/A"}
        </div>
      </div>

      <div style={styles.promptBox}>
        <strong>Prompt:</strong>
        <div style={styles.promptText}>{image.prompt?.base || "N/A"}</div>
      </div>

      <div style={styles.keyboardHints}>
        <strong>Keyboard:</strong> 1=Dislike • 2=Like (4:5) • 3=Superlike (9:16) • T=Toggle Aspect • O=Toggle Overlay
      </div>
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
  aspectToggle: {
    display: "flex",
    gap: "8px",
    marginBottom: "16px",
  },
  aspectButton: {
    flex: 1,
    padding: "8px 12px",
    backgroundColor: "#f5f5f5",
    color: "#333",
    border: "1px solid #ddd",
    cursor: "pointer",
    fontSize: "13px",
    fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto",
    transition: "all 0.2s",
  },
  aspectButtonActive: {
    backgroundColor: "#007bff",
    color: "#fff",
    borderColor: "#007bff",
  },
  overlayToggleButton: {
    padding: "8px 16px",
    backgroundColor: "#666",
    color: "#fff",
    border: "none",
    cursor: "pointer",
    fontSize: "13px",
    fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto",
  },
  warning: {
    padding: "12px",
    backgroundColor: "#fff3cd",
    color: "#856404",
    border: "1px solid #ffeaa7",
    borderRadius: "4px",
    marginBottom: "16px",
    fontSize: "14px",
  },
  imageContainer: {
    width: "100%",
    marginBottom: "16px",
    border: "1px solid #ddd",
    backgroundColor: "#fafafa",
  },
  imageWrapper: {
    position: "relative",
    width: "100%",
  },
  image: {
    width: "100%",
    height: "auto",
    display: "block",
  },
  safeAreaOverlay: {
    position: "absolute",
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    pointerEvents: "none",
  },
  safeAreaBox: {
    width: "100%",
    height: "70.3125%", // 1350/1920 = 0.703125 (4:5 safe area within 9:16)
    border: "3px dashed rgba(0, 123, 255, 0.7)",
    backgroundColor: "rgba(0, 123, 255, 0.05)",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    color: "rgba(0, 123, 255, 0.9)",
    fontSize: "16px",
    fontWeight: "bold",
    textShadow: "0 0 4px white",
  },
  hint: {
    padding: "8px 12px",
    backgroundColor: "#e7f3ff",
    color: "#004085",
    border: "1px solid #b8daff",
    borderRadius: "4px",
    marginBottom: "16px",
    fontSize: "14px",
    textAlign: "center",
  },
  controls: {
    display: "flex",
    gap: "8px",
    marginBottom: "16px",
  },
  button: {
    flex: 1,
    padding: "12px",
    backgroundColor: "#333",
    color: "#fff",
    border: "none",
    cursor: "pointer",
    fontSize: "14px",
    fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto",
  },
  meta: {
    fontSize: "14px",
    color: "#666",
    lineHeight: "1.5",
    marginBottom: "12px",
  },
  metaLine: {
    marginBottom: "4px",
  },
  promptBox: {
    marginTop: "12px",
    marginBottom: "12px",
    padding: "12px",
    backgroundColor: "#f9f9f9",
    border: "1px solid #ddd",
    maxHeight: "200px",
    overflow: "auto",
  },
  promptText: {
    fontSize: "12px",
    lineHeight: "1.5",
    whiteSpace: "pre-wrap",
    marginTop: "4px",
    color: "#333",
  },
  keyboardHints: {
    fontSize: "13px",
    color: "#999",
    textAlign: "center",
    padding: "8px",
    backgroundColor: "#f9f9f9",
    borderRadius: "4px",
  },
  error: {
    padding: "16px",
    backgroundColor: "#f5f5f5",
    color: "#666",
    textAlign: "center",
  },
};
