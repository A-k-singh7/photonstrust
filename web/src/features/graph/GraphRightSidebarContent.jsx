import JsonBox from "../../components/common/JsonBox";
import KindTrustPanel from "./KindTrustPanel";

export default function GraphRightSidebarContent({
  activeRightTab,
  inspect,
  compile,
  drc,
  invdesign,
  layout,
  lvs,
  klayout,
  spice,
  graphJson,
}) {
  if (activeRightTab === "inspect") {
    return (
      <div id="pt-panel-graph-inspect" role="tabpanel" aria-labelledby="pt-tab-graph-inspect" className="ptRightBody">
        <div className="ptRightSection">
          <div className="ptRightTitle">Selection</div>
          {inspect.selectedNode ? (
            <>
              <div className="ptKeyVal">
                <div>id</div>
                <div>{String(inspect.selectedNode.id)}</div>
              </div>
              <div className="ptKeyVal">
                <div>kind</div>
                <div>{String(inspect.selectedNode?.data?.kind)}</div>
              </div>
              <div className="ptKeyVal">
                <div>label</div>
                <div>{String(inspect.selectedNode?.data?.label || "")}</div>
              </div>
              <KindTrustPanel
                kind={String(inspect.selectedNode?.data?.kind || "")}
                kindMeta={inspect.kindRegistryByKind?.[String(inspect.selectedNode?.data?.kind || "")]}
                params={inspect.selectedNode?.data?.params}
                registryStatus={inspect.kindRegistryStatus}
                onSetParam={inspect.onSetParam}
                prettyJson={inspect.prettyJson}
              />
              <div className="ptBtnRow">
                <button className="ptBtn ptBtnGhost" onClick={inspect.onDeleteSelected}>
                  Delete node
                </button>
              </div>
              <JsonBox title="params" value={inspect.selectedNode?.data?.params} onApply={inspect.onApplySelectedParams} />
            </>
          ) : (
            <div className="ptHint">Click a node to edit its parameters.</div>
          )}
        </div>

        {inspect.profile === "qkd_link" ? (
          <div className="ptRightSection">
            <div className="ptRightTitle">Scenario</div>
            <label className="ptField">
              <span>Band</span>
              <select
                value={String(inspect.scenario?.band || "c_1550")}
                onChange={(e) => {
                  const b = String(e.target.value);
                  const opt = inspect.bandOptions.find((x) => x.id === b);
                  const wl = b === "nir_795" ? 795 : b === "nir_850" ? 850 : b === "o_1310" ? 1310 : 1550;
                  inspect.onSetScenario((s) => ({ ...(s || {}), band: b, wavelength_nm: wl, id: s?.id || "ui_qkd_link" }));
                  inspect.onSetStatus(`Scenario band: ${opt?.label || b}.`);
                }}
              >
                {inspect.bandOptions.map((b) => (
                  <option key={b.id} value={b.id}>
                    {b.label}
                  </option>
                ))}
              </select>
            </label>

            <label className="ptField">
              <span>Distance (km)</span>
              <input
                value={String(inspect.scenario?.distance_km ?? 10)}
                onChange={(e) => {
                  const v = Number(String(e.target.value));
                  inspect.onSetScenario((s) => ({ ...(s || {}), distance_km: Number.isFinite(v) ? v : 10, id: s?.id || "ui_qkd_link" }));
                }}
              />
            </label>

            <label className="ptField">
              <span>Execution mode</span>
              <select value={inspect.qkdExecutionMode} onChange={(e) => inspect.onSetQkdExecutionMode(String(e.target.value))}>
                <option value="preview">preview</option>
                <option value="certification">certification</option>
              </select>
            </label>

            <JsonBox title="scenario (advanced)" value={inspect.scenario} onApply={inspect.onApplyScenarioText} />

            <JsonBox title="uncertainty (advanced)" value={inspect.uncertainty} onApply={inspect.onApplyUncertaintyText} />

            <JsonBox title="finite_key (advanced)" value={inspect.finiteKey} onApply={inspect.onApplyFiniteKeyText} />
          </div>
        ) : (
          <div className="ptRightSection">
            <div className="ptRightTitle">Circuit</div>
            <label className="ptField">
              <span>Wavelength (nm)</span>
              <input
                value={String(inspect.circuit?.wavelength_nm ?? 1550)}
                onChange={(e) => {
                  const v = Number(String(e.target.value));
                  inspect.onSetCircuit((c) => ({ ...(c || {}), wavelength_nm: Number.isFinite(v) ? v : 1550, id: c?.id || "ui_pic_circuit" }));
                }}
              />
            </label>

            <label className="ptField ptFieldWide">
              <span>Sweep nm (comma)</span>
              <input
                value={inspect.picSweepNmText}
                onChange={(e) => inspect.onSetPicSweepNmText(String(e.target.value))}
                placeholder="1540, 1550, 1560"
              />
            </label>

            <JsonBox title="circuit (advanced)" value={inspect.circuit} onApply={inspect.onApplyCircuitText} />
          </div>
        )}

        {inspect.profile === "pic_circuit" ? (
          <div className="ptRightSection">
            <div className="ptRightTitle">Performance DRC (Crosstalk)</div>

            <label className="ptField ptFieldWide">
              <span>Gap (um)</span>
              <input
                type="range"
                min="0.2"
                max="2.0"
                step="0.01"
                value={Number(inspect.xtGapUm)}
                onChange={(e) => {
                  const v = Number(String(e.target.value));
                  const next = Number.isFinite(v) ? v : 0.6;
                  inspect.onSetXtGapUm(next);
                  if (inspect.xtLive && inspect.xtHasRunOnceRef?.current) {
                    if (typeof inspect.onScheduleLiveDrc === "function") {
                      inspect.onScheduleLiveDrc();
                    }
                  }
                }}
              />
              <input
                value={String(inspect.xtGapUm)}
                onChange={(e) => {
                  const v = Number(String(e.target.value));
                  inspect.onSetXtGapUm(Number.isFinite(v) ? v : 0.6);
                }}
              />
            </label>

            <label className="ptField">
              <span>Parallel length (um)</span>
              <input
                value={String(inspect.xtLengthUm)}
                onChange={(e) => {
                  const v = Number(String(e.target.value));
                  inspect.onSetXtLengthUm(Number.isFinite(v) ? v : 1000.0);
                }}
              />
            </label>

            <label className="ptField">
              <span>Target XT (dB)</span>
              <input
                value={String(inspect.xtTargetDb)}
                onChange={(e) => {
                  const v = Number(String(e.target.value));
                  inspect.onSetXtTargetDb(Number.isFinite(v) ? v : -40.0);
                }}
              />
            </label>

            <label className="ptCheck">
              <input type="checkbox" checked={inspect.xtLive} onChange={(e) => inspect.onSetXtLive(Boolean(e.target.checked))} />
              <span>Live update (after first run)</span>
            </label>

            <div className="ptBtnRow">
              <button className="ptBtn ptBtnPrimary" onClick={() => inspect.onRunCrosstalkDrc({ reason: "manual" })} disabled={inspect.busy}>
                Run Crosstalk DRC
              </button>
            </div>
          </div>
        ) : null}

        {inspect.profile === "pic_circuit" ? (
          <div className="ptRightSection">
            <div className="ptRightTitle">Inverse Design</div>

            <label className="ptField">
              <span>Kind</span>
              <select value={String(inspect.invKind || "mzi_phase")} onChange={(e) => inspect.onSetInvKind(String(e.target.value))}>
                <option value="mzi_phase">MZI Phase (tune phase_rad)</option>
                <option value="coupler_ratio">Coupler Ratio (tune coupling_ratio)</option>
              </select>
            </label>

            {inspect.invKind === "mzi_phase" ? (
              inspect.phaseNodeIds.length ? (
                <label className="ptField">
                  <span>Phase node</span>
                  <select value={String(inspect.invPhaseNodeId || "")} onChange={(e) => inspect.onSetInvPhaseNodeId(String(e.target.value))}>
                    {inspect.phaseNodeIds.map((nid) => (
                      <option key={nid} value={nid}>
                        {nid}
                      </option>
                    ))}
                  </select>
                </label>
              ) : (
                <div className="ptHint">
                  Add a <span className="ptMono">pic.phase_shifter</span> node to enable inverse design.
                </div>
              )
            ) : inspect.couplerNodeIds.length ? (
              <label className="ptField">
                <span>Coupler node</span>
                <select value={String(inspect.invCouplerNodeId || "")} onChange={(e) => inspect.onSetInvCouplerNodeId(String(e.target.value))}>
                  {inspect.couplerNodeIds.map((nid) => (
                    <option key={nid} value={nid}>
                      {nid}
                    </option>
                  ))}
                </select>
              </label>
            ) : (
              <div className="ptHint">
                Add a <span className="ptMono">pic.coupler</span> node to enable inverse design.
              </div>
            )}

            <label className="ptField">
              <span>Target output node</span>
              <input value={String(inspect.invOutputNode || "")} onChange={(e) => inspect.onSetInvOutputNode(String(e.target.value))} placeholder="cpl_out" />
            </label>

            <label className="ptField">
              <span>Target output port</span>
              <input value={String(inspect.invOutputPort || "")} onChange={(e) => inspect.onSetInvOutputPort(String(e.target.value))} placeholder="out1" />
            </label>

            <label className="ptField ptFieldWide">
              <span>Target power fraction</span>
              <input
                type="range"
                min="0"
                max="1"
                step="0.01"
                value={Number(inspect.invTargetFraction)}
                onChange={(e) => {
                  const v = Number(String(e.target.value));
                  inspect.onSetInvTargetFraction(Number.isFinite(v) ? v : 0.9);
                }}
              />
              <input
                value={String(inspect.invTargetFraction)}
                onChange={(e) => {
                  const v = Number(String(e.target.value));
                  inspect.onSetInvTargetFraction(Number.isFinite(v) ? v : 0.9);
                }}
              />
            </label>

            <label className="ptField">
              <span>Wavelength objective</span>
              <select value={String(inspect.invWavelengthObjectiveAgg || "mean")} onChange={(e) => inspect.onSetInvWavelengthObjectiveAgg(String(e.target.value))}>
                <option value="mean">mean</option>
                <option value="max">max (worst-case)</option>
              </select>
            </label>

            <label className="ptField">
              <span>Case objective</span>
              <select value={String(inspect.invCaseObjectiveAgg || "mean")} onChange={(e) => inspect.onSetInvCaseObjectiveAgg(String(e.target.value))}>
                <option value="mean">mean</option>
                <option value="max">max (worst-case)</option>
              </select>
            </label>

            <JsonBox
              title="robustness cases (advanced)"
              value={inspect.invRobustnessCases}
              onApply={(text) => {
                const parsed = inspect.safeParseJson(text);
                if (!parsed.ok) return parsed;
                if (!Array.isArray(parsed.value)) return { ok: false, error: "Robustness cases must be a JSON array." };
                inspect.onSetInvRobustnessCases(parsed.value);
                return { ok: true };
              }}
            />

            <div className="ptBtnRow">
              <button
                className="ptBtn ptBtnPrimary"
                onClick={inspect.onRunInvdesign}
                disabled={inspect.busy || (inspect.invKind === "coupler_ratio" ? !inspect.couplerNodeIds.length : !inspect.phaseNodeIds.length)}
              >
                Run Inverse Design
              </button>
              <button
                className="ptBtn"
                onClick={inspect.onRunInvdesignWorkflow}
                disabled={inspect.busy || (inspect.invKind === "coupler_ratio" ? !inspect.couplerNodeIds.length : !inspect.phaseNodeIds.length)}
                title="Runs: invdesign -> layout build -> LVS-lite -> (optional) KLayout pack -> SPICE export"
              >
                Run Full Workflow
              </button>
            </div>
          </div>
        ) : null}

        <div className="ptRightSection">
          <div className="ptRightTitle">Metadata</div>
          <label className="ptField">
            <span>Title</span>
            <input value={String(inspect.metadata?.title || "")} onChange={(e) => inspect.onSetMetadata((m) => ({ ...(m || {}), title: String(e.target.value) }))} />
          </label>
          <label className="ptField">
            <span>Description</span>
            <input
              value={String(inspect.metadata?.description || "")}
              onChange={(e) => inspect.onSetMetadata((m) => ({ ...(m || {}), description: String(e.target.value) }))}
            />
          </label>
        </div>
      </div>
    );
  }

  if (activeRightTab === "compile") {
    return (
      <div id="pt-panel-graph-compile" role="tabpanel" aria-labelledby="pt-tab-graph-compile" className="ptRightBody">
        <div className="ptRightSection">
          <div className="ptRightTitle">Compile Result</div>
          {compile.compileResult?.assumptions_md ? (
            <pre className="ptPre">{String(compile.compileResult.assumptions_md)}</pre>
          ) : (
            <div className="ptHint">Compile to see assumptions, compiled artifacts, and provenance.</div>
          )}
          {compile.compileResult?.diagnostics?.errors?.length ? (
            <div className="ptError">
              <div className="ptCalloutTitle">Diagnostics (errors)</div>
              <ul className="ptList">
                {compile.compileResult.diagnostics.errors.map((d, idx) => (
                  <li key={idx}>
                    <span className="ptMono">{String(d.code || "error")}</span>: {String(d.message || "")}
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
          {compile.compileResult?.diagnostics?.warnings?.length ? (
            <div className="ptCallout">
              <div className="ptCalloutTitle">Diagnostics (warnings)</div>
              <ul className="ptList">
                {compile.compileResult.diagnostics.warnings.map((d, idx) => (
                  <li key={idx}>
                    <span className="ptMono">{String(d.code || "warn")}</span>: {String(d.message || "")}
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
          {compile.compileResult?.warnings?.length ? (
            <div className="ptCallout">
              <div className="ptCalloutTitle">Warnings</div>
              <ul className="ptList">
                {compile.compileResult.warnings.map((w, idx) => (
                  <li key={idx}>{String(w)}</li>
                ))}
              </ul>
            </div>
          ) : null}
          {compile.compileResult ? <pre className="ptPre">{compile.prettyJson(compile.compileResult)}</pre> : null}
        </div>
      </div>
    );
  }

  if (activeRightTab === "drc") {
    return (
      <div id="pt-panel-graph-drc" role="tabpanel" aria-labelledby="pt-tab-graph-drc" className="ptRightBody">
        <div className="ptRightSection">
          <div className="ptRightTitle">Performance DRC Result</div>
          {drc.xtResult?.run_id && drc.xtResult?.artifact_relpaths ? (
            <div className="ptCallout">
              <div className="ptCalloutTitle">Artifacts (served)</div>
              <div className="ptHint">
                {drc.xtResult?.artifact_relpaths?.performance_drc_report_html ? (
                  <>
                    <a href={drc.buildRunArtifactUrl(drc.apiBase, drc.xtResult.run_id, drc.xtResult.artifact_relpaths.performance_drc_report_html)} target="_blank" rel="noreferrer">
                      Open report (HTML)
                    </a>{" "}
                    <span className="ptMono">[{String(drc.xtResult.artifact_relpaths.performance_drc_report_html)}]</span>
                    <br />
                  </>
                ) : null}
                {drc.xtResult?.artifact_relpaths?.performance_drc_report_json ? (
                  <>
                    <a href={drc.buildRunArtifactUrl(drc.apiBase, drc.xtResult.run_id, drc.xtResult.artifact_relpaths.performance_drc_report_json)} target="_blank" rel="noreferrer">
                      Open report (JSON)
                    </a>{" "}
                    <span className="ptMono">[{String(drc.xtResult.artifact_relpaths.performance_drc_report_json)}]</span>
                    <br />
                  </>
                ) : null}
                <a href={drc.buildRunManifestUrl(drc.apiBase, drc.xtResult.run_id)} target="_blank" rel="noreferrer">
                  Open run manifest (JSON)
                </a>
              </div>
            </div>
          ) : null}
          {drc.xtResult ? <pre className="ptPre">{drc.prettyJson(drc.xtResult)}</pre> : <div className="ptHint">Run DRC to see outputs.</div>}
        </div>
      </div>
    );
  }

  if (activeRightTab === "invdesign") {
    return (
      <div id="pt-panel-graph-invdesign" role="tabpanel" aria-labelledby="pt-tab-graph-invdesign" className="ptRightBody">
        <div className="ptRightSection">
          <div className="ptRightTitle">Inverse Design Result</div>
          {invdesign.invResult?.run_id && invdesign.invResult?.artifact_relpaths ? (
            <div className="ptCallout">
              <div className="ptCalloutTitle">Artifacts (served)</div>
              <div className="ptHint">
                {invdesign.invResult?.artifact_relpaths?.invdesign_report_json ? (
                  <>
                    <a href={invdesign.buildRunArtifactUrl(invdesign.apiBase, invdesign.invResult.run_id, invdesign.invResult.artifact_relpaths.invdesign_report_json)} target="_blank" rel="noreferrer">
                      Open report (JSON)
                    </a>{" "}
                    <span className="ptMono">[{String(invdesign.invResult.artifact_relpaths.invdesign_report_json)}]</span>
                    <br />
                  </>
                ) : null}
                {invdesign.invResult?.artifact_relpaths?.optimized_graph_json ? (
                  <>
                    <a href={invdesign.buildRunArtifactUrl(invdesign.apiBase, invdesign.invResult.run_id, invdesign.invResult.artifact_relpaths.optimized_graph_json)} target="_blank" rel="noreferrer">
                      Open optimized graph (JSON)
                    </a>{" "}
                    <span className="ptMono">[{String(invdesign.invResult.artifact_relpaths.optimized_graph_json)}]</span>
                    <br />
                  </>
                ) : null}
                <a href={invdesign.buildRunManifestUrl(invdesign.apiBase, invdesign.invResult.run_id)} target="_blank" rel="noreferrer">
                  Open run manifest (JSON)
                </a>
              </div>
            </div>
          ) : null}
          {invdesign.invResult ? <pre className="ptPre">{invdesign.prettyJson(invdesign.invResult)}</pre> : <div className="ptHint">Run inverse design to see outputs.</div>}
        </div>

        <div className="ptRightSection">
          <div className="ptRightTitle">Workflow Chain Result</div>
          {invdesign.workflowResult?.run_id && invdesign.workflowResult?.artifact_relpaths ? (
            <div className="ptCallout">
              <div className="ptCalloutTitle">Artifacts (served)</div>
              <div className="ptHint">
                {invdesign.workflowResult?.artifact_relpaths?.workflow_report_json ? (
                  <>
                    <a
                      href={invdesign.buildRunArtifactUrl(
                        invdesign.apiBase,
                        invdesign.workflowResult.run_id,
                        invdesign.workflowResult.artifact_relpaths.workflow_report_json,
                      )}
                      target="_blank"
                      rel="noreferrer"
                    >
                      Open workflow report (JSON)
                    </a>{" "}
                    <span className="ptMono">[{String(invdesign.workflowResult.artifact_relpaths.workflow_report_json)}]</span>
                    <br />
                  </>
                ) : null}
                {invdesign.workflowResult?.run_id ? (
                  <>
                    <a href={invdesign.buildRunBundleUrl(invdesign.apiBase, invdesign.workflowResult.run_id)} target="_blank" rel="noreferrer">
                      Download evidence bundle (zip)
                    </a>
                    <br />
                  </>
                ) : null}
                <a href={invdesign.buildRunManifestUrl(invdesign.apiBase, invdesign.workflowResult.run_id)} target="_blank" rel="noreferrer">
                  Open workflow run manifest (JSON)
                </a>
                <br />
                {invdesign.workflowResult?.steps?.invdesign?.run_id ? (
                  <>
                    <a href={invdesign.buildRunManifestUrl(invdesign.apiBase, invdesign.workflowResult.steps.invdesign.run_id)} target="_blank" rel="noreferrer">
                      Open invdesign child run manifest (JSON)
                    </a>
                    <br />
                  </>
                ) : null}
                {invdesign.workflowResult?.steps?.layout_build?.run_id ? (
                  <>
                    <a href={invdesign.buildRunManifestUrl(invdesign.apiBase, invdesign.workflowResult.steps.layout_build.run_id)} target="_blank" rel="noreferrer">
                      Open layout build child run manifest (JSON)
                    </a>
                    <br />
                  </>
                ) : null}
                {invdesign.workflowResult?.steps?.lvs_lite?.run_id ? (
                  <>
                    <a href={invdesign.buildRunManifestUrl(invdesign.apiBase, invdesign.workflowResult.steps.lvs_lite.run_id)} target="_blank" rel="noreferrer">
                      Open LVS-lite child run manifest (JSON)
                    </a>
                    <br />
                  </>
                ) : null}
                {invdesign.workflowResult?.steps?.klayout_pack?.run_id ? (
                  <>
                    <a href={invdesign.buildRunManifestUrl(invdesign.apiBase, invdesign.workflowResult.steps.klayout_pack.run_id)} target="_blank" rel="noreferrer">
                      Open KLayout child run manifest (JSON)
                    </a>
                    <br />
                  </>
                ) : null}
                {invdesign.workflowResult?.steps?.spice_export?.run_id ? (
                  <>
                    <a href={invdesign.buildRunManifestUrl(invdesign.apiBase, invdesign.workflowResult.steps.spice_export.run_id)} target="_blank" rel="noreferrer">
                      Open SPICE export child run manifest (JSON)
                    </a>
                    <br />
                  </>
                ) : null}
              </div>
            </div>
          ) : null}
          {invdesign.workflowResult ? <pre className="ptPre">{invdesign.prettyJson(invdesign.workflowResult)}</pre> : <div className="ptHint">Run full workflow to see chained evidence.</div>}
        </div>
      </div>
    );
  }

  if (activeRightTab === "layout") {
    return (
      <div id="pt-panel-graph-layout" role="tabpanel" aria-labelledby="pt-tab-graph-layout" className="ptRightBody">
        <div className="ptRightSection">
          <div className="ptRightTitle">Layout Build</div>

          <JsonBox
            title="pdk (advanced)"
            value={layout.layoutPdk}
            onApply={(text) => {
              const parsed = layout.safeParseJson(text);
              if (!parsed.ok) return parsed;
              if (!parsed.value || typeof parsed.value !== "object" || Array.isArray(parsed.value)) return { ok: false, error: "PDK must be a JSON object." };
              layout.onSetLayoutPdk(parsed.value);
              return { ok: true };
            }}
          />

          <JsonBox
            title="layout settings (advanced)"
            value={layout.layoutSettings}
            onApply={(text) => {
              const parsed = layout.safeParseJson(text);
              if (!parsed.ok) return parsed;
              if (!parsed.value || typeof parsed.value !== "object" || Array.isArray(parsed.value)) return { ok: false, error: "Settings must be a JSON object." };
              layout.onSetLayoutSettings(parsed.value);
              return { ok: true };
            }}
          />

          <div className="ptBtnRow">
            <button className="ptBtn ptBtnPrimary" onClick={layout.onRunLayoutBuild} disabled={layout.busy}>
              Build Layout Artifacts
            </button>
          </div>
          <div className="ptHint">
            Emits <span className="ptMono">ports.json</span> + <span className="ptMono">routes.json</span> always. <span className="ptMono">layout.gds</span> is emitted only when{" "}
            <span className="ptMono">gdstk</span> is installed.
          </div>
        </div>

        <div className="ptRightSection">
          <div className="ptRightTitle">Layout Build Result</div>
          {layout.layoutBuildResult?.run_id && layout.layoutBuildResult?.artifact_relpaths ? (
            <div className="ptCallout">
              <div className="ptCalloutTitle">Artifacts (served)</div>
              <div className="ptHint">
                {layout.layoutBuildResult?.artifact_relpaths?.layout_build_report_json ? (
                  <>
                    <a
                      href={layout.buildRunArtifactUrl(layout.apiBase, layout.layoutBuildResult.run_id, layout.layoutBuildResult.artifact_relpaths.layout_build_report_json)}
                      target="_blank"
                      rel="noreferrer"
                    >
                      Open layout report (JSON)
                    </a>{" "}
                    <span className="ptMono">[{String(layout.layoutBuildResult.artifact_relpaths.layout_build_report_json)}]</span>
                    <br />
                  </>
                ) : null}
                {layout.layoutBuildResult?.artifact_relpaths?.ports_json ? (
                  <>
                    <a
                      href={layout.buildRunArtifactUrl(layout.apiBase, layout.layoutBuildResult.run_id, layout.layoutBuildResult.artifact_relpaths.ports_json)}
                      target="_blank"
                      rel="noreferrer"
                    >
                      Open ports (JSON)
                    </a>{" "}
                    <span className="ptMono">[{String(layout.layoutBuildResult.artifact_relpaths.ports_json)}]</span>
                    <br />
                  </>
                ) : null}
                {layout.layoutBuildResult?.artifact_relpaths?.routes_json ? (
                  <>
                    <a
                      href={layout.buildRunArtifactUrl(layout.apiBase, layout.layoutBuildResult.run_id, layout.layoutBuildResult.artifact_relpaths.routes_json)}
                      target="_blank"
                      rel="noreferrer"
                    >
                      Open routes (JSON)
                    </a>{" "}
                    <span className="ptMono">[{String(layout.layoutBuildResult.artifact_relpaths.routes_json)}]</span>
                    <br />
                  </>
                ) : null}
                {layout.layoutBuildResult?.artifact_relpaths?.layout_provenance_json ? (
                  <>
                    <a
                      href={layout.buildRunArtifactUrl(layout.apiBase, layout.layoutBuildResult.run_id, layout.layoutBuildResult.artifact_relpaths.layout_provenance_json)}
                      target="_blank"
                      rel="noreferrer"
                    >
                      Open provenance (JSON)
                    </a>{" "}
                    <span className="ptMono">[{String(layout.layoutBuildResult.artifact_relpaths.layout_provenance_json)}]</span>
                    <br />
                  </>
                ) : null}
                {layout.layoutBuildResult?.artifact_relpaths?.layout_gds ? (
                  <>
                    <a
                      href={layout.buildRunArtifactUrl(layout.apiBase, layout.layoutBuildResult.run_id, layout.layoutBuildResult.artifact_relpaths.layout_gds)}
                      target="_blank"
                      rel="noreferrer"
                    >
                      Open layout (GDS)
                    </a>{" "}
                    <span className="ptMono">[{String(layout.layoutBuildResult.artifact_relpaths.layout_gds)}]</span>
                    <br />
                  </>
                ) : null}
                <a href={layout.buildRunManifestUrl(layout.apiBase, layout.layoutBuildResult.run_id)} target="_blank" rel="noreferrer">
                  Open run manifest (JSON)
                </a>
              </div>
            </div>
          ) : null}
          {layout.layoutBuildResult ? <pre className="ptPre">{layout.prettyJson(layout.layoutBuildResult)}</pre> : <div className="ptHint">Build to see outputs.</div>}
        </div>
      </div>
    );
  }

  if (activeRightTab === "lvs") {
    return (
      <div id="pt-panel-graph-lvs" role="tabpanel" aria-labelledby="pt-tab-graph-lvs" className="ptRightBody">
        <div className="ptRightSection">
          <div className="ptRightTitle">LVS-lite</div>

          <JsonBox
            title="lvs settings (advanced)"
            value={lvs.lvsSettings}
            onApply={(text) => {
              const parsed = lvs.safeParseJson(text);
              if (!parsed.ok) return parsed;
              if (!parsed.value || typeof parsed.value !== "object" || Array.isArray(parsed.value)) return { ok: false, error: "Settings must be a JSON object." };
              lvs.onSetLvsSettings(parsed.value);
              return { ok: true };
            }}
          />

          <div className="ptBtnRow">
            <button className="ptBtn ptBtnPrimary" onClick={lvs.onRunLvsLite} disabled={lvs.busy || !lvs.layoutBuildResult?.run_id}>
              Run LVS-lite (uses last Layout run)
            </button>
          </div>
          {!lvs.layoutBuildResult?.run_id ? (
            <div className="ptHint">
              Run <span className="ptMono">Layout</span> build first to generate ports/routes.
            </div>
          ) : null}
        </div>

        <div className="ptRightSection">
          <div className="ptRightTitle">LVS-lite Result</div>
          {lvs.lvsResult?.run_id && lvs.lvsResult?.artifact_relpaths ? (
            <div className="ptCallout">
              <div className="ptCalloutTitle">Artifacts (served)</div>
              <div className="ptHint">
                {lvs.lvsResult?.artifact_relpaths?.lvs_lite_report_json ? (
                  <>
                    <a href={lvs.buildRunArtifactUrl(lvs.apiBase, lvs.lvsResult.run_id, lvs.lvsResult.artifact_relpaths.lvs_lite_report_json)} target="_blank" rel="noreferrer">
                      Open LVS-lite report (JSON)
                    </a>{" "}
                    <span className="ptMono">[{String(lvs.lvsResult.artifact_relpaths.lvs_lite_report_json)}]</span>
                    <br />
                  </>
                ) : null}
                <a href={lvs.buildRunManifestUrl(lvs.apiBase, lvs.lvsResult.run_id)} target="_blank" rel="noreferrer">
                  Open run manifest (JSON)
                </a>
              </div>
            </div>
          ) : null}
          {lvs.lvsResult ? <pre className="ptPre">{lvs.prettyJson(lvs.lvsResult)}</pre> : <div className="ptHint">Run LVS-lite to see mismatches.</div>}
        </div>
      </div>
    );
  }

  if (activeRightTab === "klayout") {
    return (
      <div id="pt-panel-graph-klayout" role="tabpanel" aria-labelledby="pt-tab-graph-klayout" className="ptRightBody">
        <div className="ptRightSection">
          <div className="ptRightTitle">KLayout Artifact Pack (DRC-lite)</div>

          <JsonBox
            title="klayout pack settings (advanced)"
            value={klayout.klayoutPackSettings}
            onApply={(text) => {
              const parsed = klayout.safeParseJson(text);
              if (!parsed.ok) return parsed;
              if (!parsed.value || typeof parsed.value !== "object" || Array.isArray(parsed.value)) return { ok: false, error: "Settings must be a JSON object." };
              klayout.onSetKlayoutPackSettings(parsed.value);
              return { ok: true };
            }}
          />

          <div className="ptBtnRow">
            <button
              className="ptBtn ptBtnPrimary"
              onClick={klayout.onRunKlayoutPack}
              disabled={klayout.busy || !klayout.layoutBuildResult?.run_id || !klayout.layoutBuildResult?.artifact_relpaths?.layout_gds}
            >
              Run KLayout Pack (uses last Layout run)
            </button>
          </div>
          {!klayout.layoutBuildResult?.run_id ? (
            <div className="ptHint">
              Run <span className="ptMono">Layout</span> build first to create a layout run.
            </div>
          ) : null}
          {klayout.layoutBuildResult?.run_id && !klayout.layoutBuildResult?.artifact_relpaths?.layout_gds ? (
            <div className="ptHint">
              This environment did not emit <span className="ptMono">layout.gds</span>. Install <span className="ptMono">gdstk</span> (e.g. <span className="ptMono">pip install 'photonstrust[layout]'</span>) and rebuild
              layout.
            </div>
          ) : null}
          <div className="ptHint">Runs the repo-owned KLayout macro template in batch mode and captures stdout/stderr + output hashes as a reviewable artifact pack.</div>
        </div>

        <div className="ptRightSection">
          <div className="ptRightTitle">KLayout Pack Result</div>
          {klayout.klayoutPackResult?.run_id && klayout.klayoutPackResult?.artifact_relpaths ? (
            <div className="ptCallout">
              <div className="ptCalloutTitle">Artifacts (served)</div>
              <div className="ptHint">
                {klayout.klayoutPackResult?.artifact_relpaths?.klayout_run_artifact_pack_json ? (
                  <>
                    <a
                      href={klayout.buildRunArtifactUrl(
                        klayout.apiBase,
                        klayout.klayoutPackResult.run_id,
                        klayout.klayoutPackResult.artifact_relpaths.klayout_run_artifact_pack_json,
                      )}
                      target="_blank"
                      rel="noreferrer"
                    >
                      Open artifact pack (JSON)
                    </a>{" "}
                    <span className="ptMono">[{String(klayout.klayoutPackResult.artifact_relpaths.klayout_run_artifact_pack_json)}]</span>
                    <br />
                  </>
                ) : null}
                {klayout.klayoutPackResult?.artifact_relpaths?.drc_lite_json ? (
                  <>
                    <a href={klayout.buildRunArtifactUrl(klayout.apiBase, klayout.klayoutPackResult.run_id, klayout.klayoutPackResult.artifact_relpaths.drc_lite_json)} target="_blank" rel="noreferrer">
                      Open DRC-lite report (JSON)
                    </a>{" "}
                    <span className="ptMono">[{String(klayout.klayoutPackResult.artifact_relpaths.drc_lite_json)}]</span>
                    <br />
                  </>
                ) : null}
                {klayout.klayoutPackResult?.artifact_relpaths?.ports_extracted_json ? (
                  <>
                    <a
                      href={klayout.buildRunArtifactUrl(klayout.apiBase, klayout.klayoutPackResult.run_id, klayout.klayoutPackResult.artifact_relpaths.ports_extracted_json)}
                      target="_blank"
                      rel="noreferrer"
                    >
                      Open extracted ports (JSON)
                    </a>{" "}
                    <span className="ptMono">[{String(klayout.klayoutPackResult.artifact_relpaths.ports_extracted_json)}]</span>
                    <br />
                  </>
                ) : null}
                {klayout.klayoutPackResult?.artifact_relpaths?.routes_extracted_json ? (
                  <>
                    <a
                      href={klayout.buildRunArtifactUrl(klayout.apiBase, klayout.klayoutPackResult.run_id, klayout.klayoutPackResult.artifact_relpaths.routes_extracted_json)}
                      target="_blank"
                      rel="noreferrer"
                    >
                      Open extracted routes (JSON)
                    </a>{" "}
                    <span className="ptMono">[{String(klayout.klayoutPackResult.artifact_relpaths.routes_extracted_json)}]</span>
                    <br />
                  </>
                ) : null}
                {klayout.klayoutPackResult?.artifact_relpaths?.macro_provenance_json ? (
                  <>
                    <a
                      href={klayout.buildRunArtifactUrl(klayout.apiBase, klayout.klayoutPackResult.run_id, klayout.klayoutPackResult.artifact_relpaths.macro_provenance_json)}
                      target="_blank"
                      rel="noreferrer"
                    >
                      Open macro provenance (JSON)
                    </a>{" "}
                    <span className="ptMono">[{String(klayout.klayoutPackResult.artifact_relpaths.macro_provenance_json)}]</span>
                    <br />
                  </>
                ) : null}
                {klayout.klayoutPackResult?.artifact_relpaths?.klayout_stdout_txt ? (
                  <>
                    <a
                      href={klayout.buildRunArtifactUrl(klayout.apiBase, klayout.klayoutPackResult.run_id, klayout.klayoutPackResult.artifact_relpaths.klayout_stdout_txt)}
                      target="_blank"
                      rel="noreferrer"
                    >
                      Open stdout (txt)
                    </a>{" "}
                    <span className="ptMono">[{String(klayout.klayoutPackResult.artifact_relpaths.klayout_stdout_txt)}]</span>
                    <br />
                  </>
                ) : null}
                {klayout.klayoutPackResult?.artifact_relpaths?.klayout_stderr_txt ? (
                  <>
                    <a
                      href={klayout.buildRunArtifactUrl(klayout.apiBase, klayout.klayoutPackResult.run_id, klayout.klayoutPackResult.artifact_relpaths.klayout_stderr_txt)}
                      target="_blank"
                      rel="noreferrer"
                    >
                      Open stderr (txt)
                    </a>{" "}
                    <span className="ptMono">[{String(klayout.klayoutPackResult.artifact_relpaths.klayout_stderr_txt)}]</span>
                    <br />
                  </>
                ) : null}
                <a href={klayout.buildRunManifestUrl(klayout.apiBase, klayout.klayoutPackResult.run_id)} target="_blank" rel="noreferrer">
                  Open run manifest (JSON)
                </a>
              </div>
            </div>
          ) : null}
          {klayout.klayoutPackResult ? <pre className="ptPre">{klayout.prettyJson(klayout.klayoutPackResult)}</pre> : <div className="ptHint">Run KLayout pack to see outputs.</div>}
        </div>
      </div>
    );
  }

  if (activeRightTab === "spice") {
    return (
      <div id="pt-panel-graph-spice" role="tabpanel" aria-labelledby="pt-tab-graph-spice" className="ptRightBody">
        <div className="ptRightSection">
          <div className="ptRightTitle">SPICE Export</div>

          <JsonBox
            title="spice settings (advanced)"
            value={spice.spiceSettings}
            onApply={(text) => {
              const parsed = spice.safeParseJson(text);
              if (!parsed.ok) return parsed;
              if (!parsed.value || typeof parsed.value !== "object" || Array.isArray(parsed.value)) return { ok: false, error: "Settings must be a JSON object." };
              spice.onSetSpiceSettings(parsed.value);
              return { ok: true };
            }}
          />

          <div className="ptBtnRow">
            <button className="ptBtn ptBtnPrimary" onClick={spice.onRunSpiceExport} disabled={spice.busy}>
              Export SPICE Netlist
            </button>
          </div>
          <div className="ptHint">This is a deterministic connectivity export and mapping seam (not optical-physics signoff).</div>
        </div>

        <div className="ptRightSection">
          <div className="ptRightTitle">SPICE Export Result</div>
          {spice.spiceResult?.run_id && spice.spiceResult?.artifact_relpaths ? (
            <div className="ptCallout">
              <div className="ptCalloutTitle">Artifacts (served)</div>
              <div className="ptHint">
                {spice.spiceResult?.artifact_relpaths?.spice_export_report_json ? (
                  <>
                    <a
                      href={spice.buildRunArtifactUrl(spice.apiBase, spice.spiceResult.run_id, spice.spiceResult.artifact_relpaths.spice_export_report_json)}
                      target="_blank"
                      rel="noreferrer"
                    >
                      Open export report (JSON)
                    </a>{" "}
                    <span className="ptMono">[{String(spice.spiceResult.artifact_relpaths.spice_export_report_json)}]</span>
                    <br />
                  </>
                ) : null}
                {spice.spiceResult?.artifact_relpaths?.netlist_sp ? (
                  <>
                    <a href={spice.buildRunArtifactUrl(spice.apiBase, spice.spiceResult.run_id, spice.spiceResult.artifact_relpaths.netlist_sp)} target="_blank" rel="noreferrer">
                      Open netlist (SPICE)
                    </a>{" "}
                    <span className="ptMono">[{String(spice.spiceResult.artifact_relpaths.netlist_sp)}]</span>
                    <br />
                  </>
                ) : null}
                {spice.spiceResult?.artifact_relpaths?.spice_map_json ? (
                  <>
                    <a href={spice.buildRunArtifactUrl(spice.apiBase, spice.spiceResult.run_id, spice.spiceResult.artifact_relpaths.spice_map_json)} target="_blank" rel="noreferrer">
                      Open mapping (JSON)
                    </a>{" "}
                    <span className="ptMono">[{String(spice.spiceResult.artifact_relpaths.spice_map_json)}]</span>
                    <br />
                  </>
                ) : null}
                {spice.spiceResult?.artifact_relpaths?.spice_provenance_json ? (
                  <>
                    <a
                      href={spice.buildRunArtifactUrl(spice.apiBase, spice.spiceResult.run_id, spice.spiceResult.artifact_relpaths.spice_provenance_json)}
                      target="_blank"
                      rel="noreferrer"
                    >
                      Open provenance (JSON)
                    </a>{" "}
                    <span className="ptMono">[{String(spice.spiceResult.artifact_relpaths.spice_provenance_json)}]</span>
                    <br />
                  </>
                ) : null}
                <a href={spice.buildRunManifestUrl(spice.apiBase, spice.spiceResult.run_id)} target="_blank" rel="noreferrer">
                  Open run manifest (JSON)
                </a>
              </div>
            </div>
          ) : null}
          {spice.spiceResult ? <pre className="ptPre">{spice.prettyJson(spice.spiceResult)}</pre> : <div className="ptHint">Export to see netlist + mapping.</div>}
        </div>
      </div>
    );
  }

  if (activeRightTab === "graph") {
    return (
      <div id="pt-panel-graph-graph" role="tabpanel" aria-labelledby="pt-tab-graph-graph" className="ptRightBody">
        <div className="ptRightSection">
          <div className="ptRightTitle">Graph Payload</div>
          <pre className="ptPre">{graphJson.exportText}</pre>
          <div className="ptBtnRow">
            <button
              className="ptBtn ptBtnGhost"
              onClick={async () => {
                try {
                  await navigator.clipboard.writeText(graphJson.exportText);
                  if (typeof graphJson.onCopied === "function") graphJson.onCopied();
                } catch (err) {
                  if (typeof graphJson.onCopyFailed === "function") graphJson.onCopyFailed(err);
                }
              }}
            >
              Copy
            </button>
          </div>
        </div>
      </div>
    );
  }

  return null;
}
