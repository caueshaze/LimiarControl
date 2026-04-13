import "./index.css";
import React from "react";
import { createRoot } from "react-dom/client";
import { BattleMapPage } from "./features/battle-map/battle-map-page";

const container = document.getElementById("root");
if (container) {
  createRoot(container).render(<BattleMapPage />);
}
