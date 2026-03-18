/**
 * SynthoCAD API Client
 * Handles all communication with the backend API
 */

const API_BASE_URL = 'http://localhost:5000/api/v1';

class SynthoCADAPI {
    constructor(baseUrl = API_BASE_URL) {
        this.baseUrl = baseUrl;
    }

    async request(endpoint, options = {}) {
        const url = `${this.baseUrl}${endpoint}`;

        try {
            const response = await fetch(url, {
                ...options,
                headers: {
                    'Content-Type': 'application/json',
                    ...options.headers
                }
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.message || data.error || `HTTP ${response.status}`);
            }

            return data;
        } catch (error) {
            console.error('API Request failed:', error);
            throw error;
        }
    }

    async validatePrompt(prompt) {
        return this.request('/generate/validate-prompt', {
            method: 'POST',
            body: JSON.stringify({ prompt })
        });
    }

    async generateFromPrompt(prompt) {
        return this.request('/generate/from-prompt', {
            method: 'POST',
            body: JSON.stringify({ prompt })
        });
    }

    async generateFromBrep(prompt) {
        return this.request('/generate/brep', {
            method: 'POST',
            body: JSON.stringify({ prompt })
        });
    }

    async generateFromJSON(jsonData, outputName = null) {
        return this.request('/generate/from-json', {
            method: 'POST',
            body: JSON.stringify({
                json: jsonData,
                output_name: outputName
            })
        });
    }

    // ========== Parameter APIs ==========

    async extractParameters(filename) {
        return this.request(`/parameters/extract/${filename}?method=legacy`, {
            method: 'GET'
        });
    }

    async updateParameters(filename, parameters) {
        return this.request(`/parameters/update/${filename}`, {
            method: 'POST',
            body: JSON.stringify({ parameters })
        });
    }

    async regenerateWithParameters(filename, parameters) {
        return this.request(`/parameters/regenerate/${filename}`, {
            method: 'POST',
            body: JSON.stringify({ parameters })
        });
    }

    async updateAndRegenerate(filename, parameters) {
        return this.request(`/parameters/regenerate/${filename}`, {
            method: 'POST',
            body: JSON.stringify({ parameters })
        });
    }

    async viewJsonFile(filename) {
        return this.request(`/parameters/view/json/${filename}`, {
            method: 'GET'
        });
    }

    async viewPythonFile(filename) {
        return this.request(`/parameters/view/python/${filename}`, {
            method: 'GET'
        });
    }

    async viewStepFile(filename) {
        return this.request(`/parameters/view/step/${filename}`, {
            method: 'GET'
        });
    }

    async previewStepByName(filename) {
        return this.request(`/edit/preview-by-name`, {
            method: 'POST',
            body: JSON.stringify({ filename })
        });
    }

    // ========== Step Editor (Upload-based) APIs ==========

    async previewStep(formData) {
        /**
         * Upload a STEP file for multi-angle preview.
         * formData must contain a 'file' field with the .step file.
         * Returns { features, image_urls: [{view, label, url}], instructions }
         */
        const url = `${this.baseUrl}/edit/preview`;
        try {
            const response = await fetch(url, {
                method: 'POST',
                body: formData   // multipart, NO Content-Type header (browser sets it)
            });
            const data = await response.json();
            if (!response.ok) {
                throw new Error(data.message || data.error || `HTTP ${response.status}`);
            }
            return data;
        } catch (error) {
            console.error('previewStep failed:', error);
            throw error;
        }
    }

    async editStep(formData) {
        /**
         * Upload a STEP file + text prompt to get an edited STEP back.
         * formData must contain 'file' (.step) and 'prompt' (string).
         */
        const url = `${this.baseUrl}/edit/from-step`;
        try {
            const response = await fetch(url, {
                method: 'POST',
                body: formData
            });
            const data = await response.json();
            if (!response.ok) {
                throw new Error(data.message || data.error || `HTTP ${response.status}`);
            }
            return data;
        } catch (error) {
            console.error('editStep failed:', error);
            throw error;
        }
    }

    async editStepBrep(formData) {
        /**
         * Upload a STEP file + text prompt to apply B-Rep semantic editing.
         * formData must contain 'file' (.step) and 'prompt' (string).
         */
        const url = `${this.baseUrl}/edit/brep`;
        try {
            const response = await fetch(url, {
                method: 'POST',
                body: formData
            });
            const data = await response.json();
            if (!response.ok) {
                throw new Error(data.message || data.error || `HTTP ${response.status}`);
            }
            return data;
        } catch (error) {
            console.error('editStepBrep failed:', error);
            throw error;
        }
    }

    async templateCommand(formData) {
        /**
         * Apply a template onto an uploaded STEP using a command like:
         * "Add air scoop intake at [10,20,30]".
         */
        const url = `${this.baseUrl}/edit/template-command`;
        try {
            const response = await fetch(url, {
                method: 'POST',
                body: formData
            });
            const data = await response.json();
            if (!response.ok) {
                throw new Error(data.message || data.error || `HTTP ${response.status}`);
            }
            return data;
        } catch (error) {
            console.error('templateCommand failed:', error);
            throw error;
        }
    }

    async listGeneratedFiles() {
        return this.request(`/parameters/list-files`, {
            method: 'GET'
        });
    }

    // ========== OCP / Geometry APIs ==========

    async uploadStepFile(file) {
        /**
         * Upload a STEP file to the backend data/uploads directory.
         * Returns { url: '/data/uploads/<filename>' }
         */
        const url = `${this.baseUrl}/edit/upload`;
        const formData = new FormData();
        formData.append('file', file);
        try {
            const response = await fetch(url, { method: 'POST', body: formData });
            const data = await response.json();
            if (!response.ok) {
                throw new Error(data.message || data.error || `HTTP ${response.status}`);
            }
            return data;
        } catch (error) {
            console.error('uploadStepFile failed:', error);
            throw error;
        }
    }

    async getOcpParameters(filename) {
        return this.request(`/parameters/ocp/${encodeURIComponent(filename)}`, {
            method: 'GET'
        });
    }

    async regenerateOcp(filename, originalFeatures, updates) {
        return this.request(`/parameters/regenerate-ocp/${encodeURIComponent(filename)}`, {
            method: 'POST',
            body: JSON.stringify({
                updates,
                original_features: originalFeatures
            })
        });
    }

    // ========== Panel History APIs ==========

    async getHistory(panelId) {
        return this.request(`/parameters/history/${encodeURIComponent(panelId)}`, {
            method: 'GET'
        });
    }

    async addHistoryEntry(panelId, entry) {
        return this.request(`/parameters/history/${encodeURIComponent(panelId)}`, {
            method: 'POST',
            body: JSON.stringify(entry)
        });
    }

    async clearPanelHistory(panelId) {
        return this.request(`/parameters/history/${encodeURIComponent(panelId)}`, {
            method: 'DELETE'
        });
    }

    // ========== Cleanup APIs ==========

    async getStorageStats() {
        return this.request('/cleanup/stats', {
            method: 'GET'
        });
    }

    async cleanup(maxAgeDays = null, maxFilesPerType = null, dryRun = false) {
        return this.request('/cleanup/cleanup', {
            method: 'POST',
            body: JSON.stringify({
                max_age_days: maxAgeDays,
                max_files_per_type: maxFilesPerType,
                dry_run: dryRun
            })
        });
    }

    async cleanupByAge(maxAgeDays, fileType = 'all', dryRun = false) {
        return this.request('/cleanup/cleanup/by-age', {
            method: 'POST',
            body: JSON.stringify({
                max_age_days: maxAgeDays,
                file_type: fileType,
                dry_run: dryRun
            })
        });
    }

    async cleanupByCount(maxFiles, fileType = 'all', dryRun = false) {
        return this.request('/cleanup/cleanup/by-count', {
            method: 'POST',
            body: JSON.stringify({
                max_files: maxFiles,
                file_type: fileType,
                dry_run: dryRun
            })
        });
    }

    async deleteModel(baseName, dryRun = false) {
        const query = dryRun ? '?dry_run=true' : '';
        return this.request(`/cleanup/${baseName}${query}`, {
            method: 'DELETE'
        });
    }

    async getRetryStats(operation = null, limit = 50) {
        const params = new URLSearchParams();
        if (operation) params.append('operation', operation);
        if (limit) params.append('limit', limit.toString());

        const query = params.toString() ? `?${params.toString()}` : '';
        return this.request(`/cleanup/retry-stats${query}`, {
            method: 'GET'
        });
    }

    async getTemplates() {
        const response = await this.request('/templates', {
            method: 'GET'
        });
        return response.templates || [];
    }

    async getTemplateCatalog(mode = 'edit') {
        return this.request(`/templates/catalog?mode=${encodeURIComponent(mode)}`, {
            method: 'GET'
        });
    }

    async getTemplatesByCategory(categoryPath) {
        return this.request(`/templates/by-category/${encodeURIComponent(categoryPath)}`, {
            method: 'GET'
        });
    }

    async getTemplate(name) {
        return this.request(`/templates/${name}`, {
            method: 'GET'
        });
    }

    // ========== Health Check ==========

    async healthCheck() {
        return this.request('/health', {
            method: 'GET'
        });
    }
}

// Export for use in other scripts
const api = new SynthoCADAPI();
