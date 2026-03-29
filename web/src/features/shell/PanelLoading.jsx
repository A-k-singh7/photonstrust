export default function PanelLoading({ message }) {
  return (
    <div className="ptRightSection ptPanelLoading" role="status" aria-live="polite" aria-busy="true">
      <div className="ptHint">{String(message || "Loading panel...")}</div>
    </div>
  );
}
