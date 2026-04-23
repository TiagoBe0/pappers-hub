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

const computeRadius = (count) => {
  if (count <= 4) return 210;
  if (count <= 8) return 280;
  if (count <= 14) return 350;
  return 420;
};

const renderNodes = (files) => {
  mapNodes.replaceChildren();

  if (files.length === 0) {
    statusLabel.textContent = "Aún no hay pappers en pappers_html/.";
    return;
  }

  statusLabel.textContent = `Encontrados ${files.length} pappers.`;

  const radius = computeRadius(files.length);
  const slice = (Math.PI * 2) / files.length;

  files.forEach((file, index) => {
    const node = template.content.firstElementChild.cloneNode(true);
    const angle = -Math.PI / 2 + slice * index;
    const x = Math.cos(angle) * radius;
    const y = Math.sin(angle) * radius;

    const paperId = file.replace(/\.html$/i, "");
    node.href = `${PAPERS_FOLDER}/${file}`;
    node.style.setProperty("--x", `${x}px`);
    node.style.setProperty("--y", `${y}px`);
    node.style.setProperty("--angle", `${angle}rad`);
    node.style.setProperty("--line-length", `${Math.max(radius - 44, 1)}px`);
    node.style.animationDelay = `${index * 55}ms`;
    node.querySelector(".paper-id").textContent = paperId;

    mapNodes.appendChild(node);
  });
};

const loadPapers = async () => {
  try {
    const files = await loadFromManifest();
    renderNodes(files);
    return;
  } catch {
    // fallback silencioso al índice del directorio
  }

  try {
    const files = await loadFromDirectoryIndex();
    renderNodes(files);
  } catch {
    statusLabel.innerHTML =
      "No se pudo descubrir automáticamente los pappers. Añade <code>pappers_html/index.json</code> con un arreglo de archivos.";
  }
};

loadPapers();
