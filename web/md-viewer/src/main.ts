const root = document.querySelector<HTMLElement>("#app");

if (!root) {
  throw new Error("viewer mount #app is missing");
}

root.textContent = "Markdown viewer loading";
