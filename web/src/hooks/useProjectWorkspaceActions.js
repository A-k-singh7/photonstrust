import { useCallback } from "react";

import { apiBootstrapProject, apiGetProject, apiGetProjectWorkspace } from "../photontrust/api";
import { buildProjectBootstrapRequest, normalizeProjectWorkspace } from "../state/projectWorkspace";

export function useProjectWorkspaceActions({
  apiBase,
  applyGraphObject,
  loadRunManifest,
  projectWorkspaceLoadRef,
  projectWorkspacePauseUntilRef,
  refreshProjects,
  refreshRuns,
  setActiveRightTab,
  setApprovalNote,
  setApprovalResult,
  setBundlePublishResult,
  setBundleVerifyResult,
  setBusy,
  setDiffLhsRunId,
  setDiffRhsRunId,
  setDiffScope,
  setMode,
  setProgramStage,
  setProjectApprovals,
  setSelectedProjectId,
  setSelectedRunId,
  setSelectedRunManifest,
  setRunsDiffResult,
  setShowLanding,
  setUserMode,
  setStatus,
}) {
  const applyProjectWorkspaceState = useCallback(
    (projectId, workspace, { dismissLanding = false, graphStatusText = "" } = {}) => {
      const pid = String(projectId || "").trim();
      const parsedWorkspace = normalizeProjectWorkspace(workspace);
      const selectedRunFromWorkspace = parsedWorkspace.selectedRunId;

      projectWorkspacePauseUntilRef.current = Date.now() + 1500;
      if (pid) {
        projectWorkspaceLoadRef.current = pid;
        setSelectedProjectId(pid);
      }
      if (parsedWorkspace.userMode) setUserMode(parsedWorkspace.userMode);
      if (parsedWorkspace.stage) setProgramStage(parsedWorkspace.stage);
      if (parsedWorkspace.mode) setMode(parsedWorkspace.mode);
      if (parsedWorkspace.activeRightTab) setActiveRightTab(parsedWorkspace.activeRightTab);
      setDiffLhsRunId(parsedWorkspace.baselineRunId);
      setDiffRhsRunId(parsedWorkspace.candidateRunId);
      setDiffScope(parsedWorkspace.diffScope);
      setSelectedRunId(selectedRunFromWorkspace || null);
      setSelectedRunManifest(null);
      setRunsDiffResult(null);
      setApprovalResult(null);
      setApprovalNote("");
      setProjectApprovals({ status: "idle", error: null, projectId: null, approvals: [] });
      setBundlePublishResult(null);
      setBundleVerifyResult(null);
      if (parsedWorkspace.graph) {
        const applied = applyGraphObject(parsedWorkspace.graph, { statusText: graphStatusText });
        if (!applied?.ok) {
          throw new Error(String(applied?.error || "Could not apply project graph."));
        }
      }
      if (dismissLanding) setShowLanding(false);
      return selectedRunFromWorkspace;
    },
    [
      applyGraphObject,
      projectWorkspaceLoadRef,
      projectWorkspacePauseUntilRef,
      setActiveRightTab,
      setApprovalNote,
      setApprovalResult,
      setBundlePublishResult,
      setBundleVerifyResult,
      setDiffLhsRunId,
      setDiffRhsRunId,
      setDiffScope,
      setMode,
      setProgramStage,
      setProjectApprovals,
      setSelectedProjectId,
      setSelectedRunId,
      setSelectedRunManifest,
      setRunsDiffResult,
      setShowLanding,
      setUserMode,
    ],
  );

  const hydrateProjectWorkspace = useCallback(
    async (projectId, { dismissLanding = false, loadRuns = true, statusText = "", silentMissing = true } = {}) => {
      const pid = String(projectId || "").trim();
      if (!pid) return { ok: false, error: "project_id is required" };
      try {
        let workspace = null;
        try {
          const workspacePayload = await apiGetProjectWorkspace(apiBase, pid);
          workspace = workspacePayload?.workspace && typeof workspacePayload.workspace === "object" ? workspacePayload.workspace : null;
        } catch (err) {
          const detail = String(err?.message || err);
          if (!silentMissing || !/workspace not found|project not found/i.test(detail)) {
            throw err;
          }
          const projectPayload = await apiGetProject(apiBase, pid).catch(() => null);
          if (projectPayload?.project) {
            setSelectedProjectId(pid);
            projectWorkspaceLoadRef.current = pid;
            if (dismissLanding) setShowLanding(false);
            if (loadRuns) await refreshRuns(pid);
            return { ok: true, workspace: null };
          }
          return { ok: false, error: detail };
        }

        const selectedRunFromWorkspace = applyProjectWorkspaceState(pid, workspace, {
          dismissLanding,
          graphStatusText: "",
        });
        if (loadRuns) await refreshRuns(pid);
        if (selectedRunFromWorkspace) {
          await loadRunManifest(selectedRunFromWorkspace);
        }
        setStatus(statusText || `Loaded project workspace (${pid}).`);
        return { ok: true, workspace };
      } catch (err) {
        const msg = String(err?.message || err);
        setStatus(`Workspace load failed: ${msg}`);
        return { ok: false, error: msg };
      }
    },
    [
      apiBase,
      applyProjectWorkspaceState,
      loadRunManifest,
      projectWorkspaceLoadRef,
      refreshRuns,
      setSelectedProjectId,
      setShowLanding,
      setStatus,
    ],
  );

  const bootstrapProjectWorkspace = useCallback(
    async ({ projectId = "", demoCaseId = "", title = "", templateId = "qkd", workspace = {}, dismissLanding = false, loadRuns = true, statusText = "" } = {}) => {
      try {
        setBusy(true);
        const payload = await apiBootstrapProject(
          apiBase,
          buildProjectBootstrapRequest({ projectId, demoCaseId, title, templateId, workspace }),
        );
        const project = payload?.project && typeof payload.project === "object" ? payload.project : {};
        const pid = String(project?.project_id || projectId || "").trim();
        const workspacePayload = payload?.workspace && typeof payload.workspace === "object" ? payload.workspace : null;
        if (!pid) throw new Error("Bootstrap did not return a project_id.");
        if (workspacePayload) {
          const selectedRunFromWorkspace = applyProjectWorkspaceState(pid, workspacePayload, {
            dismissLanding,
            graphStatusText: "",
          });
          await refreshProjects();
          if (loadRuns) await refreshRuns(pid);
          if (selectedRunFromWorkspace) {
            await loadRunManifest(selectedRunFromWorkspace);
          }
        } else {
          setSelectedProjectId(pid);
          projectWorkspaceLoadRef.current = pid;
          if (dismissLanding) setShowLanding(false);
          await refreshProjects();
          if (loadRuns) await refreshRuns(pid);
        }
        setStatus(statusText || `Prepared project workspace (${pid}).`);
        return { ok: true, payload };
      } catch (err) {
        const msg = String(err?.message || err);
        setStatus(`Project bootstrap failed: ${msg}`);
        return { ok: false, error: msg };
      } finally {
        setBusy(false);
      }
    },
    [
      apiBase,
      applyProjectWorkspaceState,
      loadRunManifest,
      projectWorkspaceLoadRef,
      refreshProjects,
      refreshRuns,
      setBusy,
      setSelectedProjectId,
      setShowLanding,
      setStatus,
    ],
  );

  return {
    applyProjectWorkspaceState,
    hydrateProjectWorkspace,
    bootstrapProjectWorkspace,
  };
}
