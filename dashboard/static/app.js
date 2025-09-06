(() => {
    "use strict";

    const appRoot = document.getElementById("app-root");
    let state = {
        configs: [],
        error: null,
    };

    const api = {
        getConfigs: async () => {
            const response = await fetch("/api/configs");
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ detail: response.statusText }));
                throw new Error(`Failed to fetch configs: ${errorData.detail || response.statusText}`);
            }
            return await response.json();
        },
        updateConfig: async (key, value, description) => {
            let parsedValue;
            try {
                parsedValue = JSON.parse(value);
            } catch (e) {
                parsedValue = value;
            }

            const response = await fetch("/api/configs", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ key, value: parsedValue, description }),
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ detail: response.statusText }));
                throw new Error(`Failed to update config: ${errorData.detail || response.statusText}`);
            }
            return await response.json();
        },
        clearCache: async (key) => {
            const response = await fetch(`/api/configs/cache/${encodeURIComponent(key)}`, {
                method: "DELETE",
            });
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ detail: response.statusText }));
                throw new Error(`Failed to clear cache: ${errorData.detail || response.statusText}`);
            }
            return await response.json();
        },
    };

    const render = () => {
        appRoot.innerHTML = '';

        if (state.error) {
            appRoot.innerHTML = `<div class="error-message"><strong>Error:</strong> ${state.error}</div>`;
        }
        
        const createForm = document.createElement('div');
        createForm.innerHTML = `
            <div class="card">
                <h2>Create New Configuration</h2>
                <form class="config-form" id="create-form">
                    <div class="form-group">
                        <label for="new_key">Key</label>
                        <input type="text" id="new_key" name="key" placeholder="e.g., neuro/threads.model" required>
                    </div>
                    <div class="form-group">
                        <label for="new_value">Value (JSON)</label>
                        <textarea id="new_value" name="value" rows="3" placeholder='"anthropic/claude-3.5-sonnet"' required></textarea>
                        <small>Enter strings in quotes (e.g., "value"), numbers/booleans without (e.g., 120 or true).</small>
                    </div>
                    <div class="form-group">
                        <label for="new_description">Description</label>
                        <input type="text" id="new_description" name="description" placeholder="LLM model for generating threads.">
                    </div>
                    <button type="submit">Create</button>
                </form>
            </div>
        `;
        appRoot.appendChild(createForm);

        const configsHeader = document.createElement('h2');
        configsHeader.textContent = `Existing Configurations (${state.configs.length})`;
        appRoot.appendChild(configsHeader);

        if (state.configs.length === 0 && !state.error) {
            appRoot.insertAdjacentHTML('beforeend', `<p>No configurations found.</p>`);
        } else {
            state.configs.forEach(config => {
                const configCard = document.createElement('div');
                const safeKey = config.key.replace(/[^a-zA-Z0-9]/g, '-');
                const updatedTime = new Date(config.updated_at).toLocaleString();

                configCard.className = 'card';
                configCard.innerHTML = `
                    <form class="config-form" data-key="${config.key}">
                        <div class="form-group">
                            <label for="key_${safeKey}">Key</label>
                            <input type="text" id="key_${safeKey}" name="key" value="${config.key}" readonly>
                        </div>
                        <div class="form-group">
                            <label for="value_${safeKey}">Value (JSON)</label>
                            <textarea id="value_${safeKey}" name="value" rows="4">${JSON.stringify(config.value, null, 2)}</textarea>
                        </div>
                        <div class="form-group">
                            <label for="desc_${safeKey}">Description</label>
                            <input type="text" id="desc_${safeKey}" name="description" value="${config.description || ''}">
                        </div>
                        <div class="form-footer">
                            <small>Last Updated: ${updatedTime}</small>
                            <div>
                                <button type="button" class="button-secondary clear-cache-btn" data-key="${config.key}">Clear Cache</button>
                                <button type="submit">Save Changes</button>
                            </div>
                        </div>
                    </form>
                `;
                appRoot.appendChild(configCard);
            });
        }
    };

    const handleFormSubmit = async (event) => {
        event.preventDefault();
        const form = event.target;
        const button = form.querySelector('button[type="submit"]');
        
        const key = form.elements.key.value;
        const value = form.elements.value.value;
        const description = form.elements.description.value;

        button.disabled = true;
        button.textContent = 'Saving...';

        try {
            await api.updateConfig(key, value, description);
            await init(); 
        } catch (e) {
            alert(`Error saving config: ${e.message}`);
            button.disabled = false;
            button.textContent = form.id === 'create-form' ? 'Create' : 'Save Changes';
        }
    };

    const handleCacheClear = async (event) => {
        if (!event.target.classList.contains('clear-cache-btn')) {
            return;
        }

        const button = event.target;
        const key = button.dataset.key;
        
        if (!key || !confirm(`Are you sure you want to clear the cache for "${key}"?`)) {
            return;
        }

        const originalText = button.textContent;
        button.disabled = true;
        button.textContent = 'Clearing...';

        try {
            await api.clearCache(key);
            button.textContent = 'Cleared!';
            setTimeout(() => {
                button.disabled = false;
                button.textContent = originalText;
            }, 2000);
        } catch (e) {
            alert(`Error clearing cache: ${e.message}`);
            button.disabled = false;
            button.textContent = originalText;
        }
    };

    appRoot.addEventListener('submit', (e) => {
        if (e.target.tagName === 'FORM') {
            handleFormSubmit(e);
        }
    });

    appRoot.addEventListener('click', (e) => {
        if (e.target.classList.contains('clear-cache-btn')) {
            handleCacheClear(e);
        }
    });

    const init = async () => {
        try {
            state.error = null;
            const configs = await api.getConfigs();
            state.configs = configs.sort((a, b) => a.key.localeCompare(b.key));
        } catch (e) {
            state.error = e.message;
        }
        render();
    };

    document.addEventListener("DOMContentLoaded", init);

})();