import { renderMarkdown } from "./markdown";
import "./style.css";

const root = document.querySelector<HTMLElement>("#app");

if (!root) {
  throw new Error("viewer mount #app is missing");
}

root.classList.add("markdown-document");
const { fragment } = renderMarkdown("Markdown viewer loading", window.location.href);
root.replaceChildren(fragment);
