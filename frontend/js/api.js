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

    async generateFromPrompt(prompt, openFreecad = true) {
        return this.request('/generate/from-prompt', {
            method: 'POST',
            body: JSON.stringify({ 
                prompt, 
                open_freecad: openFreecad 
            })
        });
    }

    async generateFromJSON(jsonData, outputName = null, openFreecad = true) {
        return this.request('/generate/from-json', {
            method: 'POST',
            body: JSON.stringify({ 
                json: jsonData,
                output_name: outputName,
                open_freecad: openFreecad 
            })
        });
    }

    // ========== Parameter APIs ==========

    async extractParameters(filename) {
        return this.request(`/parameters/extract/${filename}`, {
            method: 'GET'
        });
    }

    async updateParameters(filename, parameters) {
        return this.request(`/parameters/update/${filename}`, {
            method: 'POST',
            body: JSON.stringify({ parameters })
        });
    }

    async regenerateWithParameters(filename, parameters, openFreecad = true) {
        return this.request(`/parameters/regenerate/${filename}`, {
            method: 'POST',
            body: JSON.stringify({ 
                parameters,
                open_freecad: openFreecad 
            })
        });
    }

    async updateAndRegenerate(filename, parameters, openFreecad = true) {
        return this.request(`/parameters/update/${filename}`, {
            method: 'POST',
            body: JSON.stringify({ 
                parameters,
                open_freecad: openFreecad 
            })
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

    async listGeneratedFiles() {
        return this.request(`/parameters/list-files`, {
            method: 'GET'
        });
    }

    // ========== FreeCAD Viewer APIs ==========

    async checkFreeCAD() {
        return this.request('/viewer/check', {
            method: 'GET'
        });
    }

    async openInFreeCAD(stepFile, freecadPath = null) {
        return this.request('/viewer/open', {
            method: 'POST',
            body: JSON.stringify({ 
                step_file: stepFile,
                freecad_path: freecadPath 
            })
        });
    }

    async reloadInFreeCAD(stepFile, freecadPath = null) {
        return this.request('/viewer/reload', {
            method: 'POST',
            body: JSON.stringify({ 
                step_file: stepFile,
                freecad_path: freecadPath 
            })
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

    async checkFreeCAD() {
        return this.request('/viewer/check', {
            method: 'GET'
        });
    }
}

// Export for use in other scripts
const api = new SynthoCADAPI();
