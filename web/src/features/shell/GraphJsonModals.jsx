import Modal from "../../components/common/Modal";

export default function GraphJsonModals({
  exportOpen,
  importOpen,
  exportText,
  importText,
  onCloseExport,
  onCloseImport,
  onImportTextChange,
  onImport,
}) {
  if (!exportOpen && !importOpen) return null;

  return (
    <>
      {exportOpen && (
        <Modal title="Export Graph JSON" onClose={onCloseExport}>
          <pre className="ptPre">{exportText}</pre>
          <div className="ptBtnRow">
            <button className="ptBtn ptBtnPrimary" onClick={onCloseExport}>
              Close
            </button>
          </div>
        </Modal>
      )}

      {importOpen && (
        <Modal title="Import Graph JSON" onClose={onCloseImport}>
          <textarea
            className="ptTextarea"
            value={importText}
            onChange={(e) => onImportTextChange(String(e.target.value))}
            placeholder="Paste a graph JSON payload (schema v0.1)."
          />
          <div className="ptBtnRow">
            <button className="ptBtn ptBtnGhost" onClick={onImport}>
              Import
            </button>
            <button className="ptBtn ptBtnPrimary" onClick={onCloseImport}>
              Cancel
            </button>
          </div>
        </Modal>
      )}
    </>
  );
}
