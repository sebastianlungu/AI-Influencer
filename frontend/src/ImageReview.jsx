import { useEffect, useState, useRef } from "react";
import { fetchPendingImage, rateImage, uploadAsset } from "./api";

export default function ImageReview() {
  const [image, setImage] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [uploadPromptId, setUploadPromptId] = useState("");
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef(null);

  const loadNext = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetchPendingImage();
      if (res.ok && res.image) {
        setImage(res.image);
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
      if (e.key === "1" || e.key.toLowerCase() === "j") rating = "dislike";
      else if (e.key === "2" || e.key.toLowerCase() === "k") rating = "like";

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

  const handleUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (!uploadPromptId.trim()) {
      setError("Please enter a Prompt ID first");
      return;
    }

    setUploading(true);
    setError(null);

    try {
      await uploadAsset(file, "image", uploadPromptId.trim());
      setUploadPromptId("");
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
      // Reload to show the newly uploaded image
      await loadNext();
    } catch (err) {
      setError(err.message || "Upload failed");
    } finally {
      setUploading(false);
    }
  };

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

        {/* Upload Section */}
        <div style={styles.uploadSection}>
          <h3 style={styles.uploadTitle}>Upload Image (Manual Workflow)</h3>
          <p style={styles.uploadInstructions}>
            Upload manually generated images (864×1536, 9:16). Requires Prompt ID from Prompt Lab.
          </p>
          <div style={styles.uploadForm}>
            <input
              type="text"
              value={uploadPromptId}
              onChange={(e) => setUploadPromptId(e.target.value)}
              placeholder="Enter Prompt ID (e.g., pr_abc123...)"
              style={styles.promptInput}
            />
            <input
              ref={fileInputRef}
              type="file"
              accept="image/png,image/jpeg"
              onChange={handleUpload}
              disabled={uploading || !uploadPromptId.trim()}
              style={styles.fileInput}
            />
            {uploading && <div style={styles.uploadingText}>Uploading & validating...</div>}
          </div>
        </div>

        {error && <div style={styles.error}>{error}</div>}
      </div>
    );
  }

  const imagePath = image?.image_path;

  return (
    <div style={styles.container}>
      <div style={styles.header}>Image Review</div>

      {/* Upload Section */}
      <div style={styles.uploadSection}>
        <h3 style={styles.uploadTitle}>Upload New Image</h3>
        <div style={styles.uploadForm}>
          <input
            type="text"
            value={uploadPromptId}
            onChange={(e) => setUploadPromptId(e.target.value)}
            placeholder="Prompt ID (e.g., pr_abc123...)"
            style={styles.promptInput}
          />
          <input
            ref={fileInputRef}
            type="file"
            accept="image/png,image/jpeg"
            onChange={handleUpload}
            disabled={uploading || !uploadPromptId.trim()}
            style={styles.fileInput}
          />
        </div>
        {uploading && <div style={styles.uploadingText}>Uploading...</div>}
      </div>

      {/* Image Display */}
      <div style={styles.imageContainer}>
        <img src={`/${imagePath}`} alt="Review" style={styles.image} />
      </div>

      {/* Controls */}
      <div style={styles.controls}>
        <button style={styles.button} onClick={() => rateImage(image.id, "dislike").then(loadNext)}>
          [1/J] Dislike
        </button>
        <button style={styles.button} onClick={() => rateImage(image.id, "like").then(loadNext)}>
          [2/K] Like
        </button>
      </div>

      {/* Metadata */}
      <div style={styles.meta}>
        {image.prompt_id && (
          <div style={styles.metaLine}>
            <strong>Prompt ID:</strong> {image.prompt_id}
          </div>
        )}
        <div style={styles.metaLine}>
          <strong>Image ID:</strong> {image.id?.slice(0, 12) || "N/A"}
        </div>
        <div style={styles.metaLine}>
          <strong>Source:</strong> {image.source || "N/A"}
        </div>
        <div style={styles.metaLine}>
          <strong>Created:</strong> {image.created_at ? new Date(image.created_at).toLocaleString() : "N/A"}
        </div>
      </div>

      <div style={styles.keyboardHints}>
        <strong>Keyboard:</strong> 1/J = Dislike • 2/K = Like
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
  uploadSection: {
    backgroundColor: "#f9f9f9",
    border: "1px solid #ddd",
    borderRadius: "4px",
    padding: "16px",
    marginBottom: "16px",
  },
  uploadTitle: {
    fontSize: "16px",
    fontWeight: "600",
    margin: "0 0 8px 0",
    color: "#111",
  },
  uploadInstructions: {
    fontSize: "13px",
    color: "#666",
    margin: "0 0 12px 0",
    lineHeight: "1.5",
  },
  uploadForm: {
    display: "flex",
    flexDirection: "column",
    gap: "8px",
  },
  promptInput: {
    padding: "8px 12px",
    fontSize: "13px",
    border: "1px solid #ccc",
    borderRadius: "3px",
    fontFamily: "monospace",
  },
  fileInput: {
    padding: "8px",
    fontSize: "13px",
    border: "1px solid #ccc",
    borderRadius: "3px",
    cursor: "pointer",
  },
  uploadingText: {
    fontSize: "13px",
    color: "#007bff",
    fontWeight: "500",
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
    marginBottom: "12px",
    padding: "12px",
    backgroundColor: "#f9f9f9",
    border: "1px solid #eee",
    borderRadius: "4px",
  },
  metaLine: {
    marginBottom: "4px",
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
    backgroundColor: "#fee",
    color: "#c00",
    border: "1px solid #fcc",
    borderRadius: "4px",
    marginTop: "12px",
  },
};
