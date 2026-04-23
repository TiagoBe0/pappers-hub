const mapNodes = document.getElementById("mapNodes");
const statusLabel = document.getElementById("status");
const template = document.getElementById("paperNodeTemplate");
const PAPERS_FOLDER = "pappers_html";

const extractHtmlFiles = (rawText) => {
  const matcher = /href=["']([^"']+\.html)["']/gi;
  const files = new Set();
  for (const match of rawText.matchAll(matcher)) {
    const fileName = match[1].split("/").pop();
    if (fileName && /.+\.html$/i.test(fileName)) {
      files.add(fileName);
    }
  }
  return [...files].sort((a, b) => a.localeCompare(b, "es"));
};

const loadFromManifest = async () => {
  const manifestPath = `${PAPERS_FOLDER}/index.json`;
  const response = await fetch(manifestPath, { cache: "no-store" });
  if (!response.ok) {
    throw new Error("No se encontró index.json");
  }

  const json = await response.json();
  if (!Array.isArray(json)) {
    throw new Error("index.json debe ser un arreglo de nombres de archivos");
  }

  return json
    .filter((entry) => typeof entry === "string" && entry.endsWith(".html"))
    .map((entry) => entry.split("/").pop())
    .sort((a, b) => a.localeCompare(b, "es"));
};

const loadFromDirectoryIndex = async () => {
  const response = await fetch(`${PAPERS_FOLDER}/`, { cache: "no-store" });
  if (!response.ok) {
    throw new Error("No se pudo leer el índice del directorio");
  }

  const html = await response.text();
  return extractHtmlFiles(html);
};

const formatPaperLabel = (file) => {
  const words = file
    .replace(/\.html$/i, "")
    .replace(/^resumen[-_]?/i, "")
    .replace(/[-_]+/g, " ")
    .trim();

  return words.charAt(0).toUpperCase() + words.slice(1);
};

const loadPaperTitle = async (file) => {
  try {
    const response = await fetch(`${PAPERS_FOLDER}/${file}`, { cache: "no-store" });
    if (!response.ok) {
      throw new Error("No se pudo leer el papper");
    }

    const pageText = await response.text();
    const doc = new DOMParser().parseFromString(pageText, "text/html");
    const title = doc.querySelector("h1")?.textContent || doc.querySelector("title")?.textContent;
    return title?.replace(/\s+/g, " ").trim() || formatPaperLabel(file);
  } catch {
    return formatPaperLabel(file);
  }
};

const loadPaperItems = async (files) => {
  const items = await Promise.all(
    files.map(async (file) => ({
      file,
      label: await loadPaperTitle(file),
    })),
  );

  return items.sort((a, b) => a.label.localeCompare(b.label, "es"));
};

const computeRadius = (count) => {
  if (count <= 4) return 210;
  if (count <= 8) return 280;
  if (count <= 14) return 350;
  return 420;
};

const renderNodes = (items) => {
  mapNodes.replaceChildren();

  if (items.length === 0) {
    statusLabel.textContent = "Aún no hay pappers en pappers_html/.";
    return;
  }

  statusLabel.textContent = `Encontrados ${items.length} pappers.`;

  const radius = computeRadius(items.length);
  const slice = (Math.PI * 2) / items.length;

  items.forEach(({ file, label }, index) => {
    const node = template.content.firstElementChild.cloneNode(true);
    const angle = -Math.PI / 2 + slice * index;
    const x = Math.cos(angle) * radius;
    const y = Math.sin(angle) * radius;

    node.href = `${PAPERS_FOLDER}/${file}`;
    node.style.setProperty("--x", `${x}px`);
    node.style.setProperty("--y", `${y}px`);
    node.style.setProperty("--angle", `${angle}rad`);
    node.style.setProperty("--connector-angle", `${angle + Math.PI}rad`);
    node.style.setProperty("--line-length", `${Math.max(radius - 44, 1)}px`);
    node.style.setProperty("--float-distance", `${index % 2 === 0 ? -12 : 12}px`);
    node.style.setProperty("--float-tilt", `${index % 2 === 0 ? -0.8 : 0.8}deg`);
    node.style.animationDelay = `${index * 55}ms, ${index * -320}ms`;
    node.title = label;
    node.querySelector(".paper-id").textContent = label;

    mapNodes.appendChild(node);
  });
};

const loadPapers = async () => {
  try {
    const files = await loadFromManifest();
    const items = await loadPaperItems(files);
    renderNodes(items);
    return;
  } catch {
    // fallback silencioso al índice del directorio
  }

  try {
    const files = await loadFromDirectoryIndex();
    const items = await loadPaperItems(files);
    renderNodes(items);
  } catch {
    statusLabel.innerHTML =
      "No se pudo descubrir automáticamente los pappers. Añade <code>pappers_html/index.json</code> con un arreglo de archivos.";
  }
};

loadPapers();
