import { createApp } from "vue";

import App from "./App.vue";
import "@wikimedia/codex/dist/codex.style.css";
import "./styles.css";

const rootNode = document.getElementById("root");
if (!rootNode) {
  throw new Error("Missing root element");
}

createApp(App).mount(rootNode);
