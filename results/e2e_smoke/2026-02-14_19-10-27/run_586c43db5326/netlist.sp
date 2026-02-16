* PhotonTrust SPICE export v0.1
* generated_at=2026-02-14T18:10:32.088836+00:00
* graph_id=e2e_pic_mzi
* graph_hash=3417d95e0edf40b314069061567192e3e4dff84b491c312fe390c9f473591a00
.subckt PT_TOP

Xcpl_in n_cpl_in_in1 n_cpl_in_in2 n_cpl_in_out1 n_cpl_in_out2 PT_pic_coupler coupling_ratio=0.5 insertion_loss_db=0.2
Xcpl_out n_cpl_out_in1 n_cpl_out_in2 n_cpl_out_out1 n_cpl_out_out2 PT_pic_coupler coupling_ratio=0.5 insertion_loss_db=0.2
Xps1 n_cpl_in_out1 n_cpl_out_in1 PT_pic_phase_shifter insertion_loss_db=0.1 phase_rad=3.5021032859689494
Xps2 n_cpl_in_out2 n_cpl_out_in2 PT_pic_phase_shifter insertion_loss_db=0.1 phase_rad=1.0
.ends PT_TOP
.end

* Stub subckt for kind=pic.coupler
.subckt PT_pic_coupler in1 in2 out1 out2
* TODO: replace with foundry/EDA-provided compact model subcircuit
.ends PT_pic_coupler

* Stub subckt for kind=pic.phase_shifter
.subckt PT_pic_phase_shifter in out
* TODO: replace with foundry/EDA-provided compact model subcircuit
.ends PT_pic_phase_shifter
