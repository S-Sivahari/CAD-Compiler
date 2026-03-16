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
    promptTemplates: [],
    selectedPromptTemplate: null,
    selectedPromptCategory: '',
    selectedPromptTemplateId: '',
    editTemplates: [],
    selectedEditCategory: '',
    selectedEditTemplateId: '',
    parameters: [],
    generating: false,
    previewFile: null,          // Currently selected File object for preview
    previewImageUrls: [],       // [{view, label, url}] from last preview
    previewFeatures: null,      // features dict from last preview
    panelHistory: {},           // panel_id -> entries[]
    ocpFeatures: null,          // exact geometric features from last OCP extraction
    // ── Face Groups ──────────────────────────────────────────────────
    faceGroups: {},             // { groupName: { faces: ['f0','f2'], color: '#...' } }
    selectedFaces: new Set(),   // face IDs currently selected in group-mode
    groupMode: false,           // whether selection mode is active
    llmProvider: 'gemini',      // 'gemini' | 'ollama' (Qwen)
    // ── Named Points ──────────────────────────────────────────────────
    namedPoints: {},            // { name: [x, y, z] } — user-saved surface coordinates
    pointPickMode: false,       // whether point-pick mode is active
    pendingPoint: null,         // [x, y, z] of the last clicked-but-not-yet-named point
    editDockExpanded: false,    // compact bottom drawer expanded/collapsed
};

// Colour palette cycled for successive groups
const GROUP_COLORS = [
    '#60a5fa', '#34d399', '#f472b6', '#fb923c',
    '#a78bfa', '#facc15', '#22d3ee', '#f87171',
];

// ========================================
// DOM References
// ========================================
const DOM = {
    promptInput: () => document.getElementById('prompt-input'),
    generateBtn: () => document.getElementById('generate-btn'),
    errorMessage: () => document.getElementById('error-message'),
    promptTemplateTree: () => document.getElementById('prompt-template-tree'),
    promptTemplateGrid: () => document.getElementById('prompt-template-grid'),
    promptTemplateSummary: () => document.getElementById('prompt-template-summary'),
    editTemplateTree: () => document.getElementById('edit-template-tree'),
    editTemplateGrid: () => document.getElementById('edit-template-grid'),
    editTemplateSummary: () => document.getElementById('edit-template-summary'),
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
    // Face Groups
    groupModeBtn: () => document.getElementById('group-mode-btn'),
    groupModeBar: () => document.getElementById('group-mode-bar'),
    groupSelCount: () => document.getElementById('group-sel-count'),
    groupNameInput: () => document.getElementById('group-name-input'),
    groupsList: () => document.getElementById('groups-list'),
    groupsEmptyMsg: () => document.getElementById('groups-empty-msg'),
    // Upload / Preview
    dropZone: () => document.getElementById('drop-zone'),
    stepFileInput: () => document.getElementById('step-file-input'),
    dropZoneText: () => document.getElementById('drop-zone-text'),
    previewBtn: () => document.getElementById('preview-btn'),
    view3dBtn: () => document.getElementById('view3d-btn'),
    previewError: () => document.getElementById('preview-error'),
    editArea: () => document.getElementById('edit-area'),
    editDock: () => document.getElementById('edit-dock'),
    editDockToggle: () => document.getElementById('edit-dock-toggle'),
    editDockToggleText: () => document.getElementById('edit-dock-toggle-text'),
    editDockPointBtn: () => document.getElementById('edit-dock-point-btn'),
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
    await loadPromptTemplateToolkit();
    await loadEditTemplateToolkit();
    syncEditDockVisibility();
    // Initialise the Three.js viewer (non-blocking — WASM loads in background)
    stepViewer.init();
    // Register face-click callback so 3D viewer clicks feed into group selection
    stepViewer.setFaceClickCallback((faceId) => {
        if (state.groupMode) _toggleFaceSelection(faceId);
    });
    // Register point-pick callback
    stepViewer.setPointPickCallback((xyz) => {
        _onPointPicked(xyz);
    });
}

function setSidepanelView(tab = 'workflow') {
    const sideWorkflowBtn = document.getElementById('sidepanel-workflow-btn');
    const sideParamsBtn = document.getElementById('sidepanel-params-btn');
    const sideWorkflow = document.getElementById('sidepanel-workflow');
    const sideParams = document.getElementById('sidepanel-params');
    if (!sideWorkflowBtn || !sideParamsBtn || !sideWorkflow || !sideParams) return;

    const showWorkflow = tab !== 'params';
    sideWorkflowBtn.classList.toggle('active', showWorkflow);
    sideParamsBtn.classList.toggle('active', !showWorkflow);
    sideWorkflow.classList.toggle('hidden', !showWorkflow);
    sideParams.classList.toggle('hidden', showWorkflow);
}

function syncEditDockVisibility() {
    const editArea = DOM.editArea();
    const editDock = DOM.editDock();
    if (!editArea || !editDock) return;
    const editSection = document.getElementById('mode-section-edit');
    const editModeActive = !!editSection && !editSection.classList.contains('hidden');
    const hasEditableModel = !!(state.previewFile || state.currentModel);
    const shouldShow = editModeActive && hasEditableModel;

    editDock.classList.toggle('hidden', !shouldShow);
    editArea.classList.toggle('collapsed', !state.editDockExpanded);

    const toggleBtn = DOM.editDockToggle();
    const toggleText = DOM.editDockToggleText();
    if (toggleBtn && toggleText) {
        toggleBtn.classList.toggle('expanded', state.editDockExpanded);
        toggleText.textContent = state.editDockExpanded ? 'Hide Edit Controls' : 'Open Edit Controls';
    }
}

function setupEventListeners() {
    // Generate button
    DOM.generateBtn().addEventListener('click', handleGenerate);

    // Enter key in prompt — only fire when Prompt mode is active
    DOM.promptInput().addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && e.ctrlKey) {
            const editSection = document.getElementById('mode-section-edit');
            if (editSection && !editSection.classList.contains('hidden')) return; // edit mode active
            handleGenerate();
        }
    });

    // Ctrl+Enter in edit prompt → handleEditStep
    DOM.editPromptInput().addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && e.ctrlKey) {
            e.preventDefault();
            handleEditStep();
        }
    });

    const promptTemplateTree = DOM.promptTemplateTree();
    if (promptTemplateTree) {
        promptTemplateTree.addEventListener('click', (e) => {
            const btn = e.target.closest('[data-category-path]');
            if (!btn) return;
            handlePromptTemplateCategorySelect(btn.dataset.categoryPath || '');
        });
    }

    const promptTemplateGrid = DOM.promptTemplateGrid();
    if (promptTemplateGrid) {
        promptTemplateGrid.addEventListener('click', (e) => {
            const card = e.target.closest('[data-template-id]');
            if (!card) return;
            handlePromptTemplateSelect(card.dataset.templateId || '');
        });
    }

    const editDockToggle = DOM.editDockToggle();
    if (editDockToggle) {
        editDockToggle.addEventListener('click', () => {
            state.editDockExpanded = !state.editDockExpanded;
            syncEditDockVisibility();
        });
    }

    const editTemplateTree = DOM.editTemplateTree();
    if (editTemplateTree) {
        editTemplateTree.addEventListener('click', (e) => {
            const btn = e.target.closest('[data-category-path]');
            if (!btn) return;
            handleEditTemplateCategorySelect(btn.dataset.categoryPath || '');
        });
    }

    const editTemplateGrid = DOM.editTemplateGrid();
    if (editTemplateGrid) {
        editTemplateGrid.addEventListener('click', (e) => {
            const card = e.target.closest('[data-template-id]');
            if (!card) return;
            handleEditTemplateLoad(card.dataset.templateId || '');
        });
    }

    // Regenerate button
    DOM.regenerateBtn().addEventListener('click', handleRegenerate);

    // Visualize button (3D viewer)
    DOM.visualizeBtn().addEventListener('click', handleVisualize);

    // Tab switching
    document.querySelectorAll('.tab').forEach(tab => {
        tab.addEventListener('click', () => switchTab(tab.dataset.tab));
    });

    // ── Mode tab switching ────────────────────────────────────────────────
    const modePromptBtn = document.getElementById('mode-prompt-btn');
    const modeEditBtn   = document.getElementById('mode-edit-btn');
    const modeSectionPrompt = document.getElementById('mode-section-prompt');
    const modeSectionEdit   = document.getElementById('mode-section-edit');

    const sideWorkflowBtn = document.getElementById('sidepanel-workflow-btn');
    const sideParamsBtn = document.getElementById('sidepanel-params-btn');

    if (sideWorkflowBtn && sideParamsBtn) {
        sideWorkflowBtn.addEventListener('click', () => setSidepanelView('workflow'));
        sideParamsBtn.addEventListener('click', () => setSidepanelView('params'));
    }

    if (modePromptBtn && modeEditBtn) {
        modePromptBtn.addEventListener('click', () => {
            modePromptBtn.classList.add('active');
            modeEditBtn.classList.remove('active');
            if (modeSectionPrompt) modeSectionPrompt.classList.remove('hidden');
            if (modeSectionEdit)   modeSectionEdit.classList.add('hidden');
            setSidepanelView('workflow');
            syncEditDockVisibility();
        });
        modeEditBtn.addEventListener('click', () => {
            modeEditBtn.classList.add('active');
            modePromptBtn.classList.remove('active');
            if (modeSectionEdit)   modeSectionEdit.classList.remove('hidden');
            if (modeSectionPrompt) modeSectionPrompt.classList.add('hidden');
            setSidepanelView('workflow');
            syncEditDockVisibility();
        });
    }

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

    // View 3D button
    DOM.view3dBtn().addEventListener('click', async () => {
        if (!state.previewFile) return;
        switchTab('viewer3d');
        await stepViewer.loadStepFile(state.previewFile);
        addToHistory(state.previewFile);
        // Auto-load parameters & feed face features to the 3D viewer
        await loadParameters();
        if (state.ocpFeatures) stepViewer.setFaceFeatures(state.ocpFeatures);
    });

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
    if (state.currentModel || state.previewFile) {
        loadTabContent(tabName);
    }
}

async function loadTabContent(tabName) {
    // The parameters tab works with both generated models and uploaded files.
    // All other tabs require a generated model (currentModel).
    if (!state.currentModel && tabName !== 'parameters') return;
    try {
        switch (tabName) {
            case 'parameters': await loadParameters(); break;
            default: {
                if (!state.currentModel) return;
                const baseName = state.currentModel.baseName;
                switch (tabName) {
                    case 'json': await loadJsonContent(baseName); break;
                    case 'python': await loadPythonContent(baseName); break;
                    case 'step': await loadStepContent(baseName); break;
                }
            }
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

    if (!state.currentModel && !state.previewFile) {
        form.innerHTML = '<p class="params-placeholder">Upload or generate a model to edit parameters</p>';
        regenBtn.classList.add('hidden');
        return;
    }

    // For generated models use the STEP filename; for uploads use the file name directly.
    // The backend /ocp/<filename> endpoint searches both outputs/step/ and data/uploads/.
    const filename = state.currentModel
        ? (extractFilename(state.currentModel.step_file || state.currentModel.py_file || ''))
        : state.previewFile.name;

    form.innerHTML = '<p class="params-placeholder">Analyzing geometry...</p>';

    // For uploaded files, ensure the file is on the backend so OCP can read it.
    if (!state.currentModel && state.previewFile) {
        try {
            await api.uploadStepFile(state.previewFile);
        } catch (uploadErr) {
            console.warn('Pre-upload for OCP failed:', uploadErr);
            // Continue anyway — the file might already be there from a previous upload.
        }
    }

    try {
        const result = await api.getOcpParameters(filename);
        if (!result.features) {
            form.innerHTML = '<p class="params-placeholder">No geometric features found</p>';
            regenBtn.classList.add('hidden');
            return;
        }

        state.ocpFeatures = result.features;
        regenBtn.classList.remove('hidden');
        renderOcpParameters(result.features);
        // Pass feature index to the 3D viewer for face-click tooltips
        stepViewer.setFaceFeatures(result.features);

    } catch (error) {
        form.innerHTML = `<p class="params-placeholder">Error: ${error.message}</p>`;
        regenBtn.classList.add('hidden');
    }
}

function renderOcpParameters(features) {
    const form = DOM.parametersForm();
    let html = '';

    // 0. Recognised shape blocks (from ShapeRecognizer)
    if (features.blocks && features.blocks.length > 0) {
        html += `<div class="ocp-section-title">Recognised Shapes</div>`;
        features.blocks.forEach((blk) => {
            const shape = (blk.shape_type || 'unknown').replace(/_/g, ' ')
                .replace(/\b\w/g, c => c.toUpperCase());
            const confPct = blk.confidence != null ? Math.round(blk.confidence * 100) : 0;
            const confColor = confPct >= 80 ? '#4ade80' : confPct >= 55 ? '#facc15' : '#f87171';
            const params = blk.parameters || {};
            const paramLines = Object.entries(params)
                .filter(([k]) => !k.includes('axis'))   // skip raw axis vectors
                .map(([k, v]) => {
                    const label = k.replace(/_/g, ' ');
                    const value = typeof v === 'number' ? v.toFixed(3) : v;
                    return `<div class="ocp-row"><label>${label}</label><span class="ocp-static">${value}</span></div>`;
                }).join('');
            html += `
                <div class="ocp-card ocp-card-block" data-component="${blk.component_index}">
                    <div class="ocp-card-header">
                        <span class="ocp-face-id">Block ${blk.component_index}</span>
                        <span class="ocp-face-type">${shape}</span>
                        <span class="ocp-conf-badge" style="background:${confColor}22;color:${confColor};border:1px solid ${confColor}55">${confPct}%</span>
                    </div>
                    <div class="ocp-row ocp-summary-row">
                        <span class="ocp-summary">${blk.summary || ''}</span>
                    </div>
                    ${paramLines}
                    <div class="ocp-row">
                        <label>Faces</label>
                        <span class="ocp-static face-ids-list">${(blk.face_ids || []).join(', ')}</span>
                    </div>
                </div>
            `;
        });
    }

    // 1. Cylinders
    if (features.cylinders && features.cylinders.length > 0) {
        html += `<div class="ocp-section-title">Cylindrical Faces</div>`;
        features.cylinders.forEach((c) => {
            html += `
                <div class="ocp-card" data-face-id="${c.id}" data-type="cylinder" onclick="handleFaceCardClick(event,'${c.id}')">
                    <div class="ocp-card-header">
                        <span class="ocp-face-id">${c.id.toUpperCase()}</span>
                        <span class="ocp-face-type">Cylinder</span>
                        <div class="face-group-dots" id="gdots-${c.id}"></div>
                    </div>
                    <div class="ocp-row">
                        <label>Radius (mm)</label>
                        <input type="number" class="ocp-input" data-key="radius_mm" value="${c.radius_mm}" data-original="${c.radius_mm}" step="0.1">
                    </div>
                    <div class="ocp-row">
                        <label>Location (X, Y, Z)</label>
                        <div class="ocp-xyz">
                            <input type="number" class="ocp-input-small" data-key="loc-x" value="${c.location[0]}" data-original="${c.location[0]}" step="0.5">
                            <input type="number" class="ocp-input-small" data-key="loc-y" value="${c.location[1]}" data-original="${c.location[1]}" step="0.5">
                            <input type="number" class="ocp-input-small" data-key="loc-z" value="${c.location[2]}" data-original="${c.location[2]}" step="0.5">
                        </div>
                    </div>
                </div>
            `;
        });
    }

    // 2. Planes
    if (features.planes && features.planes.length > 0) {
        html += `<div class="ocp-section-title">Planar Faces</div>`;
        features.planes.forEach((p) => {
            html += `
                <div class="ocp-card" data-face-id="${p.id}" data-type="plane" onclick="handleFaceCardClick(event,'${p.id}')">
                    <div class="ocp-card-header">
                        <span class="ocp-face-id">${p.id.toUpperCase()}</span>
                        <span class="ocp-face-type">${p.face_type || 'Plane'}</span>
                        <div class="face-group-dots" id="gdots-${p.id}"></div>
                    </div>
                    <div class="ocp-row">
                        <label>Dimensions (mm)</label>
                        <div class="ocp-xyz">
                            <input type="number" class="ocp-input" data-key="dim-0" value="${p.dims[0]}" data-original="${p.dims[0]}" step="1">
                            <span>×</span>
                            <input type="number" class="ocp-input" data-key="dim-1" value="${p.dims[1]}" data-original="${p.dims[1]}" step="1">
                        </div>
                    </div>
                    <div class="ocp-row">
                        <label>Location (X, Y, Z)</label>
                        <div class="ocp-xyz">
                            <input type="number" class="ocp-input-small" data-key="loc-x" value="${p.location[0]}" data-original="${p.location[0]}" step="0.5">
                            <input type="number" class="ocp-input-small" data-key="loc-y" value="${p.location[1]}" data-original="${p.location[1]}" step="0.5">
                            <input type="number" class="ocp-input-small" data-key="loc-z" value="${p.location[2]}" data-original="${p.location[2]}" step="0.5">
                        </div>
                    </div>
                </div>
            `;
        });
    }

    if (!html) html = '<p class="params-placeholder">No editable features found.</p>';
    form.innerHTML = html;

    // Restore group-mode class + selection state after re-render
    _applyGroupModeToForm();
    _refreshAllGroupDots();
}

// ========================================
// Face Groups
// ========================================

/** Switch the active LLM provider and update toggle button states. */
function setLLMProvider(provider) {
    state.llmProvider = provider;
    document.getElementById('provider-gemini-btn').classList.toggle('active', provider === 'gemini');
    document.getElementById('provider-qwen-btn').classList.toggle('active', provider === 'ollama');
}

// ========================================
// Named Points
// ========================================

/** Toggle point-pick mode on/off. */
function togglePointPickMode() {
    state.pointPickMode = !state.pointPickMode;
    stepViewer.enablePointPick(state.pointPickMode);
    const btn = document.getElementById('step3d-btn-pick');
    if (btn) btn.classList.toggle('active', state.pointPickMode);
    const dockBtn = DOM.editDockPointBtn();
    if (dockBtn) dockBtn.classList.toggle('active', state.pointPickMode);
    if (state.pointPickMode) {
        showToast('Point-pick ON — click any surface to drop a point', 'info');
    } else {
        state.pendingPoint = null;
        _hidePointNameBar();
    }
}

/** Called by the stepViewer point-pick callback with the clicked surface coords. */
function _onPointPicked(xyz) {
    state.pendingPoint = xyz;
    _showPointNameBar(xyz);
}

function _showPointNameBar(xyz) {
    const bar = document.getElementById('point-name-bar');
    if (!bar) return;
    const coordEl = document.getElementById('point-name-coords');
    if (coordEl) coordEl.textContent = `[${xyz.map(v => v.toFixed(2)).join(', ')}]`;
    bar.classList.remove('hidden');
    const inp = document.getElementById('point-name-input');
    if (inp) { inp.value = ''; inp.focus(); }
}

function _hidePointNameBar() {
    const bar = document.getElementById('point-name-bar');
    if (bar) bar.classList.add('hidden');
}

/** Save the pending point under the given name. */
function saveNamedPoint() {
    const inp = document.getElementById('point-name-input');
    const raw = inp ? inp.value.trim() : '';
    if (!raw) { showToast('Enter a name for the point', 'warning'); if (inp) inp.focus(); return; }
    if (!state.pendingPoint) { showToast('No point selected on the model', 'warning'); return; }
    const name = raw.replace(/\s+/g, '_');
    state.namedPoints[name] = state.pendingPoint;
    stepViewer.addNamedPointMarker(name, state.pendingPoint);
    state.pendingPoint = null;
    _hidePointNameBar();
    renderNamedPointsList();
    const xyz = state.namedPoints[name];
    showToast(`Point "${name}" saved at [${xyz.map(v => v.toFixed(1)).join(', ')}]`, 'success');
}

/** Delete a named point. */
function deleteNamedPoint(name) {
    delete state.namedPoints[name];
    stepViewer.removeNamedPointMarker(name);
    renderNamedPointsList();
}

/**
 * Insert a @name=[x,y,z] tag into the edit prompt at cursor position.
 * This allows prompts like "create a hole at @bolt_hole_1".
 */
function insertPointIntoPrompt(name) {
    const xyz = state.namedPoints[name];
    if (!xyz) return;
    const input = DOM.editPromptInput();
    if (!input) return;
    const tag = `@${name}=[${xyz.map(v => v.toFixed(2)).join(',')}]`;
    const pos = input.selectionStart || input.value.length;
    input.value = input.value.substring(0, pos) + tag + input.value.substring(pos);
    input.selectionStart = input.selectionEnd = pos + tag.length;
    input.focus();
}

/** Render the named points list in the edit area. */
function renderNamedPointsList() {
    const list = document.getElementById('named-points-list');
    const emptyMsg = document.getElementById('named-points-empty');
    if (!list) return;
    const names = Object.keys(state.namedPoints);
    if (emptyMsg) emptyMsg.classList.toggle('hidden', names.length > 0);
    list.innerHTML = '';
    names.forEach(name => {
        const xyz = state.namedPoints[name];
        const item = document.createElement('div');
        item.className = 'named-point-item';
        item.innerHTML = `
            <span class="named-point-dot"></span>
            <button class="named-point-name" title="Insert into edit prompt"
                    onclick="insertPointIntoPrompt('${name}')">${name}</button>
            <span class="named-point-coords">[${xyz.map(v => v.toFixed(1)).join(', ')}]</span>
            <button class="named-point-del" onclick="deleteNamedPoint('${name}')" title="Remove">&#x2715;</button>
        `;
        list.appendChild(item);
    });
}

/** Toggle group-selection mode on/off. */
function toggleGroupMode() {
    state.groupMode = !state.groupMode;
    const btn = DOM.groupModeBtn();
    const bar = DOM.groupModeBar();

    if (state.groupMode) {
        setSidepanelView('params');
        btn.textContent = '✓ Done';
        btn.classList.add('active');
        bar.classList.remove('hidden');
        showToast('Selection mode ON — click a face card to select it', 'info');
    } else {
        btn.textContent = '⊕ Select';
        btn.classList.remove('active');
        bar.classList.add('hidden');
        clearFaceSelection();
    }

    _applyGroupModeToForm();
}

function openGroupSelectionWorkflow() {
    setSidepanelView('params');
    if (!state.groupMode) toggleGroupMode();
}

/** Add/remove group-mode class on the parameters form and restore selected state. */
function _applyGroupModeToForm() {
    const form = DOM.parametersForm();
    if (!form) return;
    if (state.groupMode) {
        form.classList.add('group-mode');
    } else {
        form.classList.remove('group-mode');
    }
    // Restore selected highlights for currently-selected faces
    form.querySelectorAll('.ocp-card[data-face-id]').forEach(card => {
        card.classList.toggle('face-selected', state.selectedFaces.has(card.dataset.faceId));
    });
}

/** Called by onclick on every face card. In group-mode toggles selection. */
function handleFaceCardClick(event, faceId) {
    if (!state.groupMode) return;
    // Don't intercept input/button clicks — user still needs to edit values
    const tag = event.target.tagName.toLowerCase();
    if (['input', 'button', 'select', 'textarea'].includes(tag)) return;
    event.stopPropagation();
    _toggleFaceSelection(faceId);
}

function _toggleFaceSelection(faceId) {
    if (state.selectedFaces.has(faceId)) {
        state.selectedFaces.delete(faceId);
    } else {
        state.selectedFaces.add(faceId);
    }
    // Sync 3D viewer highlight (green = selected, plain = deselected)
    stepViewer.setGroupFaceSelected(faceId, state.selectedFaces.has(faceId));
    _syncSelectionUI();
}

/** Re-paint selection count + card highlights. */
function _syncSelectionUI() {
    const count = DOM.groupSelCount();
    if (count) count.textContent = state.selectedFaces.size;

    const form = DOM.parametersForm();
    if (form) {
        form.querySelectorAll('.ocp-card[data-face-id]').forEach(card => {
            card.classList.toggle('face-selected', state.selectedFaces.has(card.dataset.faceId));
        });
    }
}

/** Deselect all faces. */
function clearFaceSelection() {
    state.selectedFaces.clear();
    stepViewer.clearAllGroupHighlights();
    _syncSelectionUI();
}

/**
 * Create (or merge into) a named group from the current selection.
 * If a group with the same name already exists, the selected faces are
 * added to it.
 */
function createGroupFromSelection() {
    const nameInput = DOM.groupNameInput();
    const rawName = (nameInput ? nameInput.value.trim() : '');
    if (!rawName) {
        showToast('Please enter a group name first', 'warning');
        if (nameInput) nameInput.focus();
        return;
    }
    if (state.selectedFaces.size === 0) {
        showToast('No faces selected — click face cards to select them', 'warning');
        return;
    }

    const name = rawName.toLowerCase().replace(/\s+/g, '_');

    if (state.faceGroups[name]) {
        // Merge: add new faces to existing group
        const existing = state.faceGroups[name].faces;
        state.selectedFaces.forEach(fid => {
            if (!existing.includes(fid)) existing.push(fid);
        });
        showToast(`Added ${state.selectedFaces.size} face(s) to group "${name}"`, 'success');
    } else {
        // Create new group with next palette colour
        const usedColors = Object.values(state.faceGroups).map(g => g.color);
        const color = GROUP_COLORS.find(c => !usedColors.includes(c)) || GROUP_COLORS[Object.keys(state.faceGroups).length % GROUP_COLORS.length];
        state.faceGroups[name] = {
            faces: [...state.selectedFaces],
            color,
        };
        showToast(`Group "${name}" created with ${state.selectedFaces.size} face(s)`, 'success');
    }

    if (nameInput) nameInput.value = '';
    clearFaceSelection();
    renderGroupsPanel();
}

/** Remove a face from a specific group. */
function removeFaceFromGroup(groupName, faceId) {
    const g = state.faceGroups[groupName];
    if (!g) return;
    g.faces = g.faces.filter(f => f !== faceId);
    if (g.faces.length === 0) {
        delete state.faceGroups[groupName];
        showToast(`Group "${groupName}" deleted (empty)`, 'info');
    }
    renderGroupsPanel();
}

/** Delete an entire group. */
function deleteGroup(groupName) {
    delete state.faceGroups[groupName];
    renderGroupsPanel();
    showToast(`Group "${groupName}" deleted`, 'info');
}

/** Toggle collapsed/expanded state of a group's face list. */
function toggleGroupExpand(groupName) {
    const facesEl = document.getElementById(`gfaces-${groupName}`);
    const btnEl   = document.getElementById(`gexpand-${groupName}`);
    if (!facesEl) return;
    facesEl.classList.toggle('hidden');
    if (btnEl) btnEl.classList.toggle('rotated');
}

/** Re-render the groups list panel. */
function renderGroupsPanel() {
    const list     = DOM.groupsList();
    const emptyMsg = DOM.groupsEmptyMsg();
    if (!list) return;

    const groups = Object.entries(state.faceGroups);

    if (groups.length === 0) {
        list.innerHTML = `<p class="groups-empty-msg" id="groups-empty-msg">
            No groups yet — click <strong>⊕ Select</strong>, pick faces&nbsp;in the panel below, then save a group.
        </p>`;
        _refreshAllGroupDots();
        return;
    }

    // Hide placeholder
    list.innerHTML = groups.map(([name, g]) => {
        const { faces, color } = g;
        const faceChips = faces.map(fid => `
            <span class="group-face-chip">
                ${fid.toUpperCase()}
                <button onclick="removeFaceFromGroup('${name}','${fid}')" title="Remove from group">×</button>
            </span>
        `).join('');

        return `
            <div class="group-card" style="--group-color:${color}; border-color:${color}33; background:${color}08;">
                <div class="group-card-header" onclick="toggleGroupExpand('${name}')">
                    <span class="group-color-dot"></span>
                    <span class="group-card-name">${name}</span>
                    <span class="group-face-badge" style="color:${color};border-color:${color}55;background:${color}18;">
                        ${faces.length} face${faces.length !== 1 ? 's' : ''}
                    </span>
                    <button id="gexpand-${name}" class="group-expand-btn" title="Expand/collapse">▾</button>
                    <button class="group-delete-btn" onclick="event.stopPropagation();deleteGroup('${name}')" title="Delete group">✕</button>
                </div>
                <div id="gfaces-${name}" class="group-faces hidden">
                    ${faceChips}
                </div>
            </div>
        `;
    }).join('');

    _refreshAllGroupDots();
}

/**
 * Refresh the colored dot indicators on each face card that show which
 * group(s) the face belongs to.
 */
function _refreshAllGroupDots() {
    // Build a map: faceId → [{color, groupName}]
    const membership = {};
    Object.entries(state.faceGroups).forEach(([name, g]) => {
        g.faces.forEach(fid => {
            if (!membership[fid]) membership[fid] = [];
            membership[fid].push({ name, color: g.color });
        });
    });

    // Update every dot container in the form
    document.querySelectorAll('.face-group-dots[id^="gdots-"]').forEach(el => {
        const faceId = el.id.replace('gdots-', '');
        const groups = membership[faceId] || [];
        el.innerHTML = groups.map(({ name, color }) =>
            `<span class="face-group-dot" style="background:${color};box-shadow:0 0 4px ${color}" title="${name}"></span>`
        ).join('');
    });
}

/**
 * Builds a face-group context block to prepend to an edit prompt so the
 * AI knows which face IDs "holes", "bosses" etc. refer to.
 * Returns the original prompt unchanged if no groups exist.
 */
function _injectGroupContext(prompt) {
    const groups = Object.entries(state.faceGroups);
    if (groups.length === 0) return prompt;

    const lines = groups.map(([name, g]) =>
        `  • ${name}: ${g.faces.join(', ')} (${g.faces.length} face${g.faces.length !== 1 ? 's' : ''})`
    );
    const ctx = `[Face Groups — use these names in your prompt]\n${lines.join('\n')}\n\n`;
    return ctx + prompt;
}

/**
 * Prepends a named-points coordinate table so the AI can resolve any point
 * name the user wrote in their prompt into exact [x, y, z] coordinates.
 * Also expands any @name=[...] tags already in the prompt (inserted via the
 * "Insert" button) to plain coordinate triples so the backend sees raw numbers.
 */
function _injectPointContext(prompt) {
    // Replace @name=[x,y,z] tags with just [x,y,z] so the LLM sees coords directly
    let resolved = prompt.replace(/@([\w]+)=\[([^\]]+)\]/g, (_, pname, coords) => `[${coords}]`);

    // Also auto-expand bare point names that appear in the prompt
    // e.g. "create a hole at p1" becomes "create a hole at [x, y, z]"
    const entries = Object.entries(state.namedPoints);
    entries.forEach(([name, xyz]) => {
        const re = new RegExp(`\\b${name}\\b`, 'g');
        resolved = resolved.replace(re, `[${xyz.map(v => v.toFixed(3)).join(', ')}]`);
    });

    // Prepend a context block listing all named points regardless of whether
    // the user referenced them by name — gives the LLM full positional context.
    if (entries.length === 0) return resolved;
    const lines = entries.map(([name, xyz]) =>
        `  • ${name}: [${xyz.map(v => v.toFixed(3)).join(', ')}]`
    );
    const ctx = `[Named Points — use coordinates for location/position references]\n${lines.join('\n')}\n\n`;
    return ctx + resolved;
}

// ========================================
// Templates
// ========================================
async function loadPromptTemplateToolkit() {
    const treeEl = DOM.promptTemplateTree();
    const gridEl = DOM.promptTemplateGrid();
    const summaryEl = DOM.promptTemplateSummary();
    if (!treeEl || !gridEl || !summaryEl) return;

    try {
        const response = await api.getTemplateCatalog('prompt');
        const catalogTemplates = response?.catalog?.templates || [];

        state.promptTemplates = catalogTemplates.map(_normalizeEditTemplate);
        state.templates = state.promptTemplates;

        if (state.promptTemplates.length === 0) {
            const fallback = await api.getTemplates();
            state.promptTemplates = fallback.map(_normalizeEditTemplate);
            state.templates = state.promptTemplates;
        }

        const categories = [...new Set(
            state.promptTemplates
                .map(t => t.categoryText)
                .filter(Boolean)
        )].sort((a, b) => a.localeCompare(b));

        state.selectedPromptCategory = categories[0] || '';

        const readyCount = state.promptTemplates.filter(t => t.buildStatus === 'ready').length;
        summaryEl.textContent = `${readyCount}/${state.promptTemplates.length} ready`;

        renderPromptTemplateCategoryTree();
        renderPromptTemplateGrid();
    } catch (error) {
        console.error('Failed to load prompt template toolkit:', error);
        summaryEl.textContent = 'Templates unavailable';
        treeEl.innerHTML = '<p class="edit-template-empty">Could not load template categories.</p>';
        gridEl.innerHTML = '<p class="edit-template-empty">Could not load templates from backend.</p>';
    }
}

function renderPromptTemplateCategoryTree() {
    const treeEl = DOM.promptTemplateTree();
    if (!treeEl) return;

    if (!state.promptTemplates.length) {
        treeEl.innerHTML = '<p class="edit-template-empty">No template categories found.</p>';
        return;
    }

    const categories = [...new Set(
        state.promptTemplates
            .map(t => t.categoryText)
            .filter(Boolean)
    )].sort((a, b) => a.localeCompare(b));

    treeEl.innerHTML = '';

    categories.forEach((category) => {
        const depth = category.split('/').length - 1;
        const button = document.createElement('button');
        button.className = `edit-template-category${state.selectedPromptCategory === category ? ' active' : ''}`;
        button.style.paddingLeft = `${8 + depth * 14}px`;
        button.dataset.categoryPath = category;
        button.textContent = category.split('/').pop() || category;
        button.title = category;
        treeEl.appendChild(button);
    });
}

function renderPromptTemplateGrid() {
    const gridEl = DOM.promptTemplateGrid();
    if (!gridEl) return;

    const selected = state.selectedPromptCategory;
    const templates = state.promptTemplates
        .filter(t => !selected || t.categoryText === selected || t.categoryText.startsWith(`${selected}/`))
        .sort((a, b) => a.name.localeCompare(b.name));

    if (templates.length === 0) {
        gridEl.innerHTML = '<p class="edit-template-empty">No templates in this category.</p>';
        return;
    }

    gridEl.innerHTML = '';
    const BASE = 'http://localhost:5000';

    templates.forEach((template) => {
        const card = document.createElement('div');
        card.className = `edit-template-card${state.selectedPromptTemplateId === template.templateId ? ' active' : ''}`;
        card.dataset.templateId = template.templateId;
        card.title = `Use ${template.name} for generation`;

        const thumbWrap = document.createElement('div');
        thumbWrap.className = 'edit-template-thumb-wrap';

        if (template.thumbnailUrl) {
            const img = document.createElement('img');
            img.className = 'edit-template-thumb';
            img.src = `${BASE}${template.thumbnailUrl}`;
            img.alt = template.name;
            img.loading = 'lazy';
            img.onerror = () => {
                img.remove();
                const fallback = document.createElement('span');
                fallback.className = 'edit-template-no-thumb';
                fallback.textContent = 'No preview';
                thumbWrap.appendChild(fallback);
            };
            thumbWrap.appendChild(img);
        } else {
            const fallback = document.createElement('span');
            fallback.className = 'edit-template-no-thumb';
            fallback.textContent = 'No preview';
            thumbWrap.appendChild(fallback);
        }

        const name = document.createElement('div');
        name.className = 'edit-template-name';
        name.textContent = template.name;

        const meta = document.createElement('div');
        meta.className = 'edit-template-meta';
        meta.textContent = template.categoryText || 'general';

        card.appendChild(thumbWrap);
        card.appendChild(name);
        card.appendChild(meta);
        gridEl.appendChild(card);
    });
}

function handlePromptTemplateCategorySelect(categoryPath) {
    state.selectedPromptCategory = categoryPath;
    renderPromptTemplateCategoryTree();
    renderPromptTemplateGrid();
}

function handlePromptTemplateSelect(templateId) {
    const template = state.promptTemplates.find(t => t.templateId === templateId);
    if (!template) return;

    state.selectedPromptTemplate = {
        ...template,
        category: template.categoryText,
    };
    state.selectedPromptTemplateId = template.templateId;

    const promptInput = DOM.promptInput();
    const defaultPrompt = template.description || `Create a ${template.name}`;
    promptInput.value = defaultPrompt;

    renderPromptTemplateGrid();
}

function buildGenerationPrompt() {
    const userPrompt = DOM.promptInput().value.trim();
    const selectedTemplate = state.selectedPromptTemplate;
    if (!selectedTemplate) return userPrompt;

    const templateName = selectedTemplate.name || 'Unnamed template';
    const category = selectedTemplate.category || 'general';
    const description = selectedTemplate.description || '';

    const templateContext = [
        '[Template Context]',
        `Template: ${templateName}`,
        `Category: ${category}`,
        description ? `Description: ${description}` : null,
        '',
    ].filter(Boolean).join('\n');

    return `${templateContext}\n${userPrompt}`.trim();
}

function _normalizeEditTemplate(item) {
    const categoryPath = Array.isArray(item.category_path)
        ? item.category_path
        : (typeof item.category === 'string' && item.category ? item.category.split('/') : []);
    return {
        templateId: item.template_id || item.id || '',
        name: item.name || 'Unnamed template',
        categoryPath,
        categoryText: categoryPath.join('/'),
        thumbnailUrl: item.thumbnail_url || '',
        stepUrl: item.step_url || '',
        buildStatus: item.build_status || 'pending',
        description: item.description || '',
    };
}

async function loadEditTemplateToolkit() {
    const treeEl = DOM.editTemplateTree();
    const gridEl = DOM.editTemplateGrid();
    const summaryEl = DOM.editTemplateSummary();
    if (!treeEl || !gridEl || !summaryEl) return;

    try {
        const response = await api.getTemplateCatalog('edit');
        const catalogTemplates = response?.catalog?.templates || [];

        state.editTemplates = catalogTemplates.map(_normalizeEditTemplate);
        if (state.editTemplates.length === 0) {
            const fallback = await api.getTemplates();
            state.editTemplates = fallback.map(_normalizeEditTemplate);
        }

        const categories = [...new Set(
            state.editTemplates
                .map(t => t.categoryText)
                .filter(Boolean)
        )].sort((a, b) => a.localeCompare(b));

        state.selectedEditCategory = categories[0] || '';

        const readyCount = state.editTemplates.filter(t => t.buildStatus === 'ready').length;
        summaryEl.textContent = `${readyCount}/${state.editTemplates.length} ready`;

        renderEditTemplateCategoryTree();
        renderEditTemplateGrid();
    } catch (error) {
        console.error('Failed to load edit template toolkit:', error);
        summaryEl.textContent = 'Templates unavailable';
        treeEl.innerHTML = '<p class="edit-template-empty">Could not load template categories.</p>';
        gridEl.innerHTML = '<p class="edit-template-empty">Could not load templates from backend.</p>';
    }
}

function renderEditTemplateCategoryTree() {
    const treeEl = DOM.editTemplateTree();
    if (!treeEl) return;

    if (!state.editTemplates.length) {
        treeEl.innerHTML = '<p class="edit-template-empty">No template categories found.</p>';
        return;
    }

    const categories = [...new Set(
        state.editTemplates
            .map(t => t.categoryText)
            .filter(Boolean)
    )].sort((a, b) => a.localeCompare(b));

    treeEl.innerHTML = '';

    categories.forEach((category) => {
        const depth = category.split('/').length - 1;
        const button = document.createElement('button');
        button.className = `edit-template-category${state.selectedEditCategory === category ? ' active' : ''}`;
        button.style.paddingLeft = `${8 + depth * 14}px`;
        button.dataset.categoryPath = category;
        button.textContent = category.split('/').pop() || category;
        button.title = category;
        treeEl.appendChild(button);
    });
}

function renderEditTemplateGrid() {
    const gridEl = DOM.editTemplateGrid();
    if (!gridEl) return;

    const selected = state.selectedEditCategory;
    const templates = state.editTemplates
        .filter(t => !selected || t.categoryText === selected || t.categoryText.startsWith(`${selected}/`))
        .sort((a, b) => {
            if (a.buildStatus === b.buildStatus) return a.name.localeCompare(b.name);
            if (a.buildStatus === 'ready') return -1;
            if (b.buildStatus === 'ready') return 1;
            return a.name.localeCompare(b.name);
        });

    if (templates.length === 0) {
        gridEl.innerHTML = '<p class="edit-template-empty">No templates in this category.</p>';
        return;
    }

    gridEl.innerHTML = '';
    const BASE = 'http://localhost:5000';

    templates.forEach((template) => {
        const card = document.createElement('div');
        const isReady = template.buildStatus === 'ready';
        card.className = `edit-template-card${!isReady ? ' disabled' : ''}${state.selectedEditTemplateId === template.templateId ? ' active' : ''}`;
        card.dataset.templateId = template.templateId;
        card.title = isReady ? `Load ${template.name} in Edit mode` : `Template not ready (${template.buildStatus})`;

        const thumbWrap = document.createElement('div');
        thumbWrap.className = 'edit-template-thumb-wrap';

        if (template.thumbnailUrl) {
            const img = document.createElement('img');
            img.className = 'edit-template-thumb';
            img.src = `${BASE}${template.thumbnailUrl}`;
            img.alt = template.name;
            img.loading = 'lazy';
            img.onerror = () => {
                img.remove();
                const fallback = document.createElement('span');
                fallback.className = 'edit-template-no-thumb';
                fallback.textContent = 'No preview';
                thumbWrap.appendChild(fallback);
            };
            thumbWrap.appendChild(img);
        } else {
            const fallback = document.createElement('span');
            fallback.className = 'edit-template-no-thumb';
            fallback.textContent = 'No preview';
            thumbWrap.appendChild(fallback);
        }

        const name = document.createElement('div');
        name.className = 'edit-template-name';
        name.textContent = template.name;

        const meta = document.createElement('div');
        meta.className = 'edit-template-meta';
        meta.textContent = template.buildStatus;

        card.appendChild(thumbWrap);
        card.appendChild(name);
        card.appendChild(meta);
        gridEl.appendChild(card);
    });
}

function handleEditTemplateCategorySelect(categoryPath) {
    state.selectedEditCategory = categoryPath;
    renderEditTemplateCategoryTree();
    renderEditTemplateGrid();
}

async function handleEditTemplateLoad(templateId) {
    const template = state.editTemplates.find(t => t.templateId === templateId);
    if (!template) return;

    if (template.buildStatus !== 'ready' || !template.stepUrl) {
        showToast(`Template "${template.name}" is not ready yet`, 'warning');
        return;
    }

    const modePromptBtn = document.getElementById('mode-prompt-btn');
    const modeEditBtn = document.getElementById('mode-edit-btn');
    const modeSectionPrompt = document.getElementById('mode-section-prompt');
    const modeSectionEdit = document.getElementById('mode-section-edit');
    if (modeEditBtn && modePromptBtn && modeSectionEdit && modeSectionPrompt) {
        modeEditBtn.classList.add('active');
        modePromptBtn.classList.remove('active');
        modeSectionEdit.classList.remove('hidden');
        modeSectionPrompt.classList.add('hidden');
    }
    setSidepanelView('workflow');
    syncEditDockVisibility();

    const BASE = 'http://localhost:5000';
    const stepUrl = `${BASE}${template.stepUrl}`;
    const fileName = `${template.templateId.split('/').pop()}.step`;

    showLoading(`Loading template "${template.name}"...`);
    try {
        const loaded = await _autoLoadStepForEditing(stepUrl, fileName);
        if (!loaded) throw new Error('Unable to fetch template STEP file');

        switchTab('viewer3d');
        stepViewer.loadStepUrl(stepUrl);
        addToHistoryFromUrl(fileName, stepUrl);

        await loadParameters();
        if (state.ocpFeatures) stepViewer.setFaceFeatures(state.ocpFeatures);

        state.selectedEditTemplateId = template.templateId;
        renderEditTemplateGrid();
        showToast(`Template "${template.name}" loaded in Edit mode`, 'success');
    } catch (error) {
        DOM.editError().textContent = `Template load failed: ${error.message}`;
        showToast(`Template load failed: ${error.message}`, 'error');
    } finally {
        hideLoading();
    }
}

// ========================================
// Generation
// ========================================
async function handleGenerate() {
    const prompt = buildGenerationPrompt();
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
        // Feed features to the 3D viewer tooltip engine (loadParameters sets state.ocpFeatures)
        if (state.ocpFeatures) stepViewer.setFaceFeatures(state.ocpFeatures);

        // Auto-load the generated STEP into the 3D viewer
        const stepUrl = `http://localhost:5000/outputs/step/${stepFile}`;
        switchTab('viewer3d');
        stepViewer.loadStepUrl(stepUrl);
        addToHistoryFromUrl(stepFile, stepUrl);

        // Silently register the generated file for the edit pipeline
        // so the user can switch to Edit tab and edit immediately.
        _autoLoadStepForEditing(stepUrl, stepFile);

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
    if (!state.ocpFeatures) {
        showError('No geometric features loaded');
        showToast('Please load a model first to extract parameters', 'error');
        return;
    }

    if (!state.currentModel && !state.previewFile) {
        showError('No model loaded');
        showToast('Please generate or upload a model first', 'error');
        return;
    }

    showLoading('Mapping edits & regenerating model...');

    try {
        // Derive the filename the backend will use to find the STEP file.
        // For generated models use the STEP filename; for uploads use previewFile.name.
        const filename = state.currentModel
            ? extractFilename(state.currentModel.step_file || state.currentModel.py_file || '')
            : state.previewFile.name;

        // If this is an uploaded file, make sure it's on the backend before regenerating.
        if (!state.currentModel && state.previewFile) {
            updateLoading('Uploading file to backend...');
            try {
                await api.uploadStepFile(state.previewFile);
            } catch (uploadErr) {
                console.warn('Re-upload for regeneration failed:', uploadErr);
                // Continue — the file may already exist from the earlier loadParameters upload.
            }
        }

        updateLoading('Collecting parameter changes...');

        // Collect updates from the UI
        const updates = [];
        let hasInvalidInputs = false;
        const invalidMessages = [];
        
        document.querySelectorAll('.ocp-card').forEach(card => {
            const faceId = card.dataset.faceId;
            const type = card.dataset.type;
            const update = { id: faceId, type: type };
            let changed = false;

            // Check for radius (cylinders) — only collect if value actually changed
            const radInput = card.querySelector('[data-key="radius_mm"]');
            if (radInput) {
                const radValue = parseFloat(radInput.value);
                const radOrig  = parseFloat(radInput.dataset.original ?? radInput.value);
                if (isNaN(radValue) || radValue <= 0) {
                    hasInvalidInputs = true;
                    invalidMessages.push(`Invalid radius for ${faceId}: must be positive number`);
                } else if (radValue !== radOrig) {
                    update.radius_mm = radValue;
                    changed = true;
                }
            }

            // Check for dims (planes) — only collect if either dimension changed
            const d0 = card.querySelector('[data-key="dim-0"]');
            const d1 = card.querySelector('[data-key="dim-1"]');
            if (d0 && d1) {
                const dim0 = parseFloat(d0.value);
                const dim1 = parseFloat(d1.value);
                const origDim0 = parseFloat(d0.dataset.original ?? d0.value);
                const origDim1 = parseFloat(d1.dataset.original ?? d1.value);
                if (isNaN(dim0) || dim0 <= 0 || isNaN(dim1) || dim1 <= 0) {
                    hasInvalidInputs = true;
                    invalidMessages.push(`Invalid dimensions for ${faceId}: must be positive numbers`);
                } else if (dim0 !== origDim0 || dim1 !== origDim1) {
                    update.dims = [dim0, dim1];
                    changed = true;
                }
            }

            // Check for Location XYZ — only collect if any coordinate changed
            const lx = card.querySelector('[data-key="loc-x"]');
            const ly = card.querySelector('[data-key="loc-y"]');
            const lz = card.querySelector('[data-key="loc-z"]');
            if (lx && ly && lz) {
                const locX = parseFloat(lx.value);
                const locY = parseFloat(ly.value);
                const locZ = parseFloat(lz.value);
                const origX = parseFloat(lx.dataset.original ?? lx.value);
                const origY = parseFloat(ly.dataset.original ?? ly.value);
                const origZ = parseFloat(lz.dataset.original ?? lz.value);
                if (isNaN(locX) || isNaN(locY) || isNaN(locZ)) {
                    hasInvalidInputs = true;
                    invalidMessages.push(`Invalid location for ${faceId}: must be valid numbers`);
                } else if (locX !== origX || locY !== origY || locZ !== origZ) {
                    update.location = [locX, locY, locZ];
                    changed = true;
                }
            }

            if (changed) updates.push(update);
        });

        if (hasInvalidInputs) {
            hideLoading();
            showError('Parameter validation failed');
            showToast(invalidMessages.join('; '), 'error');
            return;
        }

        if (updates.length === 0) {
            showToast('No changes detected — edit a radius, dimension, or location value then try again.', 'warning');
            hideLoading();
            return;
        }

        updateLoading('Mapping geometric edits via LLM...');
        console.log('Sending updates:', updates);
        
        const result = await api.regenerateOcp(filename, state.ocpFeatures, updates);

        if (result.status === 'success') {
            // Update state — the regeneration always produces a generated-model result.
            state.currentModel = {
                ...result,
                baseName: result.base_name || (result.step_file ? extractFilename(result.step_file).replace('.step', '') : 'result')
            };

            if (result.glb_url) {
                DOM.visualizeBtn().classList.remove('hidden');
            }

            // Reload other panels
            updateLoading('Loading updated model files...');
            await Promise.all([
                loadJsonContent(state.currentModel.baseName),
                loadPythonContent(state.currentModel.baseName),
                loadStepContent(state.currentModel.baseName),
                loadParameters() // Re-extract new geometry features
            ]);

            // Load into viewer
            if (result.step_file) {
                const stepUrl = `http://localhost:5000/outputs/step/${extractFilename(result.step_file)}`;
                switchTab('viewer3d');
                stepViewer.loadStepUrl(stepUrl);
                addToHistoryFromUrl(extractFilename(result.step_file), stepUrl);
            }

            showToast('Model regenerated from geometric edits!', 'success');
        } else {
            throw new Error(result.error?.message || result.message || 'Regeneration failed');
        }

    } catch (error) {
        console.error('Regeneration error:', error);
        const errorMsg = error.message || 'Unknown error occurred';
        showError(`Regeneration failed: ${errorMsg}`);
        showToast(`Error: ${errorMsg}`, 'error');
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

    if (!mv) {
        // GLB model-viewer not available — fall back to loading the STEP in the Three.js viewer
        const stepFile = extractFilename(state.currentModel.step_file || '');
        if (stepFile) {
            switchTab('viewer3d');
            stepViewer.loadStepUrl(`${BASE}/outputs/step/${stepFile}`);
        }
        return;
    }

    mv.setAttribute('src', glbUrl);
    const ph   = DOM.viewer3dPlaceholder();
    const cont = DOM.viewer3dContainer();
    if (ph)   ph.classList.add('hidden');
    if (cont) cont.classList.remove('hidden');

    // Switch to 3D Viewer tab
    switchTab('viewer3d');
    showToast('3D model loaded', 'success');
}

// ========================================
// Upload & Preview
// ========================================

function selectStepFile(file) {
    state.previewFile = file;
    DOM.dropZoneText().textContent = file.name;
    DOM.dropZone().classList.add('has-file');
    DOM.previewBtn().disabled = false;
    DOM.view3dBtn().disabled = false;
    DOM.previewError().textContent = '';
    state.editDockExpanded = true;
    // Show edit dock when Edit mode is active
    syncEditDockVisibility();
    // Auto-populate the Parameters panel as soon as a file is chosen
    loadParameters().catch(() => {});
}

/**
 * Fetch a server-side STEP URL as a File object and register it as
 * state.previewFile so it can be sent to the edit pipeline without
 * the user manually re-uploading it.  Non-fatal — silently skips on error.
 */
async function _autoLoadStepForEditing(stepUrl, filename) {
    try {
        const resp = await fetch(stepUrl);
        if (!resp.ok) return false;
        const blob = await resp.blob();
        const file = new File([blob], filename, { type: 'application/octet-stream' });
        state.previewFile = file;
        // Update the upload drop-zone so the Edit tab reflects the active file
        DOM.dropZoneText().textContent = filename;
        DOM.dropZone().classList.add('has-file');
        DOM.previewBtn().disabled = false;
        DOM.view3dBtn().disabled = false;
        state.editDockExpanded = true;
        syncEditDockVisibility();
        return true;
    } catch (_) {
        return false;
    }
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
        state.editDockExpanded = true;
        syncEditDockVisibility();

        // Switch to Preview tab and render gallery
        switchTab('preview');
        renderPreviewGallery(result.image_urls);
        showToast('Preview ready — 7 views rendered', 'success');

        // Record in preview panel history
        addToHistoryEntry('preview', { name: state.previewFile.name, source: 'preview' });

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

    // Reset pan and zoom whenever a new preview loads
    _resetTransform();

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

function isTemplatePlacementCommand(prompt) {
    if (!prompt) return false;
    return /\b(add|place|insert)\b.+\bat\s*\[\s*-?\d+(?:\.\d+)?\s*,\s*-?\d+(?:\.\d+)?\s*,\s*-?\d+(?:\.\d+)?\s*\]/i.test(prompt);
}

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

    // Prepend face-group context AND named-point coordinates so the AI can
    // resolve group names and point names to exact geometry references.
    const enrichedPrompt = _injectPointContext(_injectGroupContext(prompt));

    DOM.editError().textContent = '';
    showLoading('Editing STEP file…');

    try {
        const formData = new FormData();
        formData.append('file', state.previewFile);
        formData.append('provider', state.llmProvider);

        const isTemplateCmd = isTemplatePlacementCommand(prompt);
        let result;
        if (isTemplateCmd) {
            formData.append('command', prompt);
            updateLoading('Applying template placement command…');
            result = await api.templateCommand(formData);
        } else {
            formData.append('prompt', enrichedPrompt);
            result = await api.editStep(formData);
        }

        // ── Lossless BREP path: result has step_file but no py_file / json_file ──
        // Only load what actually exists; skip JSON/Python tabs for BREP edits.
        if (result.step_url && result.step_file) {
            const stepFilename = result.step_file.split(/[\\/]/).pop();
            const baseName = stepFilename.replace('.step', '');

            state.currentModel = {
                ...result,
                baseName,
                step_file: result.step_file,
            };

            // Reload available output tabs
            updateLoading('Loading edited model…');
            const loaders = [loadStepContent(baseName), loadParameters()];
            // Only attempt code tabs if the pipeline produced them (regeneration path)
            if (result.py_file)   loaders.push(loadPythonContent(baseName));
            if (result.json_file) loaders.push(loadJsonContent(baseName));
            await Promise.all(loaders);
            if (state.ocpFeatures) stepViewer.setFaceFeatures(state.ocpFeatures);

            // auto-load into 3D viewer
            const stepUrl = `http://localhost:5000/outputs/step/${stepFilename}`;
            switchTab('viewer3d');
            stepViewer.loadStepUrl(stepUrl);
            addToHistoryFromUrl(stepFilename, stepUrl);

            // Update previewFile to the freshly-edited STEP so the next
            // edit operates on the latest version without a manual re-upload.
            _autoLoadStepForEditing(stepUrl, stepFilename);

            showToast(isTemplateCmd ? 'Template placement applied — model updated' : 'STEP edited — model updated', 'success');
        } else {
            showToast('Edit complete (no step_url returned)', 'warning');
        }

        // Record in step panel history
        addToHistoryEntry('step', {
            name: state.previewFile ? state.previewFile.name : 'edited.step',
            source: 'edit',
        });

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

// ========================================
// History — Per-Panel, Backend-Persistent
// ========================================

let _currentHistoryPanel = null;   // which panel's sidebar is open

/** Open (or close if same) the history sidebar for a given panel. */
async function toggleHistorySidebar(panelId) {
    const sidebar = document.getElementById('history-sidebar');
    const overlay = document.getElementById('history-overlay');
    const isOpen = sidebar.classList.contains('open');

    // If clicking the same panel while already open → close
    if (isOpen && _currentHistoryPanel === panelId) {
        closeHistorySidebar();
        return;
    }

    _currentHistoryPanel = panelId;

    // Update title
    const titles = {
        'viewer3d': '3D Viewer History',
        'preview': 'Preview History',
        'json': 'JSON History',
        'python': 'Python History',
        'step': 'STEP History',
        'parameters': 'Parameters History',
    };
    document.getElementById('history-sidebar-title').textContent =
        titles[panelId] || 'Panel History';

    // Highlight the active icon button (clear old)
    document.querySelectorAll('.panel-history-btn').forEach(btn => btn.classList.remove('active'));
    const activePanel = document.getElementById(`panel-${panelId}`);
    if (activePanel) {
        const btn = activePanel.querySelector('.panel-history-btn');
        if (btn) btn.classList.add('active');
    }

    // Open drawer
    sidebar.classList.add('open');
    overlay.classList.add('open');

    // Load history from backend
    await _renderHistorySidebar(panelId);
}

/** Close the history sidebar drawer. */
function closeHistorySidebar() {
    const sidebar = document.getElementById('history-sidebar');
    const overlay = document.getElementById('history-overlay');
    sidebar.classList.remove('open');
    overlay.classList.remove('open');

    // Remove active state from icon buttons
    document.querySelectorAll('.panel-history-btn').forEach(btn => btn.classList.remove('active'));
    _currentHistoryPanel = null;
}

/** Fetch entries for panelId from backend and render them. */
async function _renderHistorySidebar(panelId) {
    const list = document.getElementById('history-sidebar-list');
    list.innerHTML = '<p class="history-empty">Loading…</p>';

    try {
        const result = await api.getHistory(panelId);
        const entries = result.entries || [];
        _paintHistoryList(list, panelId, entries);
    } catch (e) {
        list.innerHTML = '<p class="history-empty">Could not load history.</p>';
    }
}

/** Render history cards into a container element. */
function _paintHistoryList(list, panelId, entries) {
    if (!entries.length) {
        list.innerHTML = '<p class="history-empty">No activity yet for this panel.</p>';
        return;
    }

    list.innerHTML = entries.map((entry, idx) => {
        const dt = new Date(entry.timestamp);
        const time = dt.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        const date = dt.toLocaleDateString([], { month: 'short', day: 'numeric' });
        const icon = entry.source === 'generated' ? '⚙' :
            entry.source === 'preview' ? '🔍' :
                entry.source === 'edit' ? '✏' : '📁';
        const hasUrl = !!(entry.url);
        return `
            <div class="history-card" onclick="loadFromHistoryEntry('${panelId}', ${idx})" data-panel="${panelId}" data-idx="${idx}">
                <div class="history-card-icon">${icon}</div>
                <div class="history-card-info">
                    <span class="history-card-name" title="${entry.name}">${entry.name}</span>
                    <span class="history-card-time">${date} ${time}</span>
                </div>
                <div class="history-card-action">${hasUrl ? '▶' : '↑'}</div>
            </div>
        `;
    }).join('');

    // Store entries on element for replay
    list._historyEntries = entries;
}

/** Replay a history entry. URL entries load into 3D viewer; upload-only entries prompt re-upload. */
async function loadFromHistoryEntry(panelId, idx) {
    const list = document.getElementById('history-sidebar-list');
    const entries = list._historyEntries || [];
    const entry = entries[idx];
    if (!entry) return;

    if (entry.url) {
        // Generated model — load directly into 3D viewer
        closeHistorySidebar();
        switchTab('viewer3d');
        await stepViewer.loadStepUrl(entry.url);
    } else {
        // Uploaded file — no server URL, guide user to re-upload
        showToast(`"${entry.name}" was uploaded from disk. Please upload it again to reload.`, 'warning');
    }
}

/**
 * Add a history entry for a panel to the backend.
 * @param {string} panelId
 * @param {{name:string, source:string, url?:string}} entry
 */
async function addToHistoryEntry(panelId, entry) {
    try {
        await api.addHistoryEntry(panelId, entry);
        // Refresh sidebar if it's currently open on this panel
        if (_currentHistoryPanel === panelId) {
            await _renderHistorySidebar(panelId);
        }
    } catch (e) {
        console.warn('addToHistoryEntry failed:', e);
    }
}

/** Called when user uploads a STEP and clicks View 3D.
 *  Saves the file to the backend so it can be replayed from history. */
async function addToHistory(file) {
    try {
        // Upload the file to the backend → get a stable serve URL
        const result = await api.uploadStepFile(file);
        await addToHistoryEntry('viewer3d', {
            name: file.name,
            source: 'upload',
            url: result.url,   // e.g. /data/uploads/part.step
        });
    } catch (e) {
        // Upload failed — still record the entry, just without a replay URL
        console.warn('Could not upload STEP for history persistence:', e);
        await addToHistoryEntry('viewer3d', { name: file.name, source: 'upload' });
    }
}

/** Called after LLM generation — we have a stable URL. */
function addToHistoryFromUrl(name, url) {
    addToHistoryEntry('viewer3d', { name, source: 'generated', url });
}

/** Clear the panel whose sidebar is currently open. */
async function clearCurrentPanelHistory() {
    if (!_currentHistoryPanel) return;
    try {
        await api.clearPanelHistory(_currentHistoryPanel);
        await _renderHistorySidebar(_currentHistoryPanel);
    } catch (e) {
        console.warn('clearCurrentPanelHistory failed:', e);
    }
}

// Legacy shim — kept so old inline calls don't break
function clearHistory() { clearCurrentPanelHistory(); }

