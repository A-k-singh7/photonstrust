function _prettyJsonDefault(obj) {
  return JSON.stringify(obj ?? null, null, 2);
}

export default function KindTrustPanel({ kind, kindMeta, params, registryStatus, onSetParam, prettyJson }) {
  const schema = Array.isArray(kindMeta?.params) ? kindMeta.params : [];
  const paramObj = params && typeof params === "object" && !Array.isArray(params) ? params : {};
  const formatPrettyJson = typeof prettyJson === "function" ? prettyJson : _prettyJsonDefault;

  const known = new Set(schema.map((p) => String(p?.name || "")));
  const unknownKeys = Object.keys(paramObj).filter((k) => !known.has(String(k)));

  if (!kind) return null;

  if (registryStatus !== "ok") {
    return <div className="ptHint">Kind registry not loaded. Use Ping to refresh the trust panel.</div>;
  }

  if (!kindMeta) {
    return <div className="ptHint">No registry entry for kind: {String(kind)}</div>;
  }

  const apiEnabled = kindMeta?.availability?.api_enabled;

  return (
    <div className="ptTrustBox">
      <div className="ptJsonTitle">Kind schema</div>
      {apiEnabled === false ? (
        <div className="ptError">
          API execution is disabled for <span className="ptMono">{String(kind)}</span>. This kind is CLI-only by default.
        </div>
      ) : null}
      {Array.isArray(kindMeta?.notes) && kindMeta.notes.length ? (
        <div className="ptHint">{kindMeta.notes.map((n, idx) => <div key={idx}>{String(n)}</div>)}</div>
      ) : null}

      {schema.length ? (
        <div className="ptParamGrid" role="group" aria-label="Parameter schema and quick editor">
          {schema.map((p) => {
            const name = String(p?.name || "");
            if (!name) return null;
            const typ = String(p?.type || "");
            const unit = p?.unit ? String(p.unit) : "";
            const required = Boolean(p?.required);
            const hasDefault = Object.prototype.hasOwnProperty.call(p || {}, "default");
            const defVal = hasDefault ? p.default : undefined;
            const min = Object.prototype.hasOwnProperty.call(p || {}, "min") ? p.min : undefined;
            const max = Object.prototype.hasOwnProperty.call(p || {}, "max") ? p.max : undefined;
            const enumList = Array.isArray(p?.enum) ? p.enum : null;

            const cur = Object.prototype.hasOwnProperty.call(paramObj, name) ? paramObj[name] : undefined;
            const isUnset = cur === null || cur === undefined;

            const rangeBits = [
              min != null ? `min ${min}` : null,
              max != null ? `max ${max}` : null,
              hasDefault ? `default ${defVal === null ? "null" : String(defVal)}` : null,
            ].filter(Boolean);

            const applies = p?.applies_when ? formatPrettyJson(p.applies_when) : "";

            const numericViolation =
              typeof cur === "number" && Number.isFinite(cur) && ((min != null && cur < Number(min)) || (max != null && cur > Number(max)));

            function setValueFromText(raw) {
              const s = String(raw ?? "");
              if (!s) {
                onSetParam(name, required ? "" : null);
                return;
              }
              onSetParam(name, s);
            }

            function setValueFromNumber(raw) {
              const s = String(raw ?? "");
              if (!s) {
                onSetParam(name, null);
                return;
              }
              const n = Number(s);
              if (!Number.isFinite(n)) return;
              if (typ === "integer") onSetParam(name, Math.trunc(n));
              else onSetParam(name, n);
            }

            function setValueFromBoolToken(tok) {
              const t = String(tok);
              if (t === "__unset__") {
                onSetParam(name, null);
              } else if (t === "true") {
                onSetParam(name, true);
              } else if (t === "false") {
                onSetParam(name, false);
              }
            }

            let control = null;
            if (enumList && enumList.length) {
              const current = isUnset ? "__unset__" : String(cur);
              control = (
                <select
                  className={`ptParamControl ${numericViolation ? "isBad" : ""}`}
                  value={current}
                  onChange={(e) => {
                    const v = String(e.target.value);
                    if (v === "__unset__") {
                      onSetParam(name, null);
                      return;
                    }
                    if (typ === "number" || typ === "integer") {
                      const n = Number(v);
                      if (!Number.isFinite(n)) return;
                      onSetParam(name, typ === "integer" ? Math.trunc(n) : n);
                    } else {
                      onSetParam(name, v);
                    }
                  }}
                >
                  {required ? null : <option value="__unset__">(unset)</option>}
                  {enumList.map((x) => (
                    <option key={String(x)} value={String(x)}>
                      {String(x)}
                    </option>
                  ))}
                </select>
              );
            } else if (typ === "boolean") {
              const current = cur === true ? "true" : cur === false ? "false" : "__unset__";
              control = (
                <select className="ptParamControl" value={current} onChange={(e) => setValueFromBoolToken(e.target.value)}>
                  {required ? null : <option value="__unset__">(unset)</option>}
                  <option value="true">true</option>
                  <option value="false">false</option>
                </select>
              );
            } else if (typ === "number" || typ === "integer") {
              control = (
                <input
                  className={`ptParamControl ${numericViolation ? "isBad" : ""}`}
                  type="number"
                  value={isUnset ? "" : String(cur)}
                  placeholder={hasDefault && defVal != null ? String(defVal) : ""}
                  onChange={(e) => setValueFromNumber(e.target.value)}
                />
              );
            } else {
              control = (
                <input
                  className="ptParamControl"
                  type="text"
                  value={isUnset ? "" : String(cur)}
                  placeholder={hasDefault && defVal != null ? String(defVal) : ""}
                  onChange={(e) => setValueFromText(e.target.value)}
                />
              );
            }

            return (
              <div className="ptParamRow" key={name}>
                <div className="ptParamMeta">
                  <div className="ptParamName">
                    {name}
                    {required ? <span className="ptParamReq">REQ</span> : null}
                    {unit ? <span className="ptParamUnit">{unit}</span> : null}
                    <span className="ptParamType">{typ}</span>
                  </div>
                  {p?.description ? <div className="ptParamDesc">{String(p.description)}</div> : null}
                  {rangeBits.length ? <div className="ptParamHint">{rangeBits.join(" | ")}</div> : null}
                  {applies ? <div className="ptParamHint">applies_when: {applies}</div> : null}
                </div>
                <div className="ptParamCtrl">{control}</div>
              </div>
            );
          })}
        </div>
      ) : (
        <div className="ptHint">No parameter schema published for this kind yet.</div>
      )}

      {unknownKeys.length ? (
        <div className="ptCallout">
          <div className="ptCalloutTitle">Unknown params (not in registry)</div>
          <div className="ptHint">{unknownKeys.map((k) => <div key={k}>{String(k)}</div>)}</div>
        </div>
      ) : null}
    </div>
  );
}
