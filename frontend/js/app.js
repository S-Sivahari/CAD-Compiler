/**
 * SynthoCAD - Simplified Single Page App
 * AutoCAD-inspired Black & Red Theme
 */

const state = {
    currentModel: null,
    templates: [],
    parameters: [],
    generating: false
};

document.addEventListener('DOMContentLoaded', () => {
    initializeApp();
});

async function initializeApp() {
    await checkBackendStatus();
    await checkFreeCADStatus();
    await loadTemplates();
    setupEventListeners();
    showToast('SynthoCAD initialized', 'success');
}

function setupEventListeners() {
    const generateBtn = document.getElementById('generate-btn');
    const promptInput = document.getElementById('prompt-input');
    const templatesToggle = document.getElementById('templates-toggle');
    const regenerateBtn = document.getElementById('regenerate-btn');
    
    generateBtn.addEventListener('click', handleGenerate);
    
    promptInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && e.ctrlKey) {
            handleGenerate();
        }
    });
    
    // Templates dropdown toggle
    templatesToggle.addEventListener('click', () => {
        const content = document.getElementById('templates-dropdown-content');
        templatesToggle.classList.toggle('active');
        content.classList.toggle('show');
    });
    
    templatesToggle.addEventListener('click', () => {
        const content = document.getElementById('templates-dropdown-content');
        templatesToggle.classList.toggle('active');
        content.classList.toggle('show');
    });
    
    regenerateBtn.addEventListener('click', handleRegenerate);
    promptInput.addEventListener('input', debounce(validatePromptRealtime, 500));
}
e');
        showToast('Backend offline', 'error');
    }
}

async function checkFreeCADStatus() {
    const freecadStatus = document.getElementById('freecad-status');
    const freecadDot = freecadStatus.querySelector('.status-dot');
    const freecadText = freecadStatus.querySelector('span:last-child');
    
    try {
        const result = await api.checkFreeCAD();
        
        if (result.installed && result.path) {
            freecadStatus.classList.add('online');
            freecadText.textContent = 'FreeCAD';
        } else {
            freecadStatus.classList.add('offline');
            freecadText.textContent = 'FreeCAD (Not Installed)';
        }
    } catch {
        freecadStatus.classList.add('offline');
        freecadText.textContent = 'FreeCAD (Error)';
    }
}

// ========== Templates ==========
async function loadTemplates() {
    const container = document.getElementById('templates-list');
    
    try {
        const templates = await api.getTemplates();
        state.templates = templates;
        
        if (templates.length === 0) {
            container.innerHTML = '<div class="empty-state">No templates available</div>';
            return;
        }
        container.innerHTML = templates.map(template => `
            <div class="template-item" onclick="useTemplate('${template.name}')">
                <div class="template-name">${template.name}</div>
                <div class="template-desc">${template.description || 'Click to use'}</div>
            </div>
        `).join('');
        
    } catch (error) {
        container.innerHTML = '<div class="error-state">Failed to load templates</div>';
        console.error('Template loading error:', error);
    }
}

async function useTemplate(templateName) {
    try {
        const template = await api.getTemplate(templateName);
        const promptInput = document.getElementById('prompt-input');
        
        // Convert template to prompt (simplified)
        promptInput.value = `Template: ${templateName}`;
        
        // Close dropdown
        const content = document.getElementById('templates-dropdown-content');
        const toggle = document.getElementById('templates-toggle');
        promptInput.value = `Template: ${templateName}`;
        
        const content = document.getElementById('templates-dropdown-content');
        const toggle = document.getElementById('templates-toggle');
        content.classList.remove('show');
        toggle.classList.remove('active');
        
        showToast(`Using template: ${templateName}`, 'success');
        
    } catch (error) {
        showToast('Failed to load template', 'error');
        console.error('Template error:', error);
    }
}
esign description', 'warning');
        return;
    }
    
    if (state.generating) {
        showToast('Generation already in progress', 'warning');
        return;
    }
    
    try {
        state.generating = true;
        showLoading('Generating CAD model...');
        disableGenerateButton();
        
        // Validate prompt first
        const validation = await api.validatePrompt(prompt);
        
        if (!validation.valid) {
        const validation = await api.validatePrompt(prompt);
        
        if (!validation.valid) {
            showToast(`Validation failed: ${validation.error}`, 'error');
            hideLoading();
            enableGenerateButton();
            return;
        }
        
        updateLoadingMessage('Calling LLM...');
        const result = await api.generateFromPrompt(prompt, false);
            // Display results
            await displayParameters(result.py_file);
            displayModelInfo(result);
            
            showToast('Model generated successfully!', 'success');
        } elawait displayParameters(result.py_file);
            displayModelInfo(result);(error) {
        showToast(`Error: ${error.message}`, 'error');
        console.error('Generation error:', error);
    } finally {
        state.generating = false;
        hideLoading();
        enableGenerateButton();
    }
}

async function validatePromptRealtime() {
    const promptInput = document.getElementById('prompt-input');
    const validationMsg = document.getElementById('validation-message');
    const prompt = promptInput.value.trim();
    
    if (!prompt) {
        validationMsg.textContent = '';
        validationMsg.className = 'validation-message';
        return;
    }
    
    try {
        const result = await api.validatePrompt(prompt);
        
        if (result.valid) {
            validationMsg.textContent = '✓ Prompt looks good';
            validationMsg.className = 'validation-message success';
        } else {
            validationMsg.textContent = result.error;
            validationMsg.className = 'validation-message error';
        }
    } catch (error) {
        validationMsg.textContent = '';
    const regenerateBtn = document.getElementById('regenerate-btn');
    
    try {
        const filename = pyFile.split('\\').pop().split('/').pop();
        const result = await api.extractParameters(filename);
        
        if (!result.parameters || result.parameters.length === 0) {
            container.innerHTML = '<div class="empty-state">No editable parameters found</div>';
            regenerateBtn.classList.add('hidden');
            return;
        }
        
        state.parameters = result.parameters;
        regenerateBtn.classList.remove('hidden');
        
        container.innerHTML = result.parameters.map((param, index) => `
            <div class="param-item">
                <div class="param-header">
                    <div class="param-name">${param.name}</div>
                    <div class="param-type">${param.type}</div>
                </div>
                <div class="param-value">
                    <input 
                        type="number" 
                        id="param-${index}" 
                        value="${param.value}"
                        step="0.1"
                        class="param-input"
                    />
                </div>
            </div>
        `).join('');
        
    } catch (error) {
        container.innerHTML = '<div class="error-state">Failed to extract parameters</div>';
        console.error('Parameter extraction error:', error);
    }
}

async function handleRegenerate() {
    if (!state.currentModel || !state.parameters || state.parameters.length === 0) {
        showToast('No parameters to update', 'warning');
        return;
    }
    
    try {
        showLoading('Regenerating model with updated parameters...');
        
        const filename = state.currentModel.py_file.split('\\').pop().split('/').pop();
        const updates = {};
        
        // Collect all parameter values
        state.parameters.forEach((param, index) => {
            const input = document.getElementById(`param-${index}`);
            const newValue = parseFloat(input.value);
            if (!isNaN(newValue)) {
                updates[param.name] = newValue;
            }
        });
        const result = await api.updateAndRegenerate(filename, updates);
        
        if (result.status === 'success') {
            state.currentModel.step_file = result.step_file;
            displayModelInfo(state.currentModel);
            showToast('Model regenerated successfully!', 'success');
        } else {
            showToast('Regeneration failed', 'error');
        }
        
    } catch (error) {
        showToast(`Regeneration error: ${error.message}`, 'error');
        console.error('Regeneration error:', error);
    const downloadButtons = document.getElementById('download-buttons');
    
    const stepFile = result.step_file.split('\\').pop().split('/').pop();
    const jsonFile = result.json_file.split('\\').pop().split('/').pop();
    const pyFile = result.py_file.split('\\').pop().split('/').pop();
    
    // Show download buttons
    downloadButtons.classList.remove('hidden');
    
    // Check FreeCAD status
    let freecadInfo = '';
    if (result.freecad_opened) {
        freecadInfo = '<div class="freecad-status success">✓ Model opened in FreeCAD</div>';
    } else {
        freecadInfo = '<div class="freecad-status warning">⚠ FreeCAD not opened (check installation)</div>';
    downloadButtons.classList.remove('hidden');
    nfo">
            <h4>📦 CAD Model Generated</h4>
            <div class="model-info-item">
                <span class="model-info-label">STEP File:</span>
                <span class="model-info-value">${stepFile}</span>
            </div>
            <div class="model-info-item">
                <span class="model-info-label">Python File:</span>
                <span class="model-info-value">${pyFile}</span>
            </div>
            <div class="model-info-item">
                <span class="model-info-label">JSON File:</span>
                <span class="model-info-value">${jsonFile}</span>
            </div>
            <div class="model-info-item">
                <span class="model-info-label">Parameters:</span>
                <span class="model-info-value">${result.parameters.total_count}</span>
            </div>
            ${freecadInfo}
            <div style="margin-top: 15px; font-size: 11px; color: var(--text-muted);">
                <p>💡 Use the download buttons above to save files</p>
                <p>📐 Modify parameters on the left and click REGENERATE</p>
            </div>
        </div>
    `;
}

async function downloadFile(type) {
    if (!state.currentModel) {
        showToast('No model to download', 'warning');
        return;
    }
    
    const file = type === 'step' ? state.currentModel.step_file : state.currentModel.json_file;
    const filename = file.split('\\').pop().split('/').pop();
    
    // Create download link
    const apiUrl = `http://localhost:5000/outputs/${type}/${filename}`;
    
    try {
        const response = await fetch(apiUrl);
        if (!response.ok) {
            throw new Error('File not found');
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
        
        showToast(`Downloaded ${filename}`, 'success');
    } catch (error) {
        showToast(`Download failed: ${error.message}`, 'error');
    }
}

async function openInFreeCAD() {
    if (!state.currentModel) {
        showToast('No model to open', 'warning');
        return;
    }
    
    try {
        showLoading('Opening in FreeCAD...');
        const stepFile = state.currentModel.step_file.split('\\').pop().split('/').pop();
        const result = await api.openInFreeCAD(stepFile);
        
        if (result.status === 'success') {
            showToast('✓ Model opened in FreeCAD', 'success');
            
            // Update freecad status in UI
            const freecadStatus = document.querySelector('.freecad-status');
            if (freecadStatus) {
                freecadStatus.className = 'freecad-status success';
                freecadStatus.textContent = '✓ Model opened in FreeCAD';
            }
        } else {
            showToast(`Failed: ${result.message || 'FreeCAD unavailable'}`, 'error');
        }
    } catch (error) {
            const freecadStatus = document.querySelector('.freecad-status');
        hideLoading(p().split('/').pop();
    const pyFile = result.py_file.split('\\').pop().split('/').pop();
    
    container.innerHTML = `
        <div class="model-info">
            <h4>📦 Model Generated</h4>
            <div class="model-info-item">
                <span class="model-info-label">STEP File:</span>
                <span class="model-info-value">${stepFile}</span>
            </div>
            <div class="model-info-item">
                <span class="model-info-label">Python File:</span>
                <span class="model-info-value">${pyFile}</span>
            </div>
            <div class="model-info-item">
                <span class="model-info-label">JSON File:</span>
                <span class="model-info-value">${jsonFile}</span>
            </div>
            <div class="model-info-item">
                <span class="model-info-label">Parameters:</span>
                <span class="model-info-value">${result.parameters.total_count}</span>
            </div>
            <div class="model-info-item">
                <span class="model-info-label">FreeCAD:</span>
                <span class="model-info-value">${result.freecad_opened ? 'Opened' : 'Not opened'}</span>
            </div>
            <div style="margin-top: 20px; text-align: center;">
                <button class="generate-btn" onclick="openInFreeCAD()">OPEN IN FREECAD</button>
            </div>
        </div>
    `;
}

async function openInFreeCAD() {
    if (!state.currentModel) {
        showToast('No model to open', 'warning');
        return;
    }
    
    try {
        const stepFile = state.currentModel.step_file.split('\\').pop().split('/').pop();
        const result = await api.openInFreeCAD(stepFile);
        
        if (result.status === 'success') {
            showToast('Model opened in FreeCAD', 'success');
        } else {
            showToast('Failed to open in FreeCAD', 'error');
        }
    } catch (error) {
        showToast(`Error: ${error.message}`, 'error');
    }
}

// ========== UI Helpers ==========
function showLoading(message = 'Processing...') {
    const overlay = document.getElementById('loading-overlay');
    const messageEl = document.getElementById('loading-message');
    messageEl.textContent = message;
    overlay.classList.remove('hidden');
}

function hideLoading() {
    const overlay = document.getElementById('loading-overlay');
    overlay.classList.add('hidden');
}

function updateLoadingMessage(message) {
    const messageEl = document.getElementById('loading-message');
    messageEl.textContent = message;
}

function disableGenerateButton() {
    const btn = document.getElementById('generate-btn');
    btn.disabled = true;
    btn.textContent = 'GENERATING...';
}

function enableGenerateButton() {
    const btn = document.getElementById('generate-btn');
    btn.disabled = false;
    btn.textContent = 'GENERATE';
}

function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `<div class="toast-message">${message}</div>`;
    
    container.appendChild(toast);
    
    setTimeout(() => {
        toast.style.opacity = '0';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}
