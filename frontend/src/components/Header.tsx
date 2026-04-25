interface HeaderProps {
  step: number;
  totalSteps?: number;
}

export function Header({ step, totalSteps = 4 }: HeaderProps) {
  return (
    <header className="h-16 flex items-center justify-between px-8 bg-white border-b border-black shrink-0">
      <span className="text-[13px] font-bold text-black tracking-normal">
        Berlin Hackathon 2026: Hera Track
      </span>
      <span className="text-[13px] font-normal text-[#666666]">
        Step {step} of {totalSteps}
      </span>
    </header>
  );
}
