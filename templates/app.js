document.addEventListener('DOMContentLoaded', () => {
    const appContentArea = document.getElementById('app-content-area');
    let odooPlannedModules = []; // State for Odoo app
    let sitePreviewUrl = null; // Revoke old blob URLs when regenerating

    // Parse JSON responses and surface HTML error pages as readable errors.
    async function parseJsonResponse(response) {
        const text = await response.text();
        const contentType = response.headers.get('content-type') || '';
        if (contentType.includes('application/json')) {
            try {
                return JSON.parse(text || '{}');
            } catch (err) {
                throw new Error(`Invalid JSON response (${response.status}): ${err.message}`);
            }
        }

        const snippet = text.slice(0, 240).replace(/\s+/g, ' ').trim();
        throw new Error(`Expected JSON but got ${contentType || 'unknown type'} (status ${response.status}). Body: ${snippet || '<empty>'}`);
    }

    /**
     * This function is called whenever the app content area is replaced.
     * It handles re-initialization of components that need it.
     */
    function onAppContentChange() {
        // 1. Ensure chat window scrolls to bottom if it exists
        const chatWindow = document.getElementById('chat-window');
        if (chatWindow) {
            chatWindow.scrollTop = chatWindow.scrollHeight;
        }

        const popoverTriggerList = appContentArea.querySelectorAll('[data-bs-toggle="popover"]');
        [...popoverTriggerList].map(popoverTriggerEl => new bootstrap.Popover(popoverTriggerEl));
    }

    // --- Theme Switcher Logic ---
    const themeSwitcher = document.getElementById('theme-switcher');
    if (themeSwitcher) {
        themeSwitcher.addEventListener('click', () => {
            const newTheme = document.documentElement.getAttribute('data-bs-theme') === 'light' ? 'dark' : 'light';
            document.documentElement.setAttribute('data-bs-theme', newTheme);
            localStorage.setItem('theme', newTheme);
        });
    }

    // --- App Loading Logic ---
    // The app launchers are now the glass cards.
    document.getElementById('load-odoo-app')?.addEventListener('click', () => loadApp('/apps/odoo'));
    document.getElementById('load-social-media-app')?.addEventListener('click', () => loadApp('/apps/social_media'));
    document.getElementById('load-email-app')?.addEventListener('click', () => loadApp('/apps/email'));
    document.getElementById('load-website-helper-app')?.addEventListener('click', () => loadApp('/apps/website_helper'));

    document.getElementById('load-website-helper-app-menu')?.addEventListener('click', (e) => {
        e.preventDefault();
        loadApp('/apps/website_helper');
    });

    async function loadApp(url) {
        // Clear any running Odoo job polls when switching apps
        if (window.odooPollInterval) clearInterval(window.odooPollInterval);

        try {
            appContentArea.innerHTML = '<div class="d-flex justify-content-center align-items-center h-100"><div class="spinner-border" role="status"><span class="visually-hidden">Loading...</span></div></div>';
            const response = await fetch(url);
            if (!response.ok) throw new Error('Failed to load app.');
            const appHtml = await response.text();
            appContentArea.innerHTML = appHtml;
            onAppContentChange(); // Initialize components in the newly loaded app
        } catch (error) {
            appContentArea.innerHTML = `<div class="alert alert-danger m-4"><strong>Error:</strong> ${error.message}</div>`;
            console.error('App loading error:', error);
        }
    }

    // --- Event Delegation for Dynamically Loaded Content ---
    appContentArea.addEventListener('submit', async (event) => {
        if (event.target.id === 'chat-form') {
            handleChatSubmit(event);
        } else if (event.target.id === 'website-helper-generate-form') {
            event.preventDefault();
            handleWebsiteGenerate(event.target);
        } else if (event.target.id === 'website-helper-site-form') {
            event.preventDefault();
            handleWebsiteSiteGenerate(event.target);
        }
    });

    appContentArea.addEventListener('click', async (event) => {
        const copyBtn = event.target.closest('.copy-snippet-btn');
        if (copyBtn) {
            handleCopySnippet(copyBtn);
            return;
        }

        if (event.target.classList.contains('plan-btn')) {
            handleOdooPlan(event.target);
        } else if (event.target.id === 'execute-btn') {
            handleOdooExecute(event.target);
        } else if (event.target.closest('.theme-card')) {
            handleThemeSelection(event.target.closest('.theme-card'));
        } else if (event.target.id === 'bm-plan-btn') {
            handleBrandManagerPlan(event.target);
        } else if (event.target.id === 'bm-execute-btn') {
            handleBrandManagerExecute(event.target);
        }
    });

    appContentArea.addEventListener('change', (event) => {
        if (event.target.classList.contains('theme-select')) {
            handleThemeSelect(event.target);
        }
    });

    function handleOdooPlan(planBtn) {
        const planType = planBtn.dataset.planType;
        const businessNeedInput = document.getElementById(planType === 'community' ? 'business-need' : `business-need-${planType}`);
        const businessNeed = businessNeedInput.value.trim();
        if (!businessNeed) {
            alert('Please describe your business need.');
            return;
        }

        const planBtnSpinner = planBtn.querySelector('.spinner-border');
        const planError = document.getElementById(planType === 'community' ? 'plan-error' : `plan-error-${planType}`);

        planBtn.disabled = true;
        planBtnSpinner.style.display = 'inline-block';
        if (planError) planError.style.display = 'none';

        fetch('/odoo/plan', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                business_need: businessNeed,
                plan_type: planType
            })
        })
        .then(response => parseJsonResponse(response))
        .then(data => {
            if (planType === 'community') {
                const planDisplay = document.getElementById('plan-display');
                planDisplay.style.display = 'block';
                if (data.error || (data.modules && data.modules.length === 0)) {
                    document.getElementById('plan-summary').textContent = data.summary || data.error || 'Could not determine modules. Please try rephrasing your request.';
                    document.getElementById('module-container').style.display = 'none';
                    document.getElementById('execute-btn').style.display = 'none';
                } else {
                    odooPlannedModules = data.modules;
                    document.getElementById('plan-summary').textContent = data.summary;
                    const moduleList = document.getElementById('module-list');
                    moduleList.innerHTML = '';
                    data.modules.forEach(module => {
                        const li = document.createElement('li');
                        li.className = 'list-group-item';
                        li.textContent = module;
                        moduleList.appendChild(li);
                    });

                    // Show and reset website theme selector if 'website' module is included
                    const websiteDesignSelector = document.getElementById('website-design-selector');
                    const websiteDesignInput = document.getElementById('website-design-input');
                    const websiteDesignError = document.getElementById('website-design-input-error');
                    const websiteDesignSelect = document.getElementById('website-design-select');
                    if (websiteDesignSelector) {
                        const requiresTheme = data.modules.includes('website');
                        websiteDesignSelector.style.display = requiresTheme ? 'block' : 'none';
                        if (websiteDesignInput) {
                            websiteDesignInput.value = '';
                        }
                        if (websiteDesignSelect) {
                            websiteDesignSelect.value = '';
                        }
                        websiteDesignSelector.querySelectorAll('.theme-card').forEach(card => card.classList.remove('selected'));
                        if (websiteDesignError) websiteDesignError.style.display = 'none';
                    }

                    document.getElementById('module-container').style.display = 'block';
                    document.getElementById('execute-btn').style.display = 'block';
                }
            } else if (planType === 'online') {
                const planDisplay = document.getElementById('plan-display-online');
                planDisplay.style.display = 'block';
                if (data.error) {
                    document.getElementById('plan-summary-online').textContent = data.summary || data.error;
                    document.getElementById('execute-btn-online').style.display = 'none';
                } else {
                    document.getElementById('plan-summary-online').innerHTML = data.summary;
                    document.getElementById('execute-btn-online').href = data.url;
                    document.getElementById('execute-btn-online').style.display = 'inline-block';
                }
            } else if (planType === 'sh') {
                const planDisplay = document.getElementById('plan-display-sh');
                planDisplay.style.display = 'block';
                if (data.error) {
                    document.getElementById('plan-summary-sh').textContent = data.summary || data.error;
                } else {
                    document.getElementById('plan-summary-sh').innerHTML = data.guide_html;
                }
            }
        })
        .catch(error => {
            if(planError) {
                planError.textContent = `A network error occurred: ${error.message}`;
                planError.style.display = 'block';
            }
        })
        .finally(() => {
            planBtn.disabled = false;
            planBtnSpinner.style.display = 'none';
        });
    }

    function handleBrandManagerPlan(planBtn) {
        const businessNeed = document.getElementById('bm-business-need').value.trim();
        if (!businessNeed) {
            alert('Please describe the business requirements.');
            return;
        }

        const planBtnSpinner = planBtn.querySelector('.spinner-border');
        const planError = document.getElementById('bm-plan-error');

        planBtn.disabled = true;
        planBtnSpinner.style.display = 'inline-block';
        planError.style.display = 'none';

        fetch('/odoo/plan', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ business_need: businessNeed, plan_type: 'community' })
        })
        .then(response => parseJsonResponse(response))
        .then(data => {
            const planDisplay = document.getElementById('bm-plan-display');
            planDisplay.style.display = 'block';
            if (data.error || (data.modules && data.modules.length === 0)) {
                document.getElementById('bm-plan-summary').textContent = data.summary || data.error || 'Could not determine modules.';
                document.getElementById('bm-module-list').innerHTML = '';
                document.getElementById('bm-execute-btn').style.display = 'none';
            } else {
                odooPlannedModules = data.modules; // Save to state
                document.getElementById('bm-plan-summary').textContent = data.summary;
                const moduleList = document.getElementById('bm-module-list');
                moduleList.innerHTML = '';
                data.modules.forEach(module => {
                    const li = document.createElement('li');
                    li.className = 'list-group-item';
                    li.textContent = module;
                    moduleList.appendChild(li);
                });

                const bmWebsiteSelector = document.getElementById('bm-website-design-selector');
                const bmWebsiteInput = document.getElementById('bm-website-design-input');
                const bmWebsiteError = document.getElementById('bm-website-design-input-error');
                const bmWebsiteSelect = document.getElementById('bm-website-design-select');
                if (bmWebsiteSelector) {
                    const requiresTheme = data.modules.includes('website');
                    bmWebsiteSelector.style.display = requiresTheme ? 'block' : 'none';
                    if (bmWebsiteInput) bmWebsiteInput.value = '';
                    if (bmWebsiteSelect) bmWebsiteSelect.value = '';
                    bmWebsiteSelector.querySelectorAll('.theme-card').forEach(card => card.classList.remove('selected'));
                    if (bmWebsiteError) bmWebsiteError.style.display = 'none';
                }

                document.getElementById('bm-execute-btn').style.display = 'block';
            }
        })
        .catch(error => {
            planError.textContent = `A network error occurred: ${error.message}`;
            planError.style.display = 'block';
        })
        .finally(() => {
            planBtn.disabled = false;
            planBtnSpinner.style.display = 'none';
        });
    }

    function handleBrandManagerExecute(executeBtn) {
        const odooVersion = document.getElementById('bm-odoo-version-input').value;
        // --- This is where you define YOUR branding modules ---
        const brandingModules = ['my_software_theme', 'my_software_debrand'];

        const bmDesignSelect = document.getElementById('bm-website-design-select');
        const bmDesignInput = document.getElementById('bm-website-design-input');
        const bmWebsiteDesign = bmDesignSelect?.value?.trim() || (bmDesignInput ? bmDesignInput.value.trim() : '');
        const bmThemeError = document.getElementById('bm-website-design-input-error');
        const requiresTheme = odooPlannedModules.includes('website');
        if (requiresTheme && !bmWebsiteDesign) {
            if (bmThemeError) {
                bmThemeError.textContent = 'Please select a website theme before creating the environment.';
                bmThemeError.style.display = 'block';
            }
            return;
        }

        executeBtn.disabled = true;
        document.getElementById('bm-creation-status').style.display = 'block';
        const creationLog = document.getElementById('bm-creation-log');
        creationLog.textContent = 'Sending request to create branded environment...';

        fetch('/odoo/execute', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ modules: odooPlannedModules, odoo_version: odooVersion, branding_modules: brandingModules, website_design: bmWebsiteDesign })
        })
        .then(response => parseJsonResponse(response))
        .then(data => {
            if (data && data.job_id) {
                pollJobStatus(data.job_id, 'bm-');
            } else {
                creationLog.textContent = `Error creating environment: ${data && data.error ? data.error : 'no job_id returned'} \nResponse: ${JSON.stringify(data)}`;
                console.error('BM create response (no job_id):', data);
            }
        })
        .catch(error => creationLog.textContent = `Error: ${error && error.message ? error.message : String(error)}`);
    }

    function handleThemeSelect(selectEl) {
        const themeValue = (selectEl.value || '').trim();
        const targetInputId = selectEl.dataset.targetInput || 'website-design-input';
        const designInput = document.getElementById(targetInputId);
        if (designInput) {
            designInput.value = themeValue;
        }

        const errorEl = document.getElementById(`${targetInputId}-error`);
        if (errorEl) {
            errorEl.style.display = 'none';
            errorEl.textContent = '';
        }
    }

    function handleThemeSelection(selectedCard) {
        const themeValue = (selectedCard.dataset.themeValue || '').trim();
        const targetInputId = selectedCard.dataset.targetInput || 'website-design-input';
        const designInput = document.getElementById(targetInputId);
        if (!designInput) return;
        designInput.value = themeValue;

        // Remove 'selected' class from cards in the same group / target input
        const groupContainer = selectedCard.closest('[data-theme-group]') || document;
        const scopedCards = groupContainer.querySelectorAll(`.theme-card[data-target-input="${targetInputId}"]`);
        scopedCards.forEach(card => card.classList.remove('selected'));

        // Add 'selected' class to the clicked card
        selectedCard.classList.add('selected');

        const errorEl = document.getElementById(`${targetInputId}-error`);
        if (errorEl) {
            errorEl.style.display = 'none';
            errorEl.textContent = '';
        }
    }

    function handleOdooExecute(executeBtn) {
        const designSelect = document.getElementById('website-design-select');
        const designInput = document.getElementById('website-design-input');
        const websiteDesign = designSelect?.value?.trim() || (designInput ? designInput.value.trim() : '');
        const themeError = document.getElementById('website-design-input-error');
        const requiresTheme = odooPlannedModules.includes('website');
        if (requiresTheme && !websiteDesign) {
            if (themeError) {
                themeError.textContent = 'Please select a website theme before creating the environment.';
                themeError.style.display = 'block';
            }
            return;
        }

        executeBtn.disabled = true;
        document.getElementById('creation-status').style.display = 'block';
        const creationLog = document.getElementById('creation-log');
        creationLog.textContent = 'Sending request to create environment...';

        // Get the selected Odoo version
        const versionInput = document.getElementById('odoo-version-input');
        const odooVersion = versionInput ? versionInput.value : '19.0'; // Default to 19.0

        fetch('/odoo/execute', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ modules: odooPlannedModules, website_design: websiteDesign, odoo_version: odooVersion })
        })
        .then(response => parseJsonResponse(response))
        .then(data => {
            if (data && data.job_id) {
                pollJobStatus(data.job_id);
            } else {
                creationLog.textContent = `Error creating environment: ${data && data.error ? data.error : 'no job_id returned'} \nResponse: ${JSON.stringify(data)}`;
                console.error('Create response (no job_id):', data);
            }
        })
        .catch(error => creationLog.textContent = `Error: ${error && error.message ? error.message : String(error)}`);
    }

    async function pollJobStatus(jobId, prefix = '') {
        // Use a global-like variable on window to be able to clear it when switching apps
        window.odooPollInterval = setInterval(() => {
            fetch(`/odoo/job_status/${jobId}`)
                .then(response => parseJsonResponse(response))
                .then(data => {
                    const creationLog = document.getElementById(`${prefix}creation-log`);
                    if (!creationLog) { // If user navigated away
                        clearInterval(window.odooPollInterval);
                        return;
                    }
                    creationLog.textContent = data.log ? data.log.join('\n') : 'Waiting for log...';
                    creationLog.scrollTop = creationLog.scrollHeight;

                    if (data.status === 'completed' || data.status === 'failed') {
                        clearInterval(window.odooPollInterval);
                        if (data.status === 'completed' && data.url) {
                            document.getElementById(`${prefix}environment-link`).href = data.url;
                            document.getElementById(`${prefix}environment-link-container`).style.display = 'block';
                        }
                    }
                })
                .catch(error => {
                    console.error('Polling error:', error);
                    clearInterval(window.odooPollInterval);
                });
        }, 2000);
    }

    async function handleChatSubmit(event) {
        event.preventDefault();
        const messageInput = document.getElementById('message-input');
        const userInput = messageInput.value.trim();
        if (!userInput) return;

        window.addMessage(userInput, 'user');
        messageInput.value = '';
        const thinkingMessage = window.addMessage('...', 'ai', true);

        try {
            const response = await fetch('/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: userInput }),
            });

            const data = await parseJsonResponse(response);
            thinkingMessage.remove();

            if (response.ok) {
                window.addMessage(data.response, 'ai');
            } else {
                window.addMessage(`Error: ${data.error}`, 'error');
            }
        } catch (error) {
            thinkingMessage.remove();
            window.addMessage(`An unexpected error occurred: ${error.message}`, 'error');
            console.error('Fetch error:', error);
        }
    }

    async function handleWebsiteGenerate(formEl) {
        const resultEl = document.getElementById('website-helper-generate-result');
        if (!resultEl) return;
        const prompt = formEl.querySelector('#design-prompt-input')?.value || '';
        const outputPath = formEl.querySelector('#output-path-input')?.value || '';
        const apply = formEl.querySelector('#apply-toggle')?.checked || false;
        resultEl.innerHTML = '<div class="alert alert-info">Generating CSS...</div>';
        try {
            const response = await fetch('/website_helper/generate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ prompt, output_path: outputPath, apply })
            });
            const data = await parseJsonResponse(response);
            if (!response.ok) {
                resultEl.innerHTML = `<div class="alert alert-danger">${data.message || 'Generation failed.'}</div>`;
                return;
            }

            const saved = data.saved_path ? `<div class="alert alert-success mt-2">Saved to ${data.saved_path}</div>` : '';
            resultEl.innerHTML = `
                <div class="alert alert-primary">Generated theme CSS</div>
                <pre class="p-3 bg-light border rounded" style="white-space: pre-wrap;">${data.css.replace(/</g, '&lt;')}</pre>
                ${saved}
            `;
        } catch (err) {
            resultEl.innerHTML = `<div class="alert alert-danger">Generation error: ${err.message}</div>`;
        }
    }

    async function handleWebsiteSiteGenerate(formEl) {
        const resultEl = document.getElementById('website-helper-site-result');
        if (!resultEl) return;

        const prompt = formEl.querySelector('#site-design-prompt-input')?.value || '';
        const brand = formEl.querySelector('#site-brand-input')?.value || '';
        const cta = formEl.querySelector('#site-cta-input')?.value || '';
        const accent = formEl.querySelector('#site-accent-input')?.value || '';
        const backgroundImage = formEl.querySelector('#site-bg-input')?.value || '';
        const sourceHtml = formEl.querySelector('#site-source-html')?.value || '';

        resultEl.innerHTML = '<div class="alert alert-info">Generating layout...</div>';

        try {
            const response = await fetch('/website_helper/site_generator', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ prompt, brand, cta, accent, background_image: backgroundImage, source_html: sourceHtml })
            });

            const data = await parseJsonResponse(response);
            if (!response.ok || data.status !== 'ok') {
                resultEl.innerHTML = `<div class="alert alert-danger">${data.message || data.error || 'Generation failed.'}</div>`;
                return;
            }

            const escapeHtml = (str = '') => str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
            const escapeAttr = (str = '') => str.replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
            const htmlSafe = escapeHtml(data.html || '');
            const cssSafe = escapeHtml(data.css || '');
            const combinedRaw = data.combined || '';
            const combinedSafe = escapeHtml(combinedRaw);

            if (sitePreviewUrl) {
                URL.revokeObjectURL(sitePreviewUrl);
            }
            sitePreviewUrl = combinedRaw ? URL.createObjectURL(new Blob([combinedRaw], { type: 'text/html' })) : null;

            const iframeHtml = combinedRaw ? `
                <div class="d-flex justify-content-between align-items-center mt-3 mb-2">
                    <span class="fw-semibold">Preview</span>
                    <a class="btn btn-sm btn-outline-primary" href="${sitePreviewUrl}" target="_blank" rel="noopener">Open in new tab</a>
                </div>
                <div class="border rounded overflow-hidden" style="min-height: 640px;">
                    <iframe srcdoc="${escapeAttr(combinedRaw)}" style="width:100%; height:640px; border:0;" loading="lazy" sandbox="allow-same-origin allow-scripts allow-popups allow-forms"></iframe>
                </div>
            ` : '';

            resultEl.innerHTML = `
                <div class="alert alert-success">Site layout generated. Paste into an Odoo snippet.</div>
                ${iframeHtml}
                <div class="d-flex flex-wrap gap-2 mb-2">
                    <button type="button" class="btn btn-sm btn-outline-secondary copy-snippet-btn" data-copy-target="site-html-snippet">Copy HTML</button>
                    <button type="button" class="btn btn-sm btn-outline-secondary copy-snippet-btn" data-copy-target="site-css-snippet">Copy CSS</button>
                    <button type="button" class="btn btn-sm btn-primary copy-snippet-btn" data-copy-target="site-combined-snippet">Copy HTML + CSS</button>
                </div>
                <label class="form-label fw-semibold">HTML</label>
                <pre id="site-html-snippet" class="p-3 bg-light border rounded" style="white-space: pre-wrap;">${htmlSafe}</pre>
                <label class="form-label fw-semibold mt-2">CSS</label>
                <pre id="site-css-snippet" class="p-3 bg-light border rounded" style="white-space: pre-wrap;">${cssSafe}</pre>
                <label class="form-label fw-semibold mt-2">HTML + CSS</label>
                <pre id="site-combined-snippet" class="p-3 bg-light border rounded" style="white-space: pre-wrap;">${combinedSafe}</pre>
            `;
        } catch (err) {
            resultEl.innerHTML = `<div class="alert alert-danger">Generator error: ${err.message}</div>`;
        }
    }

    function handleCopySnippet(copyBtn) {
        const targetId = copyBtn.dataset.copyTarget;
        if (!targetId) return;
        const targetEl = document.getElementById(targetId);
        if (!targetEl) return;

        const originalLabel = copyBtn.textContent;
        const content = targetEl.textContent || '';
        navigator.clipboard.writeText(content)
            .then(() => {
                copyBtn.textContent = 'Copied';
                setTimeout(() => copyBtn.textContent = originalLabel, 1400);
            })
            .catch(() => {
                copyBtn.textContent = 'Copy failed';
                setTimeout(() => copyBtn.textContent = originalLabel, 1400);
            });
    }

    // This function is attached to the window object to be accessible
    // after new content (like the email app) is loaded dynamically.
    window.addMessage = function(content, type, isTemp = false) {
        const chatWindow = document.getElementById('chat-window');
        if (!chatWindow) return; // Don't do anything if the chat window isn't loaded

        const messageDiv = document.createElement('div');
        messageDiv.classList.add('message', `${type}-message`);
        const p = document.createElement('p');
        p.innerHTML = content;
        messageDiv.appendChild(p);

        chatWindow.appendChild(messageDiv);
        chatWindow.scrollTop = chatWindow.scrollHeight;
        if (isTemp) {
            messageDiv.classList.add('thinking');
        }
        return messageDiv;
    }

    // --- Agent FAB and Edit Modal Logic ---
    const agentEditModal = new bootstrap.Modal(document.getElementById('agent-edit-modal'));
    const agentEditSendBtn = document.getElementById('agent-edit-send');
    const agentEditInput = document.getElementById('agent-edit-input');
    const agentEditChatWindow = document.getElementById('agent-edit-chat-window');

    agentEditSendBtn.addEventListener('click', handleAgentEdit);
    agentEditInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') handleAgentEdit();
    });

    async function handleAgentEdit() {
        const userRequest = agentEditInput.value.trim();
        if (!userRequest) return;

        addMessageToEditChat(userRequest, 'user');
        agentEditInput.value = '';
        const thinkingIndicator = addMessageToEditChat('...', 'ai', true);
        const currentAppHtml = appContentArea.innerHTML;

        try {
            const response = await fetch('/gemini/edit_ui', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    user_request: userRequest,
                    app_html: currentAppHtml
                })
            });

            thinkingIndicator.remove();
            const data = await parseJsonResponse(response);

            if (response.ok) {
                addMessageToEditChat(data.suggested_html, 'ai-code');
            } else {
                addMessageToEditChat(`Error: ${data.error}`, 'error');
            }
        } catch (error) {
            thinkingIndicator.remove();
            addMessageToEditChat(`An unexpected network error occurred: ${error.message}`, 'error');
        }
    }

    function addMessageToEditChat(content, type, isTemp = false) {
        const messageContainer = document.createElement('div');
        messageContainer.className = `p-2 mb-2 rounded`;

        if (type === 'user') {
            messageContainer.classList.add('bg-light', 'text-dark', 'text-end');
            messageContainer.textContent = content;
        } else if (type === 'ai') {
            messageContainer.classList.add('bg-secondary', 'text-white');
            messageContainer.textContent = content;
        } else if (type === 'error') {
            messageContainer.classList.add('alert', 'alert-danger');
            messageContainer.textContent = content;
        } else if (type === 'ai-code') {
            messageContainer.classList.add('bg-light', 'border', 'p-3');
            const escapedContent = content.replace(/</g, "&lt;").replace(/>/g, "&gt;");
            messageContainer.innerHTML = `
                <div class="agent-code-block-header">
                    <p class="fw-bold mb-0">Gemini's Suggestion:</p>
                    <button class="btn btn-sm btn-outline-secondary copy-btn">Copy</button>
                </div>
                <pre class="agent-code-block">${escapedContent}</pre>
                <button class="btn btn-success btn-sm mt-2 apply-btn">Apply Changes</button>
            `;
            messageContainer.querySelector('.apply-btn').onclick = () => {
                appContentArea.innerHTML = content;
                onAppContentChange(); // Re-initialize components after applying agent changes
                agentEditModal.hide();
            };
            messageContainer.querySelector('.copy-btn').onclick = () => {
                navigator.clipboard.writeText(content).then(() => {
                    // Optional: show a "Copied!" message
                });
            };
        }
        if (isTemp) messageContainer.classList.add('thinking');
        agentEditChatWindow.appendChild(messageContainer);
        agentEditChatWindow.scrollTop = agentEditChatWindow.scrollHeight;
        return messageContainer;
    }

    // --- Initialize Draggable FAB ---
    const agentFab = document.getElementById('agent-fab');
    if (agentFab) {
        makeDraggable(agentFab, () => agentEditModal.show());
    }

    // --- Odoo environment history rendering & start handler (graceful for local environments) ---
    async function refreshEnvHistory() {
        const body = document.getElementById('env-history-body');
        const empty = document.getElementById('env-history-empty');
        if (!body) return; // Not on the Odoo app page

        try {
            const res = await fetch('/odoo/environments');
            const data = await parseJsonResponse(res);
            const envs = (data && data.environments) || [];
            body.innerHTML = '';
            if (envs.length === 0) {
                empty.style.display = 'block';
                return;
            }
            empty.style.display = 'none';

            envs.forEach(env => {
                const tr = document.createElement('tr');
                const openedTd = document.createElement('td');
                openedTd.textContent = env.created_at ? new Date(env.created_at).toLocaleString() : '-';
                const dbTd = document.createElement('td');
                dbTd.textContent = env.db_name || '-';
                const verTd = document.createElement('td');
                verTd.textContent = env.odoo_version || '-';
                const modTd = document.createElement('td');
                modTd.textContent = (env.modules || []).join(', ');
                const actionsTd = document.createElement('td');
                actionsTd.className = 'text-end';

                const openBtn = document.createElement('button');
                openBtn.className = 'btn btn-sm btn-primary me-2';
                openBtn.textContent = 'Open';
                openBtn.addEventListener('click', async () => {
                    const creationLog = document.getElementById('creation-log');
                    if (creationLog) creationLog.textContent = `Starting environment '${env.db_name}'...`;
                    try {
                        const startRes = await fetch('/odoo/local_env/start', {
                            method: 'POST', headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ db_name: env.db_name })
                        });
                        const startData = await parseJsonResponse(startRes);

                        // Handle different backend shapes (status/message/url or error)
                        if (startData && (startData.status === 'started' || startData.message)) {
                            const msg = startData.message || `Started environment '${env.db_name}'`;
                            if (creationLog) creationLog.textContent = msg;
                            // Show link if available
                            if (startData.url) {
                                const linkEl = document.getElementById('environment-link');
                                if (linkEl) {
                                    linkEl.href = startData.url;
                                    document.getElementById('environment-link-container').style.display = 'block';
                                }
                            }
                            // Optionally fetch the latest log and show it
                            try {
                                const logRes = await fetch(`/odoo/local_env/log/${encodeURIComponent(env.db_name)}`);
                                const logJson = await parseJsonResponse(logRes);
                                if (logJson && logJson.log && document.getElementById('creation-log')) {
                                    document.getElementById('creation-log').textContent = logJson.log;
                                }
                            } catch (e) {
                                // ignore log fetch errors
                            }
                        } else if (startData && startData.error) {
                            if (creationLog) creationLog.textContent = `Error: ${startData.error}`;
                        } else {
                            if (creationLog) creationLog.textContent = JSON.stringify(startData);
                        }

                    } catch (err) {
                        const creationLog = document.getElementById('creation-log');
                        if (creationLog) creationLog.textContent = `Error starting environment: ${err.message}`;
                    }
                    // Refresh history (in case the backend wrote a new entry)
                    setTimeout(refreshEnvHistory, 1200);
                });

                const logsBtn = document.createElement('button');
                logsBtn.className = 'btn btn-sm btn-outline-secondary';
                logsBtn.textContent = 'View Log';
                logsBtn.addEventListener('click', async () => {
                    const creationLog = document.getElementById('creation-log');
                    try {
                        const logRes = await fetch(`/odoo/local_env/log/${encodeURIComponent(env.db_name)}`);
                        const logJson = await parseJsonResponse(logRes);
                        if (logJson && logJson.log && creationLog) creationLog.textContent = logJson.log;
                        else if (creationLog) creationLog.textContent = logJson.error || 'No log available.';
                    } catch (e) {
                        if (creationLog) creationLog.textContent = `Error fetching log: ${e.message}`;
                    }
                });

                actionsTd.appendChild(openBtn);
                actionsTd.appendChild(logsBtn);

                tr.appendChild(openedTd);
                tr.appendChild(dbTd);
                tr.appendChild(verTd);
                tr.appendChild(modTd);
                tr.appendChild(actionsTd);
                body.appendChild(tr);
            });
        } catch (err) {
            console.error('Failed to refresh env history:', err);
        }
    }

    // Wire up refresh button and auto-refresh when Odoo app loads
    document.getElementById('env-history-refresh')?.addEventListener('click', (e) => { e.preventDefault(); refreshEnvHistory(); });
    // If the Odoo app is currently loaded, refresh immediately
    if (document.getElementById('env-history-body')) refreshEnvHistory();

});