/**
 * SynthoCAD - Application Logic
 * Component-based architecture with clean separation
 */

// ========================================
// State Management
// ========================================
const state = {
    currentModel: null,
    templates: [],
    parameters: [],
    generating: false,
    previewFile: null,          // Currently selected File object for preview
    previewImageUrls: [],       // [{view, label, url}] from last preview
    previewFeatures: null,      // features dict from last preview
    lastGeneratedPrompt: null,  // prompt used for last generation (pencil icon)
};

/** Reset upload-related UI and state */
function clearUploadState() {
    state.previewFile = null;
    state.previewImageUrls = [];
    state.previewFeatures = null;
    const dz = DOM.dropZone();
    if (dz) { dz.classList.remove('has-file'); }
    const dzt = DOM.dropZoneText();
    if (dzt) { dzt.textContent = 'Drop .step file or click to browse'; }
    const fi = DOM.stepFileInput();
    if (fi) { fi.value = ''; }
    const r3d = DOM.render3dBtn();
    if (r3d) { r3d.disabled = true; }
    const ue = DOM.uploadError();
    if (ue) { ue.textContent = ''; }
    // Reset step code viewer for uploads
    const scc = document.getElementById('step-code-container');
    if (scc) scc.style.display = 'none';
}

/** Reset generate-related UI and state */
function clearGenerateState() {
    state.currentModel = null;
    state.parameters = [];
    state.lastGeneratedPrompt = null;
    DOM.promptInput().value = '';
    const editBtn = DOM.promptEditBtn();
    if (editBtn) editBtn.classList.add('hidden');
    // Reset viewers
    const jv = DOM.jsonViewer();
    if (jv) jv.textContent = 'Generate a model to view JSON output';
    const pv = DOM.pythonViewer();
    if (pv) pv.textContent = 'Generate a model to view Python code';
    const si = DOM.stepInfo();
    if (si) si.innerHTML = '<p class="step-placeholder">Generate a model to view STEP file</p>';
    const scc = document.getElementById('step-code-container');
    if (scc) scc.style.display = 'none';
    const pf = DOM.parametersForm();
    if (pf) pf.innerHTML = '<p class="params-placeholder">Generate a model to edit parameters</p>';
    DOM.regenerateBtn().classList.add('hidden');
    // Deselect template
    const list = DOM.templatesSelect();
    if (list) list.querySelectorAll('.template-item').forEach(el => el.classList.remove('active'));
}

// ========================================
// DOM References
// ========================================
const DOM = {
    promptInput: () => document.getElementById('prompt-input'),
    promptEditBtn: () => document.getElementById('prompt-edit-btn'),
    generateBtn: () => document.getElementById('generate-btn'),
    errorMessage: () => document.getElementById('error-message'),
    templatesSelect: () => document.getElementById('templates-list'),
    regenerateBtn: () => document.getElementById('regenerate-btn'),
    loadingOverlay: () => document.getElementById('loading-overlay'),
    loadingMessage: () => document.getElementById('loading-message'),
    toastContainer: () => document.getElementById('toast-container'),
    jsonViewer: () => document.getElementById('json-viewer'),
    pythonViewer: () => document.getElementById('python-viewer'),
    stepInfo: () => document.getElementById('step-info'),
    parametersForm: () => document.getElementById('parameters-form'),
    // 3D Viewer
    viewer3dPlaceholder: () => document.getElementById('viewer3d-placeholder'),
    viewer3dContainer: () => document.getElementById('viewer3d-container'),
    modelViewer: () => document.getElementById('model-viewer'),
    visualizeBtn: () => document.getElementById('visualize-btn'),
    // Upload / Preview
    dropZone: () => document.getElementById('drop-zone'),
    stepFileInput: () => document.getElementById('step-file-input'),
    dropZoneText: () => document.getElementById('drop-zone-text'),
    render3dBtn: () => document.getElementById('render3d-btn'),
    uploadError: () => document.getElementById('upload-error'),
    // Preview gallery
    previewPlaceholder: () => document.getElementById('preview-placeholder'),
    previewViewer: () => document.getElementById('preview-viewer'),
    viewStrip: () => document.getElementById('view-strip'),
    viewMainImg: () => document.getElementById('view-main-img'),
    viewMainLabel: () => document.getElementById('view-main-label'),
};

// ========================================
// Initialization
// ========================================
document.addEventListener('DOMContentLoaded', initApp);

async function initApp() {
    setupEventListeners();
    await loadTemplates();
    // Initialise the Three.js viewer (non-blocking — WASM loads in background)
    stepViewer.init();
}

function setupEventListeners() {
    // Generate button
    DOM.generateBtn().addEventListener('click', handleGenerate);

    // Enter key in prompt (Ctrl+Enter)
    DOM.promptInput().addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && e.ctrlKey) handleGenerate();
    });

    // Pencil icon — show modified state when prompt changes after generation
    DOM.promptInput().addEventListener('input', () => {
        const editBtn = DOM.promptEditBtn();
        if (!editBtn || !state.currentModel) return;
        const current = DOM.promptInput().value.trim();
        if (current !== state.lastGeneratedPrompt) {
            editBtn.classList.add('modified');
        } else {
            editBtn.classList.remove('modified');
        }
    });

    // Pencil icon click — focus the textarea
    const pencilBtn = DOM.promptEditBtn();
    if (pencilBtn) {
        pencilBtn.addEventListener('click', () => DOM.promptInput().focus());
    }

    // Templates list
    // (event delegation handled inside loadTemplates)

    // Regenerate button (parameters)
    DOM.regenerateBtn().addEventListener('click', handleRegenerate);

    // Visualize button (3D viewer)
    DOM.visualizeBtn().addEventListener('click', handleVisualize);

    // Tab switching
    document.querySelectorAll('.tab').forEach(tab => {
        tab.addEventListener('click', () => {
            switchTab(tab.dataset.tab);
        });
    });

    // ── Upload / Render 3D ──────────────────────────────────────────────────
    const dropZone = DOM.dropZone();
    const fileInput = DOM.stepFileInput();

    fileInput.addEventListener('change', () => {
        const file = fileInput.files[0];
        if (file) selectStepFile(file);
    });

    // Drag & Drop
    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('drag-over');
    });
    dropZone.addEventListener('dragleave', () => dropZone.classList.remove('drag-over'));
    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('drag-over');
        const file = e.dataTransfer.files[0];
        if (file && (file.name.endsWith('.step') || file.name.endsWith('.stp'))) {
            selectStepFile(file);
        } else {
            DOM.uploadError().textContent = 'Only .step / .stp files are accepted.';
        }
    });

    // Render 3D button
    DOM.render3dBtn().addEventListener('click', handleRender3D);
}

// ========================================
// Tab Management
// ========================================
/** Show only the tabs whose data-tab is in the given list */
function setVisibleTabs(visibleList) {
    document.querySelectorAll('.tab').forEach(tab => {
        tab.style.display = visibleList.includes(tab.dataset.tab) ? '' : 'none';
    });
}

function switchTab(tabName) {
    document.querySelectorAll('.tab').forEach(tab => {
        tab.classList.toggle('active', tab.dataset.tab === tabName);
    });
    document.querySelectorAll('.tab-panel').forEach(panel => {
        panel.classList.toggle('active', panel.id === `panel-${tabName}`);
    });
    if (state.currentModel) {
        loadTabContent(tabName);
    }
}

async function loadTabContent(tabName) {
    if (!state.currentModel) return;
    const baseName = state.currentModel.baseName;
    try {
        switch (tabName) {
            case 'json': await loadJsonContent(baseName); break;
            case 'python': await loadPythonContent(baseName); break;
            case 'step': await loadStepContent(baseName); break;
            case 'parameters': await loadParameters(); break;
        }
    } catch (error) {
        console.error(`Failed to load ${tabName}:`, error);
        showError(`Failed to load ${tabName} content`);
    }
}

// ========================================
// Content Loaders
// ========================================
async function loadJsonContent(baseName) {
    const viewer = DOM.jsonViewer();
    viewer.textContent = 'Loading...';
    try {
        const result = await api.viewJsonFile(`${baseName}.json`);
        viewer.textContent = result.success ? result.content_str : `Error: ${result.message}`;
    } catch (error) {
        viewer.textContent = `Error: ${error.message}`;
    }
}

async function loadPythonContent(baseName) {
    const viewer = DOM.pythonViewer();
    viewer.textContent = 'Loading...';
    try {
        const result = await api.viewPythonFile(`${baseName}_generated.py`);
        viewer.textContent = result.success ? result.content : `Error: ${result.message}`;
    } catch (error) {
        viewer.textContent = `Error: ${error.message}`;
    }
}

async function loadStepContent(baseName) {
    const container = DOM.stepInfo();
    try {
        const result = await api.viewStepFile(`${baseName}.step`);
        if (result.success) {
            container.innerHTML = `
                <div class="step-details">
                    <div class="step-row">
                        <span class="step-label">Filename</span>
                        <span class="step-value">${result.filename}</span>
                    </div>
                    <div class="step-row">
                        <span class="step-label">Size</span>
                        <span class="step-value">${result.file_size_kb} KB</span>
                    </div>
                    <div class="step-row">
                        <span class="step-label">Path</span>
                        <span class="step-value">${result.file_path}</span>
                    </div>
                </div>
                <button class="download-btn" onclick="downloadStepFile()">Download STEP File</button>
            `;
        } else {
            container.innerHTML = `<p class="step-placeholder">Error: ${result.message}</p>`;
        }
    } catch (error) {
        container.innerHTML = `<p class="step-placeholder">Error: ${error.message}</p>`;
    }
}

async function loadParameters() {
    const form = DOM.parametersForm();
    const regenBtn = DOM.regenerateBtn();
    if (!state.currentModel) {
        form.innerHTML = '<p class="params-placeholder">Generate a model to edit parameters</p>';
        regenBtn.classList.add('hidden');
        return;
    }
    try {
        const filename = extractFilename(state.currentModel.py_file);
        const result = await api.extractParameters(filename);
        if (!result.parameters || result.parameters.length === 0) {
            form.innerHTML = '<p class="params-placeholder">No editable parameters found</p>';
            regenBtn.classList.add('hidden');
            return;
        }
        state.parameters = result.parameters;
        regenBtn.classList.remove('hidden');
        form.innerHTML = result.parameters.map((param, i) => `
            <div class="param-row">
                <span class="param-name" title="${param.name}">${param.description || param.name}</span>
                <span class="param-type">${param.unit || param.type}</span>
                <input 
                    type="number" 
                    class="param-input" 
                    id="param-${i}"
                    value="${param.value}"
                    min="${param.min != null ? param.min : ''}"
                    max="${param.max != null ? param.max : ''}"
                    step="0.1"
                />
            </div>
        `).join('');
    } catch (error) {
        form.innerHTML = `<p class="params-placeholder">Error: ${error.message}</p>`;
        regenBtn.classList.add('hidden');
    }
}

/**
 * Read an uploaded STEP file client-side and show the raw text in the STEP tab.
 */
function loadUploadedStepContent(file) {
    const infoEl = document.getElementById('step-info');
    const codeContainer = document.getElementById('step-code-container');
    const codeViewer = document.getElementById('step-code-viewer');

    // Show file metadata
    const sizeKB = (file.size / 1024).toFixed(1);
    infoEl.innerHTML = `
        <div class="step-details">
            <div class="step-row">
                <span class="step-label">Filename</span>
                <span class="step-value">${file.name}</span>
            </div>
            <div class="step-row">
                <span class="step-label">Size</span>
                <span class="step-value">${sizeKB} KB</span>
            </div>
        </div>
    `;

    // Read and display raw STEP text
    const reader = new FileReader();
    reader.onload = () => {
        codeViewer.textContent = reader.result;
        codeContainer.style.display = '';
    };
    reader.onerror = () => {
        codeViewer.textContent = 'Failed to read file.';
        codeContainer.style.display = '';
    };
    reader.readAsText(file);
}

/**
 * Display features from STEP analysis as read-only info in the parameters panel.
 */
function displayFeatures(features) {
    const form = DOM.parametersForm();
    const regenBtn = DOM.regenerateBtn();
    regenBtn.classList.add('hidden');

    if (!features || Object.keys(features).length === 0) {
        form.innerHTML = '<p class="params-placeholder">No features detected</p>';
        return;
    }

    let html = '';

    // Bounding box
    if (features.bounding_box) {
        const bb = features.bounding_box;
        html += '<div class="param-section-label">Bounding Box</div>';
        [['x_mm', 'X'], ['y_mm', 'Y'], ['z_mm', 'Z']].forEach(([key, label]) => {
            if (bb[key] != null) {
                html += `<div class="param-row">
                    <span class="param-name">${label} length</span>
                    <span class="param-value-ro">${Number(bb[key]).toFixed(2)} mm</span>
                </div>`;
            }
        });
    }

    // Face count
    if (features.face_count) {
        html += `<div class="param-row">
            <span class="param-name">Total faces</span>
            <span class="param-value-ro">${features.face_count}</span>
        </div>`;
    }

    // Summary text
    if (features.summary) {
        html += '<div class="param-section-label">Summary</div>';
        html += `<p class="feature-summary">${features.summary}</p>`;
    }

    // Cylinders
    if (features.cylinders && features.cylinders.length > 0) {
        html += `<div class="param-section-label">Cylinders (${features.cylinders.length})</div>`;
        // Show unique radii
        const uniqueRadii = [...new Set(features.cylinders.map(c => c.radius_mm))].sort((a, b) => a - b);
        uniqueRadii.forEach(r => {
            const count = features.cylinders.filter(c => c.radius_mm === r).length;
            html += `<div class="param-row">
                <span class="param-name">r=${Number(r).toFixed(2)}mm</span>
                <span class="param-value-ro">×${count} face${count > 1 ? 's' : ''}</span>
            </div>`;
        });
    }

    // Cones
    if (features.cones && features.cones.length > 0) {
        html += `<div class="param-section-label">Cones (${features.cones.length})</div>`;
        features.cones.slice(0, 5).forEach((c, i) => {
            html += `<div class="param-row">
                <span class="param-name">${c.id} apex r</span>
                <span class="param-value-ro">${Number(c.apex_radius_mm).toFixed(2)} mm</span>
            </div>`;
        });
    }

    // Tori (fillets)
    if (features.tori && features.tori.length > 0) {
        html += `<div class="param-section-label">Fillets / Tori (${features.tori.length})</div>`;
        const uniqueMinor = [...new Set(features.tori.map(t => t.minor_radius_mm))].sort((a, b) => a - b);
        uniqueMinor.forEach(r => {
            const count = features.tori.filter(t => t.minor_radius_mm === r).length;
            html += `<div class="param-row">
                <span class="param-name">fillet r=${Number(r).toFixed(2)}mm</span>
                <span class="param-value-ro">×${count}</span>
            </div>`;
        });
    }

    // Planes
    if (features.planes && features.planes.length > 0) {
        html += `<div class="param-section-label">Planes (${features.planes.length})</div>`;
    }

    form.innerHTML = html || '<p class="params-placeholder">No extractable features</p>';
}

// ========================================
// Templates
// ========================================
const PREDEFINED_TEMPLATES = [
    { name: 'Cylinder', prompt: 'Create a cylinder with diameter 20mm and height 50mm' },
    { name: 'Bolt', prompt: 'Create an M8 hex bolt with thread length 25mm and head height 5mm' },
    { name: 'Nut', prompt: 'Create an M8 hex nut with height 6.5mm' },
    { name: 'Gear', prompt: 'Create a spur gear with 24 teeth, module 2mm, and thickness 10mm' },
    { name: 'Plate with Holes', prompt: 'Create a rectangular plate 100mm x 60mm x 5mm with 4 corner holes of 6mm diameter' }
];

async function loadTemplates() {
    const list = DOM.templatesSelect();
    list.innerHTML = '';

    function renderList(templates) {
        state.templates = templates;
        templates.forEach(t => {
            const item = document.createElement('div');
            item.className = 'template-item';
            item.textContent = t.name;
            item.dataset.name = t.name;
            item.addEventListener('click', () => {
                list.querySelectorAll('.template-item').forEach(el => el.classList.remove('active'));
                item.classList.add('active');
                DOM.promptInput().value = t.prompt || `Create a ${t.name}`;
            });
            list.appendChild(item);
        });
    }

    try {
        const templates = await api.getTemplates();
        if (templates && templates.length > 0) {
            renderList(templates);
            return;
        }
    } catch (error) {
        console.log('Backend templates not available, using predefined');
    }
    renderList(PREDEFINED_TEMPLATES);
}


// ========================================
// Generation
// ========================================
async function handleGenerate() {
    const prompt = DOM.promptInput().value.trim();
    if (!prompt) { showError('Please enter a design description'); return; }
    if (state.generating) { showError('Generation already in progress'); return; }

    clearError();
    state.generating = true;
    setGenerating(true);
    showLoading('Generating CAD model...');

    // Clear any upload state first
    clearUploadState();

    try {
        const validation = await api.validatePrompt(prompt);
        if (!validation.valid) throw new Error(validation.error || 'Invalid prompt');

        updateLoading('Calling LLM...');
        const result = await api.generateFromPrompt(prompt);

        const stepFile = extractFilename(result.step_file);
        state.currentModel = { ...result, baseName: stepFile.replace('.step', '') };

        // Show Visualize button if GLB is available
        if (result.glb_url) {
            DOM.visualizeBtn().classList.remove('hidden');
        }

        await Promise.all([
            loadJsonContent(state.currentModel.baseName),
            loadPythonContent(state.currentModel.baseName),
            loadStepContent(state.currentModel.baseName),
            loadParameters()
        ]);

        // Show all tabs for generated models
        setVisibleTabs(['viewer3d', 'preview', 'json', 'python', 'step']);

        // Auto-load the generated STEP into the 3D viewer
        const stepUrl = `http://localhost:5000/outputs/step/${stepFile}`;
        switchTab('viewer3d');
        stepViewer.loadStepUrl(stepUrl);

        // Generate preview images in background (non-blocking)
        api.previewStepByName(stepFile).then(previewResult => {
            if (previewResult && previewResult.image_urls) {
                state.previewImageUrls = previewResult.image_urls;
                state.previewFeatures = previewResult.features || null;
                renderPreviewGallery(previewResult.image_urls);
            }
        }).catch(err => console.warn('Preview generation failed:', err));

        // Show pencil icon (indicates prompt can be edited & regenerated)
        state.lastGeneratedPrompt = prompt;
        const editBtn = DOM.promptEditBtn();
        if (editBtn) {
            editBtn.classList.remove('hidden');
            editBtn.classList.remove('modified');
        }

        showToast('Model generated successfully', 'success');
    } catch (error) {
        showError(error.message);
        showToast(`Error: ${error.message}`, 'error');
    } finally {
        state.generating = false;
        setGenerating(false);
        hideLoading();
    }
}

// ========================================
// Regeneration
// ========================================
async function handleRegenerate() {
    if (!state.currentModel || state.parameters.length === 0) {
        showError('No parameters to update');
        return;
    }
    showLoading('Regenerating model...');
    try {
        const filename = extractFilename(state.currentModel.py_file);
        const updates = {};
        state.parameters.forEach((param, i) => {
            const input = document.getElementById(`param-${i}`);
            const value = parseFloat(input.value);
            if (!isNaN(value) && value !== param.value) updates[param.name] = value;
        });
        if (Object.keys(updates).length === 0) {
            showToast('No parameters were changed', 'info');
            hideLoading();
            return;
        }
        const result = await api.updateAndRegenerate(filename, updates);
        if (result.success) {
            // Update step file reference
            const stepFile = result.step_file
                ? result.step_file.split(/[\\/]/).pop()
                : state.currentModel.baseName + '.step';
            state.currentModel.step_file = result.step_file;

            if (result.glb_url) {
                state.currentModel.glb_url = result.glb_url;
                DOM.visualizeBtn().classList.remove('hidden');
            }

            // Reload code tabs
            await Promise.all([
                loadPythonContent(state.currentModel.baseName),
                loadStepContent(state.currentModel.baseName)
            ]);

            // Reload the 3D viewer with updated STEP (cache-bust)
            const stepUrl = `http://localhost:5000/outputs/step/${stepFile}?t=${Date.now()}`;
            stepViewer.loadStepUrl(stepUrl);

            // Re-extract parameters (values updated in .py) and refresh the form
            await loadParameters();

            // Regenerate preview in background
            api.previewStepByName(stepFile).then(prev => {
                if (prev && prev.image_urls) {
                    state.previewImageUrls = prev.image_urls;
                    state.previewFeatures = prev.features || null;
                    renderPreviewGallery(prev.image_urls);
                }
            }).catch(() => {});

            switchTab('viewer3d');
            showToast('Model regenerated successfully', 'success');
        } else {
            throw new Error(result.message || 'Regeneration failed');
        }
    } catch (error) {
        showError(error.message);
        showToast(`Error: ${error.message}`, 'error');
    } finally {
        hideLoading();
    }
}

// ========================================
// 3D Visualization (Google Model Viewer)
// ========================================
function handleVisualize() {
    if (!state.currentModel || !state.currentModel.glb_url) {
        showToast('No 3D model available. Generate a model first.', 'error');
        return;
    }
    const BASE = 'http://localhost:5000';
    const glbUrl = BASE + state.currentModel.glb_url;
    const mv = DOM.modelViewer();

    mv.setAttribute('src', glbUrl);
    DOM.viewer3dPlaceholder().classList.add('hidden');
    DOM.viewer3dContainer().classList.remove('hidden');

    // Switch to 3D Viewer tab
    switchTab('viewer3d');
    showToast('3D model loaded', 'success');
}

// ========================================
// Upload & Preview
// ========================================
// Upload & Render 3D
// ========================================

function selectStepFile(file) {
    state.previewFile = file;
    DOM.dropZoneText().textContent = file.name;
    DOM.dropZone().classList.add('has-file');
    DOM.render3dBtn().disabled = false;
    DOM.uploadError().textContent = '';
}

async function handleRender3D() {
    if (!state.previewFile) {
        DOM.uploadError().textContent = 'Please select a .step file first.';
        return;
    }

    DOM.uploadError().textContent = '';
    showLoading('Rendering 3D model & generating previews…');

    // Clear any generate state first
    clearGenerateState();

    try {
        // Step 1: Load into 3D viewer
        await stepViewer.loadStepFile(state.previewFile);
        
        // Step 2: Generate preview images in background
        const formData = new FormData();
        formData.append('file', state.previewFile);
        
        const result = await api.previewStep(formData);
        
        state.previewImageUrls = result.image_urls || [];
        state.previewFeatures = result.features || null;
        
        // Render preview gallery
        renderPreviewGallery(result.image_urls);

        // Load STEP content into the STEP tab (client-side read)
        loadUploadedStepContent(state.previewFile);

        // Display extracted features as read-only parameters
        displayFeatures(result.features);
        
        // Imported file — only show 3D viewer, preview and STEP tabs
        setVisibleTabs(['viewer3d', 'preview', 'step']);

        // Switch to 3D Viewer tab
        switchTab('viewer3d');
        
        showToast('3D model loaded', 'success');

    } catch (error) {
        DOM.uploadError().textContent = `Render failed: ${error.message}`;
        showToast(`Render error: ${error.message}`, 'error');
    } finally {
        hideLoading();
    }
}

function renderPreviewGallery(imageUrls) {
    if (!imageUrls || imageUrls.length === 0) {
        DOM.previewPlaceholder().classList.remove('hidden');
        DOM.previewViewer().classList.add('hidden');
        return;
    }

    DOM.previewPlaceholder().classList.add('hidden');
    DOM.previewViewer().classList.remove('hidden');

    // Reset pan and zoom whenever a new preview loads
    if (typeof _resetTransform === 'function') {
        _resetTransform();
    }

    const BASE = 'http://localhost:5000';
    const strip = DOM.viewStrip();
    strip.innerHTML = '';

    imageUrls.forEach((item, idx) => {
        const thumb = document.createElement('div');
        thumb.className = 'view-thumb' + (idx === 0 ? ' active' : '');
        thumb.dataset.url = BASE + item.url;
        thumb.dataset.label = item.label;

        const img = document.createElement('img');
        img.src = BASE + item.url;
        img.alt = item.label;
        img.className = 'view-thumb-img';

        const lbl = document.createElement('span');
        lbl.className = 'view-thumb-label';
        lbl.textContent = item.label;

        thumb.appendChild(img);
        thumb.appendChild(lbl);
        strip.appendChild(thumb);

        thumb.addEventListener('click', () => selectView(thumb, item));
    });

    // Select first image by default
    if (imageUrls.length > 0) {
        selectView(strip.firstChild, imageUrls[0]);
    }
}

function selectView(thumbEl, item) {
    const BASE = 'http://localhost:5000';
    // Update active state
    document.querySelectorAll('.view-thumb').forEach(t => t.classList.remove('active'));
    thumbEl.classList.add('active');

    // Update main image and reset pan+zoom
    _resetTransform();
    DOM.viewMainImg().src = BASE + item.url;
    DOM.viewMainImg().alt = item.label;
    DOM.viewMainLabel().textContent = item.label;
}

// ========================================
// Image Pan + Zoom
// ========================================
let _zoomLevel = 1;
let _panX = 0;
let _panY = 0;
let _isDragging = false;
let _dragStart = { x: 0, y: 0 };
let _panStart = { x: 0, y: 0 };

const ZOOM_MIN = 0.25;
const ZOOM_MAX = 8;
const ZOOM_STEP = 0.15;

function _applyTransform() {
    const img = DOM.viewMainImg();
    if (!img) return;
    // transform-origin is top-left (0 0); pan+scale are applied together
    img.style.transformOrigin = '0 0';
    img.style.transform = `translate(${_panX}px, ${_panY}px) scale(${_zoomLevel})`;
    const zoomPct = document.getElementById('zoom-pct');
    if (zoomPct) zoomPct.textContent = Math.round(_zoomLevel * 100) + '%';
}

function _resetTransform() {
    _zoomLevel = 1;
    _panX = 0;
    _panY = 0;
    _applyTransform();
}

// Zoom toward a specific viewport point (px, py) relative to the wrap element
function _zoomToward(delta, viewportX, viewportY) {
    const newZoom = Math.min(ZOOM_MAX, Math.max(ZOOM_MIN, _zoomLevel + delta));
    const scale = newZoom / _zoomLevel;
    // Keep the point under the cursor fixed in image space
    _panX = viewportX - scale * (viewportX - _panX);
    _panY = viewportY - scale * (viewportY - _panY);
    _zoomLevel = newZoom;
    _applyTransform();
}

// Attach wheel + drag listeners once DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    const wrap = document.querySelector('.view-main-wrap');
    if (!wrap) return;

    // Wheel: zoom toward cursor
    wrap.addEventListener('wheel', (e) => {
        e.preventDefault();
        const rect = wrap.getBoundingClientRect();
        const mouseX = e.clientX - rect.left;
        const mouseY = e.clientY - rect.top;
        const delta = e.deltaY < 0 ? ZOOM_STEP : -ZOOM_STEP;
        _zoomToward(delta, mouseX, mouseY);
    }, { passive: false });

    // Drag: pan the image
    wrap.addEventListener('mousedown', (e) => {
        if (e.button !== 0) return;   // left button only
        _isDragging = true;
        _dragStart = { x: e.clientX, y: e.clientY };
        _panStart = { x: _panX, y: _panY };
        wrap.style.cursor = 'grabbing';
        e.preventDefault();
    });

    document.addEventListener('mousemove', (e) => {
        if (!_isDragging) return;
        _panX = _panStart.x + (e.clientX - _dragStart.x);
        _panY = _panStart.y + (e.clientY - _dragStart.y);
        _applyTransform();
    });

    document.addEventListener('mouseup', () => {
        if (_isDragging) {
            _isDragging = false;
            if (wrap) wrap.style.cursor = 'grab';
        }
    });
});

// Toolbar button helpers — zoom toward the visible center
function _wrapCenter() {
    const wrap = document.querySelector('.view-main-wrap');
    if (!wrap) return { x: 0, y: 0 };
    return { x: wrap.clientWidth / 2, y: wrap.clientHeight / 2 };
}
function zoomIn() { const c = _wrapCenter(); _zoomToward(ZOOM_STEP * 2, c.x, c.y); }
function zoomOut() { const c = _wrapCenter(); _zoomToward(-ZOOM_STEP * 2, c.x, c.y); }
function zoomReset() { _resetTransform(); }

// ========================================
// Download
// ========================================
function downloadStepFile() {
    if (!state.currentModel) return;
    const stepPath = state.currentModel.step_file;
    const filename = extractFilename(stepPath);
    const url = `http://localhost:5000/outputs/step/${filename}`;
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
}

// ========================================
// UI Helpers
// ========================================
function showError(message) { DOM.errorMessage().textContent = message; }
function clearError() { DOM.errorMessage().textContent = ''; }

function setGenerating(isGenerating) {
    const btn = DOM.generateBtn();
    btn.disabled = isGenerating;
    btn.textContent = isGenerating ? 'Generating...' : 'Generate';
}

function showLoading(message) {
    DOM.loadingMessage().textContent = message;
    DOM.loadingOverlay().classList.remove('hidden');
}

function updateLoading(message) { DOM.loadingMessage().textContent = message; }
function hideLoading() { DOM.loadingOverlay().classList.add('hidden'); }

function showToast(message, type = 'info') {
    const container = DOM.toastContainer();
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    container.appendChild(toast);
    setTimeout(() => toast.remove(), 4000);
}

// ========================================
// Utilities
// ========================================
function extractFilename(path) {
    return path.split('\\').pop().split('/').pop();
}
