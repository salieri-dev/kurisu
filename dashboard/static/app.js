(() => {
    "use strict";

    const appRoot = document.getElementById("app-root");
    let state = {
        configs: [],
        error: null,
    };

    // --- API Communication ---
    const api = {
        getConfigs: async () => {
            const response = await fetch("/api/configs");
            if (!response.ok) {
                throw new Error(`Failed to fetch configs: ${response.statusText}`);
            }
            return await response.json();
        },
        updateConfig: async (key, value, description) => {
            let parsedValue;
            try {
                parsedValue = JSON.parse(value);
            } catch (e) {
                parsedValue = value; // Keep as string if not valid JSON
            }

            const response = await fetch("/api/configs", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ key, value: parsedValue, description }),
            });

            if (!response.ok) {
                throw new Error(`Failed to update config: ${response.statusText}`);
            }
            return await response.json();
        },
    };

    // --- HTML Rendering ---
    const render = () => {
        appRoot.innerHTML = ''; // Clear previous content

        if (state.error) {
            appRoot.innerHTML = `<div class="error-message"><strong>Error:</strong> ${state.error}</div>`;
        }
        
        // Render "Create New" form
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

        // Render existing configs
        const configsHeader = document.createElement('h2');
        configsHeader.textContent = `Existing Configurations (${state.configs.length})`;
        appRoot.appendChild(configsHeader);

        if (state.configs.length === 0 && !state.error) {
            appRoot.innerHTML += `<p>No configurations found.</p>`;
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
                            <button type="submit">Save Changes</button>
                        </div>
                    </form>
                `;
                appRoot.appendChild(configCard);
            });
        }
    };

    // --- Event Handling ---
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
            // On success, refresh all data to ensure consistency
            await init(); 
        } catch (e) {
            alert(`Error saving config: ${e.message}`);
            button.disabled = false;
            button.textContent = form.id === 'create-form' ? 'Create' : 'Save Changes';
        }
    };

    appRoot.addEventListener('submit', handleFormSubmit);

    // --- Initialization ---
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