import { useState } from "react";

const FIXTURE_URL = "https://www.airbnb.com/rooms/kreuzberg-loft-demo";

interface UrlInputProps {
  onSubmit: (url: string) => void;
  loading: boolean;
  outpaintEnabled: boolean;
  onOutpaintChange: (v: boolean) => void;
}

export function UrlInput({ onSubmit, loading, outpaintEnabled, onOutpaintChange }: UrlInputProps) {
  const [value, setValue] = useState(FIXTURE_URL);
  const [validationError, setValidationError] = useState<string | null>(null);

  function handleSubmit() {
    setValidationError(null);
    try {
      new URL(value);
    } catch {
      setValidationError("Enter a valid URL.");
      return;
    }
    onSubmit(value);
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter") handleSubmit();
  }

  return (
    <div className="flex flex-col items-center gap-6 w-full max-w-[1280px] px-16 py-16 mx-auto">
      <h1 className="text-[36px] font-bold leading-[1.2] text-black text-center max-w-[760px]">
        Turn an Airbnb listing into a 15-second video.
      </h1>
      <p className="text-[16px] font-normal leading-[1.4] text-[#555555] text-center max-w-[640px]">
        Paste a link. Our agent picks the hook, the angle, and the pacing.
      </p>

      <div className="flex gap-3 w-[720px] h-16">
        <input
          type="url"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={FIXTURE_URL}
          className="flex-1 bg-white border border-black px-5 text-[16px] font-normal text-black outline-none focus:outline-none placeholder:text-[#9CA3AF]"
          aria-label="Airbnb listing URL"
        />
        <button
          onClick={handleSubmit}
          disabled={loading}
          className="bg-black text-white text-[14px] font-bold px-7 h-full border border-black disabled:opacity-50 cursor-pointer disabled:cursor-not-allowed hover:bg-[#1A1A1A] transition-colors duration-100"
        >
          {loading ? "Loading..." : "Generate"}
        </button>
      </div>

      <label className="flex items-center gap-2 text-[13px] font-normal text-[#555555] cursor-pointer">
        <input
          type="checkbox"
          checked={outpaintEnabled}
          onChange={(e) => onOutpaintChange(e.target.checked)}
          className="w-4 h-4 cursor-pointer"
        />
        Outpaint photos to 9:16
      </label>

      {validationError && (
        <p className="text-[13px] text-black">{validationError}</p>
      )}
      {!validationError && (
        <p className="text-[13px] text-[#9CA3AF]">
          Example: airbnb.com/rooms/12345
        </p>
      )}
    </div>
  );
}
