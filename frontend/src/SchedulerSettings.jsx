import { useEffect, useState } from "react";
import { fetchHealth, schedulerRunOnce, schedulerDryRun, fetchApprovedVideos } from "./api";

export default function SchedulerSettings() {
  const [config, setConfig] = useState(null);
  const [approvedCount, setApprovedCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [message, setMessage] = useState(null);
  const [dryRunResult, setDryRunResult] = useState(null);

  const loadConfig = async () => {
    setLoading(true);
    setError(null);
    try {
      const health = await fetchHealth();
      setConfig(health);

      // Fetch approved videos count
      const approved = await fetchApprovedVideos();
      setApprovedCount(approved.videos?.length || 0);
    } catch (e) {
      setError(e.message || "Failed to load configuration");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadConfig();
  }, []);

  const handleRunOnce = async () => {
    setMessage(null);
    setError(null);
    setDryRunResult(null);
    try {
      const result = await schedulerRunOnce();
      if (result.ok) {
        setMessage(
          result.posted === 1
            ? `✅ Successfully posted video ${result.video_id} to ${result.platform} (ID: ${result.post_id})`
            : result.skipped_window
            ? "⏰ Outside posting window - no video posted"
            : "ℹ️ No approved videos available to post"
        );
        loadConfig(); // Refresh counts
      } else {
        setError(result.error || "Posting failed");
      }
    } catch (e) {
      setError(e.message || "Run-once execution failed");
    }
  };

  const handleDryRun = async () => {
    setMessage(null);
    setError(null);
    setDryRunResult(null);
    try {
      const result = await schedulerDryRun();
      setDryRunResult(result);
    } catch (e) {
      setError(e.message || "Dry-run execution failed");
    }
  };

  if (loading) {
    return (
      <div style={styles.container}>
        <div style={styles.header}>Loading Scheduler Configuration...</div>
      </div>
    );
  }

  if (!config) {
    return (
      <div style={styles.container}>
        <div style={styles.header}>Scheduler Settings</div>
        <div style={styles.error}>{error || "Failed to load configuration"}</div>
      </div>
    );
  }

  const schedulerEnabled = config.scheduler_enabled || false;
  const providers = config.providers || {};
  const schedulerConfig = config.scheduler_config || {};

  return (
    <div style={styles.container}>
      <div style={styles.header}>Scheduler Settings</div>

      {message && <div style={styles.success}>{message}</div>}
      {error && <div style={styles.error}>{error}</div>}

      {/* Scheduler Status */}
      <div style={styles.section}>
        <div style={styles.sectionTitle}>Scheduler Status</div>
        <div style={styles.statusRow}>
          <span style={styles.label}>Enabled:</span>
          <span style={schedulerEnabled ? styles.statusEnabled : styles.statusDisabled}>
            {schedulerEnabled ? "✅ YES" : "❌ NO"}
          </span>
        </div>
        {!schedulerEnabled && (
          <div style={styles.hint}>
            Set <code>ENABLE_SCHEDULER=true</code> in .env to enable automated posting
          </div>
        )}
      </div>

      {/* Posting Configuration */}
      <div style={styles.section}>
        <div style={styles.sectionTitle}>Posting Configuration</div>
        <div style={styles.configGrid}>
          <div style={styles.configRow}>
            <span style={styles.label}>Platform:</span>
            <span style={styles.value}>{schedulerConfig.platform || "tiktok"}</span>
          </div>
          <div style={styles.configRow}>
            <span style={styles.label}>Cron Schedule:</span>
            <span style={styles.value}>{schedulerConfig.cron || "*/20 minutes"}</span>
          </div>
          <div style={styles.configRow}>
            <span style={styles.label}>Posting Window:</span>
            <span style={styles.value}>{schedulerConfig.window || "09:00-21:00"}</span>
          </div>
          <div style={styles.configRow}>
            <span style={styles.label}>Timezone:</span>
            <span style={styles.value}>{schedulerConfig.timezone || "Europe/Paris"}</span>
          </div>
        </div>
      </div>

      {/* Platform Readiness */}
      <div style={styles.section}>
        <div style={styles.sectionTitle}>Platform Readiness</div>
        <div style={styles.platformGrid}>
          <div style={styles.platformRow}>
            <span style={styles.label}>Grok (Prompting):</span>
            <span
              style={
                providers.grok === "configured" ? styles.statusEnabled : styles.statusDisabled
              }
            >
              {providers.grok === "configured" ? "✅ Configured" : "❌ Not Configured"}
            </span>
          </div>
          <div style={styles.platformRow}>
            <span style={styles.label}>Suno (Music):</span>
            <span
              style={
                providers.suno === "configured" ? styles.statusEnabled : styles.statusDisabled
              }
            >
              {providers.suno === "configured" ? "✅ Configured" : "❌ Not Configured"}
            </span>
          </div>
          <div style={styles.platformRow}>
            <span style={styles.label}>TikTok:</span>
            <span
              style={
                providers.tiktok === "configured" ? styles.statusEnabled : styles.statusDisabled
              }
            >
              {providers.tiktok === "configured" ? "✅ Configured" : "❌ Not Configured"}
            </span>
          </div>
          <div style={styles.platformRow}>
            <span style={styles.label}>Instagram:</span>
            <span
              style={
                providers.instagram === "configured"
                  ? styles.statusEnabled
                  : styles.statusDisabled
              }
            >
              {providers.instagram === "configured" ? "✅ Configured" : "❌ Not Configured"}
            </span>
          </div>
        </div>
      </div>

      {/* Queue Status */}
      <div style={styles.section}>
        <div style={styles.sectionTitle}>Queue Status</div>
        <div style={styles.queueRow}>
          <span style={styles.label}>Approved Videos:</span>
          <span style={styles.queueCount}>{approvedCount}</span>
        </div>
      </div>

      {/* Dry Run Result */}
      {dryRunResult && (
        <div style={styles.section}>
          <div style={styles.sectionTitle}>Dry Run Preview</div>
          <div style={styles.dryRunBox}>
            <div style={styles.dryRunMessage}>{dryRunResult.message}</div>
            {dryRunResult.video && (
              <div style={styles.dryRunVideo}>
                <div style={styles.dryRunRow}>
                  <span style={styles.label}>Video ID:</span>
                  <span style={styles.value}>{dryRunResult.video.id}</span>
                </div>
                <div style={styles.dryRunRow}>
                  <span style={styles.label}>Created:</span>
                  <span style={styles.value}>
                    {new Date(dryRunResult.video.created_at).toLocaleString()}
                  </span>
                </div>
                <div style={styles.dryRunRow}>
                  <span style={styles.label}>Has Social Meta:</span>
                  <span style={styles.value}>
                    {dryRunResult.video.has_social_meta ? "Yes" : "No (will generate)"}
                  </span>
                </div>
              </div>
            )}
            <div style={styles.dryRunRow}>
              <span style={styles.label}>Window Active:</span>
              <span style={dryRunResult.window_active ? styles.statusEnabled : styles.statusDisabled}>
                {dryRunResult.window_active ? "✅ Yes" : "❌ No"}
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Manual Controls */}
      <div style={styles.section}>
        <div style={styles.sectionTitle}>Manual Controls</div>
        <div style={styles.buttonRow}>
          <button style={styles.buttonPrimary} onClick={handleRunOnce}>
            Run Once (Live)
          </button>
          <button style={styles.buttonSecondary} onClick={handleDryRun}>
            Dry Run (Preview)
          </button>
          <button style={styles.buttonSecondary} onClick={loadConfig}>
            Refresh
          </button>
        </div>
        <div style={styles.hint}>
          ⚠️ "Run Once" requires <code>ALLOW_LIVE=true</code>
        </div>
      </div>
    </div>
  );
}

const styles = {
  container: {
    padding: "32px",
    maxWidth: "900px",
    margin: "0 auto",
  },
  header: {
    fontSize: "24px",
    fontWeight: "600",
    marginBottom: "32px",
    color: "#111",
    fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto",
  },
  section: {
    backgroundColor: "#fff",
    border: "1px solid #e0e0e0",
    borderRadius: "8px",
    padding: "24px",
    marginBottom: "24px",
  },
  sectionTitle: {
    fontSize: "16px",
    fontWeight: "600",
    marginBottom: "16px",
    color: "#111",
    borderBottom: "2px solid #f0f0f0",
    paddingBottom: "8px",
  },
  statusRow: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: "8px",
  },
  configGrid: {
    display: "flex",
    flexDirection: "column",
    gap: "12px",
  },
  configRow: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
  },
  platformGrid: {
    display: "flex",
    flexDirection: "column",
    gap: "12px",
  },
  platformRow: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
  },
  queueRow: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
  },
  queueCount: {
    fontSize: "24px",
    fontWeight: "600",
    color: "#111",
  },
  label: {
    fontSize: "14px",
    color: "#666",
    fontWeight: "400",
  },
  value: {
    fontSize: "14px",
    color: "#111",
    fontWeight: "500",
    fontFamily: "'Courier New', monospace",
  },
  statusEnabled: {
    fontSize: "14px",
    color: "#059669",
    fontWeight: "500",
  },
  statusDisabled: {
    fontSize: "14px",
    color: "#dc2626",
    fontWeight: "500",
  },
  hint: {
    fontSize: "12px",
    color: "#666",
    marginTop: "8px",
    fontStyle: "italic",
  },
  dryRunBox: {
    backgroundColor: "#f9fafb",
    border: "1px solid #e5e7eb",
    borderRadius: "6px",
    padding: "16px",
  },
  dryRunMessage: {
    fontSize: "14px",
    color: "#111",
    marginBottom: "12px",
    fontWeight: "500",
  },
  dryRunVideo: {
    backgroundColor: "#fff",
    border: "1px solid #e5e7eb",
    borderRadius: "4px",
    padding: "12px",
    marginBottom: "12px",
  },
  dryRunRow: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: "8px",
  },
  buttonRow: {
    display: "flex",
    gap: "12px",
    marginBottom: "12px",
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
    fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto",
  },
  buttonSecondary: {
    padding: "12px 24px",
    backgroundColor: "#fff",
    color: "#111",
    border: "1px solid #e0e0e0",
    borderRadius: "6px",
    cursor: "pointer",
    fontSize: "14px",
    fontWeight: "500",
    fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto",
  },
  success: {
    backgroundColor: "#d1fae5",
    color: "#065f46",
    padding: "12px 16px",
    borderRadius: "6px",
    marginBottom: "16px",
    fontSize: "14px",
    border: "1px solid #6ee7b7",
  },
  error: {
    backgroundColor: "#fee2e2",
    color: "#991b1b",
    padding: "12px 16px",
    borderRadius: "6px",
    marginBottom: "16px",
    fontSize: "14px",
    border: "1px solid #fca5a5",
  },
};
