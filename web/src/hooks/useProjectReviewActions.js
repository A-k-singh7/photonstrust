import { useCallback } from "react";

import {
  apiCreateProjectApproval,
  apiDiffRuns,
  apiListProjectApprovals,
  apiPublishRunBundle,
  apiVerifyPublishedBundle,
} from "../photontrust/api";

function packetRunId(selectedRunManifest, workflowResult, runResult) {
  return String(selectedRunManifest?.run_id || workflowResult?.run_id || runResult?.run_id || "").trim();
}

export function useProjectReviewActions({
  apiBase,
  approvalActor,
  approvalNote,
  buildRunBundleUrl,
  bundlePublishResult,
  diffLhsRunId,
  diffRhsRunId,
  diffScope,
  emitUiEvent,
  recordActivity,
  runResult,
  selectedRunManifest,
  setApprovalResult,
  setBusy,
  setBundlePublishResult,
  setBundleVerifyResult,
  setProjectApprovals,
  setRunsDiffResult,
  setStatus,
  workflowResult,
}) {
  const approveSelectedRun = useCallback(async () => {
    const rid = String(selectedRunManifest?.run_id || "").trim();
    if (!rid) return;
    const pid = String(selectedRunManifest?.input?.project_id || "default").trim() || "default";
    setBusy(true);
    setApprovalResult(null);
    try {
      const payload = await apiCreateProjectApproval(apiBase, pid, rid, {
        actor: String(approvalActor || "ui"),
        note: String(approvalNote || ""),
      });
      setApprovalResult(payload);
      recordActivity("approval", "Approved selected run.", {
        run_id: rid,
        project_id: pid,
      });
      setStatus(`Approved run (${rid}) in project=${pid}.`);
      try {
        const approvalsPayload = await apiListProjectApprovals(apiBase, pid, { limit: 50 });
        const approvals = Array.isArray(approvalsPayload?.approvals) ? approvalsPayload.approvals : [];
        setProjectApprovals({ status: "ok", error: null, projectId: pid, approvals });
      } catch (err) {
        setProjectApprovals((prev) => ({ ...(prev || {}), status: "error", error: String(err?.message || err) }));
      }
    } catch (err) {
      setApprovalResult({ error: String(err?.message || err) });
      recordActivity("approval", "Approval failed.", {
        run_id: rid,
        project_id: pid,
      });
      setStatus(`Approve failed: ${String(err?.message || err)}`);
    } finally {
      setBusy(false);
    }
  }, [
    apiBase,
    approvalActor,
    approvalNote,
    recordActivity,
    selectedRunManifest,
    setApprovalResult,
    setBusy,
    setProjectApprovals,
    setStatus,
  ]);

  const diffRuns = useCallback(async () => {
    const lhs = String(diffLhsRunId || "").trim();
    const rhs = String(diffRhsRunId || "").trim();
    if (!lhs || !rhs) return;
    const startedAtMs = Date.now();
    setBusy(true);
    setRunsDiffResult(null);
    try {
      const payload = await apiDiffRuns(apiBase, lhs, rhs, { scope: String(diffScope || "input"), limit: 200 });
      setRunsDiffResult(payload);
      emitUiEvent("ui_compare_completed", {
        duration_ms: Date.now() - startedAtMs,
        outcome: "success",
      });
      recordActivity("compare", "Computed baseline-candidate diff.", {
        lhs,
        rhs,
        scope: String(diffScope || "input"),
      });
      setStatus(`Diff computed (${lhs} vs ${rhs}).`);
    } catch (err) {
      setRunsDiffResult({ error: String(err?.message || err) });
      emitUiEvent("ui_compare_completed", {
        duration_ms: Date.now() - startedAtMs,
        outcome: "failure",
      });
      recordActivity("compare", "Diff failed.", {
        lhs,
        rhs,
        scope: String(diffScope || "input"),
      });
      setStatus(`Diff failed: ${String(err?.message || err)}`);
    } finally {
      setBusy(false);
    }
  }, [
    apiBase,
    diffLhsRunId,
    diffRhsRunId,
    diffScope,
    emitUiEvent,
    recordActivity,
    setBusy,
    setRunsDiffResult,
    setStatus,
  ]);

  const exportDecisionPacket = useCallback(() => {
    const rid = packetRunId(selectedRunManifest, workflowResult, runResult);
    if (!rid) {
      emitUiEvent("ui_packet_exported", { outcome: "abandoned" });
      recordActivity("packet_export", "Packet export abandoned (no run selected).", {});
      setStatus("No run selected for packet export. Select a run manifest or execute a run first.");
      return;
    }

    const url = typeof buildRunBundleUrl === "function" ? buildRunBundleUrl(apiBase, rid) : "";
    try {
      window.open(url, "_blank", "noopener,noreferrer");
      emitUiEvent("ui_packet_exported", { run_id: rid, outcome: "success" });
      recordActivity("packet_export", "Opened decision packet bundle.", { run_id: rid });
      setStatus(`Opened decision packet bundle (${rid}).`);
    } catch (err) {
      emitUiEvent("ui_packet_exported", { run_id: rid, outcome: "failure" });
      recordActivity("packet_export", "Packet export failed.", { run_id: rid });
      setStatus(`Packet export failed: ${String(err?.message || err)}`);
    }
  }, [apiBase, buildRunBundleUrl, emitUiEvent, recordActivity, runResult, selectedRunManifest, setStatus, workflowResult]);

  const publishDecisionPacket = useCallback(async () => {
    const rid = packetRunId(selectedRunManifest, workflowResult, runResult);
    if (!rid) {
      setStatus("No run selected for published packet export.");
      return { ok: false, error: "No run selected." };
    }
    setBusy(true);
    setBundlePublishResult(null);
    setBundleVerifyResult(null);
    try {
      const payload = await apiPublishRunBundle(apiBase, rid);
      setBundlePublishResult(payload);
      recordActivity("packet_publish", "Published decision packet bundle.", {
        run_id: rid,
        bundle_sha256: String(payload?.bundle_sha256 || ""),
      });
      setStatus(`Published decision packet (${String(payload?.bundle_sha256 || rid).slice(0, 12)}...).`);
      return { ok: true, payload };
    } catch (err) {
      const msg = String(err?.message || err);
      recordActivity("packet_publish", "Decision packet publish failed.", { run_id: rid });
      setStatus(`Packet publish failed: ${msg}`);
      return { ok: false, error: msg };
    } finally {
      setBusy(false);
    }
  }, [apiBase, recordActivity, runResult, selectedRunManifest, setBundlePublishResult, setBundleVerifyResult, setBusy, setStatus, workflowResult]);

  const verifyPublishedDecisionPacket = useCallback(async () => {
    const digest = String(bundlePublishResult?.bundle_sha256 || "").trim();
    if (!digest) {
      setStatus("Publish a decision packet before verifying it.");
      return { ok: false, error: "No published bundle digest." };
    }
    setBusy(true);
    try {
      const payload = await apiVerifyPublishedBundle(apiBase, digest);
      setBundleVerifyResult(payload);
      recordActivity("packet_verify", "Verified published decision packet.", { bundle_sha256: digest });
      setStatus(`Verified published packet (${digest.slice(0, 12)}...).`);
      return { ok: true, payload };
    } catch (err) {
      const msg = String(err?.message || err);
      recordActivity("packet_verify", "Published packet verification failed.", { bundle_sha256: digest });
      setStatus(`Packet verify failed: ${msg}`);
      return { ok: false, error: msg };
    } finally {
      setBusy(false);
    }
  }, [apiBase, bundlePublishResult, recordActivity, setBundleVerifyResult, setBusy, setStatus]);

  return {
    approveSelectedRun,
    diffRuns,
    exportDecisionPacket,
    publishDecisionPacket,
    verifyPublishedDecisionPacket,
  };
}
