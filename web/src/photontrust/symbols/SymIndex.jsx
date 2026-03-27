import SymWaveguide from "./SymWaveguide";
import SymGratingCoupler from "./SymGratingCoupler";
import SymEdgeCoupler from "./SymEdgeCoupler";
import SymPhaseShifter from "./SymPhaseShifter";
import SymIsolator from "./SymIsolator";
import SymRing from "./SymRing";
import SymCoupler from "./SymCoupler";
import SymMMI from "./SymMMI";
import SymYBranch from "./SymYBranch";
import SymCrossing from "./SymCrossing";
import SymMZM from "./SymMZM";
import SymPhotodetector from "./SymPhotodetector";
import SymAWG from "./SymAWG";
import SymHeater from "./SymHeater";
import SymSSC from "./SymSSC";
import SymTouchstone from "./SymTouchstone";

const SYMBOL_MAP = {
  "pic.waveguide": SymWaveguide,
  "pic.grating_coupler": SymGratingCoupler,
  "pic.edge_coupler": SymEdgeCoupler,
  "pic.phase_shifter": SymPhaseShifter,
  "pic.isolator_2port": SymIsolator,
  "pic.ring": SymRing,
  "pic.coupler": SymCoupler,
  "pic.mmi": SymMMI,
  "pic.y_branch": SymYBranch,
  "pic.crossing": SymCrossing,
  "pic.mzm": SymMZM,
  "pic.photodetector": SymPhotodetector,
  "pic.awg": SymAWG,
  "pic.heater": SymHeater,
  "pic.ssc": SymSSC,
  "pic.touchstone_2port": SymTouchstone,
  "pic.touchstone_nport": SymTouchstone,
};

export default function ComponentSymbol({ kind, width = 80, height = 50 }) {
  const Sym = SYMBOL_MAP[kind];
  if (!Sym) return null;
  return <Sym width={width} height={height} />;
}
