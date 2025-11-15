import { useState, useEffect } from "react";
import { generatePromptBundle, getRecentPrompts, getLocations, updatePromptState } from "./api";

const RECENT_LOCATIONS_KEY = "plab_recent_locations";
const MAX_RECENT = 5;

export default function PromptLab() {
  // Form inputs
  const [selectedLocationId, setSelectedLocationId] = useState("");
  const [seedWords, setSeedWords] = useState("");
  const [count, setCount] = useState(1);

  // Locations state
  const [locations, setLocations] = useState([]);
  const [locationsLoading, setLocationsLoading] = useState(true);
  const [locationsError, setLocationsError] = useState(null);
  const [recentLocationIds, setRecentLocationIds] = useState([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [usaOnly, setUsaOnly] = useState(false);

  // Binding toggles
  const [bindScene, setBindScene] = useState(true);
  const [bindPose, setBindPose] = useState(true);
  const [bindLighting, setBindLighting] = useState(true);
  const [bindCamera, setBindCamera] = useState(true);
  const [bindAngle, setBindAngle] = useState(true);
  const [bindAccessories, setBindAccessories] = useState(true);
  const [bindWardrobe, setBindWardrobe] = useState(false);
  const [singleAccessory, setSingleAccessory] = useState(true);

  // UI state
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [bundles, setBundles] = useState([]);
  const [activeId, setActiveId] = useState(null);

  // Filtering state
  const [promptSearchQuery, setPromptSearchQuery] = useState("");
  const [usageFilter, setUsageFilter] = useState("all");

  // Toast state
  const [toast, setToast] = useState({ show: false, message: "" });

  // Load locations and recent prompts on mount
  useEffect(() => {
    loadLocations();
    loadRecentPrompts();
    loadRecentLocationIds();
  }, []);

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

  const loadRecentPrompts = async () => {
    try {
      const data = await getRecentPrompts(200);
      const bundlesWithPreview = (data.prompts || []).map((p) => ({
        ...p,
        preview: p.image_prompt?.final_prompt?.substring(0, 100) || "",
      }));
      setBundles(bundlesWithPreview);
    } catch (err) {
      console.error("Failed to load recent prompts:", err);
    }
  };

  const setAllBindOn = () => {
    setBindScene(true);
    setBindPose(true);
    setBindLighting(true);
    setBindCamera(true);
    setBindAngle(true);
    setBindAccessories(true);
  };

  const setMostBindOff = () => {
    setBindScene(false);
    setBindPose(false);
    setBindLighting(false);
    setBindCamera(false);
    setBindAngle(false);
    setBindAccessories(true);
    setSingleAccessory(true);
  };

  const handleGenerate = async () => {
    if (!selectedLocationId) {
      setError("Location is required");
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
        setting_id: selectedLocationId,
        seed_words: seedWordsArray.length > 0 ? seedWordsArray : null,
        count,
        bind_scene: bindScene,
        bind_pose_microaction: bindPose,
        bind_lighting: bindLighting,
        bind_camera: bindCamera,
        bind_angle: bindAngle,
        bind_accessories: bindAccessories,
        bind_wardrobe: bindWardrobe,
        single_accessory: singleAccessory,
      });

      const newBundles = (data.bundles || []).map((b) => ({
        ...b,
        timestamp: new Date().toISOString(),
        preview: b.image_prompt?.final_prompt?.substring(0, 100) || "",
      }));

      setBundles([...newBundles, ...bundles]);
      if (newBundles.length > 0) {
        setActiveId(newBundles[0].id);
      }

      saveRecentLocationId(selectedLocationId);
      setSeedWords("");
      setCount(1);
    } catch (err) {
      setError(err.message || "Failed to generate prompts");
    } finally {
      setLoading(false);
    }
  };

  const handleUsedToggle = async (bundle, newValue) => {
    try {
      await updatePromptState(bundle.id, newValue);
      await loadRecentPrompts();
      showToast("Updated");
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

  const getFilteredBundles = () => {
    return bundles.filter((bundle) => {
      if (usageFilter === "used" && !bundle.used) return false;
      if (usageFilter === "unused" && bundle.used) return false;

      if (promptSearchQuery) {
        const q = promptSearchQuery.toLowerCase();
        const matchesId = bundle.id?.toLowerCase().includes(q);
        const matchesSetting = bundle.setting?.toLowerCase().includes(q);
        const matchesSeedWords = bundle.seed_words?.some((w) =>
          w.toLowerCase().includes(q)
        );
        const matchesPreview = bundle.preview?.toLowerCase().includes(q);

        if (!matchesId && !matchesSetting && !matchesSeedWords && !matchesPreview) {
          return false;
        }
      }

      return true;
    });
  };

  const getFilteredLocations = (locations, searchQuery, usaOnly) => {
    const filtered = locations.filter((loc) => {
      if (usaOnly && !loc.group.startsWith("USA /")) {
        return false;
      }

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

  const activeBundle = bundles.find((b) => b.id === activeId);

  return (
    <div className="max-w-[1320px] mx-auto p-4">
      {/* Header */}
      <header className="mb-4">
        <h1 className="text-xl font-bold text-gray-900">Prompt Lab</h1>
        <p className="text-sm text-gray-600">
          Generate image + video prompts with configurable slot bindings
        </p>
      </header>

      {/* TOOLBAR: Full-width controls */}
      <div className="bg-white border border-zinc-200 rounded-lg p-4 mb-4">
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-4 mb-3">
          {/* Location */}
          <div className="lg:col-span-2">
            <label className="block text-xs font-medium text-gray-700 mb-1">
              Location <span className="text-red-500">*</span>
            </label>
            {locationsLoading && (
              <div className="text-xs text-gray-500 py-1">Loading locations...</div>
            )}
            {locationsError && (
              <div className="text-xs text-red-600 py-1">
                {locationsError}. <button onClick={loadLocations} className="underline">Retry</button>
              </div>
            )}
            {!locationsLoading && !locationsError && (
              <>
                <div className="flex gap-1 mb-1">
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="Search locations..."
                    className="flex-1 px-2 py-1 text-xs border border-gray-300 rounded focus:ring-1 focus:ring-blue-500"
                  />
                  <button
                    onClick={() => setUsaOnly(!usaOnly)}
                    className={`px-2 py-1 text-[10px] font-medium rounded border whitespace-nowrap ${
                      usaOnly
                        ? "bg-blue-100 border-blue-300 text-blue-700"
                        : "bg-gray-50 border-gray-200 text-gray-600"
                    }`}
                  >
                    USA Only
                  </button>
                </div>
                <select
                  value={selectedLocationId}
                  onChange={(e) => setSelectedLocationId(e.target.value)}
                  className="w-full px-2 py-1 text-xs border border-gray-300 rounded focus:ring-1 focus:ring-blue-500"
                >
                  <option value="">— Select a location —</option>
                  {getFilteredLocations(locations, searchQuery, usaOnly).map((group) => (
                    <optgroup key={group.name} label={group.name}>
                      {group.items.map((loc) => (
                        <option key={loc.id} value={loc.id}>
                          {loc.label} ({loc.count} scenes)
                        </option>
                      ))}
                    </optgroup>
                  ))}
                </select>
              </>
            )}
          </div>

          {/* Seed Words */}
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1">
              Seed Words (optional)
            </label>
            <input
              type="text"
              value={seedWords}
              onChange={(e) => setSeedWords(e.target.value)}
              placeholder="dojo, dusk..."
              className="w-full px-2 py-1 text-xs border border-gray-300 rounded focus:ring-1 focus:ring-blue-500"
            />
          </div>

          {/* Count */}
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1">
              Count
            </label>
            <input
              type="number"
              value={count}
              onChange={(e) => setCount(Math.max(1, Math.min(5, parseInt(e.target.value) || 1)))}
              min="1"
              max="5"
              className="w-full px-2 py-1 text-xs border border-gray-300 rounded focus:ring-1 focus:ring-blue-500"
            />
          </div>
        </div>

        {/* Bindings Row */}
        <div className="flex flex-wrap gap-3 items-center mb-3">
          <label className="text-xs font-medium text-gray-700">Slot Bindings:</label>
          <Toggle label="Scene" checked={bindScene} onChange={setBindScene} />
          <Toggle label="Micro-action" checked={bindPose} onChange={setBindPose} />
          <Toggle label="Lighting" checked={bindLighting} onChange={setBindLighting} />
          <Toggle label="Camera" checked={bindCamera} onChange={setBindCamera} />
          <Toggle label="Angle" checked={bindAngle} onChange={setBindAngle} />
          <Toggle label="Accessories" checked={bindAccessories} onChange={setBindAccessories} />
          <Toggle label="Wardrobe" checked={bindWardrobe} onChange={setBindWardrobe} />
          <Toggle label="Single Accessory" checked={singleAccessory} onChange={setSingleAccessory} />
        </div>

        {/* Actions */}
        <div className="flex gap-2">
          <button
            onClick={setAllBindOn}
            className="px-3 py-1.5 text-xs font-medium bg-gray-100 hover:bg-gray-200 text-gray-700 rounded"
          >
            All ON
          </button>
          <button
            onClick={setMostBindOff}
            className="px-3 py-1.5 text-xs font-medium bg-gray-100 hover:bg-gray-200 text-gray-700 rounded"
          >
            Most OFF
          </button>
          <button
            onClick={handleGenerate}
            disabled={loading || !selectedLocationId}
            className={`px-4 py-1.5 text-xs font-semibold rounded ml-auto ${
              loading || !selectedLocationId
                ? "bg-gray-300 text-gray-500 cursor-not-allowed"
                : "bg-black hover:bg-gray-800 text-white"
            }`}
          >
            {loading ? "Generating..." : "Generate Bundle(s)"}
          </button>
        </div>

        {error && (
          <div className="mt-2 px-3 py-2 bg-red-50 border border-red-200 rounded text-xs text-red-700">
            {error}
          </div>
        )}
      </div>

      {/* MAIN: Two-pane layout */}
      <div className="grid grid-cols-[35%_65%] gap-4" style={{ minHeight: "70vh" }}>
        {/* LEFT: Prompt List */}
        <aside className="bg-white border border-zinc-200 rounded-lg p-3 overflow-hidden flex flex-col">
          <div className="mb-3">
            <div className="flex gap-2 mb-2">
              <button
                onClick={() => setUsageFilter("all")}
                className={`px-2 py-1 text-xs font-medium rounded ${
                  usageFilter === "all"
                    ? "bg-blue-600 text-white"
                    : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                }`}
              >
                All
              </button>
              <button
                onClick={() => setUsageFilter("unused")}
                className={`px-2 py-1 text-xs font-medium rounded ${
                  usageFilter === "unused"
                    ? "bg-blue-600 text-white"
                    : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                }`}
              >
                Unused
              </button>
              <button
                onClick={() => setUsageFilter("used")}
                className={`px-2 py-1 text-xs font-medium rounded ${
                  usageFilter === "used"
                    ? "bg-blue-600 text-white"
                    : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                }`}
              >
                Used
              </button>
            </div>
            <input
              type="text"
              value={promptSearchQuery}
              onChange={(e) => setPromptSearchQuery(e.target.value)}
              placeholder="Search prompts..."
              className="w-full px-2 py-1 text-xs border border-gray-300 rounded focus:ring-1 focus:ring-blue-500"
            />
          </div>

          <div className="overflow-y-auto flex-1">
            {getFilteredBundles().length === 0 && bundles.length > 0 && (
              <div className="text-xs text-gray-500 text-center py-8">
                No prompts match your filters
              </div>
            )}
            {bundles.length === 0 && (
              <div className="text-xs text-gray-500 text-center py-8">
                No prompts generated yet
              </div>
            )}
            {getFilteredBundles().map((bundle) => (
              <ListCard
                key={bundle.id}
                bundle={bundle}
                active={activeId === bundle.id}
                onClick={() => setActiveId(bundle.id)}
              />
            ))}
          </div>
        </aside>

        {/* RIGHT: Detail View */}
        <section className="bg-white border border-zinc-200 rounded-lg p-4 overflow-y-auto">
          {!activeId && (
            <div className="flex items-center justify-center h-full text-gray-500">
              Select a prompt on the left to view details
            </div>
          )}
          {activeId && activeBundle && (
            <DetailView
              bundle={activeBundle}
              onCopy={copyToClipboard}
              onUsedToggle={handleUsedToggle}
            />
          )}
        </section>
      </div>

      {/* Toast */}
      {toast.show && (
        <div className="fixed bottom-6 right-6 bg-gray-900 text-white px-4 py-2 rounded-lg shadow-lg text-sm animate-fade-in">
          {toast.message}
        </div>
      )}
    </div>
  );
}

function Toggle({ label, checked, onChange }) {
  return (
    <label className="flex items-center gap-1.5 cursor-pointer">
      <input
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        className="w-3 h-3 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
      />
      <span className="text-xs text-gray-700">{label}</span>
    </label>
  );
}

function ListCard({ bundle, active, onClick }) {
  const formatDate = (timestamp) => {
    try {
      const date = new Date(timestamp);
      return date.toLocaleString("en-US", {
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch {
      return "---";
    }
  };

  const isUsed = bundle.used || false;

  return (
    <div
      onClick={onClick}
      className={`cursor-pointer p-3 mb-2 border rounded-lg transition ${
        active
          ? "border-blue-500 bg-blue-50"
          : "border-gray-200 hover:bg-gray-50"
      }`}
    >
      <div className="flex items-start justify-between mb-1">
        <span className="text-xs font-mono text-gray-600">
          {bundle.id.slice(0, 12)}...
        </span>
        <span
          className={`text-[9px] px-1.5 py-0.5 rounded font-medium ${
            isUsed ? "bg-blue-100 text-blue-700" : "bg-gray-200 text-gray-600"
          }`}
        >
          {isUsed ? "Used" : "Unused"}
        </span>
      </div>
      <div className="text-sm font-medium text-gray-900 mb-1">{bundle.setting}</div>
      <div className="text-xs text-gray-500">{formatDate(bundle.timestamp)}</div>
      {bundle.seed_words && bundle.seed_words.length > 0 && (
        <div className="text-xs text-gray-500 italic mt-1">
          + {bundle.seed_words.join(", ")}
        </div>
      )}
    </div>
  );
}

function DetailView({ bundle, onCopy, onUsedToggle }) {
  const [showNegative, setShowNegative] = useState(false);
  const [updatingState, setUpdatingState] = useState(false);

  const charCount = bundle.image_prompt?.final_prompt?.length || 0;
  const getCharColor = () => {
    if (charCount >= 1300 && charCount <= 1500) return "bg-green-100 text-green-700";
    if ((charCount >= 1200 && charCount < 1300) || (charCount > 1500 && charCount <= 1650))
      return "bg-amber-100 text-amber-700";
    return "bg-red-100 text-red-700";
  };

  const formatTimestamp = (timestamp) => {
    try {
      const date = new Date(timestamp);
      return date.toLocaleString("en-US", {
        month: "short",
        day: "numeric",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch {
      return "---";
    }
  };

  const handleToggle = async (e) => {
    setUpdatingState(true);
    await onUsedToggle(bundle, e.target.checked);
    setUpdatingState(false);
  };

  const copyAllVideo = () => {
    const vp = bundle.video_prompt || {};
    const text = `Motion: ${vp.motion || ""}\nAction: ${vp.character_action || ""}\nEnvironment: ${vp.environment || ""}\nDuration: ${vp.duration_seconds || 6}s\nNotes: ${vp.notes || ""}`;
    onCopy(text, "Video copied");
  };

  const isUsed = bundle.used || false;

  return (
    <div className="space-y-4">
      {/* Header */}
      <header className="pb-3 border-b border-gray-200">
        <div className="flex items-start justify-between mb-2">
          <div className="flex-1">
            <div className="text-xs font-mono text-gray-600">{bundle.id}</div>
            <div className="text-base font-semibold text-gray-900">{bundle.setting}</div>
            <div className="text-xs text-gray-500">{formatTimestamp(bundle.timestamp)}</div>
          </div>
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={isUsed}
              onChange={handleToggle}
              disabled={updatingState}
              className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
            />
            <span className={`text-sm font-medium ${isUsed ? "text-blue-600" : "text-gray-600"}`}>
              {isUsed ? "Used" : "Unused"}
            </span>
          </label>
        </div>
      </header>

      {/* Image Prompt */}
      <section>
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-sm font-semibold text-gray-900">📷 Image Prompt</h3>
          <div className="flex items-center gap-2">
            <span className={`text-xs font-mono font-semibold px-2 py-0.5 rounded ${getCharColor()}`}>
              {charCount} chars
            </span>
            <button
              onClick={() => onCopy(bundle.image_prompt?.final_prompt || "")}
              className="px-2 py-1 text-xs border border-gray-300 rounded hover:bg-gray-50 font-medium"
            >
              Copy
            </button>
          </div>
        </div>
        <pre className="whitespace-pre-wrap text-xs leading-5 bg-gray-50 p-3 rounded border border-gray-200 font-mono">
          {bundle.image_prompt?.final_prompt || "No image prompt"}
        </pre>
        <div className="mt-2 text-xs text-gray-500">
          Dimensions: {bundle.image_prompt?.width || 864} × {bundle.image_prompt?.height || 1536}
        </div>
        <button
          onClick={() => setShowNegative(!showNegative)}
          className="mt-2 text-xs text-blue-600 hover:underline"
        >
          {showNegative ? "Hide" : "Show"} Negative Prompt
        </button>
        {showNegative && (
          <div className="mt-2">
            <div className="flex items-center justify-between mb-1">
              <h4 className="text-xs font-medium text-gray-700">Negative Prompt</h4>
              <button
                onClick={() => onCopy(bundle.image_prompt?.negative_prompt || "")}
                className="px-2 py-0.5 text-[10px] border border-gray-300 rounded hover:bg-gray-50"
              >
                Copy
              </button>
            </div>
            <pre className="whitespace-pre-wrap text-[11px] leading-4 bg-gray-50 p-2 rounded border border-gray-200 font-mono">
              {bundle.image_prompt?.negative_prompt || "No negative prompt"}
            </pre>
          </div>
        )}
      </section>

      {/* Video Motion */}
      <section className="pt-3 border-t border-gray-200">
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-sm font-semibold text-gray-900">🎬 Video Motion</h3>
          <button
            onClick={copyAllVideo}
            className="px-2 py-1 text-xs border border-gray-300 rounded hover:bg-gray-50 font-medium"
          >
            Copy All Video
          </button>
        </div>
        <div className="space-y-2 text-xs">
          <Field
            label="Motion"
            value={bundle.video_prompt?.motion || ""}
            onCopy={() => onCopy(bundle.video_prompt?.motion || "")}
          />
          <Field
            label="Action"
            value={bundle.video_prompt?.character_action || ""}
            onCopy={() => onCopy(bundle.video_prompt?.character_action || "")}
          />
          <Field
            label="Environment"
            value={bundle.video_prompt?.environment || ""}
            onCopy={() => onCopy(bundle.video_prompt?.environment || "")}
          />
          <div>
            <span className="font-medium text-gray-700">Duration:</span>{" "}
            <span className="text-gray-900">{bundle.video_prompt?.duration_seconds || 6}s</span>
          </div>
          {bundle.video_prompt?.notes && (
            <Field
              label="Notes"
              value={bundle.video_prompt.notes}
              onCopy={() => onCopy(bundle.video_prompt.notes)}
            />
          )}
        </div>
      </section>

      {/* Media Caption */}
      {bundle.social_meta && (
        <section className="pt-3 border-t border-gray-200">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-sm font-semibold text-gray-900">🎧 Media / Social</h3>
            <button
              onClick={() => onCopy(bundle.social_meta?.title || "")}
              className="px-2 py-1 text-xs border border-gray-300 rounded hover:bg-gray-50 font-medium"
            >
              Copy
            </button>
          </div>
          <div className="bg-gray-50 p-3 rounded border border-gray-200">
            <p className="text-sm text-gray-900 leading-relaxed">
              {bundle.social_meta?.title || "No media prompt"}
            </p>
            <div className="mt-2 text-xs text-gray-500">
              {bundle.social_meta?.title?.length || 0} chars
            </div>
          </div>
        </section>
      )}
    </div>
  );
}

function Field({ label, value, onCopy }) {
  return (
    <div>
      <div className="flex items-center justify-between mb-1">
        <span className="font-medium text-gray-700">{label}:</span>
        {onCopy && (
          <button
            onClick={onCopy}
            className="px-1.5 py-0.5 text-[10px] border border-gray-300 rounded hover:bg-gray-50"
          >
            Copy
          </button>
        )}
      </div>
      <div className="text-gray-900 bg-gray-50 p-2 rounded text-xs">{value}</div>
    </div>
  );
}
