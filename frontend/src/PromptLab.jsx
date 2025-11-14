import { useState, useEffect } from "react";
import { generatePromptBundle, getRecentPrompts, getLocations } from "./api";
import PromptItem from "./PromptItem";
import PromptDetail from "./PromptDetail";

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
  const [usageFilter, setUsageFilter] = useState("all"); // "all" | "used" | "unused"

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
      // Remove if already exists
      recent = recent.filter((id) => id !== locationId);
      // Add to front
      recent.unshift(locationId);
      // Keep only last MAX_RECENT
      recent = recent.slice(0, MAX_RECENT);
      setRecentLocationIds(recent);
      localStorage.setItem(RECENT_LOCATIONS_KEY, JSON.stringify(recent));
    } catch (err) {
      console.error("Failed to save recent location:", err);
    }
  };

  const loadRecentPrompts = async () => {
    try {
      const data = await getRecentPrompts(20);
      const bundlesWithPreview = (data.prompts || []).map((p) => ({
        ...p,
        preview: p.image_prompt?.final_prompt?.substring(0, 140) || "",
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

      // Add preview to new bundles
      const newBundles = (data.bundles || []).map((b) => ({
        ...b,
        timestamp: new Date().toISOString(),
        preview: b.image_prompt?.final_prompt?.substring(0, 140) || "",
      }));

      // Prepend new bundles and auto-select first one
      setBundles([...newBundles, ...bundles]);
      if (newBundles.length > 0) {
        setActiveId(newBundles[0].id);
      }

      // Save to recent locations
      saveRecentLocationId(selectedLocationId);

      // Clear form (but keep location selected)
      setSeedWords("");
      setCount(1);
    } catch (err) {
      setError(err.message || "Failed to generate prompts");
    } finally {
      setLoading(false);
    }
  };

  // Filter bundles based on search query and usage filter
  const getFilteredBundles = () => {
    return bundles.filter((bundle) => {
      // Usage filter
      if (usageFilter === "used" && !bundle.used) return false;
      if (usageFilter === "unused" && bundle.used) return false;

      // Search filter
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

  return (
    <div className="mx-auto max-w-[1400px] p-3">
      {/* Header */}
      <div className="mb-3">
        <h2 className="text-lg font-semibold text-gray-900">Prompt Lab</h2>
        <p className="text-xs text-gray-600">
          Generate image + video prompts with configurable slot bindings
        </p>
      </div>

      {/* Main layout: Controls (left) | List + Detail (right) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-3">
        {/* LEFT COLUMN: Compact Controls */}
        <section className="lg:col-span-4 space-y-3">
          {/* Form Card */}
          <div className="bg-white border border-zinc-200 rounded-lg p-3 space-y-2">
            {/* Location Selector */}
            <div>
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
                  {/* Recent selections */}
                  {recentLocationIds.length > 0 && (
                    <div className="mb-1 flex gap-1 flex-wrap">
                      {recentLocationIds.map((id) => {
                        const loc = locations.find((l) => l.id === id);
                        if (!loc) return null;
                        return (
                          <button
                            key={id}
                            onClick={() => setSelectedLocationId(id)}
                            className={`px-2 py-0.5 text-[10px] rounded border ${
                              selectedLocationId === id
                                ? "bg-blue-100 border-blue-300 text-blue-700"
                                : "bg-gray-50 border-gray-200 text-gray-600 hover:bg-gray-100"
                            }`}
                            title={`${loc.label} (${loc.count} scenes)`}
                          >
                            {loc.label}
                          </button>
                        );
                      })}
                    </div>
                  )}
                  {/* Search input and USA filter */}
                  <div className="flex gap-1 mb-1">
                    <input
                      type="text"
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      placeholder="Search locations..."
                      className="flex-1 px-2 py-1 text-xs border border-gray-300 rounded focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
                    />
                    <button
                      onClick={() => setUsaOnly(!usaOnly)}
                      className={`px-2 py-1 text-[10px] font-medium rounded border whitespace-nowrap ${
                        usaOnly
                          ? "bg-blue-100 border-blue-300 text-blue-700"
                          : "bg-gray-50 border-gray-200 text-gray-600 hover:bg-gray-100"
                      }`}
                      title="Filter to USA locations only"
                    >
                      USA Only
                    </button>
                  </div>
                  {/* Location select */}
                  <select
                    value={selectedLocationId}
                    onChange={(e) => setSelectedLocationId(e.target.value)}
                    className="w-full px-2 py-1 text-xs border border-gray-300 rounded focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
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
                  {selectedLocationId && (
                    <div className="text-[10px] text-gray-500 mt-1">
                      Selected: {locations.find((l) => l.id === selectedLocationId)?.label}
                    </div>
                  )}
                  {!selectedLocationId && (
                    <div className="text-[10px] text-gray-500 mt-1">
                      Select a location to enable generation
                    </div>
                  )}
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
                className="w-full px-2 py-1 text-xs border border-gray-300 rounded focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>

            {/* Count & Presets */}
            <div className="flex items-center gap-2">
              <div className="w-20">
                <label className="block text-xs font-medium text-gray-700 mb-1">
                  Count
                </label>
                <input
                  type="number"
                  value={count}
                  onChange={(e) =>
                    setCount(Math.max(1, Math.min(5, parseInt(e.target.value) || 1)))
                  }
                  min="1"
                  max="5"
                  className="w-full px-2 py-1 text-xs border border-gray-300 rounded focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
                />
              </div>
              <div className="flex gap-1 ml-auto">
                <button
                  onClick={setAllBindOn}
                  className="px-2 py-1 text-[11px] font-medium bg-gray-100 hover:bg-gray-200 text-gray-700 rounded"
                >
                  All ON
                </button>
                <button
                  onClick={setMostBindOff}
                  className="px-2 py-1 text-[11px] font-medium bg-gray-100 hover:bg-gray-200 text-gray-700 rounded"
                >
                  Most OFF
                </button>
              </div>
            </div>

            {error && (
              <div className="px-2 py-1.5 bg-red-50 border border-red-200 rounded text-xs text-red-700">
                {error}
              </div>
            )}

            <button
              onClick={handleGenerate}
              disabled={loading || !selectedLocationId}
              className={`w-full py-1.5 text-xs font-semibold rounded ${
                loading || !selectedLocationId
                  ? "bg-gray-300 text-gray-500 cursor-not-allowed"
                  : "bg-black hover:bg-gray-800 text-white"
              }`}
            >
              {loading ? "Generating..." : "Generate Bundle(s)"}
            </button>
          </div>

          {/* Binding Toggles Card */}
          <div className="bg-white border border-zinc-200 rounded-lg p-3">
            <h3 className="text-xs font-semibold text-gray-900 mb-2">
              Slot Bindings
            </h3>
            <div className="space-y-1">
              <Toggle label="Scene" checked={bindScene} onChange={setBindScene} />
              <Toggle label="Micro-action (Pose)" checked={bindPose} onChange={setBindPose} />
              <Toggle
                label="Lighting"
                checked={bindLighting}
                onChange={setBindLighting}
              />
              <Toggle label="Camera" checked={bindCamera} onChange={setBindCamera} />
              <Toggle label="Angle" checked={bindAngle} onChange={setBindAngle} />
              <Toggle
                label="Accessories"
                checked={bindAccessories}
                onChange={setBindAccessories}
              />
              <Toggle
                label="Wardrobe"
                checked={bindWardrobe}
                onChange={setBindWardrobe}
              />
              <div className="pt-1 border-t border-zinc-200 mt-1">
                <Toggle
                  label="Single Accessory"
                  checked={singleAccessory}
                  onChange={setSingleAccessory}
                />
              </div>
            </div>
          </div>
        </section>

        {/* RIGHT COLUMN: List + Detail */}
        <section className="lg:col-span-8 grid grid-cols-12 gap-3">
          {/* Master List (left side of right column) */}
          <aside className="col-span-12 lg:col-span-5 rounded-lg border border-zinc-200 bg-white p-2 h-[75vh] flex flex-col">
            <div className="mb-2">
              <div className="flex items-center justify-between mb-2">
                <h3 className="text-xs font-semibold text-gray-900">
                  Recent Prompts ({bundles.length})
                </h3>
                <button
                  onClick={loadRecentPrompts}
                  className="text-[11px] text-blue-600 hover:underline"
                >
                  Refresh
                </button>
              </div>

              {/* Search box */}
              <input
                type="text"
                value={promptSearchQuery}
                onChange={(e) => setPromptSearchQuery(e.target.value)}
                placeholder="Search prompts..."
                className="w-full px-2 py-1 text-xs border border-gray-300 rounded focus:ring-1 focus:ring-blue-500 focus:border-blue-500 mb-2"
              />

              {/* Filter pills */}
              <div className="flex gap-1">
                <button
                  onClick={() => setUsageFilter("all")}
                  className={`px-2 py-0.5 text-[10px] font-medium rounded border ${
                    usageFilter === "all"
                      ? "bg-blue-100 border-blue-300 text-blue-700"
                      : "bg-gray-50 border-gray-200 text-gray-600 hover:bg-gray-100"
                  }`}
                >
                  All
                </button>
                <button
                  onClick={() => setUsageFilter("used")}
                  className={`px-2 py-0.5 text-[10px] font-medium rounded border ${
                    usageFilter === "used"
                      ? "bg-blue-100 border-blue-300 text-blue-700"
                      : "bg-gray-50 border-gray-200 text-gray-600 hover:bg-gray-100"
                  }`}
                >
                  Used
                </button>
                <button
                  onClick={() => setUsageFilter("unused")}
                  className={`px-2 py-0.5 text-[10px] font-medium rounded border ${
                    usageFilter === "unused"
                      ? "bg-blue-100 border-blue-300 text-blue-700"
                      : "bg-gray-50 border-gray-200 text-gray-600 hover:bg-gray-100"
                  }`}
                >
                  Unused
                </button>
              </div>
            </div>

            <ul className="space-y-1 overflow-auto flex-1">
              {getFilteredBundles().length === 0 && bundles.length > 0 && (
                <li className="text-xs text-zinc-500 text-center py-8">
                  No prompts match your filters
                </li>
              )}
              {bundles.length === 0 && (
                <li className="text-xs text-zinc-500 text-center py-8">
                  No prompts generated yet
                </li>
              )}
              {getFilteredBundles().map((bundle) => (
                <PromptItem
                  key={bundle.id}
                  item={bundle}
                  active={activeId === bundle.id}
                  onClick={() => setActiveId(bundle.id)}
                />
              ))}
            </ul>
          </aside>

          {/* Detail View (right side of right column) */}
          <main className="col-span-12 lg:col-span-7 rounded-lg border border-zinc-200 bg-white p-3 h-[75vh] overflow-auto">
            <PromptDetail
              id={activeId}
              bundles={bundles}
              onStateChange={loadRecentPrompts}
            />
          </main>
        </section>
      </div>
    </div>
  );
}

// Helper function to filter and group locations
function getFilteredLocations(locations, searchQuery, usaOnly) {
  // Filter locations by USA flag and search query
  const filtered = locations.filter((loc) => {
    // USA filter
    if (usaOnly && !loc.group.startsWith("USA /")) {
      return false;
    }

    // Search filter
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase();
    return (
      loc.label.toLowerCase().includes(q) ||
      loc.group.toLowerCase().includes(q) ||
      loc.id.toLowerCase().includes(q)
    );
  });

  // Group by group name
  const grouped = {};
  filtered.forEach((loc) => {
    if (!grouped[loc.group]) {
      grouped[loc.group] = [];
    }
    grouped[loc.group].push(loc);
  });

  // Convert to array format for rendering
  return Object.entries(grouped).map(([groupName, items]) => ({
    name: groupName,
    items: items.sort((a, b) => a.label.localeCompare(b.label)),
  }));
}

// Toggle component
function Toggle({ label, checked, onChange }) {
  return (
    <label className="flex items-center gap-2 cursor-pointer">
      <input
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        className="w-3 h-3 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
      />
      <span className="text-[11px] font-medium text-gray-700">
        {label}
      </span>
    </label>
  );
}
