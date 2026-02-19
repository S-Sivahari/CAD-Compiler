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
};

// ========================================
// DOM References
// ========================================
const DOM = {
    promptInput: () => document.getElementById('prompt-input'),
    generateBtn: () => document.getElementById('generate-btn'),
    errorMessage: () => document.getElementById('error-message'),
    templatesSelect: () => document.getElementById('templates-select'),
    regenerateBtn: () => document.getElementById('regenerate-btn'),
    loadingOverlay: () => document.getElementById('loading-overlay'),
    loadingMessage: () => document.getElementById('loading-message'),
    toastContainer: () => document.getElementById('toast-container'),
    jsonViewer: () => document.getElementById('json-viewer'),
    pythonViewer: () => document.getElementById('python-viewer'),
    stepInfo: () => document.getElementById('step-info'),
    parametersForm: () => document.getElementById('parameters-form'),
    // Upload / Preview
    dropZone: () => document.getElementById('drop-zone'),
    stepFileInput: () => document.getElementById('step-file-input'),
    dropZoneText: () => document.getElementById('drop-zone-text'),
    previewBtn: () => document.getElementById('preview-btn'),
    previewError: () => document.getElementById('preview-error'),
    editArea: () => document.getElementById('edit-area'),
    editPromptInput: () => document.getElementById('edit-prompt-input'),
    editBtn: () => document.getElementById('edit-btn'),
    editError: () => document.getElementById('edit-error'),
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
}

function setupEventListeners() {
    // Generate button
    DOM.generateBtn().addEventListener('click', handleGenerate);

    // Enter key in prompt
    DOM.promptInput().addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && e.ctrlKey) handleGenerate();
    });

    // Templates dropdown
    DOM.templatesSelect().addEventListener('change', handleTemplateSelect);

    // Regenerate button
    DOM.regenerateBtn().addEventListener('click', handleRegenerate);

    // Tab switching
    document.querySelectorAll('.tab').forEach(tab => {
        tab.addEventListener('click', () => switchTab(tab.dataset.tab));
    });

    // ── Upload / Preview ──────────────────────────────────────────────────
    const dropZone = DOM.dropZone();
    const fileInput = DOM.stepFileInput();

    // The file input already covers the entire drop zone (position:absolute, full size),
    // so clicks propagate naturally — no extra click listener needed (that caused double dialog).
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
            DOM.previewError().textContent = 'Only .step / .stp files are accepted.';
        }
    });

    // Preview button
    DOM.previewBtn().addEventListener('click', handlePreview);

    // Edit STEP button
    DOM.editBtn().addEventListener('click', handleEditStep);
}

// ========================================
// Tab Management
// ========================================
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
                <span class="param-name">${param.name}</span>
                <span class="param-type">${param.type}</span>
                <input 
                    type="number" 
                    class="param-input" 
                    id="param-${i}"
                    value="${param.value}"
                    step="0.1"
                />
            </div>
        `).join('');
    } catch (error) {
        form.innerHTML = `<p class="params-placeholder">Error: ${error.message}</p>`;
        regenBtn.classList.add('hidden');
    }
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
    const select = DOM.templatesSelect();
    try {
        const templates = await api.getTemplates();
        if (templates && templates.length > 0) {
            state.templates = templates;
            templates.forEach(t => {
                const option = document.createElement('option');
                option.value = t.name;
                option.textContent = t.name;
                select.appendChild(option);
            });
            return;
        }
    } catch (error) {
        console.log('Backend templates not available, using predefined');
    }
    state.templates = PREDEFINED_TEMPLATES;
    PREDEFINED_TEMPLATES.forEach(t => {
        const option = document.createElement('option');
        option.value = t.name;
        option.textContent = t.name;
        select.appendChild(option);
    });
}

function handleTemplateSelect(e) {
    const templateName = e.target.value;
    if (!templateName) return;
    const template = state.templates.find(t => t.name === templateName);
    if (template) {
        DOM.promptInput().value = template.prompt || `Create a ${template.name}`;
    }
    e.target.value = '';
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

    try {
        const validation = await api.validatePrompt(prompt);
        if (!validation.valid) throw new Error(validation.error || 'Invalid prompt');

        updateLoading('Calling LLM...');
        const result = await api.generateFromPrompt(prompt, false);

        const stepFile = extractFilename(result.step_file);
        state.currentModel = { ...result, baseName: stepFile.replace('.step', '') };

        await Promise.all([
            loadJsonContent(state.currentModel.baseName),
            loadPythonContent(state.currentModel.baseName),
            loadStepContent(state.currentModel.baseName),
            loadParameters()
        ]);
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
            if (!isNaN(value)) updates[param.name] = value;
        });
        const result = await api.updateAndRegenerate(filename, updates, false);
        if (result.status === 'success') {
            state.currentModel.step_file = result.step_file;
            await Promise.all([
                loadJsonContent(state.currentModel.baseName),
                loadPythonContent(state.currentModel.baseName),
                loadStepContent(state.currentModel.baseName)
            ]);
            showToast('Model regenerated successfully', 'success');
        } else {
            throw new Error('Regeneration failed');
        }
    } catch (error) {
        showError(error.message);
        showToast(`Error: ${error.message}`, 'error');
    } finally {
        hideLoading();
    }
}

// ========================================
// Upload & Preview
// ========================================

function selectStepFile(file) {
    state.previewFile = file;
    DOM.dropZoneText().textContent = file.name;
    DOM.dropZone().classList.add('has-file');
    DOM.previewBtn().disabled = false;
    DOM.previewError().textContent = '';
}

async function handlePreview() {
    if (!state.previewFile) {
        DOM.previewError().textContent = 'Please select a .step file first.';
        return;
    }

    DOM.previewError().textContent = '';
    showLoading('Analyzing & rendering 7 views…');

    try {
        const formData = new FormData();
        formData.append('file', state.previewFile);

        const result = await api.previewStep(formData);

        state.previewImageUrls = result.image_urls || [];
        state.previewFeatures = result.features || null;

        // Show edit area (we have features now)
        DOM.editArea().classList.remove('hidden');

        // Switch to Preview tab and render gallery
        switchTab('preview');
        renderPreviewGallery(result.image_urls);
        showToast('Preview ready — 7 views rendered', 'success');

    } catch (error) {
        DOM.previewError().textContent = `Preview failed: ${error.message}`;
        showToast(`Preview error: ${error.message}`, 'error');
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

    // Reset zoom whenever a new preview loads
    _zoomLevel = 1;
    _applyZoom();

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

    // Update main image and reset zoom
    _zoomLevel = 1;
    _applyZoom();
    DOM.viewMainImg().src = BASE + item.url;
    DOM.viewMainImg().alt = item.label;
    DOM.viewMainLabel().textContent = item.label;
}

// ========================================
// Image Zoom
// ========================================
let _zoomLevel = 1;
const ZOOM_MIN = 0.5;
const ZOOM_MAX = 6;
const ZOOM_STEP = 0.15;

function _applyZoom() {
    const img = DOM.viewMainImg();
    img.style.transform = `scale(${_zoomLevel})`;
    img.style.transformOrigin = 'center center';
    const zoomPct = document.getElementById('zoom-pct');
    if (zoomPct) zoomPct.textContent = Math.round(_zoomLevel * 100) + '%';
}

// Attach wheel + button zoom after DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    // Wheel zoom on the main image wrap
    const wrap = document.querySelector('.view-main-wrap');
    if (wrap) {
        wrap.addEventListener('wheel', (e) => {
            e.preventDefault();
            const delta = e.deltaY < 0 ? ZOOM_STEP : -ZOOM_STEP;
            _zoomLevel = Math.min(ZOOM_MAX, Math.max(ZOOM_MIN, _zoomLevel + delta));
            _applyZoom();
        }, { passive: false });
    }
});

function zoomIn() { _zoomLevel = Math.min(ZOOM_MAX, _zoomLevel + ZOOM_STEP * 2); _applyZoom(); }
function zoomOut() { _zoomLevel = Math.max(ZOOM_MIN, _zoomLevel - ZOOM_STEP * 2); _applyZoom(); }
function zoomReset() { _zoomLevel = 1; _applyZoom(); }

// ========================================
// Edit STEP
// ========================================
async function handleEditStep() {
    if (!state.previewFile) {
        DOM.editError().textContent = 'No STEP file loaded.';
        return;
    }
    const prompt = DOM.editPromptInput().value.trim();
    if (!prompt) {
        DOM.editError().textContent = 'Please enter an edit prompt.';
        return;
    }

    DOM.editError().textContent = '';
    showLoading('Editing STEP file…');

    try {
        const formData = new FormData();
        formData.append('file', state.previewFile);
        formData.append('prompt', prompt);

        const result = await api.editStep(formData);

        showToast('STEP edited successfully', 'success');

        // If a step_url is returned, refresh the file download area
        if (result.step_url) {
            const container = DOM.stepInfo();
            container.innerHTML = `
                <div class="step-details">
                    <div class="step-row">
                        <span class="step-label">Edited File</span>
                        <span class="step-value">${result.step_file || 'generated'}</span>
                    </div>
                </div>
                <a class="download-btn" href="http://localhost:5000${result.step_url}" download>
                    Download Edited STEP
                </a>
            `;
            switchTab('step');
        }
    } catch (error) {
        DOM.editError().textContent = `Edit failed: ${error.message}`;
        showToast(`Edit error: ${error.message}`, 'error');
    } finally {
        hideLoading();
    }
}

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
