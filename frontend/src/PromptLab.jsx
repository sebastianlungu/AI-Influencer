import { useState, useEffect } from "react";
import { generatePromptBundle, getRecentPrompts } from "./api";
import PromptItem from "./PromptItem";
import PromptDetail from "./PromptDetail";

export default function PromptLab() {
  // Form inputs
  const [setting, setSetting] = useState("");
  const [seedWords, setSeedWords] = useState("");
  const [count, setCount] = useState(1);

  // Binding toggles
  const [bindScene, setBindScene] = useState(true);
  const [bindPose, setBindPose] = useState(true);
  const [bindLighting, setBindLighting] = useState(true);
  const [bindCamera, setBindCamera] = useState(true);
  const [bindAngle, setBindAngle] = useState(true);
  const [bindTwist, setBindTwist] = useState(true);
  const [bindAccessories, setBindAccessories] = useState(true);
  const [bindWardrobe, setBindWardrobe] = useState(false);
  const [singleAccessory, setSingleAccessory] = useState(true);

  // UI state
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [bundles, setBundles] = useState([]);
  const [activeId, setActiveId] = useState(null);

  // Load recent prompts on mount
  useEffect(() => {
    loadRecentPrompts();
  }, []);

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
    setBindTwist(true);
    setBindAccessories(true);
  };

  const setMostBindOff = () => {
    setBindScene(false);
    setBindPose(false);
    setBindLighting(false);
    setBindCamera(false);
    setBindAngle(false);
    setBindTwist(true);
    setBindAccessories(true);
    setSingleAccessory(true);
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
        bind_scene: bindScene,
        bind_pose_microaction: bindPose,
        bind_lighting: bindLighting,
        bind_camera: bindCamera,
        bind_angle: bindAngle,
        bind_twist: bindTwist,
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
            {/* Setting & Seed Words */}
            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">
                  Setting <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  value={setting}
                  onChange={(e) => setSetting(e.target.value)}
                  placeholder="Japan, Greece..."
                  className="w-full px-2 py-1 text-xs border border-gray-300 rounded focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">
                  Seed Words
                </label>
                <input
                  type="text"
                  value={seedWords}
                  onChange={(e) => setSeedWords(e.target.value)}
                  placeholder="dojo, dusk..."
                  className="w-full px-2 py-1 text-xs border border-gray-300 rounded focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
                />
              </div>
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
              disabled={loading || !setting.trim()}
              className={`w-full py-1.5 text-xs font-semibold rounded ${
                loading || !setting.trim()
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
              <Toggle label="Pose" checked={bindPose} onChange={setBindPose} />
              <Toggle
                label="Lighting"
                checked={bindLighting}
                onChange={setBindLighting}
              />
              <Toggle label="Camera" checked={bindCamera} onChange={setBindCamera} />
              <Toggle label="Angle" checked={bindAngle} onChange={setBindAngle} />
              <Toggle
                label="Twist"
                checked={bindTwist}
                onChange={setBindTwist}
                mandatory
              />
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
            <ul className="space-y-1 overflow-auto flex-1">
              {bundles.length === 0 && (
                <li className="text-xs text-zinc-500 text-center py-8">
                  No prompts generated yet
                </li>
              )}
              {bundles.map((bundle) => (
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
            <PromptDetail id={activeId} bundles={bundles} />
          </main>
        </section>
      </div>
    </div>
  );
}

// Toggle component
function Toggle({ label, checked, onChange, mandatory }) {
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
        {mandatory && (
          <span className="ml-1 text-[10px] text-blue-600">(mandatory)</span>
        )}
      </span>
    </label>
  );
}
