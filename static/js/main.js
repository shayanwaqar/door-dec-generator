const namesTextarea = document.getElementById("names");
const nameCountEl = document.getElementById("name-count");
const arrangeBtn = document.getElementById("arrangeBtn");
const previewBtn = document.getElementById("previewBtn");
const generateBtn = document.getElementById("generateBtn");
const statusEl = document.getElementById("status");
const modeIndicator = document.getElementById("mode-indicator");
const modeInstructions = document.getElementById("mode-instructions");
const fileInput = document.getElementById("images");
const previewImageContainer = document.getElementById("preview-image-container");
const previewGrid = document.getElementById("preview-grid");
const positionsInput = document.getElementById("positions");
const form = document.getElementById("mainForm");

function updateNameCount() {
  const raw = namesTextarea.value || "";
  const lines = raw.split(/\r?\n/).map(l => l.trim()).filter(l => l.length > 0);
  nameCountEl.textContent = `${lines.length} name${lines.length === 1 ? "" : "s"}`;
}

namesTextarea.addEventListener("input", updateNameCount);
updateNameCount();

arrangeBtn.addEventListener("click", () => {
  const files = fileInput.files;
  if (!files || files.length === 0) {
    statusEl.textContent = "Please upload at least one image to preview.";
    statusEl.className = "error";
    return;
  }

  const hasName = namesTextarea.value.trim().length > 0;
  if (!hasName) {
    statusEl.textContent = "Please enter at least one name to preview.";
    statusEl.className = "error";
    return;
  }

  loadAndDisplayPreviews(true); // Enter Arrange Mode
});

previewBtn.addEventListener("click", () => {
  loadAndDisplayPreviews(false); // Enter Preview Mode
});

async function loadAndDisplayPreviews(isArrangeMode) {
  previewImageContainer.style.display = "none";
  previewBtn.disabled = true;
  arrangeBtn.disabled = true;
  generateBtn.disabled = true;
  statusEl.textContent = "Generating preview...";

  try {
    const formData = new FormData(form);
    const response = await fetch("/preview", { method: "POST", body: formData });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(errorText || "Failed to generate preview.");
    }

    const data = await response.json();

    // Only reset positions if we are not already in an arrange session
    if (Object.keys(positions).length === 0) {
        data.previews.forEach((_, idx) => {
            positions[idx] = { x: 0.5, y: 0.5 };
        });
    }

    previewGrid.innerHTML = ""; // Clear previous previews

    data.previews.forEach((preview, idx) => {
        const { container } = createPreviewElement(preview, isArrangeMode);
        previewGrid.appendChild(container);
    });

    previewImageContainer.style.display = "block";
    statusEl.textContent = "";

    // Update button states based on the new mode
    if (isArrangeMode) {
        modeIndicator.textContent = "Arrange Mode";
        modeInstructions.textContent = "Drag each name to your desired position on the template.";
        arrangeBtn.disabled = true;
        previewBtn.disabled = false;
    } else {
        modeIndicator.textContent = "Preview Mode";
        modeInstructions.textContent = "This is how your generated tags will appear. Click 'Arrange Names' to go back and reposition.";
        arrangeBtn.disabled = false;
        previewBtn.disabled = true;
    }

    // Always ensure the hidden input is up-to-date
    positionsInput.value = JSON.stringify(positions);
  } catch (err) {
    statusEl.textContent = `Error: ${err.message}`;
    statusEl.className = "error";
  } finally {
    generateBtn.disabled = false;
  }
}

function createPreviewElement(preview, inArrangeMode) {
    const wrapper = document.createElement("div");
    wrapper.style.display = "inline-block";
    wrapper.style.margin = "0.5rem";

    const imageContainer = document.createElement("div");
    imageContainer.className = "template-container";
    imageContainer.classList.add(inArrangeMode ? "arrange-mode" : "preview-mode");

    const img = document.createElement("img");
    img.className = "template-image";
    img.src = preview.src;

    imageContainer.appendChild(img);
    wrapper.appendChild(imageContainer);

    // Only add draggable label if in arrange mode
    if (inArrangeMode) {
        const idx = previewGrid.children.length; // Get the index for the new element
        const label = document.createElement("div");
        label.className = "drag-label";
        label.textContent = preview.name;

        // --- Retain State ---
        // Set the initial position of the label from our stored positions object.
        const pos = positions[idx];
        if (pos) {
            label.style.left = `${pos.x * 100}%`;
            label.style.top = `${pos.y * 100}%`;
        }

        imageContainer.appendChild(label);
        makeDraggable(label, imageContainer, idx);

        // --- Add Preset Position Links ---
        const presetsContainer = document.createElement("div");
        presetsContainer.className = "preset-positions";
        
        const presets = { "Top": 0.15, "Center": 0.5, "Bottom": 0.85 };
        for (const [name, yPos] of Object.entries(presets)) {
            const link = document.createElement("span");
            link.className = "preset-link";
            link.textContent = name;
            link.onclick = () => {
                const newPos = { x: 0.5, y: yPos };
                positions[idx] = newPos;
                positionsInput.value = JSON.stringify(positions);
                label.style.left = `${newPos.x * 100}%`;
                label.style.top = `${newPos.y * 100}%`;
            };
            presetsContainer.appendChild(link);
        }

        const centerXLink = document.createElement("span");
        centerXLink.className = "preset-link";
        centerXLink.textContent = "Center X";
        centerXLink.onclick = () => {
            const newPos = { x: 0.5, y: positions[idx].y };
            positions[idx] = newPos;
            positionsInput.value = JSON.stringify(positions);
            label.style.left = `${newPos.x * 100}%`;
        };
        presetsContainer.appendChild(centerXLink);

        const centerYLink = document.createElement("span");
        centerYLink.className = "preset-link";
        centerYLink.textContent = "Center Y";
        centerYLink.onclick = () => {
            const newPos = { x: positions[idx].x, y: 0.5 };
            positions[idx] = newPos;
            positionsInput.value = JSON.stringify(positions);
            label.style.top = `${newPos.y * 100}%`;
        };
        presetsContainer.appendChild(centerYLink);

        wrapper.appendChild(presetsContainer);
    }

    // Return the main wrapper to be appended to the grid
    return { container: wrapper, img };
}

function makeDraggable(label, container, idx) {
  let dragging = false;

  label.addEventListener("mousedown", (e) => {
    dragging = true;
    e.preventDefault();
  });

  document.addEventListener("mousemove", (e) => {
    if (!dragging) return;
    const rect = container.getBoundingClientRect();

    // Position label inside container (top-left origin)
    let x = e.clientX - rect.left;
    let y = e.clientY - rect.top;

    // Clamp inside container bounds
    x = Math.max(0, Math.min(x, rect.width));
    y = Math.max(0, Math.min(y, rect.height));

    label.style.left = x + "px";
    label.style.top = y + "px";
    label.style.transform = "translate(-50%, -50%)";

    positions[idx] = { x: x / rect.width, y: y / rect.height };
    // Update the hidden input on every drag move
    positionsInput.value = JSON.stringify(positions);
  });

  document.addEventListener("mouseup", () => {
    dragging = false;
  });
}

// Global state for positions, to be populated by the preview step
let positions = {};