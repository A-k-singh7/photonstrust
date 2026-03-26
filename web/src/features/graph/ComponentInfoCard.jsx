import { COMPONENT_INFO } from "../../photontrust/componentInfo";

const styles = {
  overlay: {
    position: "fixed",
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    zIndex: 1000,
    background: "rgba(16, 23, 34, 0.18)",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    animation: "ptFadeIn 120ms ease",
  },
  card: {
    position: "relative",
    width: "min(480px, 92vw)",
    maxHeight: "80vh",
    overflowY: "auto",
    borderRadius: "14px",
    border: "1px solid rgba(16, 23, 34, 0.14)",
    background: "rgba(255, 255, 255, 0.96)",
    boxShadow: "0 18px 44px rgba(16, 23, 34, 0.14)",
    padding: "20px 22px 18px",
    color: "#101722",
    fontFamily: "'Inter', 'Segoe UI', system-ui, sans-serif",
    fontSize: "13px",
    lineHeight: 1.5,
  },
  closeBtn: {
    position: "absolute",
    top: "12px",
    right: "14px",
    border: "none",
    background: "transparent",
    fontSize: "18px",
    cursor: "pointer",
    color: "rgba(16, 23, 34, 0.5)",
    lineHeight: 1,
    padding: "2px 6px",
    borderRadius: "6px",
  },
  kindLabel: {
    fontFamily: "'Space Grotesk', 'IBM Plex Mono', ui-monospace, monospace",
    fontWeight: 600,
    fontSize: "15px",
    letterSpacing: "-0.02em",
    marginBottom: "14px",
    paddingRight: "28px",
  },
  sectionTitle: {
    fontWeight: 600,
    fontSize: "10px",
    letterSpacing: "0.08em",
    textTransform: "uppercase",
    color: "rgba(16, 23, 34, 0.5)",
    marginTop: "14px",
    marginBottom: "6px",
  },
  physics: {
    fontSize: "12px",
    lineHeight: 1.55,
    color: "rgba(16, 23, 34, 0.82)",
    fontFamily: "'IBM Plex Mono', ui-monospace, monospace",
    background: "rgba(44, 154, 116, 0.06)",
    border: "1px solid rgba(44, 154, 116, 0.14)",
    borderRadius: "8px",
    padding: "10px 12px",
  },
  table: {
    width: "100%",
    borderCollapse: "collapse",
    fontSize: "12px",
  },
  th: {
    textAlign: "left",
    fontWeight: 600,
    fontSize: "10px",
    letterSpacing: "0.04em",
    textTransform: "uppercase",
    color: "rgba(16, 23, 34, 0.5)",
    padding: "4px 8px 4px 0",
    borderBottom: "1px solid rgba(16, 23, 34, 0.1)",
  },
  td: {
    padding: "5px 8px 5px 0",
    borderBottom: "1px solid rgba(16, 23, 34, 0.06)",
    verticalAlign: "top",
  },
  paramName: {
    fontFamily: "'IBM Plex Mono', ui-monospace, monospace",
    fontSize: "11px",
    color: "rgba(44, 154, 116, 0.95)",
    fontWeight: 500,
  },
  typical: {
    fontFamily: "'IBM Plex Mono', ui-monospace, monospace",
    fontSize: "11px",
  },
  notes: {
    fontSize: "11px",
    color: "rgba(16, 23, 34, 0.6)",
  },
  appList: {
    fontSize: "12px",
    color: "rgba(16, 23, 34, 0.78)",
  },
  foundry: {
    fontSize: "12px",
    lineHeight: 1.5,
    color: "rgba(16, 23, 34, 0.72)",
  },
  refList: {
    margin: 0,
    paddingLeft: "18px",
    fontSize: "11px",
    color: "rgba(16, 23, 34, 0.55)",
    fontStyle: "italic",
  },
};

export default function ComponentInfoCard({ kind, onClose }) {
  const info = COMPONENT_INFO[kind];
  if (!info) return null;

  return (
    <div style={styles.overlay} onClick={onClose}>
      <div
        style={styles.card}
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-label={`Component info: ${kind}`}
      >
        <button
          style={styles.closeBtn}
          onClick={onClose}
          aria-label="Close info card"
          title="Close"
        >
          {"\u00d7"}
        </button>

        <div style={styles.kindLabel}>{kind}</div>

        <div style={styles.sectionTitle}>Physics</div>
        <div style={styles.physics}>{info.physics}</div>

        <div style={styles.sectionTitle}>Key Parameters</div>
        <table style={styles.table}>
          <thead>
            <tr>
              <th style={styles.th}>Parameter</th>
              <th style={styles.th}>Typical</th>
              <th style={styles.th}>Notes</th>
            </tr>
          </thead>
          <tbody>
            {info.keyParams.map((p) => (
              <tr key={p.name}>
                <td style={{ ...styles.td, ...styles.paramName }}>{p.name}</td>
                <td style={{ ...styles.td, ...styles.typical }}>{p.typical}</td>
                <td style={{ ...styles.td, ...styles.notes }}>{p.notes}</td>
              </tr>
            ))}
          </tbody>
        </table>

        <div style={styles.sectionTitle}>Applications</div>
        <div style={styles.appList}>{info.applications.join(", ")}</div>

        <div style={styles.sectionTitle}>Foundry Notes</div>
        <div style={styles.foundry}>{info.foundryNotes}</div>

        <div style={styles.sectionTitle}>References</div>
        <ul style={styles.refList}>
          {info.references.map((ref, i) => (
            <li key={i}>{ref}</li>
          ))}
        </ul>
      </div>
    </div>
  );
}
