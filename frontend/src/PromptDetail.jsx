import { useState } from "react";

/**
 * PromptDetail - Detail view for a selected prompt bundle
 * @param {Object} props
 * @param {string|null} props.id - Selected prompt ID
 * @param {Object[]} props.bundles - All bundles to find the selected one
 */
export default function PromptDetail({ id, bundles }) {
  const [showNegative, setShowNegative] = useState(false);

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
  };

  const copyVideo = (videoPrompt) => {
    const text = `Motion: ${videoPrompt.motion}
Character: ${videoPrompt.character_action}
Environment: ${videoPrompt.environment}
Duration: ${videoPrompt.duration_seconds}s${
      videoPrompt.notes ? `\nNotes: ${videoPrompt.notes}` : ""
    }`;
    copyToClipboard(text);
  };

  const copyAll = (bundle) => {
    const text = `Setting: ${bundle.setting}
ID: ${bundle.id}

IMAGE PROMPT:
${bundle.image_prompt.final_prompt}

NEGATIVE PROMPT:
${bundle.image_prompt.negative_prompt}

VIDEO MOTION:
Motion: ${bundle.video_prompt.motion}
Character: ${bundle.video_prompt.character_action}
Environment: ${bundle.video_prompt.environment}
Duration: ${bundle.video_prompt.duration_seconds}s`;
    copyToClipboard(text);
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
    if (charCount < 800) return "text-red-600";
    if (charCount > 1400) return "text-orange-600";
    return "text-green-600";
  };

  return (
    <div className="space-y-3">
      {/* Sticky header */}
      <header className="sticky top-0 bg-white/90 backdrop-blur-sm z-10 pb-2 border-b border-zinc-200">
        <div className="flex items-center justify-between">
          <div>
            <div className="text-xs font-mono text-zinc-600">{bundle.id}</div>
            <div className="text-sm font-semibold text-gray-900">
              Setting: {bundle.setting}
            </div>
            {bundle.seed_words && bundle.seed_words.length > 0 && (
              <div className="text-xs text-zinc-500 italic">
                + {bundle.seed_words.join(", ")}
              </div>
            )}
          </div>
          <button
            onClick={() => copyAll(bundle)}
            className="text-xs border border-zinc-300 px-3 py-1.5 rounded hover:bg-zinc-50 font-medium"
          >
            Copy All
          </button>
        </div>
      </header>

      {/* Section 1: Image Prompt */}
      <section className="rounded-lg border border-zinc-200 p-3 bg-white">
        <div className="flex items-center justify-between mb-2">
          <h4 className="text-sm font-semibold text-gray-900">
            📷 Image Prompt
          </h4>
          <div className="flex items-center gap-2">
            <span className={`text-xs font-mono font-semibold ${getCharColor()}`}>
              {charCount} chars
            </span>
            <button
              onClick={() => copyToClipboard(bundle.image_prompt.final_prompt)}
              className="text-xs border border-zinc-300 px-2 py-1 rounded hover:bg-zinc-50"
            >
              Copy
            </button>
          </div>
        </div>
        <pre className="whitespace-pre-wrap text-xs leading-5 bg-zinc-50 p-3 rounded border border-zinc-200 max-h-64 overflow-auto">
          {bundle.image_prompt.final_prompt}
        </pre>

        {/* Dimensions */}
        <div className="mt-2 text-xs text-zinc-500">
          Dimensions: {bundle.image_prompt.width} × {bundle.image_prompt.height}
        </div>

        {/* Negative prompt (collapsible) */}
        <div className="mt-2">
          <button
            onClick={() => setShowNegative(!showNegative)}
            className="text-xs text-blue-600 hover:underline cursor-pointer"
          >
            {showNegative ? "Hide" : "Show"} Negative Prompt
          </button>
          {showNegative && (
            <pre className="whitespace-pre-wrap text-[11px] leading-4 bg-zinc-50 p-2 rounded border border-zinc-200 mt-1">
              {bundle.image_prompt.negative_prompt}
            </pre>
          )}
        </div>
      </section>

      {/* Section 2: Video Motion */}
      <section className="rounded-lg border border-zinc-200 p-3 bg-white">
        <div className="flex items-center justify-between mb-2">
          <h4 className="text-sm font-semibold text-gray-900">🎬 Video Motion</h4>
          <button
            onClick={() => copyVideo(bundle.video_prompt)}
            className="text-xs border border-zinc-300 px-2 py-1 rounded hover:bg-zinc-50"
          >
            Copy
          </button>
        </div>
        <div className="grid grid-cols-2 gap-2 text-xs">
          <KeyVal label="Motion" value={bundle.video_prompt.motion} />
          <KeyVal label="Action" value={bundle.video_prompt.character_action} />
          <KeyVal label="Environment" value={bundle.video_prompt.environment} />
          <KeyVal
            label="Duration"
            value={`${bundle.video_prompt.duration_seconds}s`}
          />
          {bundle.video_prompt.notes && (
            <div className="col-span-2">
              <KeyVal label="Notes" value={bundle.video_prompt.notes} />
            </div>
          )}
        </div>
      </section>

      {/* Social Meta (if present) */}
      {bundle.social_meta && (
        <section className="rounded-lg border border-zinc-200 p-3 bg-white">
          <h4 className="text-sm font-semibold text-gray-900 mb-2">
            📱 Social Meta
          </h4>
          <div className="space-y-1 text-xs">
            <KeyVal label="Title" value={bundle.social_meta.title} />
            <KeyVal
              label="Tags"
              value={bundle.social_meta.tags?.join(", ") || ""}
            />
            <KeyVal
              label="Hashtags"
              value={bundle.social_meta.hashtags?.join(" ") || ""}
            />
          </div>
        </section>
      )}
    </div>
  );
}

// Helper component for key-value pairs
function KeyVal({ label, value }) {
  return (
    <div className="bg-zinc-50 p-2 rounded border border-zinc-200">
      <div className="text-[10px] uppercase tracking-wide text-zinc-500 mb-0.5">
        {label}
      </div>
      <div className="text-xs text-gray-900">{value}</div>
    </div>
  );
}
