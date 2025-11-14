import { useState } from "react";
import { updatePromptState } from "./api";

/**
 * PromptDetail - Detail view for a selected prompt bundle
 * @param {Object} props
 * @param {string|null} props.id - Selected prompt ID
 * @param {Object[]} props.bundles - All bundles to find the selected one
 * @param {Function} props.onStateChange - Callback when used state changes
 */
export default function PromptDetail({ id, bundles, onStateChange }) {
  const [showNegative, setShowNegative] = useState(false);
  const [updatingState, setUpdatingState] = useState(false);

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
  };

  const copyVideo = (videoPrompt) => {
    const text = `${videoPrompt.motion}; ${videoPrompt.character_action}; ${videoPrompt.environment}.`;
    copyToClipboard(text);
  };

  const copyCaption = (social_meta) => {
    if (!social_meta) return;
    const text = social_meta.title || "";
    copyToClipboard(text);
  };

  const copyAll = (bundle) => {
    const videoText = `${bundle.video_prompt.motion}; ${bundle.video_prompt.character_action}; ${bundle.video_prompt.environment}.`;
    const captionText = bundle.social_meta?.title || "";

    const text = `[IMAGE PROMPT]
${bundle.image_prompt.final_prompt}

[VIDEO MOTION]
${videoText}

[MEDIA CAPTION]
${captionText}`;
    copyToClipboard(text);
  };

  const handleUsedToggle = async (bundle, newValue) => {
    setUpdatingState(true);
    try {
      await updatePromptState(bundle.id, newValue);
      // Call callback to refresh list
      if (onStateChange) {
        onStateChange();
      }
    } catch (err) {
      console.error("Failed to update state:", err);
      alert("Failed to update state: " + err.message);
    } finally {
      setUpdatingState(false);
    }
  };

  if (!id) {
    return (
      <div className="flex items-center justify-center h-full text-sm text-zinc-500">
        Select a prompt on the left to view details
      </div>
    );
  }

  const bundle = bundles.find((b) => b.id === id);

  if (!bundle) {
    return (
      <div className="flex items-center justify-center h-full text-sm text-zinc-500">
        Prompt not found
      </div>
    );
  }

  const charCount = bundle.image_prompt.final_prompt.length;
  const getCharColor = () => {
    // Green: 1300-1500, Amber: 1200-1299 or 1501-1650, Red: otherwise
    if (charCount >= 1300 && charCount <= 1500) return "bg-green-100 text-green-700";
    if ((charCount >= 1200 && charCount < 1300) || (charCount > 1500 && charCount <= 1650)) return "bg-amber-100 text-amber-700";
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

  const isUsed = bundle.used || false;

  return (
    <div className="space-y-3">
      {/* Sticky header */}
      <header className="sticky top-0 bg-white/90 backdrop-blur-sm z-10 pb-2 border-b border-zinc-200">
        <div className="flex items-center justify-between mb-1">
          <div className="flex-1">
            <div className="text-xs font-mono text-zinc-600">{bundle.id}</div>
            <div className="text-sm font-semibold text-gray-900">
              {bundle.setting}
            </div>
            <div className="text-xs text-zinc-500">
              {formatTimestamp(bundle.timestamp)}
            </div>
          </div>
          <div className="flex items-center gap-2">
            {/* Used/Unused toggle */}
            <label className="flex items-center gap-1.5 cursor-pointer">
              <input
                type="checkbox"
                checked={isUsed}
                onChange={(e) => handleUsedToggle(bundle, e.target.checked)}
                disabled={updatingState}
                className="w-3.5 h-3.5 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
              />
              <span className={`text-xs font-medium ${isUsed ? "text-blue-600" : "text-zinc-500"}`}>
                {isUsed ? "Used" : "Unused"}
              </span>
            </label>
          </div>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => copyAll(bundle)}
            className="text-xs border border-zinc-300 px-3 py-1.5 rounded hover:bg-zinc-50 font-medium"
          >
            Copy All
          </button>
          <button
            onClick={() => setShowNegative(!showNegative)}
            className="text-xs border border-zinc-300 px-3 py-1.5 rounded hover:bg-zinc-50 font-medium"
          >
            {showNegative ? "Hide" : "Reveal"} Negative Prompt
          </button>
        </div>
      </header>

      {/* Section 1: Image Prompt */}
      <section className="rounded-lg border border-zinc-200 bg-white">
        <div className="flex items-center justify-between p-3 bg-zinc-50 border-b border-zinc-200">
          <h4 className="text-sm font-semibold text-gray-900">
            📷 Image Prompt
          </h4>
          <div className="flex items-center gap-2">
            <span className={`text-xs font-mono font-semibold px-2 py-0.5 rounded ${getCharColor()}`}>
              {charCount} chars
            </span>
            <button
              onClick={() => copyToClipboard(bundle.image_prompt.final_prompt)}
              className="text-xs border border-zinc-300 px-2 py-1 rounded hover:bg-zinc-50 bg-white font-medium"
            >
              Copy
            </button>
          </div>
        </div>
        <div className="p-3">
          <pre className="whitespace-pre-wrap text-xs leading-5 bg-zinc-50 p-3 rounded border border-zinc-200 max-h-64 overflow-auto">
            {bundle.image_prompt.final_prompt}
          </pre>
          <div className="mt-2 text-xs text-zinc-500">
            Dimensions: {bundle.image_prompt.width} × {bundle.image_prompt.height}
          </div>
          {/* Negative prompt (collapsible) */}
          {showNegative && (
            <div className="mt-2">
              <div className="text-xs font-medium text-gray-700 mb-1">Negative Prompt:</div>
              <pre className="whitespace-pre-wrap text-[11px] leading-4 bg-zinc-50 p-2 rounded border border-zinc-200">
                {bundle.image_prompt.negative_prompt}
              </pre>
            </div>
          )}
        </div>
      </section>

      {/* Section 2: Video Motion */}
      <section className="rounded-lg border border-zinc-200 bg-white">
        <div className="flex items-center justify-between p-3 bg-zinc-50 border-b border-zinc-200">
          <h4 className="text-sm font-semibold text-gray-900">🎬 Video Motion</h4>
          <button
            onClick={() => copyVideo(bundle.video_prompt)}
            className="text-xs border border-zinc-300 px-2 py-1 rounded hover:bg-zinc-50 bg-white font-medium"
          >
            Copy
          </button>
        </div>
        <div className="p-3 space-y-2 text-xs">
          <div>
            <span className="font-medium text-gray-700">Motion:</span>{" "}
            <span className="text-gray-900">{bundle.video_prompt.motion}</span>
          </div>
          <div>
            <span className="font-medium text-gray-700">Action:</span>{" "}
            <span className="text-gray-900">{bundle.video_prompt.character_action}</span>
          </div>
          <div>
            <span className="font-medium text-gray-700">Environment:</span>{" "}
            <span className="text-gray-900">{bundle.video_prompt.environment}</span>
          </div>
          <div>
            <span className="font-medium text-gray-700">Duration:</span>{" "}
            <span className="text-gray-900">{bundle.video_prompt.duration_seconds}s</span>
          </div>
          {bundle.video_prompt.notes && (
            <div>
              <span className="font-medium text-gray-700">Notes:</span>{" "}
              <span className="text-gray-900">{bundle.video_prompt.notes}</span>
            </div>
          )}
        </div>
      </section>

      {/* Section 3: Media Caption */}
      {bundle.social_meta && (
        <section className="rounded-lg border border-zinc-200 bg-white">
          <div className="flex items-center justify-between p-3 bg-zinc-50 border-b border-zinc-200">
            <h4 className="text-sm font-semibold text-gray-900">📝 Media Caption</h4>
            <button
              onClick={() => copyCaption(bundle.social_meta)}
              className="text-xs border border-zinc-300 px-2 py-1 rounded hover:bg-zinc-50 bg-white font-medium"
            >
              Copy
            </button>
          </div>
          <div className="p-3">
            <p className="text-sm text-gray-900 leading-relaxed">
              {bundle.social_meta.title}
            </p>
            <div className="mt-2 text-xs text-zinc-500">
              {bundle.social_meta.title?.length || 0} chars
            </div>
          </div>
        </section>
      )}
    </div>
  );
}

