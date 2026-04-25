type RowState = "done" | "active" | "pending";

interface StatusRowProps {
  state: RowState;
  label: string;
  suffix?: string;
}

export function StatusRow({ state, label, suffix }: StatusRowProps) {
  const icon =
    state === "done" ? (
      <span className="text-[16px] font-bold text-black w-5 shrink-0">✓</span>
    ) : state === "active" ? (
      <span className="w-5 h-5 shrink-0 flex items-center justify-center">
        <span className="w-2.5 h-2.5 rounded-full bg-black animate-pulse" />
      </span>
    ) : (
      <span className="w-5 h-5 shrink-0 flex items-center justify-center">
        <span className="w-2.5 h-2.5 rounded-full border border-[#9CA3AF]" />
      </span>
    );

  return (
    <div className="flex items-center gap-3">
      {icon}
      <span
        className={`text-[14px] ${
          state === "pending" ? "text-[#9CA3AF]" : "text-black"
        }`}
      >
        {label}
      </span>
      {suffix && (
        <span className="text-[13px] text-[#9CA3AF] ml-1">{suffix}</span>
      )}
    </div>
  );
}
