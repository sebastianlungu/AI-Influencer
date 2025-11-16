import { useState, useEffect, Fragment, useMemo } from "react";
import {
  generatePromptBundle,
  getPrompts,
  getPromptBundle,
  getLocations,
  updatePromptState
} from "./api";

const RECENT_LOCATIONS_KEY = "plab_recent_locations";
const MAX_RECENT = 5;

export default function PromptLab({ onShowLogs }) {
  // Form state
  const [selectedLocationId, setSelectedLocationId] = useState("");
  const [count, setCount] = useState(1);
  const [locations, setLocations] = useState([]);
  const [locationsLoading, setLocationsLoading] = useState(true);
  const [locationsError, setLocationsError] = useState(null);
  const [recentLocationIds, setRecentLocationIds] = useState([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Binding toggles
  const [bindScene, setBindScene] = useState(true);
  const [bindPose, setBindPose] = useState(true);
  const [bindLighting, setBindLighting] = useState(true);
  const [bindCamera, setBindCamera] = useState(true);
  const [bindAngle, setBindAngle] = useState(true);
  const [bindAccessories, setBindAccessories] = useState(true);
  const [bindWardrobe, setBindWardrobe] = useState(true);
  const [bindHair, setBindHair] = useState(true);
  const [singleAccessory, setSingleAccessory] = useState(true);

  // Table state
  const [prompts, setPrompts] = useState([]);
  const [totalPrompts, setTotalPrompts] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [statusFilter, setStatusFilter] = useState("all");
  const [searchFilter, setSearchFilter] = useState("");
  const [sortField, setSortField] = useState("-created_at");
  const [sortDir, setSortDir] = useState("desc"); // 'asc' | 'desc'

  // Drawer state
  const [selectedPromptId, setSelectedPromptId] = useState(null);
  const [promptDetails, setPromptDetails] = useState(null);
  const [drawerLoading, setDrawerLoading] = useState(false);

  // Toast state
  const [toast, setToast] = useState({ show: false, message: "" });

  // Load initial data
  useEffect(() => {
    loadLocations();
    loadRecentLocationIds();
    loadPrompts();
  }, []);

  // Reload prompts when filters change
  useEffect(() => {
    loadPrompts();
  }, [statusFilter, searchFilter]);

  const loadLocations = async () => {
    try {
      setLocationsLoading(true);
      const data = await getLocations();
      setLocations(data.locations || []);
      setLocationsError(null);
    } catch (err) {
      console.error("Failed to load locations:", err);
      setLocationsError(err.message || "Failed to load locations");
    } finally {
      setLocationsLoading(false);
    }
  };

  const loadRecentLocationIds = () => {
    try {
      const stored = localStorage.getItem(RECENT_LOCATIONS_KEY);
      if (stored) {
        setRecentLocationIds(JSON.parse(stored));
      }
    } catch (err) {
      console.error("Failed to load recent locations:", err);
    }
  };

  const saveRecentLocationId = (locationId) => {
    try {
      let recent = [...recentLocationIds];
      recent = recent.filter((id) => id !== locationId);
      recent.unshift(locationId);
      recent = recent.slice(0, MAX_RECENT);
      setRecentLocationIds(recent);
      localStorage.setItem(RECENT_LOCATIONS_KEY, JSON.stringify(recent));
    } catch (err) {
      console.error("Failed to save recent location:", err);
    }
  };

  const loadPrompts = async () => {
    try {
      const data = await getPrompts({
        status: statusFilter,
        search: searchFilter,
        fetch_all: "true",  // Fetch all prompts (no pagination)
        order: "created_desc",  // Newest first
      });
      setPrompts(data.items || []);
      setTotalPrompts(data.total || 0);
    } catch (err) {
      console.error("Failed to load prompts:", err);
    }
  };

  const loadPromptDetails = async (promptId) => {
    try {
      setDrawerLoading(true);
      const data = await getPromptBundle(promptId);
      setPromptDetails(data.bundle);
    } catch (err) {
      console.error("Failed to load prompt details:", err);
      showToast("Failed to load details");
    } finally {
      setDrawerLoading(false);
    }
  };

  const setAllBindOn = () => {
    setBindScene(true);
    setBindPose(true);
    setBindLighting(true);
    setBindCamera(true);
    setBindAngle(true);
    setBindAccessories(true);
    setBindWardrobe(true);
    setBindHair(true);
    setSingleAccessory(true);
  };

  const setAllBindOff = () => {
    setBindScene(false);
    setBindPose(false);
    setBindLighting(false);
    setBindCamera(false);
    setBindAngle(false);
    setBindAccessories(false);
    setBindWardrobe(false);
    setBindHair(false);
    setSingleAccessory(false);
  };

  const handleGenerate = async () => {
    if (!selectedLocationId) {
      setError("Location is required");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      await generatePromptBundle({
        setting_id: selectedLocationId,
        seed_words: null,
        count,
        bind_scene: bindScene,
        bind_pose_microaction: bindPose,
        bind_lighting: bindLighting,
        bind_camera: bindCamera,
        bind_angle: bindAngle,
        bind_accessories: bindAccessories,
        bind_wardrobe: bindWardrobe,
        bind_hair: bindHair,
        single_accessory: singleAccessory,
      });

      saveRecentLocationId(selectedLocationId);
      setCount(1);

      // Reload prompts
      await loadPrompts();
      showToast("Prompts generated!");
    } catch (err) {
      setError(err.message || "Failed to generate prompts");
      onShowLogs?.(); // Auto-open logs when generation fails
    } finally {
      setLoading(false);
    }
  };

  const handleUsedToggle = async (promptId, newValue) => {
    try {
      await updatePromptState(promptId, newValue);
      await loadPrompts();
      if (selectedPromptId === promptId) {
        await loadPromptDetails(promptId);
      }
      showToast(newValue ? "Marked as used" : "Marked as unused");
    } catch (err) {
      console.error("Failed to update state:", err);
      showToast("Failed to update");
    }
  };

  const showToast = (message) => {
    setToast({ show: true, message });
    setTimeout(() => setToast({ show: false, message: "" }), 1200);
  };

  const copyToClipboard = async (text, label = "Copied") => {
    try {
      await navigator.clipboard.writeText(text);
      showToast(label);
    } catch (err) {
      console.error("Failed to copy:", err);
      showToast("Failed to copy");
    }
  };

  const handleRowClick = (promptId) => {
    // Toggle: if same row clicked, close; otherwise open new
    if (selectedPromptId === promptId) {
      setSelectedPromptId(null);
      setPromptDetails(null);
    } else {
      setSelectedPromptId(promptId);
      loadPromptDetails(promptId);
    }
  };

  const handleRowKeyDown = (e, promptId) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      handleRowClick(promptId);
    } else if (e.key === "Escape" && selectedPromptId) {
      setSelectedPromptId(null);
      setPromptDetails(null);
    }
  };

  const closeDetails = () => {
    setSelectedPromptId(null);
    setPromptDetails(null);
  };

  // Responsive: check if narrow screen
  const [isNarrow, setIsNarrow] = useState(false);
  useEffect(() => {
    const checkWidth = () => setIsNarrow(window.innerWidth < 768);
    checkWidth();
    window.addEventListener("resize", checkWidth);
    return () => window.removeEventListener("resize", checkWidth);
  }, []);

  const getFilteredLocations = (locations, searchQuery) => {
    const filtered = locations.filter((loc) => {
      if (!searchQuery) return true;
      const q = searchQuery.toLowerCase();
      return (
        loc.label.toLowerCase().includes(q) ||
        loc.group.toLowerCase().includes(q) ||
        loc.id.toLowerCase().includes(q)
      );
    });

    const grouped = {};
    filtered.forEach((loc) => {
      if (!grouped[loc.group]) {
        grouped[loc.group] = [];
      }
      grouped[loc.group].push(loc);
    });

    return Object.entries(grouped).map(([groupName, items]) => ({
      name: groupName,
      items: items.sort((a, b) => a.label.localeCompare(b.label)),
    }));
  };

  // Client-side sort by created date
  const sortedPrompts = useMemo(() => {
    const rows = [...prompts];
    rows.sort((a, b) => {
      const da = new Date(a.created_at).getTime();
      const db = new Date(b.created_at).getTime();
      return sortDir === "desc" ? (db - da) : (da - db);
    });
    return rows;
  }, [prompts, sortDir]);

  const totalPages = Math.ceil(totalPrompts / pageSize);

  return (
    <div style={{ maxWidth: "1440px", margin: "0 auto", padding: "0 28px" }}>
      {/* Two-column layout */}
      <div style={{ display: "grid", gridTemplateColumns: "380px 1fr", gap: "24px", alignItems: "start" }}>
        {/* LEFT COLUMN: Generation Form */}
        <aside>
          <div style={styles.card}>
            <h3 style={styles.cardTitle}>Generate Prompts</h3>

            {/* Location */}
            <div style={{ marginBottom: "16px" }}>
              <label style={styles.label}>
                Location <span style={{ color: "#ef4444" }}>*</span>
              </label>
              {locationsLoading && (
                <div style={{ fontSize: "12px", color: "#6b7280", padding: "4px 0" }}>
                  Loading locations...
                </div>
              )}
              {locationsError && (
                <div style={{ fontSize: "12px", color: "#dc2626", padding: "4px 0" }}>
                  {locationsError}.{" "}
                  <button onClick={loadLocations} style={styles.linkButton}>
                    Retry
                  </button>
                </div>
              )}
              {!locationsLoading && !locationsError && (
                <>
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="Search locations..."
                    style={{ ...styles.input, marginBottom: "4px" }}
                  />
                  <select
                    value={selectedLocationId}
                    onChange={(e) => setSelectedLocationId(e.target.value)}
                    style={styles.select}
                  >
                    <option value="">— Select a location —</option>
                    {getFilteredLocations(locations, searchQuery).map((group) => (
                      <optgroup key={group.name} label={group.name}>
                        {group.items.map((loc) => (
                          <option key={loc.id} value={loc.id}>
                            {loc.label} ({loc.count})
                          </option>
                        ))}
                      </optgroup>
                    ))}
                  </select>
                </>
              )}
            </div>

            {/* Count */}
            <div style={{ marginBottom: "16px" }}>
              <label style={styles.label}>Count</label>
              <input
                type="number"
                value={count}
                onChange={(e) => setCount(Math.max(1, Math.min(5, parseInt(e.target.value) || 1)))}
                min="1"
                max="5"
                style={styles.input}
              />
            </div>

            {/* Bindings */}
            <div style={{ marginBottom: "16px" }}>
              <label style={styles.label}>Slot Bindings</label>
              <div style={{ display: "flex", flexWrap: "wrap", gap: "12px", marginBottom: "8px" }}>
                <Toggle label="Scene" checked={bindScene} onChange={setBindScene} />
                <Toggle label="Pose" checked={bindPose} onChange={setBindPose} />
                <Toggle label="Light" checked={bindLighting} onChange={setBindLighting} />
                <Toggle label="Camera" checked={bindCamera} onChange={setBindCamera} />
                <Toggle label="Angle" checked={bindAngle} onChange={setBindAngle} />
                <Toggle label="Accessories" checked={bindAccessories} onChange={setBindAccessories} />
                <Toggle label="Wardrobe" checked={bindWardrobe} onChange={setBindWardrobe} />
                <Toggle label="Hairstyle" checked={bindHair} onChange={setBindHair} />
                <Toggle
                  label="Single Accessory"
                  checked={singleAccessory}
                  onChange={setSingleAccessory}
                  disabled={!bindAccessories}
                  title={!bindAccessories ? "Only applies when Accessories are bound" : ""}
                />
              </div>
              <div style={{ display: "flex", gap: "8px" }}>
                <button onClick={setAllBindOn} style={styles.secondaryButton}>
                  All ON
                </button>
                <button onClick={setAllBindOff} style={styles.secondaryButton}>
                  All OFF
                </button>
              </div>
            </div>

            {/* Generate Button */}
            <button
              onClick={handleGenerate}
              disabled={loading || !selectedLocationId}
              style={{
                ...styles.primaryButton,
                ...(loading || !selectedLocationId ? styles.buttonDisabled : {}),
              }}
            >
              {loading ? "Generating..." : "Generate Bundle(s)"}
            </button>

            {error && (
              <div style={styles.errorBox}>
                {error}
              </div>
            )}
          </div>
        </aside>

        {/* RIGHT COLUMN: Table + Drawer */}
        <main>
          <div style={styles.card}>
            {/* Table Toolbar */}
            <div style={{ marginBottom: "16px", display: "flex", gap: "12px", alignItems: "center", flexWrap: "wrap" }}>
              {/* Status Pills */}
              <div style={{ display: "flex", gap: "4px" }}>
                {["all", "unused", "used"].map((status) => (
                  <button
                    key={status}
                    onClick={() => {
                      setStatusFilter(status);
                    }}
                    style={{
                      ...styles.pill,
                      ...(statusFilter === status ? styles.pillActive : {}),
                    }}
                  >
                    {status.charAt(0).toUpperCase() + status.slice(1)}
                  </button>
                ))}
              </div>

              {/* Search */}
              <input
                type="text"
                value={searchFilter}
                onChange={(e) => {
                  setSearchFilter(e.target.value);
                }}
                placeholder="Search prompts..."
                style={{ ...styles.input, flex: 1, minWidth: "200px" }}
              />

              {/* Total count display */}
              <div style={{ fontSize: "12px", color: "#6b7280", whiteSpace: "nowrap" }}>
                {totalPrompts} total
              </div>
            </div>

            {/* Table */}
            <div style={{ overflowX: "auto" }}>
              <table style={styles.table}>
                <thead>
                  <tr>
                    <th style={styles.th}>ID</th>
                    <th style={styles.th}>Location</th>
                    <th style={styles.th}>Seed</th>
                    <th style={styles.th}>
                      Created
                      <button
                        onClick={() => setSortDir((d) => (d === "desc" ? "asc" : "desc"))}
                        title={sortDir === "desc" ? "Newest first" : "Oldest first"}
                        style={{
                          marginLeft: "6px",
                          padding: "2px 6px",
                          fontSize: "10px",
                          border: "1px solid #d1d5db",
                          borderRadius: "3px",
                          backgroundColor: "#fff",
                          cursor: "pointer",
                        }}
                      >
                        {sortDir === "desc" ? "↓" : "↑"}
                      </button>
                    </th>
                    <th style={styles.th}>Media</th>
                    <th style={styles.th}>Used</th>
                    <th style={styles.th}>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {sortedPrompts.length === 0 && (
                    <tr>
                      <td colSpan="7" style={{ ...styles.td, textAlign: "center", color: "#9ca3af", padding: "32px" }}>
                        No prompts found
                      </td>
                    </tr>
                  )}
                  {sortedPrompts.map((prompt, idx) => (
                    <Fragment key={prompt.id}>
                      <tr
                        tabIndex={0}
                        onClick={() => handleRowClick(prompt.id)}
                        onKeyDown={(e) => handleRowKeyDown(e, prompt.id)}
                        style={{
                          ...styles.tr,
                          backgroundColor: selectedPromptId === prompt.id ? "#f3f4f6" : (idx % 2 === 0 ? "#fff" : "#fafafa"),
                          cursor: "pointer",
                        }}
                      >
                        <td style={styles.td} title={prompt.id}>
                          <span style={{ fontFamily: "monospace", fontSize: "11px" }}>
                            {prompt.id.slice(3, 12)}...
                          </span>
                        </td>
                        <td style={styles.td}>{prompt.location}</td>
                        <td style={styles.td}>
                          {prompt.seed_words && prompt.seed_words.length > 0
                            ? prompt.seed_words.join(", ")
                            : "—"}
                        </td>
                        <td style={styles.td}>
                          {new Date(prompt.created_at).toLocaleString("en-US", {
                            month: "short",
                            day: "numeric",
                            hour: "2-digit",
                            minute: "2-digit",
                          })}
                        </td>
                        <td style={styles.td}>
                          {prompt.media.w}×{prompt.media.h} • {prompt.media.ar}
                        </td>
                        <td style={styles.td}>
                          <input
                            type="checkbox"
                            checked={prompt.used}
                            onChange={(e) => {
                              e.stopPropagation();
                              handleUsedToggle(prompt.id, e.target.checked);
                            }}
                            onClick={(e) => e.stopPropagation()}
                          />
                        </td>
                        <td style={styles.td}>
                          <div style={{ display: "flex", gap: "4px" }} onClick={(e) => e.stopPropagation()}>
                            <button
                              onClick={() => {
                                loadPromptDetails(prompt.id).then(() => {
                                  if (promptDetails) {
                                    copyToClipboard(promptDetails.image_prompt, "Image copied");
                                  }
                                });
                              }}
                              style={styles.ghostButton}
                              title="Copy Image"
                            >
                              📷
                            </button>
                            <button
                              onClick={() => {
                                loadPromptDetails(prompt.id).then(() => {
                                  if (promptDetails && promptDetails.video) {
                                    copyToClipboard(promptDetails.video.line, "Video copied");
                                  }
                                });
                              }}
                              style={styles.ghostButton}
                              title="Copy Video"
                            >
                              🎬
                            </button>
                          </div>
                        </td>
                      </tr>

                      {/* Inline details row (desktop only) */}
                      {selectedPromptId === prompt.id && !isNarrow && (
                        <tr>
                          <td colSpan="7" style={{ padding: 0, border: "none" }}>
                            <InlineRowDetails
                              promptDetails={promptDetails}
                              loading={drawerLoading}
                              onClose={closeDetails}
                              onCopy={copyToClipboard}
                              onUsedToggle={handleUsedToggle}
                            />
                          </td>
                        </tr>
                      )}
                    </Fragment>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </main>
      </div>

      {/* Details Drawer (mobile only) */}
      {selectedPromptId && isNarrow && (
        <DetailsDrawer
          promptDetails={promptDetails}
          loading={drawerLoading}
          onClose={closeDetails}
          onCopy={copyToClipboard}
          onUsedToggle={handleUsedToggle}
        />
      )}

      {/* Toast */}
      {toast.show && (
        <div style={styles.toast}>
          {toast.message}
        </div>
      )}
    </div>
  );
}

function Toggle({ label, checked, onChange, disabled = false, title = "" }) {
  return (
    <label
      style={{
        display: "flex",
        alignItems: "center",
        gap: "4px",
        cursor: disabled ? "not-allowed" : "pointer",
        fontSize: "12px",
        opacity: disabled ? 0.5 : 1,
      }}
      title={title}
    >
      <input
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        disabled={disabled}
        style={{ width: "14px", height: "14px" }}
      />
      <span>{label}</span>
    </label>
  );
}

function InlineRowDetails({ promptDetails, loading, onClose, onCopy, onUsedToggle }) {
  const [showNegative, setShowNegative] = useState(false);

  if (loading) {
    return (
      <div style={{
        padding: "24px",
        textAlign: "center",
        color: "#6b7280",
        backgroundColor: "#fafafa",
        borderTop: "1px solid #e5e7eb",
        borderBottom: "2px solid #e5e7eb",
        animation: "fadeIn 0.15s ease-out",
      }}>
        Loading details...
      </div>
    );
  }

  if (!promptDetails) return null;

  const charCount = promptDetails.image_prompt?.length || 0;
  const getCharColor = () => {
    if (charCount >= 1300 && charCount <= 1400) return { bg: "#dcfce7", color: "#166534" };
    if (charCount >= 1400 && charCount <= 1500) return { bg: "#fef3c7", color: "#92400e" };
    return { bg: "#fee2e2", color: "#991b1b" };
  };
  const charColors = getCharColor();

  const copyVideoLine = () => {
    onCopy(promptDetails.video.line, "Video copied");
  };

  return (
    <div
      style={{
        padding: "16px",
        backgroundColor: "#fafafa",
        borderTop: "1px solid #e5e7eb",
        borderBottom: "2px solid #e5e7eb",
        animation: "fadeIn 0.2s ease-out",
      }}
      role="region"
      aria-label={`Details for ${promptDetails.location}`}
    >
      <div style={{ display: "grid", gridTemplateColumns: "60% 40%", gap: "16px" }}>
        {/* Left: Image Prompt */}
        <section style={styles.inlineCard}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
            <h3 style={{ fontSize: "13px", fontWeight: "600", margin: 0 }}>📷 Image Prompt</h3>
            <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
              <span
                style={{
                  fontSize: "10px",
                  fontFamily: "monospace",
                  fontWeight: "600",
                  padding: "2px 6px",
                  borderRadius: "3px",
                  backgroundColor: charColors.bg,
                  color: charColors.color,
                }}
              >
                {charCount} chars
              </span>
              <button onClick={() => onCopy(promptDetails.image_prompt, "Image copied")} style={styles.copyButtonSmall}>
                Copy
              </button>
            </div>
          </div>
          <textarea
            value={promptDetails.image_prompt}
            readOnly
            style={{
              width: "100%",
              height: "180px",
              fontSize: "11px",
              fontFamily: "monospace",
              lineHeight: "1.4",
              padding: "10px",
              border: "1px solid #d1d5db",
              borderRadius: "4px",
              backgroundColor: "#fff",
              resize: "none",
            }}
          />
          <div style={{ marginTop: "6px", fontSize: "10px", color: "#6b7280" }}>
            {promptDetails.media.dimensions}
          </div>
          <button onClick={() => setShowNegative(!showNegative)} style={styles.linkButton}>
            {showNegative ? "Hide" : "Show"} Negative Prompt
          </button>
          {showNegative && (
            <div style={{ marginTop: "8px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "4px" }}>
                <h4 style={{ fontSize: "11px", fontWeight: "600", margin: 0 }}>Negative Prompt</h4>
                <button
                  onClick={() => onCopy(promptDetails.negative_prompt, "Negative copied")}
                  style={{ ...styles.copyButtonSmall, fontSize: "10px", padding: "2px 5px" }}
                >
                  Copy
                </button>
              </div>
              <pre
                style={{
                  fontSize: "10px",
                  fontFamily: "monospace",
                  lineHeight: "1.3",
                  padding: "8px",
                  border: "1px solid #d1d5db",
                  borderRadius: "4px",
                  backgroundColor: "#fff",
                  whiteSpace: "pre-wrap",
                  margin: 0,
                }}
              >
                {promptDetails.negative_prompt}
              </pre>
            </div>
          )}
        </section>

        {/* Caption Section */}
        {promptDetails.social_meta?.caption && (
          <section style={styles.inlineCard}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
              <h3 style={{ fontSize: "13px", fontWeight: "600", margin: 0 }}>📝 Caption</h3>
              <button onClick={() => onCopy(promptDetails.social_meta.caption, "Caption copied")} style={styles.copyButtonSmall}>
                Copy
              </button>
            </div>
            <input
              type="text"
              value={promptDetails.social_meta.caption}
              readOnly
              style={{
                width: "100%",
                fontSize: "12px",
                lineHeight: "1.5",
                padding: "10px",
                border: "1px solid #d1d5db",
                borderRadius: "4px",
                backgroundColor: "#fff",
              }}
            />
            <div style={{ marginTop: "6px", fontSize: "10px", color: "#6b7280" }}>
              {promptDetails.social_meta.caption.length} chars
            </div>
          </section>
        )}

        {/* Right: Video Motion */}
        <section style={styles.inlineCard}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
            <h3 style={{ fontSize: "13px", fontWeight: "600", margin: 0 }}>🎬 Video Motion</h3>
            <button onClick={copyVideoLine} style={styles.copyButtonSmall}>
              Copy
            </button>
          </div>
          <textarea
            value={promptDetails.video.line || ""}
            readOnly
            style={{
              width: "100%",
              height: "100px",
              fontSize: "11px",
              fontFamily: "monospace",
              lineHeight: "1.4",
              padding: "10px",
              border: "1px solid #d1d5db",
              borderRadius: "4px",
              backgroundColor: "#fff",
              resize: "none",
            }}
          />
          <div style={{ marginTop: "6px", fontSize: "10px", color: "#6b7280" }}>
            {(promptDetails.video.line || "").length} chars • 6s duration
          </div>
        </section>
      </div>
    </div>
  );
}

function VideoField({ label, value, onCopy }) {
  return (
    <div style={{ border: "1px solid #e5e7eb", borderRadius: "4px", padding: "6px 8px", backgroundColor: "#fff" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "3px" }}>
        <span style={{ fontSize: "10px", fontWeight: "600", color: "#6b7280" }}>{label}</span>
        <button
          onClick={onCopy}
          style={{
            ...styles.copyButtonSmall,
            fontSize: "9px",
            padding: "2px 5px",
          }}
          aria-label={`Copy ${label}`}
        >
          Copy
        </button>
      </div>
      <div style={{ fontSize: "11px", lineHeight: "1.4", color: "#111" }}>{value || "—"}</div>
    </div>
  );
}

function DetailsDrawer({ promptDetails, loading, onClose, onCopy, onUsedToggle }) {
  const [showNegative, setShowNegative] = useState(false);

  if (!promptDetails && !loading) return null;

  const charCount = promptDetails?.image_prompt?.length || 0;
  const getCharColor = () => {
    if (charCount >= 1300 && charCount <= 1400) return { bg: "#dcfce7", color: "#166534" };
    if (charCount >= 1400 && charCount <= 1500) return { bg: "#fef3c7", color: "#92400e" };
    return { bg: "#fee2e2", color: "#991b1b" };
  };
  const charColors = getCharColor();

  const copyVideoLine = () => {
    if (!promptDetails || !promptDetails.video) return;
    onCopy(promptDetails.video.line, "Video copied");
  };

  return (
    <>
      {/* Backdrop */}
      <div
        onClick={onClose}
        style={{
          position: "fixed",
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: "rgba(0, 0, 0, 0.3)",
          zIndex: 999,
        }}
      />

      {/* Drawer */}
      <div
        style={{
          position: "fixed",
          top: 0,
          right: 0,
          bottom: 0,
          width: "560px",
          backgroundColor: "#fff",
          boxShadow: "-2px 0 8px rgba(0,0,0,0.1)",
          zIndex: 1000,
          overflowY: "auto",
          padding: "24px",
        }}
      >
        {loading && (
          <div style={{ textAlign: "center", padding: "32px", color: "#6b7280" }}>
            Loading details...
          </div>
        )}

        {!loading && promptDetails && (
          <div>
            {/* Header */}
            <div style={{ marginBottom: "24px", paddingBottom: "16px", borderBottom: "1px solid #e5e7eb" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "8px" }}>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: "11px", fontFamily: "monospace", color: "#6b7280", marginBottom: "4px" }}>
                    {promptDetails.id}
                  </div>
                  <div style={{ fontSize: "16px", fontWeight: "600", color: "#111", marginBottom: "4px" }}>
                    {promptDetails.location}
                  </div>
                  <div style={{ fontSize: "12px", color: "#6b7280" }}>
                    {new Date(promptDetails.created_at).toLocaleString()}
                  </div>
                </div>
                <button onClick={onClose} style={{ ...styles.ghostButton, fontSize: "18px" }}>
                  ✕
                </button>
              </div>
              <label style={{ display: "flex", alignItems: "center", gap: "8px", cursor: "pointer" }}>
                <input
                  type="checkbox"
                  checked={promptDetails.used}
                  onChange={(e) => onUsedToggle(promptDetails.id, e.target.checked)}
                  style={{ width: "16px", height: "16px" }}
                />
                <span style={{ fontSize: "14px", fontWeight: "500", color: promptDetails.used ? "#2563eb" : "#6b7280" }}>
                  {promptDetails.used ? "Used" : "Unused"}
                </span>
              </label>
            </div>

            {/* Image Prompt */}
            <section style={{ marginBottom: "24px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
                <h3 style={{ fontSize: "14px", fontWeight: "600", margin: 0 }}>📷 Image Prompt</h3>
                <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                  <span
                    style={{
                      fontSize: "11px",
                      fontFamily: "monospace",
                      fontWeight: "600",
                      padding: "2px 8px",
                      borderRadius: "4px",
                      backgroundColor: charColors.bg,
                      color: charColors.color,
                    }}
                  >
                    {charCount} chars
                  </span>
                  <button
                    onClick={() => onCopy(promptDetails.image_prompt, "Image copied")}
                    style={styles.copyButton}
                  >
                    Copy
                  </button>
                </div>
              </div>
              <textarea
                value={promptDetails.image_prompt}
                readOnly
                style={{
                  width: "100%",
                  height: "220px",
                  fontSize: "12px",
                  fontFamily: "monospace",
                  lineHeight: "1.5",
                  padding: "12px",
                  border: "1px solid #e5e7eb",
                  borderRadius: "6px",
                  backgroundColor: "#f9fafb",
                  resize: "none",
                }}
              />
              <div style={{ marginTop: "8px", fontSize: "12px", color: "#6b7280" }}>
                {promptDetails.media.dimensions}
              </div>
              <button
                onClick={() => setShowNegative(!showNegative)}
                style={styles.linkButton}
              >
                {showNegative ? "Hide" : "Show"} Negative Prompt
              </button>
              {showNegative && (
                <div style={{ marginTop: "8px" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "4px" }}>
                    <h4 style={{ fontSize: "12px", fontWeight: "600", margin: 0 }}>Negative Prompt</h4>
                    <button
                      onClick={() => onCopy(promptDetails.negative_prompt, "Negative copied")}
                      style={{ ...styles.copyButton, fontSize: "11px", padding: "2px 6px" }}
                    >
                      Copy
                    </button>
                  </div>
                  <pre
                    style={{
                      fontSize: "11px",
                      fontFamily: "monospace",
                      lineHeight: "1.4",
                      padding: "8px",
                      border: "1px solid #e5e7eb",
                      borderRadius: "4px",
                      backgroundColor: "#f9fafb",
                      whiteSpace: "pre-wrap",
                      margin: 0,
                    }}
                  >
                    {promptDetails.negative_prompt}
                  </pre>
                </div>
              )}
            </section>

            {/* Caption */}
            {promptDetails.social_meta?.caption && (
              <section style={{ marginBottom: "24px", paddingTop: "16px", borderTop: "1px solid #e5e7eb" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
                  <h3 style={{ fontSize: "14px", fontWeight: "600", margin: 0 }}>📝 Caption</h3>
                  <button
                    onClick={() => onCopy(promptDetails.social_meta.caption, "Caption copied")}
                    style={styles.copyButton}
                  >
                    Copy
                  </button>
                </div>
                <input
                  type="text"
                  value={promptDetails.social_meta.caption}
                  readOnly
                  style={{
                    width: "100%",
                    fontSize: "12px",
                    lineHeight: "1.5",
                    padding: "12px",
                    border: "1px solid #e5e7eb",
                    borderRadius: "6px",
                    backgroundColor: "#f9fafb",
                  }}
                />
                <div style={{ marginTop: "8px", fontSize: "12px", color: "#6b7280" }}>
                  {promptDetails.social_meta.caption.length} chars
                </div>
              </section>
            )}

            {/* Video Motion */}
            <section style={{ marginBottom: "24px", paddingTop: "16px", borderTop: "1px solid #e5e7eb" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
                <h3 style={{ fontSize: "14px", fontWeight: "600", margin: 0 }}>🎬 Video Motion</h3>
                <button onClick={copyVideoLine} style={styles.copyButton}>
                  Copy
                </button>
              </div>
              <textarea
                value={promptDetails.video.line || ""}
                readOnly
                style={{
                  width: "100%",
                  height: "120px",
                  fontSize: "12px",
                  fontFamily: "monospace",
                  lineHeight: "1.5",
                  padding: "12px",
                  border: "1px solid #e5e7eb",
                  borderRadius: "6px",
                  backgroundColor: "#f9fafb",
                  resize: "none",
                }}
              />
              <div style={{ marginTop: "8px", fontSize: "12px", color: "#6b7280" }}>
                {(promptDetails.video.line || "").length} chars • 6s duration
              </div>
            </section>

            {/* Media Settings */}
            <section style={{ paddingTop: "16px", borderTop: "1px solid #e5e7eb" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
                <h3 style={{ fontSize: "14px", fontWeight: "600", margin: 0 }}>📐 Media Settings</h3>
                <button
                  onClick={() => onCopy(`${promptDetails.media.dimensions} • ${promptDetails.media.aspect} • ${promptDetails.media.format}`, "Media copied")}
                  style={styles.copyButton}
                >
                  Copy
                </button>
              </div>
              <div style={{ fontSize: "12px", color: "#374151", padding: "12px", backgroundColor: "#f9fafb", border: "1px solid #e5e7eb", borderRadius: "6px" }}>
                <div><strong>Dimensions:</strong> {promptDetails.media.dimensions}</div>
                <div><strong>Aspect Ratio:</strong> {promptDetails.media.aspect}</div>
                <div><strong>Format:</strong> {promptDetails.media.format}</div>
              </div>
            </section>
          </div>
        )}
      </div>
    </>
  );
}

function Field({ label, value, onCopy }) {
  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "4px" }}>
        <span style={{ fontWeight: "600", color: "#374151" }}>{label}:</span>
        {onCopy && (
          <button onClick={onCopy} style={{ ...styles.copyButton, fontSize: "10px", padding: "2px 6px" }}>
            Copy
          </button>
        )}
      </div>
      <div style={{ padding: "8px", backgroundColor: "#f9fafb", borderRadius: "4px", color: "#111" }}>
        {value}
      </div>
    </div>
  );
}

const styles = {
  card: {
    backgroundColor: "#fff",
    border: "1px solid #e5e7eb",
    borderRadius: "10px",
    padding: "20px",
  },
  cardTitle: {
    fontSize: "15px",
    fontWeight: "600",
    margin: "0 0 16px",
    color: "#111",
  },
  label: {
    display: "block",
    fontSize: "12px",
    fontWeight: "500",
    color: "#374151",
    marginBottom: "4px",
  },
  input: {
    width: "100%",
    padding: "6px 10px",
    fontSize: "13px",
    border: "1px solid #d1d5db",
    borderRadius: "6px",
    outline: "none",
  },
  select: {
    width: "100%",
    padding: "6px 10px",
    fontSize: "13px",
    border: "1px solid #d1d5db",
    borderRadius: "6px",
    outline: "none",
  },
  button: {
    padding: "6px 12px",
    fontSize: "12px",
    fontWeight: "500",
    border: "1px solid #d1d5db",
    borderRadius: "6px",
    backgroundColor: "#f9fafb",
    color: "#374151",
    cursor: "pointer",
  },
  buttonActive: {
    backgroundColor: "#dbeafe",
    borderColor: "#3b82f6",
    color: "#1e40af",
  },
  primaryButton: {
    width: "100%",
    padding: "10px 16px",
    fontSize: "14px",
    fontWeight: "600",
    border: "none",
    borderRadius: "6px",
    backgroundColor: "#111",
    color: "#fff",
    cursor: "pointer",
  },
  secondaryButton: {
    padding: "6px 12px",
    fontSize: "12px",
    fontWeight: "500",
    border: "1px solid #d1d5db",
    borderRadius: "6px",
    backgroundColor: "#f9fafb",
    color: "#374151",
    cursor: "pointer",
  },
  buttonDisabled: {
    backgroundColor: "#e5e7eb",
    color: "#9ca3af",
    cursor: "not-allowed",
  },
  linkButton: {
    background: "none",
    border: "none",
    color: "#2563eb",
    fontSize: "12px",
    cursor: "pointer",
    textDecoration: "underline",
    padding: "4px 0",
    marginTop: "4px",
  },
  errorBox: {
    marginTop: "12px",
    padding: "10px 12px",
    backgroundColor: "#fef2f2",
    border: "1px solid #fecaca",
    borderRadius: "6px",
    fontSize: "12px",
    color: "#dc2626",
  },
  pill: {
    padding: "4px 12px",
    fontSize: "12px",
    fontWeight: "500",
    border: "1px solid #e5e7eb",
    borderRadius: "16px",
    backgroundColor: "#fff",
    color: "#6b7280",
    cursor: "pointer",
  },
  pillActive: {
    backgroundColor: "#2563eb",
    borderColor: "#2563eb",
    color: "#fff",
  },
  table: {
    width: "100%",
    borderCollapse: "collapse",
    fontSize: "13px",
  },
  th: {
    textAlign: "left",
    padding: "10px 12px",
    borderBottom: "2px solid #e5e7eb",
    fontWeight: "600",
    color: "#374151",
    backgroundColor: "#f9fafb",
    position: "sticky",
    top: 0,
    fontSize: "12px",
  },
  tr: {
    transition: "background-color 0.1s",
  },
  td: {
    padding: "10px 12px",
    borderBottom: "1px solid #f3f4f6",
    color: "#111",
    fontSize: "12px",
  },
  ghostButton: {
    padding: "4px 8px",
    fontSize: "12px",
    border: "1px solid #e5e7eb",
    borderRadius: "4px",
    backgroundColor: "#fff",
    cursor: "pointer",
  },
  copyButton: {
    padding: "4px 10px",
    fontSize: "11px",
    fontWeight: "500",
    border: "1px solid #d1d5db",
    borderRadius: "4px",
    backgroundColor: "#fff",
    color: "#374151",
    cursor: "pointer",
  },
  copyButtonSmall: {
    padding: "3px 8px",
    fontSize: "10px",
    fontWeight: "500",
    border: "1px solid #d1d5db",
    borderRadius: "3px",
    backgroundColor: "#fff",
    color: "#374151",
    cursor: "pointer",
  },
  inlineCard: {
    backgroundColor: "#fff",
    border: "1px solid #e5e7eb",
    borderRadius: "6px",
    padding: "12px",
  },
  toast: {
    position: "fixed",
    bottom: "24px",
    right: "24px",
    backgroundColor: "#1f2937",
    color: "#fff",
    padding: "12px 20px",
    borderRadius: "8px",
    boxShadow: "0 4px 12px rgba(0,0,0,0.3)",
    fontSize: "14px",
    zIndex: 2000,
  },
};
