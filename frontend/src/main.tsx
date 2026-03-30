import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import App from "./App";
import "./styles.css";
import "@wikimedia/codex/dist/codex.style.css";

const rootNode = document.getElementById("root");
if (!rootNode) {
  throw new Error("Missing root element");
}

createRoot(rootNode).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
