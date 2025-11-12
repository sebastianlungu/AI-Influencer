/**
 * PromptItem - Compact list item for prompt bundles
 * @param {Object} props
 * @param {Object} props.item - Prompt bundle summary
 * @param {boolean} props.active - Whether this item is currently selected
 * @param {Function} props.onClick - Click handler
 */
export default function PromptItem({ item, active, onClick }) {
  // Format timestamp
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

  return (
    <li
      onClick={onClick}
      className={`cursor-pointer rounded-lg p-2 border transition ${
        active
          ? "border-black bg-zinc-50"
          : "border-zinc-200 hover:bg-zinc-50 hover:border-zinc-300"
      }`}
    >
      <div className="flex items-center justify-between mb-1">
        <span className="text-xs font-mono text-zinc-600">
          {item.id.slice(0, 10)}...
        </span>
        <span className="text-[11px] text-zinc-500">
          {formatDate(item.timestamp)}
        </span>
      </div>
      <div className="text-sm font-medium text-gray-900">{item.setting}</div>
      {item.seed_words && item.seed_words.length > 0 && (
        <div className="text-xs text-zinc-500 italic">
          + {item.seed_words.join(", ")}
        </div>
      )}
      <div className="text-xs text-zinc-600 line-clamp-2 mt-1">
        {item.preview}
      </div>
      {active && (
        <div className="mt-1 text-[10px] uppercase tracking-wide text-blue-600 font-semibold">
          Currently Viewing
        </div>
      )}
    </li>
  );
}
