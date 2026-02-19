export default function StatusFooter({
  busy,
  statusText,
  stageText,
  userMode,
  nodeCount,
  edgeCount,
  hashText,
}) {
  return (
    <footer className="ptStatusbar">
      <div className="ptStatusLeft">
        <span className="ptDot" data-state={busy ? "busy" : "idle"} />
        <span aria-live="polite">{statusText}</span>
      </div>
      <div className="ptStatusRight">
        <span>stage: {stageText}</span>
        <span>persona: {userMode}</span>
        <span>nodes: {nodeCount}</span>
        <span>edges: {edgeCount}</span>
        <span className="ptMono">hash: {hashText}</span>
      </div>
    </footer>
  );
}
