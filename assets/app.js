const mapNodes = document.getElementById("mapNodes");
const statusLabel = document.getElementById("status");
const template = document.getElementById("paperNodeTemplate");
const PAPERS_FOLDER = "pappers_html";

const normalizeHtmlFileName = (entry) => {
  if (typeof entry !== "string") return null;

  const fileName = decodeURIComponent(entry).split("/").pop();
  if (!fileName || fileName === "index.html") return null;

  return /^papper[\w.-]*\.html$/i.test(fileName) ? fileName : null;
};

const extractHtmlFiles = (rawText) => {
  const matcher = /href=["']([^"']+\.html)["']/gi;
  const files = new Set();

  for (const match of rawText.matchAll(matcher)) {
    const fileName = normalizeHtmlFileName(match[1]);
    if (fileName) files.add(fileName);
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
    .map(normalizeHtmlFileName)
    .filter(Boolean)
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

const renderNodes = (files, discoveryMode) => {
  mapNodes.replaceChildren();

  if (files.length === 0) {
    statusLabel.innerHTML =
      "Aún no hay pappers detectados. Agrega archivos <code>papper_id.html</code> en <code>pappers_html/</code>.";
    return;
  }

  statusLabel.textContent = `Encontrados ${files.length} pappers (${discoveryMode}).`;

  const radius = computeRadius(files.length);
  const slice = (Math.PI * 2) / files.length;

  files.forEach((file, index) => {
    const node = template.content.firstElementChild.cloneNode(true);
    const angle = -Math.PI / 2 + slice * index;
    const x = Math.cos(angle) * radius;
    const y = Math.sin(angle) * radius;

    const paperId = file.replace(/\.html$/i, "").replace(/^papper[_-]?/i, "");
    node.href = `${PAPERS_FOLDER}/${file}`;
    node.setAttribute("aria-label", `Abrir resumen ${paperId}`);
    node.style.setProperty("--x", `${x}px`);
    node.style.setProperty("--y", `${y}px`);
    node.style.setProperty("--angle", `${angle + Math.PI}rad`);
    node.style.setProperty("--line-length", `${Math.max(radius - 92, 1)}px`);
    node.style.animationDelay = `${index * 55}ms`;
    node.querySelector(".paper-id").textContent = paperId;

    mapNodes.appendChild(node);
  });
};

const loadPapers = async () => {
  const discovered = new Set();
  const modes = [];

  try {
    const files = await loadFromManifest();
    files.forEach((file) => discovered.add(file));
    if (files.length > 0) modes.push("index.json");
  } catch {
    // El manifiesto es opcional: si falta o es inválido, probamos el índice del directorio.
  }

  try {
    const files = await loadFromDirectoryIndex();
    files.forEach((file) => discovered.add(file));
    if (files.length > 0) modes.push("carpeta pappers_html");
  } catch {
    // Algunos hosts estáticos no permiten listar carpetas; en esos casos se usa index.json.
  }

  const files = [...discovered].sort((a, b) => a.localeCompare(b, "es"));
  renderNodes(files, modes.length > 0 ? modes.join(" + ") : "sin manifiesto detectable");
};

loadPapers();
