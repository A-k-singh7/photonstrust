import { useEffect, useMemo, useState } from "react";

function pretty(value) {
  return JSON.stringify(value ?? null, null, 2);
}

export default function JsonBox({ title, value, onApply, textareaClassName = "ptTextarea ptTextareaSmall" }) {
  const prettyValue = useMemo(() => pretty(value), [value]);
  const [text, setText] = useState(() => prettyValue);
  const [err, setErr] = useState(null);

  useEffect(() => {
    setText(prettyValue);
  }, [prettyValue]);

  return (
    <div className="ptJsonBox">
      <div className="ptJsonTop">
        <div className="ptJsonTitle">{String(title)}</div>
        <button
          className="ptBtn ptBtnTiny"
          onClick={() => {
            const result = onApply(text);
            if (!result?.ok) {
              setErr(String(result?.error || "Invalid JSON"));
            } else {
              setErr(null);
            }
          }}
        >
          Apply
        </button>
      </div>
      <textarea className={textareaClassName} value={text} onChange={(e) => setText(String(e.target.value))} spellCheck={false} />
      {err ? <div className="ptError">{err}</div> : null}
    </div>
  );
}
