import { useEffect, useId, useRef } from "react";

function getFocusableElements(root) {
  if (!root) return [];
  return Array.from(root.querySelectorAll('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])')).filter(
    (el) => !el.hasAttribute("disabled"),
  );
}

export default function Modal({ title, children, onClose }) {
  const titleId = useId();
  const outerRef = useRef(null);
  const modalRef = useRef(null);
  const previousFocusRef = useRef(null);

  useEffect(() => {
    previousFocusRef.current = document.activeElement instanceof HTMLElement ? document.activeElement : null;

    const modal = modalRef.current;
    if (modal) {
      const focusables = getFocusableElements(modal);
      if (focusables.length) {
        focusables[0].focus();
      } else {
        modal.focus();
      }
    }

    function onKeyDown(event) {
      if (event.key === "Escape") {
        onClose();
        return;
      }

      if (event.key !== "Tab") return;
      const root = modalRef.current;
      const focusables = getFocusableElements(root);
      if (!focusables.length) return;

      const first = focusables[0];
      const last = focusables[focusables.length - 1];
      const active = document.activeElement;

      if (event.shiftKey && active === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && active === last) {
        event.preventDefault();
        first.focus();
      }
    }

    window.addEventListener("keydown", onKeyDown);
    return () => {
      window.removeEventListener("keydown", onKeyDown);
      if (previousFocusRef.current && typeof previousFocusRef.current.focus === "function") {
        previousFocusRef.current.focus();
      }
    };
  }, [onClose]);

  return (
    <div
      className="ptModalBackdrop"
      ref={outerRef}
      onMouseDown={(event) => {
        if (event.target === outerRef.current) onClose();
      }}
      role="dialog"
      aria-modal="true"
      aria-labelledby={titleId}
    >
      <div className="ptModal" ref={modalRef} tabIndex={-1}>
        <div className="ptModalTop">
          <div className="ptModalTitle" id={titleId}>
            {String(title || "Modal")}
          </div>
          <button className="ptBtn ptBtnTiny" onClick={onClose}>
            Close
          </button>
        </div>
        <div className="ptModalBody">{children}</div>
      </div>
    </div>
  );
}
