export default function ApprovalControls({
  approvalActor,
  approvalNote,
  onApprovalActorChange,
  onApprovalNoteChange,
  onApprove,
  busy,
}) {
  return (
    <>
      <label className="ptField" style={{ marginTop: 10 }}>
        <span>actor</span>
        <input
          value={approvalActor}
          onChange={(e) => onApprovalActorChange(String(e.target.value))}
          placeholder="ui"
        />
      </label>
      <label className="ptField" style={{ marginTop: 10 }}>
        <span>note</span>
        <input
          value={approvalNote}
          onChange={(e) => onApprovalNoteChange(String(e.target.value))}
          placeholder="Why is this run approved?"
        />
      </label>
      <div className="ptBtnRow" style={{ marginTop: 10 }}>
        <button className="ptBtn ptBtnPrimary" onClick={onApprove} disabled={busy}>
          Approve Selected Run
        </button>
      </div>
    </>
  );
}
