document.addEventListener('DOMContentLoaded', () => {
    const appContentArea = document.getElementById('app-content-area');
    let odooPlannedModules = []; // State for Odoo app

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
        }
    });

    appContentArea.addEventListener('click', async (event) => {
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
        .then(response => response.json())
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

                    // Show website theme selector if 'website' module is included
                    const websiteDesignSelector = document.getElementById('website-design-selector');
                    if (data.modules.includes('website')) {
                        websiteDesignSelector.style.display = 'block';
                    } else {
                        websiteDesignSelector.style.display = 'none';
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
        .then(response => response.json())
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
        executeBtn.disabled = true;
        document.getElementById('bm-creation-status').style.display = 'block';
        const creationLog = document.getElementById('bm-creation-log');
        creationLog.textContent = 'Sending request to create branded environment...';

        const odooVersion = document.getElementById('bm-odoo-version-input').value;
        // --- This is where you define YOUR branding modules ---
        const brandingModules = ['my_software_theme', 'my_software_debrand'];

        fetch('/odoo/execute', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ modules: odooPlannedModules, odoo_version: odooVersion, branding_modules: brandingModules })
        })
        .then(response => response.json())
        .then(data => data.job_id ? pollJobStatus(data.job_id, 'bm-') : (creationLog.textContent = `Error: ${data.error}`))
        .catch(error => creationLog.textContent = `Error: ${error.message}`);
    }

    function handleThemeSelection(selectedCard) {
        const themeValue = selectedCard.dataset.themeValue;
        const designInput = document.getElementById('website-design-input');
        designInput.value = themeValue;

        // Remove 'selected' class from all cards
        const allThemeCards = document.querySelectorAll('.theme-card');
        allThemeCards.forEach(card => card.classList.remove('selected'));

        // Add 'selected' class to the clicked card
        selectedCard.classList.add('selected');
    }

    function handleOdooExecute(executeBtn) {
        executeBtn.disabled = true;
        document.getElementById('creation-status').style.display = 'block';
        const creationLog = document.getElementById('creation-log');
        creationLog.textContent = 'Sending request to create environment...';

        // Get the selected website design, if any
        const designInput = document.getElementById('website-design-input');
        const websiteDesign = designInput ? designInput.value : null;

        // Get the selected Odoo version
        const versionInput = document.getElementById('odoo-version-input');
        const odooVersion = versionInput ? versionInput.value : '19.0'; // Default to 19.0

        fetch('/odoo/execute', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ modules: odooPlannedModules, website_design: websiteDesign, odoo_version: odooVersion })
        })
        .then(response => response.json())
        .then(data => data.job_id ? pollJobStatus(data.job_id) : (creationLog.textContent = `Error: ${data.error}`))
        .catch(error => creationLog.textContent = `Error: ${error.message}`);
    }

    async function pollJobStatus(jobId, prefix = '') {
        // Use a global-like variable on window to be able to clear it when switching apps
        window.odooPollInterval = setInterval(() => {
            fetch(`/odoo/job_status/${jobId}`)
                .then(response => response.json())
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

            const data = await response.json();
            thinkingMessage.remove();

            if (response.ok) {
                window.addMessage(data.response, 'ai');
            } else {
                window.addMessage(`Error: ${data.error}`, 'error');
            }
        } catch (error) {
            thinkingMessage.remove();
            window.addMessage('An unexpected error occurred. Please check the server logs.', 'error');
            console.error('Fetch error:', error);
        }
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
            const data = await response.json();

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
});