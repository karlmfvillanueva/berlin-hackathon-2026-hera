interface ErrorStateProps {
  message: string;
  onRetry: () => void;
}

export function ErrorState({ message, onRetry }: ErrorStateProps) {
  return (
    <div className="flex-1 flex items-center justify-center p-8">
      <div className="max-w-[480px] w-full bg-white border border-black p-6 flex flex-col gap-4">
        <span className="text-[20px] font-bold text-black">
          Something went wrong.
        </span>
        <p className="text-[14px] font-normal text-[#555555] leading-[1.4]">
          {message || "We couldn't generate the video. Try again."}
        </p>
        <button
          onClick={onRetry}
          className="self-start bg-black text-white text-[14px] font-bold px-7 py-3.5 cursor-pointer hover:bg-[#1A1A1A] transition-colors duration-100"
        >
          Try again
        </button>
      </div>
    </div>
  );
}
