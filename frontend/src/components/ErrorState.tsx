const ERROR_MESSAGES: Record<string, string> = {
  scrape_blocked: "Airbnb blocked us on that listing. Try a different one, or paste a listing we've seen before.",
  scrape_failed: "We couldn't read that listing. The page may have changed. Try again.",
  fixture_not_found: "We don't have a fixture for that listing yet.",
  classifier_failed: "The agent couldn't read this listing. Try another.",
  hera_submission_failed: "Video generation failed. Try again.",
  hera_unreachable: "Video generation failed. Try again.",
  timeout: "This is taking longer than expected.",
};

function parseMessage(raw: string): string {
  try {
    const parsed: unknown = JSON.parse(raw);
    if (
      parsed !== null &&
      typeof parsed === "object" &&
      "detail" in parsed &&
      parsed.detail !== null &&
      typeof parsed.detail === "object" &&
      "error" in parsed.detail &&
      typeof (parsed.detail as Record<string, unknown>).error === "string"
    ) {
      const code = (parsed.detail as Record<string, string>).error;
      if (code in ERROR_MESSAGES) {
        return ERROR_MESSAGES[code];
      }
    }
  } catch {
    // not JSON — fall through
  }
  return raw;
}

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
          {parseMessage(message) || "We couldn't generate the video. Try again."}
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
