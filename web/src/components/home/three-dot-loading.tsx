export function ThreeDotLoading() {
  return (
    <span aria-hidden="true" style={{ display: "inline-flex", gap: "3px", alignItems: "center" }}>
      <span className="dot-pulse" style={{ animationDelay: "0s" }}>·</span>
      <span className="dot-pulse" style={{ animationDelay: "0.2s" }}>·</span>
      <span className="dot-pulse" style={{ animationDelay: "0.4s" }}>·</span>
    </span>
  );
}
