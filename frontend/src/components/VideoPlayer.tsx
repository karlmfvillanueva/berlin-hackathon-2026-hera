interface VideoPlayerProps {
  fileUrl: string;
}

export function VideoPlayer({ fileUrl }: VideoPlayerProps) {
  return (
    <div className="aspect-[9/16] max-h-[560px] bg-[#1A1A1A] border border-black flex items-center justify-center overflow-hidden">
      <video
        src={fileUrl}
        autoPlay
        muted
        loop
        controls
        className="w-full h-full object-contain"
      />
    </div>
  );
}
