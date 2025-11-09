import { useState, useEffect } from "react";
import { generatePromptBundle, getRecentPrompts } from "./api";

export default function PromptLab() {
  const [setting, setSetting] = useState("");
  const [seedWords, setSeedWords] = useState("");
  const [count, setCount] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [recentPrompts, setRecentPrompts] = useState([]);
  const [selectedBundle, setSelectedBundle] = useState(null);

  // Load recent prompts on mount
  useEffect(() => {
    loadRecentPrompts();
  }, []);

  const loadRecentPrompts = async () => {
    try {
      const data = await getRecentPrompts(20);
      setRecentPrompts(data.prompts || []);
    } catch (err) {
      console.error("Failed to load recent prompts:", err);
    }
  };

  const handleGenerate = async () => {
    if (!setting.trim()) {
      setError("Setting is required");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const seedWordsArray = seedWords
        .split(",")
        .map((w) => w.trim())
        .filter((w) => w.length > 0);

      const data = await generatePromptBundle({
        setting: setting.trim(),
        seed_words: seedWordsArray.length > 0 ? seedWordsArray : null,
        count,
      });

      // Select first bundle for display
      if (data.bundles && data.bundles.length > 0) {
        setSelectedBundle(data.bundles[0]);
      }

      // Reload recent prompts
      await loadRecentPrompts();

      // Clear form
      setSetting("");
      setSeedWords("");
      setCount(1);
    } catch (err) {
      setError(err.message || "Failed to generate prompts");
    } finally {
      setLoading(false);
    }
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
  };

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <h2 style={styles.title}>Prompt Lab</h2>
        <p style={styles.subtitle}>
          Generate image & video prompt pairs for manual generation workflow
        </p>
      </div>

      <div style={styles.form}>
        <div style={styles.formGroup}>
          <label style={styles.label}>Setting (required)</label>
          <input
            type="text"
            value={setting}
            onChange={(e) => setSetting(e.target.value)}
            placeholder="e.g., Japan, Santorini, Tokyo rooftop"
            style={styles.input}
          />
        </div>

        <div style={styles.formGroup}>
          <label style={styles.label}>Seed Words (optional, comma-separated)</label>
          <input
            type="text"
            value={seedWords}
            onChange={(e) => setSeedWords(e.target.value)}
            placeholder="e.g., dojo, dusk, sunrise"
            style={styles.input}
          />
        </div>

        <div style={styles.formGroup}>
          <label style={styles.label}>Count (1-5)</label>
          <input
            type="number"
            value={count}
            onChange={(e) => setCount(Math.max(1, Math.min(5, parseInt(e.target.value) || 1)))}
            min="1"
            max="5"
            style={styles.inputSmall}
          />
        </div>

        {error && <div style={styles.error}>{error}</div>}

        <button
          onClick={handleGenerate}
          disabled={loading || !setting.trim()}
          style={loading ? styles.buttonDisabled : styles.button}
        >
          {loading ? "Generating..." : "Generate Prompt Pair(s)"}
        </button>
      </div>

      {selectedBundle && (
        <div style={styles.bundleDisplay}>
          <div style={styles.bundleHeader}>
            <h3 style={styles.bundleTitle}>Generated Prompt Bundle</h3>
            <div style={styles.promptId}>
              ID: <code style={styles.code}>{selectedBundle.id}</code>
              <button
                onClick={() => copyToClipboard(selectedBundle.id)}
                style={styles.copyButton}
              >
                Copy ID
              </button>
            </div>
          </div>

          <div style={styles.promptSection}>
            <div style={styles.promptHeader}>
              <h4 style={styles.sectionTitle}>Image Prompt (864×1536)</h4>
              {(() => {
                const charCount = selectedBundle.image_prompt.final_prompt.length;
                const remaining = 1500 - charCount;
                const getColor = () => {
                  if (charCount > 1400) return '#c00';  // Red: exceeds safe zone
                  if (charCount > 1100) return '#f80';  // Orange: above target
                  return '#080';                         // Green: within target (900-1100)
                };
                return (
                  <span style={{ ...styles.charCount, color: getColor() }}>
                    {charCount} chars ({remaining > 0 ? remaining : 0} remaining)
                  </span>
                );
              })()}
            </div>
            <pre style={styles.promptBox}>
              {selectedBundle.image_prompt.final_prompt}
            </pre>
            <button
              onClick={() => copyToClipboard(selectedBundle.image_prompt.final_prompt)}
              style={styles.copyButton}
            >
              Copy Image Prompt
            </button>
          </div>

          <div style={styles.promptSection}>
            <h4 style={styles.sectionTitle}>Video Prompt (6s, 9:16)</h4>
            <div style={styles.videoPromptDetails}>
              <p>
                <strong>Motion:</strong> {selectedBundle.video_prompt.motion}
              </p>
              <p>
                <strong>Character Action:</strong> {selectedBundle.video_prompt.character_action}
              </p>
              <p>
                <strong>Environment:</strong> {selectedBundle.video_prompt.environment}
              </p>
              <p>
                <strong>Notes:</strong> {selectedBundle.video_prompt.notes}
              </p>
            </div>
            <button
              onClick={() =>
                copyToClipboard(
                  `Motion: ${selectedBundle.video_prompt.motion}\nCharacter: ${selectedBundle.video_prompt.character_action}\nEnvironment: ${selectedBundle.video_prompt.environment}\nNotes: ${selectedBundle.video_prompt.notes}`
                )
              }
              style={styles.copyButton}
            >
              Copy Video Prompt
            </button>
          </div>

          <div style={styles.instructions}>
            <h4 style={styles.instructionsTitle}>Next Steps:</h4>
            <ol style={styles.instructionsList}>
              <li>Copy the Prompt ID above</li>
              <li>Rename your generated files: <code>{selectedBundle.id}_image.png</code>, <code>{selectedBundle.id}_video.mp4</code></li>
              <li>Generate image in Leonardo using the Image Prompt</li>
              <li>Generate video in Veo using the Video Prompt</li>
              <li>Upload via Image/Video Review tabs using the Prompt ID</li>
            </ol>
          </div>
        </div>
      )}

      <div style={styles.recentSection}>
        <h3 style={styles.recentTitle}>Recent Prompts (Last 20)</h3>
        <div style={styles.recentList}>
          {recentPrompts.length === 0 && (
            <p style={styles.emptyMessage}>No prompts generated yet</p>
          )}
          {recentPrompts.map((prompt) => (
            <div
              key={prompt.id}
              style={styles.recentItem}
              onClick={() => setSelectedBundle(prompt)}
            >
              <div style={styles.recentHeader}>
                <code style={styles.recentId}>{prompt.id}</code>
                <span style={styles.recentTimestamp}>
                  {new Date(prompt.timestamp).toLocaleString()}
                </span>
              </div>
              <div style={styles.recentMeta}>
                <span style={styles.recentSetting}>{prompt.setting}</span>
                {prompt.seed_words && prompt.seed_words.length > 0 && (
                  <span style={styles.recentSeeds}>
                    + {prompt.seed_words.join(", ")}
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

const styles = {
  container: {
    padding: "16px",
    maxWidth: "1200px",
    margin: "0 auto",
  },
  header: {
    marginBottom: "16px",
  },
  title: {
    fontSize: "22px",
    fontWeight: "600",
    margin: "0 0 8px 0",
    color: "#111",
  },
  subtitle: {
    fontSize: "14px",
    color: "#666",
    margin: "0",
  },
  form: {
    backgroundColor: "#fff",
    border: "1px solid #ddd",
    borderRadius: "8px",
    padding: "16px",
    marginBottom: "16px",
  },
  formGroup: {
    marginBottom: "12px",
  },
  label: {
    display: "block",
    fontSize: "13px",
    fontWeight: "500",
    color: "#333",
    marginBottom: "6px",
  },
  input: {
    width: "100%",
    padding: "10px 12px",
    fontSize: "14px",
    border: "1px solid #ccc",
    borderRadius: "4px",
    fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto",
  },
  inputSmall: {
    width: "100px",
    padding: "10px 12px",
    fontSize: "14px",
    border: "1px solid #ccc",
    borderRadius: "4px",
    fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto",
  },
  error: {
    padding: "12px",
    backgroundColor: "#fee",
    border: "1px solid #fcc",
    borderRadius: "4px",
    color: "#c00",
    fontSize: "13px",
    marginBottom: "16px",
  },
  button: {
    padding: "8px 16px",
    backgroundColor: "#111",
    color: "#fff",
    border: "none",
    borderRadius: "4px",
    fontSize: "14px",
    fontWeight: "500",
    cursor: "pointer",
  },
  buttonDisabled: {
    padding: "8px 16px",
    backgroundColor: "#ccc",
    color: "#999",
    border: "none",
    borderRadius: "4px",
    fontSize: "14px",
    fontWeight: "500",
    cursor: "not-allowed",
  },
  bundleDisplay: {
    backgroundColor: "#fff",
    border: "1px solid #ddd",
    borderRadius: "8px",
    padding: "24px",
    marginBottom: "24px",
  },
  bundleHeader: {
    marginBottom: "24px",
    paddingBottom: "16px",
    borderBottom: "1px solid #eee",
  },
  bundleTitle: {
    fontSize: "18px",
    fontWeight: "600",
    margin: "0 0 12px 0",
    color: "#111",
  },
  promptId: {
    display: "flex",
    alignItems: "center",
    gap: "12px",
    fontSize: "14px",
    color: "#666",
  },
  code: {
    padding: "4px 8px",
    backgroundColor: "#f5f5f5",
    border: "1px solid #ddd",
    borderRadius: "3px",
    fontFamily: "monospace",
    fontSize: "13px",
    color: "#111",
  },
  copyButton: {
    padding: "6px 12px",
    backgroundColor: "#f5f5f5",
    color: "#333",
    border: "1px solid #ccc",
    borderRadius: "4px",
    fontSize: "12px",
    cursor: "pointer",
    fontWeight: "500",
  },
  promptSection: {
    marginBottom: "24px",
  },
  sectionTitle: {
    fontSize: "15px",
    fontWeight: "600",
    margin: "0",
    color: "#333",
  },
  promptHeader: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: "12px",
  },
  charCount: {
    fontSize: "12px",
    fontWeight: "500",
    fontFamily: "monospace",
  },
  promptBox: {
    padding: "16px",
    backgroundColor: "#f9f9f9",
    border: "1px solid #ddd",
    borderRadius: "4px",
    fontSize: "13px",
    lineHeight: "1.6",
    fontFamily: "monospace",
    whiteSpace: "pre-wrap",
    wordWrap: "break-word",
    marginBottom: "12px",
    maxHeight: "150px",
    overflowY: "auto",
  },
  videoPromptDetails: {
    padding: "16px",
    backgroundColor: "#f9f9f9",
    border: "1px solid #ddd",
    borderRadius: "4px",
    marginBottom: "12px",
  },
  instructions: {
    padding: "16px",
    backgroundColor: "#f0f8ff",
    border: "1px solid #cce",
    borderRadius: "4px",
  },
  instructionsTitle: {
    fontSize: "14px",
    fontWeight: "600",
    margin: "0 0 12px 0",
    color: "#0066cc",
  },
  instructionsList: {
    margin: "0",
    paddingLeft: "20px",
    fontSize: "13px",
    lineHeight: "1.8",
    color: "#333",
  },
  recentSection: {
    backgroundColor: "#fff",
    border: "1px solid #ddd",
    borderRadius: "8px",
    padding: "24px",
  },
  recentTitle: {
    fontSize: "18px",
    fontWeight: "600",
    margin: "0 0 16px 0",
    color: "#111",
  },
  recentList: {
    display: "flex",
    flexDirection: "column",
    gap: "8px",
  },
  emptyMessage: {
    fontSize: "14px",
    color: "#999",
    textAlign: "center",
    padding: "24px",
  },
  recentItem: {
    padding: "12px",
    backgroundColor: "#f9f9f9",
    border: "1px solid #eee",
    borderRadius: "4px",
    cursor: "pointer",
    transition: "background-color 0.2s",
  },
  recentHeader: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: "6px",
  },
  recentId: {
    fontFamily: "monospace",
    fontSize: "12px",
    color: "#666",
  },
  recentTimestamp: {
    fontSize: "11px",
    color: "#999",
  },
  recentMeta: {
    display: "flex",
    gap: "12px",
    fontSize: "13px",
  },
  recentSetting: {
    fontWeight: "500",
    color: "#333",
  },
  recentSeeds: {
    color: "#666",
    fontStyle: "italic",
  },
};
