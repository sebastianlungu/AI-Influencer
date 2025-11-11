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
  const [showSocial, setShowSocial] = useState(false);

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
        setShowSocial(false); // Collapse social by default
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
        <h2 style={styles.title}>Prompt Generation</h2>
        <p style={styles.subtitle}>
          Generate image + video motion + social prompts for manual copy/paste to Leonardo & Veo
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
          {loading ? "Generating..." : "Generate Prompt Bundle(s)"}
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

          {/* Image Prompt Section */}
          <div style={styles.promptSection}>
            <div style={styles.promptHeader}>
              <h4 style={styles.sectionTitle}>📷 IMAGE PROMPT (864×1536, native 9:16, no upscale)</h4>
              {(() => {
                const charCount = selectedBundle.image_prompt.final_prompt.length;
                const remaining = 1500 - charCount;
                const getColor = () => {
                  if (charCount > 1400) return '#c00';
                  if (charCount > 1100) return '#f80';
                  return '#080';
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

          {/* Video Motion Brief Section */}
          <div style={styles.promptSection}>
            <h4 style={styles.sectionTitle}>🎬 VIDEO MOTION BRIEF (6s, single subtle move)</h4>
            <div style={styles.videoPromptDetails}>
              <p><strong>Camera Motion:</strong> {selectedBundle.video_prompt.motion}</p>
              <p><strong>Character Action:</strong> {selectedBundle.video_prompt.character_action}</p>
              <p><strong>Environment:</strong> {selectedBundle.video_prompt.environment}</p>
              {selectedBundle.video_prompt.notes && (
                <p><strong>Notes:</strong> {selectedBundle.video_prompt.notes}</p>
              )}
            </div>
            <button
              onClick={() =>
                copyToClipboard(
                  `Motion: ${selectedBundle.video_prompt.motion}\nCharacter: ${selectedBundle.video_prompt.character_action}\nEnvironment: ${selectedBundle.video_prompt.environment}${selectedBundle.video_prompt.notes ? '\nNotes: ' + selectedBundle.video_prompt.notes : ''}`
                )
              }
              style={styles.copyButton}
            >
              Copy Video Motion Brief
            </button>
          </div>

          {/* Social Meta Section (Collapsible) */}
          <div style={styles.promptSection}>
            <div style={styles.socialHeader}>
              <h4 style={styles.sectionTitle}>📱 SOCIAL META (optional)</h4>
              <button
                onClick={() => setShowSocial(!showSocial)}
                style={styles.toggleButton}
              >
                {showSocial ? "Hide" : "Show"}
              </button>
            </div>
            {showSocial && selectedBundle.social_meta && (
              <>
                <div style={styles.socialDetails}>
                  <p><strong>Title:</strong> {selectedBundle.social_meta.title}</p>
                  <p><strong>Tags:</strong> {selectedBundle.social_meta.tags?.join(", ")}</p>
                  <p><strong>Hashtags:</strong> {selectedBundle.social_meta.hashtags?.join(" ")}</p>
                </div>
                <button
                  onClick={() =>
                    copyToClipboard(
                      `Title: ${selectedBundle.social_meta.title}\nTags: ${selectedBundle.social_meta.tags?.join(", ")}\nHashtags: ${selectedBundle.social_meta.hashtags?.join(" ")}`
                    )
                  }
                  style={styles.copyButton}
                >
                  Copy Social Meta
                </button>
              </>
            )}
          </div>

          <div style={styles.instructions}>
            <h4 style={styles.instructionsTitle}>Next Steps:</h4>
            <ol style={styles.instructionsList}>
              <li>Copy the <strong>Image Prompt</strong> above</li>
              <li>Paste into Leonardo.ai (Vision XL model, 864×1536, native 9:16)</li>
              <li>Download generated image (save as <code>{selectedBundle.id}_image.png</code>)</li>
              <li>Copy the <strong>Video Motion Brief</strong> above</li>
              <li>Upload image to Veo 3 with motion prompt (6s duration)</li>
              <li>Download generated video (save as <code>{selectedBundle.id}_video.mp4</code>)</li>
              <li>(Optional) Use Social Meta for posting manually</li>
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
              onClick={() => { setSelectedBundle(prompt); setShowSocial(false); }}
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
    padding: "10px 20px",
    backgroundColor: "#111",
    color: "#fff",
    border: "none",
    borderRadius: "4px",
    fontSize: "14px",
    fontWeight: "600",
    cursor: "pointer",
  },
  buttonDisabled: {
    padding: "10px 20px",
    backgroundColor: "#ccc",
    color: "#999",
    border: "none",
    borderRadius: "4px",
    fontSize: "14px",
    fontWeight: "600",
    cursor: "not-allowed",
  },
  bundleDisplay: {
    backgroundColor: "#fff",
    border: "2px solid #111",
    borderRadius: "8px",
    padding: "24px",
    marginBottom: "24px",
  },
  bundleHeader: {
    marginBottom: "24px",
    paddingBottom: "16px",
    borderBottom: "2px solid #eee",
  },
  bundleTitle: {
    fontSize: "20px",
    fontWeight: "700",
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
    fontSize: "16px",
    fontWeight: "600",
    margin: "0",
    color: "#111",
  },
  promptHeader: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: "12px",
  },
  charCount: {
    fontSize: "12px",
    fontWeight: "600",
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
    maxHeight: "200px",
    overflowY: "auto",
  },
  videoPromptDetails: {
    padding: "16px",
    backgroundColor: "#f9f9f9",
    border: "1px solid #ddd",
    borderRadius: "4px",
    marginTop: "12px",
    marginBottom: "12px",
  },
  socialHeader: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: "12px",
  },
  toggleButton: {
    padding: "4px 12px",
    backgroundColor: "#e9e9e9",
    border: "1px solid #ccc",
    borderRadius: "4px",
    fontSize: "12px",
    cursor: "pointer",
  },
  socialDetails: {
    padding: "16px",
    backgroundColor: "#f9f9f9",
    border: "1px solid #ddd",
    borderRadius: "4px",
    marginBottom: "12px",
  },
  instructions: {
    padding: "16px",
    backgroundColor: "#f0f8ff",
    border: "2px solid #0066cc",
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
