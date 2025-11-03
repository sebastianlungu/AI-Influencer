import { useEffect, useState } from "react";
import { fetchPendingImage, rateImage } from "./api";

export default function ImageReview() {
  const [image, setImage] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [pendingCount, setPendingCount] = useState(0);

  const loadNext = async () => {
    setLoading(true);
    setError(null);
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
  }, [image, loading]);

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

  return (
    <div style={styles.container}>
      <div style={styles.header}>Image Review</div>

      <div style={styles.imageContainer}>
        <img
          src={`/${image.image_path}`}
          alt="Review"
          style={styles.image}
        />
      </div>

      <div style={styles.controls}>
        <button style={styles.button} onClick={() => rateImage(image.id, "dislike").then(loadNext)}>
          [1] Dislike
        </button>
        <button style={styles.button} onClick={() => rateImage(image.id, "like").then(loadNext)}>
          [2] Like
        </button>
        <button style={styles.button} onClick={() => rateImage(image.id, "superlike").then(loadNext)}>
          [3] ⭐ Superlike
        </button>
      </div>

      <div style={styles.meta}>
        <div style={styles.metaLine}>
          <strong>Variation:</strong> {image.prompt?.variation || "N/A"}
        </div>
        <div style={styles.metaLine}>
          <strong>ID:</strong> {image.id?.slice(0, 8) || "N/A"}
        </div>
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
  imageContainer: {
    width: "100%",
    marginBottom: "16px",
    border: "1px solid #ddd",
    backgroundColor: "#fafafa",
  },
  image: {
    width: "100%",
    height: "auto",
    display: "block",
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
  },
  metaLine: {
    marginBottom: "4px",
  },
  error: {
    padding: "16px",
    backgroundColor: "#f5f5f5",
    color: "#666",
    textAlign: "center",
  },
};
