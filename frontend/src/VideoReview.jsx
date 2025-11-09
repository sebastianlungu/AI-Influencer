import { useEffect, useState, useRef } from "react";
import {
  fetchPendingVideo,
  rateVideo,
  regenerateVideo,
  suggestMusic,
  generateMusic,
  muxMusic,
  rateMusic,
  uploadAsset,
} from "./api";

export default function VideoReview() {
  const [video, setVideo] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showMusicPanel, setShowMusicPanel] = useState(false);
  const [musicBrief, setMusicBrief] = useState(null);
  const [musicStatus, setMusicStatus] = useState("idle"); // idle, suggesting, suggested, generating, generated, muxing, muxed
  const [musicWorking, setMusicWorking] = useState(false);
  const [uploadPromptId, setUploadPromptId] = useState("");
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef(null);

  const loadNext = async () => {
    setLoading(true);
    setError(null);
    setShowMusicPanel(false);
    setMusicBrief(null);
    setMusicStatus("idle");
    try {
      const res = await fetchPendingVideo();
      if (res.ok && res.video) {
        setVideo(res.video);
      } else {
        setVideo(null);
        setError(res.message || "No pending videos");
      }
    } catch (e) {
      setError(e.message || "Failed to load video");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadNext();
  }, []);

  useEffect(() => {
    const handleKey = async (e) => {
      if (!video || loading || musicWorking) return;

      // If music panel is showing, don't handle video rating keys
      if (showMusicPanel) return;

      let action = null;
      if (e.key === "1") action = "dislike";
      else if (e.key === "2") action = "like";
      else if (e.key === "r" || e.key === "R") action = "regenerate";

      if (!action) return;

      try {
        if (action === "regenerate") {
          await regenerateVideo(video.id);
          setError("Regeneration queued - video will regenerate with new motion");
          setTimeout(loadNext, 2000);
        } else if (action === "dislike") {
          await rateVideo(video.id, "dislike");
          loadNext();
        } else if (action === "like") {
          await rateVideo(video.id, "like");
          setShowMusicPanel(true);
        }
      } catch (e) {
        setError(e.message || "Action failed");
      }
    };

    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [video, loading, showMusicPanel, musicWorking]);

  const handleDislike = async () => {
    try {
      await rateVideo(video.id, "dislike");
      loadNext();
    } catch (e) {
      setError(e.message || "Dislike failed");
    }
  };

  const handleLike = async () => {
    try {
      await rateVideo(video.id, "like");
      setShowMusicPanel(true);
    } catch (e) {
      setError(e.message || "Like failed");
    }
  };

  const handleRegenerate = async () => {
    try {
      await regenerateVideo(video.id);
      setError("Regeneration queued - video will regenerate with new motion");
      setTimeout(loadNext, 2000);
    } catch (e) {
      setError(e.message || "Regenerate failed");
    }
  };

  // Music workflow handlers
  const handleSuggestMusic = async () => {
    setMusicWorking(true);
    setError(null);
    try {
      setMusicStatus("suggesting");
      const res = await suggestMusic(video.id);
      if (res.ok) {
        setMusicBrief(res.music_brief);
        setMusicStatus("suggested");
      } else {
        setError(res.error || "Failed to suggest music");
        setMusicStatus("idle");
      }
    } catch (e) {
      setError(e.message || "Music suggestion failed");
      setMusicStatus("idle");
    } finally {
      setMusicWorking(false);
    }
  };

  const handleGenerateMusic = async () => {
    setMusicWorking(true);
    setError(null);
    try {
      setMusicStatus("generating");
      const res = await generateMusic(video.id);
      if (res.ok) {
        setMusicStatus("generated");
        // Automatically mux after generation
        await handleMuxMusic();
      } else {
        setError(res.error || "Failed to generate music");
        setMusicStatus("suggested");
      }
    } catch (e) {
      setError(e.message || "Music generation failed");
      setMusicStatus("suggested");
    } finally {
      setMusicWorking(false);
    }
  };

  const handleMuxMusic = async () => {
    setMusicWorking(true);
    setError(null);
    try {
      setMusicStatus("muxing");
      const res = await muxMusic(video.id);
      if (res.ok) {
        setMusicStatus("muxed");
        // Update video path to play muxed version
        setVideo({ ...video, video_path: res.video_path });
      } else {
        setError(res.error || "Failed to mux music");
        setMusicStatus("generated");
      }
    } catch (e) {
      setError(e.message || "Music muxing failed");
      setMusicStatus("generated");
    } finally {
      setMusicWorking(false);
    }
  };

  const handleApproveMusic = async () => {
    setMusicWorking(true);
    setError(null);
    try {
      const res = await rateMusic(video.id, "approve");
      if (res.ok) {
        setError("✅ Music approved! Video ready for scheduler.");
        setTimeout(loadNext, 2000);
      } else {
        setError(res.error || "Failed to approve music");
      }
    } catch (e) {
      setError(e.message || "Music approval failed");
    } finally {
      setMusicWorking(false);
    }
  };

  const handleRegenerateMusic = async () => {
    setMusicWorking(true);
    setError(null);
    try {
      const res = await rateMusic(video.id, "regenerate");
      if (res.ok) {
        setMusicBrief(null);
        setMusicStatus("idle");
        setError("Music reset. Try suggesting again for a different style.");
      } else {
        setError(res.error || "Failed to regenerate music");
      }
    } catch (e) {
      setError(e.message || "Music regeneration failed");
    } finally {
      setMusicWorking(false);
    }
  };

  const handleSkipMusic = async () => {
    setMusicWorking(true);
    setError(null);
    try {
      const res = await rateMusic(video.id, "skip");
      if (res.ok) {
        setError("✅ Music skipped. Video ready for scheduler (no music).");
        setTimeout(loadNext, 2000);
      } else {
        setError(res.error || "Failed to skip music");
      }
    } catch (e) {
      setError(e.message || "Music skip failed");
    } finally {
      setMusicWorking(false);
    }
  };

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
      await uploadAsset(file, "video", uploadPromptId.trim());
      setUploadPromptId("");
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
      // Reload to show the newly uploaded video
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

  if (error && !video) {
    return (
      <div style={styles.container}>
        <div style={styles.header}>Video Review</div>

        {/* Upload Section */}
        <div style={styles.uploadSection}>
          <h3 style={styles.uploadTitle}>Upload Video (Manual Workflow)</h3>
          <p style={styles.uploadInstructions}>
            Upload manually generated videos (6s, 9:16). Requires Prompt ID from Prompt Lab.
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
              accept="video/mp4,video/mov"
              onChange={handleUpload}
              disabled={uploading || !uploadPromptId.trim()}
              style={styles.fileInput}
            />
            {uploading && <div style={styles.uploadingText}>Uploading & validating...</div>}
          </div>
        </div>

        <div style={styles.error}>{error || "No videos available"}</div>
      </div>
    );
  }

  return (
    <div style={styles.container}>
      <div style={styles.header}>Video Review</div>

      {/* Upload Section */}
      <div style={styles.uploadSection}>
        <h3 style={styles.uploadTitle}>Upload New Video</h3>
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
            accept="video/mp4,video/mov"
            onChange={handleUpload}
            disabled={uploading || !uploadPromptId.trim()}
            style={styles.fileInput}
          />
        </div>
        {uploading && <div style={styles.uploadingText}>Uploading...</div>}
      </div>

      {error && <div style={styles.errorBanner}>{error}</div>}

      <div style={styles.videoContainer}>
        <video
          key={video.id + "_" + musicStatus}
          src={`/${video.video_path}`}
          autoPlay
          loop
          muted
          controls
          style={styles.video}
        />
      </div>

      {!showMusicPanel ? (
        <>
          <div style={styles.controls}>
            <button style={styles.button} onClick={handleDislike}>
              [1] Dislike
            </button>
            <button style={styles.button} onClick={handleLike}>
              [2] Like
            </button>
            <button style={styles.buttonAlt} onClick={handleRegenerate}>
              [R] Regenerate
            </button>
          </div>

          <div style={styles.meta}>
            <div style={styles.metaLine}>
              <strong>Motion:</strong> {video.video_meta?.motion_prompt || "N/A"}
            </div>
            <div style={styles.metaLine}>
              <strong>Duration:</strong> {video.video_meta?.duration_s || "N/A"}s
            </div>
            <div style={styles.metaLine}>
              <strong>Regenerations:</strong> {video.video_meta?.regeneration_count || 0}
            </div>
            <div style={styles.metaLine}>
              <strong>ID:</strong> {video.id?.slice(0, 8) || "N/A"}
            </div>
          </div>
        </>
      ) : (
        <>
          {/* Music Review Panel */}
          <div style={styles.musicPanel}>
            <div style={styles.musicPanelHeader}>🎵 Music Review</div>

            {musicStatus === "idle" && (
              <div style={styles.musicStep}>
                <div style={styles.musicStepTitle}>Step 1: Suggest Music</div>
                <div style={styles.musicStepDesc}>
                  Generate a music brief using Grok based on the video's visual style and motion.
                </div>
                <button
                  style={styles.buttonPrimary}
                  onClick={handleSuggestMusic}
                  disabled={musicWorking}
                >
                  {musicWorking ? "Suggesting..." : "Suggest Music"}
                </button>
              </div>
            )}

            {musicStatus === "suggesting" && (
              <div style={styles.musicStep}>
                <div style={styles.musicStepTitle}>Generating music brief...</div>
                <div style={styles.spinner}>⏳</div>
              </div>
            )}

            {(musicStatus === "suggested" ||
              musicStatus === "generating" ||
              musicStatus === "generated" ||
              musicStatus === "muxing" ||
              musicStatus === "muxed") &&
              musicBrief && (
                <div style={styles.musicStep}>
                  <div style={styles.musicStepTitle}>Music Brief</div>
                  <div style={styles.musicBriefBox}>
                    <div style={styles.musicBriefLine}>
                      <strong>Prompt:</strong> {musicBrief.prompt || musicBrief.brief || "N/A"}
                    </div>
                    <div style={styles.musicBriefLine}>
                      <strong>Style:</strong> {musicBrief.style || "N/A"}
                    </div>
                    <div style={styles.musicBriefLine}>
                      <strong>Mood:</strong> {musicBrief.mood || "N/A"}
                    </div>
                  </div>
                </div>
              )}

            {musicStatus === "suggested" && (
              <div style={styles.musicStep}>
                <div style={styles.musicStepTitle}>Step 2: Generate Audio</div>
                <div style={styles.musicStepDesc}>
                  Use Suno AI to generate a 6-second instrumental track based on this brief.
                </div>
                <button
                  style={styles.buttonPrimary}
                  onClick={handleGenerateMusic}
                  disabled={musicWorking}
                >
                  {musicWorking ? "Generating..." : "Generate Music"}
                </button>
              </div>
            )}

            {(musicStatus === "generating" || musicStatus === "muxing") && (
              <div style={styles.musicStep}>
                <div style={styles.musicStepTitle}>
                  {musicStatus === "generating"
                    ? "Generating audio with Suno..."
                    : "Muxing video with music..."}
                </div>
                <div style={styles.spinner}>⏳ This may take 30-60 seconds</div>
              </div>
            )}

            {musicStatus === "muxed" && (
              <div style={styles.musicStep}>
                <div style={styles.musicStepTitle}>Step 3: Rate the Music</div>
                <div style={styles.musicStepDesc}>
                  Play the video above (with music). Choose an action:
                </div>
                <div style={styles.musicButtonRow}>
                  <button
                    style={styles.buttonSuccess}
                    onClick={handleApproveMusic}
                    disabled={musicWorking}
                  >
                    ✅ Approve
                  </button>
                  <button
                    style={styles.buttonWarning}
                    onClick={handleRegenerateMusic}
                    disabled={musicWorking}
                  >
                    🔄 Regenerate
                  </button>
                  <button
                    style={styles.buttonSecondary}
                    onClick={handleSkipMusic}
                    disabled={musicWorking}
                  >
                    ⏭️ Skip Music
                  </button>
                </div>
              </div>
            )}

            <div style={styles.musicHint}>
              💡 Tip: Approve sends video to scheduler. Regenerate tries a different style. Skip
              sends video without music.
            </div>
          </div>
        </>
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
  videoContainer: {
    width: "100%",
    marginBottom: "16px",
    border: "1px solid #ddd",
    backgroundColor: "#000",
  },
  video: {
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
  buttonAlt: {
    flex: 1,
    padding: "12px",
    backgroundColor: "#666",
    color: "#fff",
    border: "none",
    cursor: "pointer",
    fontSize: "14px",
    fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto",
  },
  buttonPrimary: {
    padding: "12px 24px",
    backgroundColor: "#111",
    color: "#fff",
    border: "none",
    borderRadius: "6px",
    cursor: "pointer",
    fontSize: "14px",
    fontWeight: "500",
  },
  buttonSuccess: {
    flex: 1,
    padding: "12px",
    backgroundColor: "#059669",
    color: "#fff",
    border: "none",
    borderRadius: "6px",
    cursor: "pointer",
    fontSize: "14px",
    fontWeight: "500",
  },
  buttonWarning: {
    flex: 1,
    padding: "12px",
    backgroundColor: "#f59e0b",
    color: "#fff",
    border: "none",
    borderRadius: "6px",
    cursor: "pointer",
    fontSize: "14px",
    fontWeight: "500",
  },
  buttonSecondary: {
    flex: 1,
    padding: "12px",
    backgroundColor: "#6b7280",
    color: "#fff",
    border: "none",
    borderRadius: "6px",
    cursor: "pointer",
    fontSize: "14px",
    fontWeight: "500",
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
  errorBanner: {
    padding: "8px",
    backgroundColor: "#f0f0f0",
    color: "#666",
    marginBottom: "16px",
    fontSize: "14px",
    border: "1px solid #ddd",
  },
  musicPanel: {
    backgroundColor: "#f9fafb",
    border: "1px solid #e5e7eb",
    borderRadius: "8px",
    padding: "24px",
    marginBottom: "16px",
  },
  musicPanelHeader: {
    fontSize: "18px",
    fontWeight: "600",
    marginBottom: "16px",
    color: "#111",
  },
  musicStep: {
    marginBottom: "16px",
  },
  musicStepTitle: {
    fontSize: "14px",
    fontWeight: "600",
    marginBottom: "8px",
    color: "#111",
  },
  musicStepDesc: {
    fontSize: "13px",
    color: "#666",
    marginBottom: "12px",
  },
  musicBriefBox: {
    backgroundColor: "#fff",
    border: "1px solid #e5e7eb",
    borderRadius: "6px",
    padding: "12px",
    marginBottom: "12px",
  },
  musicBriefLine: {
    fontSize: "13px",
    color: "#111",
    marginBottom: "6px",
  },
  musicButtonRow: {
    display: "flex",
    gap: "8px",
  },
  musicHint: {
    fontSize: "12px",
    color: "#666",
    fontStyle: "italic",
    marginTop: "12px",
  },
  spinner: {
    fontSize: "14px",
    color: "#666",
    textAlign: "center",
    padding: "12px",
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
};
