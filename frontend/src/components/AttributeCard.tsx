import { useState } from "react";

interface AttributeCardProps {
  label: string;
  children: React.ReactNode;
  onEdit?: () => void;
}

export function AttributeCard({ label, children, onEdit }: AttributeCardProps) {
  const [approved, setApproved] = useState(false);

  return (
    <div
      className="bg-white border border-black p-5 flex flex-col justify-between gap-4 h-[280px]"
      style={approved ? { borderWidth: "2px" } : undefined}
    >
      <div className="flex flex-col gap-2.5">
        <span className="text-[11px] font-bold text-[#9CA3AF] uppercase tracking-[1.5px]">
          {approved ? "✓ Approved" : label}
        </span>
        <div className="text-[18px] font-bold text-black leading-[1.3] overflow-hidden">
          {children}
        </div>
      </div>

      <div className="flex gap-2 justify-end">
        <button
          onClick={onEdit}
          className="bg-white border border-black text-[12px] font-normal text-black px-3.5 py-2 cursor-pointer hover:bg-[#FAFAFA] transition-colors duration-100"
        >
          Edit
        </button>
        <button
          onClick={() => setApproved((v) => !v)}
          className="bg-black text-white text-[12px] font-bold px-3.5 py-2 cursor-pointer hover:bg-[#1A1A1A] transition-colors duration-100"
        >
          {approved ? "✓ Approved" : "✓ Looks good"}
        </button>
      </div>
    </div>
  );
}
