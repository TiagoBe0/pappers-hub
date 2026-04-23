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

const cleanText = (value) => value?.replace(/\s+/g, " ").trim() || "";

const buildSummary = (doc, title) => {
  const candidates = [...doc.querySelectorAll("main p, article p, p")]
    .map((paragraph) => cleanText(paragraph.textContent))
    .filter((text) => text.length > 70 && text !== title && !text.startsWith("Archivo fuente:"));

  const summary = candidates[0] || "Resumen disponible en la ficha completa del paper.";
  return summary.length > 220 ? `${summary.slice(0, 217).trim()}...` : summary;
};

const loadPaperMeta = async (file) => {
  try {
    const response = await fetch(`${PAPERS_FOLDER}/${file}`, { cache: "no-store" });
    if (!response.ok) {
      throw new Error("No se pudo leer el papper");
    }

    const pageText = await response.text();
    const doc = new DOMParser().parseFromString(pageText, "text/html");
    const title = cleanText(doc.querySelector("h1")?.textContent || doc.querySelector("title")?.textContent) || formatPaperLabel(file);
    return {
      file,
      label: title,
      summary: buildSummary(doc, title),
    };
  } catch {
    return {
      file,
      label: formatPaperLabel(file),
      summary: "Resumen disponible en la ficha completa del paper.",
    };
  }
};

const loadPaperItems = async (files) => {
  const items = await Promise.all(files.map((file) => loadPaperMeta(file)));

  return items.sort((a, b) => a.label.localeCompare(b.label, "es"));
};

const computeBaseRadius = (count) => {
  if (count <= 4) return 640;
  if (count <= 8) return 860;
  if (count <= 14) return 1250;
  return 1480;
};

const computeNodeRadius = (baseRadius, index, count) => {
  const ringOffsets = count <= 6 ? [-120, 150] : [-260, 100, 390, -80, 250];
  return baseRadius + ringOffsets[index % ringOffsets.length];
};

const renderNodes = (items) => {
  mapNodes.replaceChildren();

  if (items.length === 0) {
    statusLabel.textContent = "Aún no hay pappers en pappers_html/.";
    return;
  }

  statusLabel.textContent = `Encontrados ${items.length} pappers.`;

  const baseRadius = computeBaseRadius(items.length);
  const slice = (Math.PI * 2) / items.length;

  items.forEach(({ file, label, summary }, index) => {
    const node = template.content.firstElementChild.cloneNode(true);
    const angle = -Math.PI / 2 + slice * index;
    const radius = computeNodeRadius(baseRadius, index, items.length);
    const x = Math.cos(angle) * radius;
    const y = Math.sin(angle) * radius;

    node.href = `${PAPERS_FOLDER}/${file}`;
    node.style.setProperty("--x", `${x}px`);
    node.style.setProperty("--y", `${y}px`);
    node.style.setProperty("--angle", `${angle}rad`);
    node.style.setProperty("--connector-angle", `${angle + Math.PI}rad`);
    node.style.setProperty("--line-length", `${Math.max(radius - 120, 1)}px`);
    node.style.setProperty("--float-distance", `${index % 2 === 0 ? -16 : 13}px`);
    node.style.setProperty("--float-tilt", `${index % 2 === 0 ? -0.55 : 0.55}deg`);
    node.style.animationDelay = `${index * 55}ms, ${index * -320}ms`;
    node.title = label;
    node.querySelector(".paper-id").textContent = label;
    node.querySelector(".paper-summary").textContent = summary;

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
