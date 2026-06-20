export default function PortfolioLoading() {
  return (
    <div className="min-h-screen bg-[#0a0a0f] flex flex-col">
      {/* Hero skeleton */}
      <div className="relative overflow-hidden border-b border-white/5 bg-gradient-to-b from-[#0d0d18] to-[#0a0a0f] py-16 px-4">
        <div className="max-w-5xl mx-auto flex flex-col items-center gap-6">
          <div className="w-24 h-24 rounded-full bg-white/5 animate-pulse" />
          <div className="w-48 h-7 bg-white/5 rounded-lg animate-pulse" />
          <div className="w-32 h-5 bg-white/5 rounded-md animate-pulse" />
          <div className="flex gap-6 mt-4">
            {[...Array(3)].map((_, i) => (
              <div key={i} className="w-24 h-16 bg-white/5 rounded-xl animate-pulse" />
            ))}
          </div>
        </div>
      </div>
      {/* Grid skeleton */}
      <div className="max-w-5xl mx-auto w-full px-4 py-10 grid grid-cols-1 md:grid-cols-2 gap-6">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="h-52 rounded-2xl bg-white/[0.03] border border-white/5 animate-pulse" />
        ))}
      </div>
    </div>
  );
}
