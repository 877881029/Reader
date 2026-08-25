import "./style.css";
import { createViewer } from "./viewer";

const app = document.querySelector<HTMLDivElement>("#app");

if (!app) {
  throw new Error("Missing #app mount point");
}

createViewer(app, {
  slideCount: 1,
  slideWidth: 1600,
  slideHeight: 900,
  onRender(index, host) {
    host.textContent = `Slide ${index + 1} placeholder`;
  },
});
