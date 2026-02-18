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

        // Ensure Create buttons are visible for the Odoo planner even if planning hasn't run yet
        const execBtn = document.getElementById('execute-btn');
        const createWithoutBtn = document.getElementById('create-without-plan');
        if (execBtn) execBtn.style.display = 'inline-block';
        if (createWithoutBtn) createWithoutBtn.style.display = 'inline-block';

        // Initialize Email app features if present
        const inboxList = document.getElementById('inbox-list');
        if (inboxList) {
            initEmailApp();
        }

        // Initialize Odoo environment history if the section exists
        const envHistoryBody = document.getElementById('env-history-body');
        if (envHistoryBody) {
            initOdooHistory();
        }
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
    // The app launchers are now the glass cards and the offcanvas menu.
    document.getElementById('load-odoo-app')?.addEventListener('click', () => loadApp('/apps/odoo'));
    document.getElementById('load-social-media-app')?.addEventListener('click', () => loadApp('/apps/social_media'));
    document.getElementById('load-email-app')?.addEventListener('click', () => loadApp('/apps/email'));
    document.getElementById('load-website-helper-app')?.addEventListener('click', () => loadApp('/apps/website_helper'));
    document.getElementById('cta-website-redesign')?.addEventListener('click', () => loadApp('/apps/website_helper'));
    document.getElementById('load-admin-app')?.addEventListener('click', () => loadApp('/apps/admin'));

        // Save the original dashboard HTML so we can restore it when users click Back.
        let originalHeroHtml = appContentArea ? appContentArea.innerHTML : '';

        function attachCardListeners() {
            // Card click handlers
            document.getElementById('load-odoo-app')?.addEventListener('click', () => loadApp('/apps/odoo'));
            document.getElementById('load-social-media-app')?.addEventListener('click', () => loadApp('/apps/social_media'));
            document.getElementById('load-email-app')?.addEventListener('click', () => loadApp('/apps/email'));
            document.getElementById('load-website-helper-app')?.addEventListener('click', () => loadApp('/apps/website_helper'));
            document.getElementById('cta-website-redesign')?.addEventListener('click', () => loadApp('/apps/website_helper'));

            // Offcanvas menu links should also load apps and close the menu
            document.getElementById('load-odoo-app-menu')?.addEventListener('click', (e) => {
                e.preventDefault();
                loadApp('/apps/odoo');
                const offcanvasEl = document.getElementById('main-menu');
                const oc = offcanvasEl ? bootstrap.Offcanvas.getInstance(offcanvasEl) : null;
                if (oc) oc.hide();
            });
            document.getElementById('load-social-media-app-menu')?.addEventListener('click', (e) => {
                e.preventDefault();
                loadApp('/apps/social_media');
                const offcanvasEl = document.getElementById('main-menu');
                const oc = offcanvasEl ? bootstrap.Offcanvas.getInstance(offcanvasEl) : null;
                if (oc) oc.hide();
            });
            document.getElementById('load-email-app-menu')?.addEventListener('click', (e) => {
                e.preventDefault();
                loadApp('/apps/email');
                const offcanvasEl = document.getElementById('main-menu');
                const oc = offcanvasEl ? bootstrap.Offcanvas.getInstance(offcanvasEl) : null;
                if (oc) oc.hide();
            });
            document.getElementById('load-website-helper-app-menu')?.addEventListener('click', (e) => {
                e.preventDefault();
                loadApp('/apps/website_helper');
                const offcanvasEl = document.getElementById('main-menu');
                const oc = offcanvasEl ? bootstrap.Offcanvas.getInstance(offcanvasEl) : null;
                if (oc) oc.hide();
            });
            document.getElementById('load-admin-app-menu')?.addEventListener('click', (e) => {
                e.preventDefault();
                loadApp('/apps/admin');
                const offcanvasEl = document.getElementById('main-menu');
                const oc = offcanvasEl ? bootstrap.Offcanvas.getInstance(offcanvasEl) : null;
                if (oc) oc.hide();
            });
        }

        // Attach listeners initially
        attachCardListeners();

    // Offcanvas menu links should also load apps and close the menu
    document.getElementById('load-odoo-app-menu')?.addEventListener('click', (e) => {
        e.preventDefault();
        loadApp('/apps/odoo');
        const offcanvasEl = document.getElementById('main-menu');
        const oc = offcanvasEl ? bootstrap.Offcanvas.getInstance(offcanvasEl) : null;
        if (oc) oc.hide();
    });
    document.getElementById('load-social-media-app-menu')?.addEventListener('click', (e) => {
        e.preventDefault();
        loadApp('/apps/social_media');
        const offcanvasEl = document.getElementById('main-menu');
        const oc = offcanvasEl ? bootstrap.Offcanvas.getInstance(offcanvasEl) : null;
        if (oc) oc.hide();
    });
    document.getElementById('load-email-app-menu')?.addEventListener('click', (e) => {
        e.preventDefault();
        loadApp('/apps/email');
        const offcanvasEl = document.getElementById('main-menu');
        const oc = offcanvasEl ? bootstrap.Offcanvas.getInstance(offcanvasEl) : null;
        if (oc) oc.hide();
    });

    async function loadApp(url) {
        // Clear any running Odoo job polls when switching apps
        if (window.odooPollInterval) clearInterval(window.odooPollInterval);

        try {
            appContentArea.innerHTML = '<div class="d-flex justify-content-center align-items-center h-100"><div class="spinner-border" role="status"><span class="visually-hidden">Loading...</span></div></div>';
            const response = await fetch(url);
            if (!response.ok) throw new Error('Failed to load app.');
            const appHtml = await response.text();
                // Insert a small back header and the app HTML
                appContentArea.innerHTML = '';
                const backWrap = document.createElement('div');
                backWrap.className = 'mb-3';
                const backBtn = document.createElement('button');
                backBtn.className = 'btn btn-outline-secondary btn-sm';
                backBtn.textContent = '← Back to Dashboard';
                backBtn.addEventListener('click', () => {
                    restoreDashboard();
                });
                backWrap.appendChild(backBtn);
                appContentArea.appendChild(backWrap);

                const appNode = document.createElement('div');
                appNode.innerHTML = appHtml;
                appContentArea.appendChild(appNode);

                onAppContentChange(); // Initialize components in the newly loaded app
        } catch (error) {
            appContentArea.innerHTML = `<div class="alert alert-danger m-4"><strong>Error:</strong> ${error.message}</div>`;
            console.error('App loading error:', error);
        }
    }

        function restoreDashboard() {
            if (!originalHeroHtml) return;
            appContentArea.innerHTML = originalHeroHtml;
            // Re-attach listeners to the freshly restored DOM
            attachCardListeners();
            onAppContentChange();
            // Scroll to top for good measure
            window.scrollTo({ top: 0, behavior: 'smooth' });
        }

    // --- Event Delegation for Dynamically Loaded Content ---
    appContentArea.addEventListener('submit', async (event) => {
        const formId = event.target.id;
        if (!formId) return;
        // Always stop native navigation for our in-app forms
        event.preventDefault();

        if (formId === 'chat-form') {
            handleChatSubmit(event);
        } else if (formId === 'website-helper-audit-form') {
            handleWebsiteAudit(event.target);
        } else if (formId === 'website-helper-generate-form') {
            handleWebsiteGenerate(event.target);
        } else if (formId === 'website-helper-site-form') {
            handleWebsiteSiteGenerate(event.target);
        } else if (formId === 'website-helper-visual-form') {
            handleWebsiteVisualAudit(event.target);
        } else if (formId === 'website-helper-inject-form') {
            handleWebsiteInject(event.target);
        }
    });

    appContentArea.addEventListener('click', async (event) => {
        const copyBtn = event.target.closest('.copy-snippet-btn');
        if (copyBtn) {
            handleCopySnippet(copyBtn);
            return;
        }

        // Email quick actions
        const quickBtn = event.target.closest('[data-quick-prompt]');
        if (quickBtn) {
            event.preventDefault();
            const prompt = quickBtn.getAttribute('data-quick-prompt');
            const input = document.getElementById('message-input');
            const form = document.getElementById('chat-form');
            if (input && form) {
                input.value = prompt;
                form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
            }
            return;
        }

        if (event.target.classList.contains('plan-btn')) {
            handleOdooPlan(event.target);
        } else if (event.target.id === 'create-without-plan') {
            // User opted to create without a generated plan — use sensible defaults and execute
            odooPlannedModules = ['base', 'web', 'website'];
            const moduleList = document.getElementById('module-list');
            moduleList.innerHTML = odooPlannedModules.map(m => `<li class="list-group-item">${m}</li>`).join('');
            document.getElementById('plan-summary').textContent = 'Proceeding without a plan — using default modules.';
            document.getElementById('module-container').style.display = 'block';
            document.getElementById('execute-btn').style.display = 'block';
            // Execute immediately
            handleOdooExecute(document.getElementById('execute-btn'));
        } else if (event.target.id === 'execute-btn') {
            handleOdooExecute(event.target);
        } else if (event.target.closest('.theme-card')) {
            handleThemeSelection(event.target.closest('.theme-card'));
        } else if (event.target.id === 'bm-plan-btn') {
            handleBrandManagerPlan(event.target);
        } else if (event.target.id === 'bm-execute-btn') {
            handleBrandManagerExecute(event.target);
        } else if (event.target.closest('[data-reopen-db]')) {
            const btn = event.target.closest('[data-reopen-db]');
            handleOdooReopen(btn.getAttribute('data-reopen-db'));
        } else if (event.target.closest('[data-drop-db]')) {
            const btn = event.target.closest('[data-drop-db]');
            handleOdooDrop(btn.getAttribute('data-drop-db'));
        }
    });

    async function initEmailApp() {
        const refreshBtn = document.getElementById('inbox-refresh');
        const inboxList = document.getElementById('inbox-list');
        const searchInput = document.getElementById('inbox-search');
        const searchBtn = document.getElementById('inbox-search-btn');
        const unreadToggle = document.getElementById('inbox-unread');
        const prevBtn = document.getElementById('inbox-prev');
        const nextBtn = document.getElementById('inbox-next');
        const pageIndicator = document.getElementById('inbox-page-indicator');
        if (!refreshBtn || !inboxList) return;

        // Inbox state
        const state = {
            q: '',
            unread: true,
            page: 1,
            limit: 10,
            hasMore: false,
        };

        function updateIndicator() {
            if (pageIndicator) pageIndicator.textContent = `Page ${state.page}`;
            prevBtn.disabled = state.page <= 1;
            nextBtn.disabled = !state.hasMore;
        }

        refreshBtn.addEventListener('click', (e) => { e.preventDefault(); state.page = 1; fetchAndRenderInbox(); });
        if (searchInput) {
            searchInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    state.q = searchInput.value.trim();
                    state.page = 1;
                    fetchAndRenderInbox();
                }
            });
            // Debounced search on typing for convenience
            let searchDebounce;
            searchInput.addEventListener('input', () => {
                clearTimeout(searchDebounce);
                searchDebounce = setTimeout(() => {
                    state.q = searchInput.value.trim();
                    state.page = 1;
                    fetchAndRenderInbox();
                }, 500);
            });
        }
        if (searchBtn) {
            searchBtn.addEventListener('click', (e) => {
                e.preventDefault();
                state.q = (searchInput?.value || '').trim();
                state.page = 1;
                fetchAndRenderInbox();
            });
        }
        if (unreadToggle) {
            unreadToggle.addEventListener('change', () => {
                state.unread = !!unreadToggle.checked;
                state.page = 1;
                fetchAndRenderInbox();
            });
        }
        if (prevBtn) prevBtn.addEventListener('click', (e) => { e.preventDefault(); if (state.page>1){ state.page--; fetchAndRenderInbox(); }});
        if (nextBtn) nextBtn.addEventListener('click', (e) => { e.preventDefault(); if (state.hasMore){ state.page++; fetchAndRenderInbox(); }});
        
        // Auto-load on first open
        fetchAndRenderInbox();

        // Delegate clicks to open email modal
        inboxList.addEventListener('click', (e) => {
            const item = e.target.closest('[data-email-id]');
            if (!item) return;
            const id = item.getAttribute('data-email-id');
            readEmail(id);
        });

        async function fetchAndRenderInbox() {
            inboxList.innerHTML = '<li class="list-group-item">Loading...</li>';
            try {
                const params = new URLSearchParams({
                    unread: String(state.unread),
                    page: String(state.page),
                    limit: String(state.limit),
                });
                if (state.q) params.set('q', state.q);
                const res = await fetch('/email/list?' + params.toString());
                const data = await res.json();
                if (!res.ok) throw new Error(data.error || 'Failed to load inbox');
                const emails = Array.isArray(data.emails) ? data.emails : [];
                state.hasMore = !!data.has_more;
                updateIndicator();
                if (emails.length === 0) {
                    inboxList.innerHTML = '<li class="list-group-item text-muted">No emails found</li>';
                    return;
                }
                inboxList.innerHTML = emails.map(e => renderInboxItem(e)).join('');
            } catch (err) {
                inboxList.innerHTML = `<li class="list-group-item text-danger">${err.message}</li>`;
            }
        }
    }

    function renderInboxItem(e) {
        const safe = (s) => (s || '').replace(/</g, '&lt;').replace(/>/g, '&gt;');
        return `
          <li class="list-group-item list-group-item-action" role="button" data-email-id="${safe(e.id)}">
            <div class="d-flex w-100 justify-content-between">
              <h6 class="mb-1 text-truncate" style="max-width:70%">${safe(e.subject || '(No subject)')}</h6>
              <span class="badge bg-success-subtle text-success border border-success">NEW</span>
            </div>
            <small class="text-muted d-block">${safe(e.from || '')}</small>
            <small class="text-muted d-block text-truncate">${safe(e.snippet || '')}</small>
          </li>`;
    }

    async function readEmail(id) {
        try {
            const res = await fetch(`/email/read?id=${encodeURIComponent(id)}`);
            const data = await res.json();
            if (!res.ok) throw new Error(data.error || 'Failed to read email');
            const bodyEl = document.getElementById('emailReaderBody');
            const titleEl = document.getElementById('emailReaderLabel');
            if (bodyEl && titleEl) {
                titleEl.textContent = `Email #${id}`;
                bodyEl.textContent = data.content || '(No content)';
                const modal = new bootstrap.Modal(document.getElementById('emailReaderModal'));
                modal.show();
                // Store current email id on modal for actions
                const modalEl = document.getElementById('emailReaderModal');
                modalEl.setAttribute('data-email-id', id);
                // Reset draft area
                const draftArea = document.getElementById('emailDraftArea');
                const useBtn = document.getElementById('emailUseInChatBtn');
                const sendBtn = document.getElementById('emailSendBtn');
                if (draftArea) draftArea.style.display = 'none';
                if (useBtn) useBtn.style.display = 'none';
                if (sendBtn) sendBtn.style.display = 'none';
            }
        } catch (err) {
            alert(err.message);
        }
    }

    // Draft/Send actions on email modal
    document.addEventListener('click', async (e) => {
        if (e.target && e.target.id === 'emailDraftBtn') {
            e.preventDefault();
            const modalEl = document.getElementById('emailReaderModal');
            const id = modalEl?.getAttribute('data-email-id');
            if (!id) return;
            const tone = document.getElementById('emailDraftTone')?.value || 'professional';
            try {
                const res = await fetch('/email/draft', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ email_id: id, tone })
                });
                const data = await res.json();
                if (!res.ok) throw new Error(data.error || 'Failed to draft');
                // Show draft
                document.getElementById('emailDraftSubject').textContent = data.subject || '';
                document.getElementById('emailDraftBody').textContent = data.body || '';
                document.getElementById('emailDraftArea').style.display = 'block';
                document.getElementById('emailUseInChatBtn').style.display = 'inline-block';
                document.getElementById('emailSendBtn').style.display = 'inline-block';
                // Store draft for send
                modalEl.setAttribute('data-draft-to', data.to || '');
                modalEl.setAttribute('data-draft-subject', data.subject || '');
                modalEl.setAttribute('data-draft-body', data.body || '');
            } catch (err) {
                alert(err.message);
            }
        }
        if (e.target && e.target.id === 'emailUseInChatBtn') {
            e.preventDefault();
            const draftBody = document.getElementById('emailDraftBody')?.textContent || '';
            const input = document.getElementById('message-input');
            if (input) {
                input.value = draftBody;
                input.focus();
            }
        }
        if (e.target && e.target.id === 'emailSendBtn') {
            e.preventDefault();
            const modalEl = document.getElementById('emailReaderModal');
            const id = modalEl?.getAttribute('data-email-id');
            const to = modalEl?.getAttribute('data-draft-to') || '';
            const subject = modalEl?.getAttribute('data-draft-subject') || '';
            const body = modalEl?.getAttribute('data-draft-body') || '';
            if (!subject || !body) { alert('No draft available.'); return; }
            if (!confirm(`Send email to ${to || '(original sender)'}?`)) return;
            try {
                const res = await fetch('/email/send', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ email_id: id, to, subject, body })
                });
                const data = await res.json();
                if (!res.ok) throw new Error(data.error || 'Failed to send');
                alert('Email sent successfully.');
                // Optionally close modal
                const modal = bootstrap.Modal.getInstance(modalEl);
                modal?.hide();
            } catch (err) {
                alert(err.message);
            }
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
            // Debug: log planner response so we can see why UI may hide the execute button
            console.debug('[odoo_plan] response:', data);

            if (planType === 'community') {
                const planDisplay = document.getElementById('plan-display');
                planDisplay.style.display = 'block';

                // Agent disabled fallback: show message and allow proceeding with sensible defaults
                if (data && data.status === 'agent_disabled') {
                    console.info('[odoo_plan] agent disabled fallback:', data);
                    document.getElementById('plan-summary').textContent = data.message || 'Agent is disabled; proceed with default modules or configure an LLM to enable planning.';
                    const moduleList = document.getElementById('module-list');
                    moduleList.innerHTML = '';
                    odooPlannedModules = ['base', 'web', 'website'];
                    odooPlannedModules.forEach(module => {
                        const li = document.createElement('li');
                        li.className = 'list-group-item';
                        li.textContent = module;
                        moduleList.appendChild(li);
                    });
                    document.getElementById('module-container').style.display = 'block';
                    document.getElementById('execute-btn').style.display = 'block';
                    const cwb = document.getElementById('create-without-plan');
                    if (cwb) cwb.style.display = 'inline-block';
                    return;
                }

                if (data.error || (data.modules && data.modules.length === 0)) {
                    document.getElementById('plan-summary').textContent = data.summary || data.error || 'Could not determine modules. Please try rephrasing your request.';
                    document.getElementById('module-container').style.display = 'none';
                    document.getElementById('execute-btn').style.display = 'none';
                } else {
                    // Guard against unexpected shapes in the response
                    if (!Array.isArray(data.modules)) {
                        document.getElementById('plan-summary').textContent = data.summary || 'Unexpected response from planner.';
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
            console.error('[odoo_plan] network error:', error);
            if(planError) {
                planError.textContent = `A network error occurred: ${error.message}. You can create an environment without a generated plan.`;
                planError.style.display = 'block';
            }
            // Fallback: expose sensible defaults so the user can proceed
            const moduleList = document.getElementById('module-list');
            moduleList.innerHTML = '';
            odooPlannedModules = ['base', 'web', 'website'];
            odooPlannedModules.forEach(module => {
                const li = document.createElement('li');
                li.className = 'list-group-item';
                li.textContent = module;
                moduleList.appendChild(li);
            });
            document.getElementById('plan-summary').textContent = 'Using default modules due to planner error — you can proceed to create the environment.';
            document.getElementById('module-container').style.display = 'block';
            document.getElementById('execute-btn').style.display = 'block';
            const cwb = document.getElementById('create-without-plan');
            if (cwb) cwb.style.display = 'inline-block';
        })
        .finally(() => {
            planBtn.disabled = false;
            planBtnSpinner.style.display = 'none';
        });
    }

    async function initOdooHistory() {
        const bodyEl = document.getElementById('env-history-body');
        const emptyEl = document.getElementById('env-history-empty');
        const refreshBtn = document.getElementById('env-history-refresh');
        if (!bodyEl) return;

        if (refreshBtn && !refreshBtn.dataset.bound) {
            refreshBtn.dataset.bound = 'true';
            refreshBtn.addEventListener('click', (e) => {
                e.preventDefault();
                loadHistory();
            });
        }

        loadHistory();

        async function loadHistory() {
            bodyEl.innerHTML = '<tr><td colspan="5" class="text-muted">Loading…</td></tr>';
            try {
                const res = await fetch('/odoo/environments');
                const data = await parseJsonResponse(res);
                const list = Array.isArray(data.environments) ? data.environments : [];
                showToast(`Refreshed: loaded ${list.length} environment(s)`, 'info');
                if (list.length === 0) {
                    bodyEl.innerHTML = '';
                    if (emptyEl) emptyEl.style.display = 'block';
                    return;
                }
                if (emptyEl) emptyEl.style.display = 'none';
                const html = list.map(renderHistoryRow).join('');
                bodyEl.innerHTML = html;
                console.log('[OdooHistory] Rendered table HTML:', html);
            } catch (err) {
                showToast(`Refresh failed: ${err.message}`, 'danger');
                bodyEl.innerHTML = `<tr><td colspan="5" class="text-danger">${err.message}</td></tr>`;
                if (emptyEl) emptyEl.style.display = 'none';
            }
        }
    }

    function showToast(message, variant = 'info') {
        const container = document.getElementById('toast-container');
        if (!container) {
            alert(message);
            return;
        }

        const variants = {
            info: 'primary',
            success: 'success',
            danger: 'danger',
            warning: 'warning'
        };

        const toast = document.createElement('div');
        toast.className = `toast align-items-center text-bg-${variants[variant] || 'primary'} border-0`;
        toast.role = 'status';
        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">${message}</div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>`;

        container.appendChild(toast);
        const toastObj = bootstrap.Toast.getOrCreateInstance(toast, { delay: 4000 });
        toast.addEventListener('hidden.bs.toast', () => toast.remove());
        toastObj.show();
    }

    function renderHistoryRow(env) {
        const safe = (v) => (v || '').toString().replace(/</g, '&lt;').replace(/>/g, '&gt;');
        const modules = Array.isArray(env.modules) ? env.modules.join(', ') : '';
        const created = env.created_at ? new Date(env.created_at).toLocaleString() : '';
        const dbRaw = env.db_name || '';
        const dbLabel = safe(dbRaw);
        const dbAttr = dbRaw.replace(/"/g, '&quot;');
        const url = safe(env.url);
        const logUrl = dbRaw ? `/odoo/local_env/log/${encodeURIComponent(dbRaw)}` : '#';
        return `
            <tr>
                <td class="text-nowrap">${created}</td>
                <td>${dbLabel}</td>
                <td>${safe(env.odoo_version || '')}</td>
                <td>${safe(modules)}</td>
                <td class="text-end">
                    <a class="btn btn-link btn-sm" href="${url}" target="_blank" rel="noopener noreferrer">Open</a>
                    <a class="btn btn-outline-secondary btn-sm" href="${logUrl}" target="_blank" rel="noopener noreferrer">Log</a>
                    <button class="btn btn-outline-primary btn-sm" data-reopen-db="${dbAttr}">Re-open</button>
                    <button class="btn btn-outline-danger btn-sm" data-drop-db="${dbAttr}">Drop</button>
                </td>
            </tr>`;
    }

    async function handleOdooReopen(dbName) {
        if (!dbName) return;
        const logEl = document.getElementById('creation-log');
        const linkEl = document.getElementById('environment-link');
        try {
            const res = await fetch('/odoo/local_env/start', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ db_name: dbName })
            });
            const data = await parseJsonResponse(res);
            if (!res.ok) throw new Error(data.message || data.error || 'Failed to start environment');
            if (logEl) logEl.textContent = `${logEl.textContent || ''}\nReopened ${dbName}: ${data.url}`;
            const container = document.getElementById('environment-link-container');
            if (linkEl && container) {
                linkEl.href = data.url;
                linkEl.textContent = '🚀 Access Odoo Backend';
                container.style.display = 'block';
            }
            showToast(data.message || 'Environment started', 'success');
        } catch (err) {
            alert(err.message);
        }
    }

    async function handleOdooDrop(dbName) {
        if (!dbName) return;
        if (!confirm(`Drop database '${dbName}'? This cannot be undone.`)) return;
        try {
            const res = await fetch('/odoo/local_env/drop', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ db_name: dbName })
            });
            const data = await parseJsonResponse(res);
            if (!res.ok) throw new Error(data.message || data.error || 'Failed to drop database');
            showToast(data.message || 'Dropped', 'success');
            initOdooHistory();
        } catch (err) {
            showToast(err.message, 'danger');
        }
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

        // Example payload for local env creation
        const payload = {
            env_name: `odoo-brand-${odooVersion}`,
            github_repo_url: 'https://github.com/Yamkia/odoo-community-17.0.git', // Change as needed
            requirements_path: 'requirements.txt',
            env_files: [
                { filename: '.env', content: 'ODOO_VERSION=' + odooVersion + '\nBRANDING_MODULES=' + brandingModules.join(',') }
            ],
            branch: 'social'
        };
        showToast('Creating branded environment...', 'info');
        fetch('http://127.0.0.1:5001/odoo/create_local_env', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                creationLog.textContent = data.message;
                showToast(data.message || 'Branded environment created', 'success');
                // Prefer URL from backend; otherwise assume local Odoo on this laptop
                const targetUrl = data.url || 'http://localhost:8069';
                const link = document.getElementById('bm-environment-link');
                const container = document.getElementById('bm-environment-link-container');
                if (link && container) {
                    link.href = targetUrl;
                    container.style.display = 'block';
                }
                // Attempt to auto-open the environment UI in a new tab
                try {
                    window.open(targetUrl, '_blank');
                } catch (e) {
                    console.warn('Unable to auto-open environment UI:', e);
                }
            } else {
                const errMsg = data.message || data.error || 'Environment creation failed.';
                creationLog.textContent = `Error: ${errMsg}`;
                showToast(errMsg, 'danger');
            }
        })
        .catch(error => {
            const errMsg = error && error.message ? error.message : 'Network error';
            creationLog.textContent = `Error: ${errMsg}`;
            showToast(`Failed to create branded environment: ${errMsg}`, 'danger');
        });
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

        // Show immediate feedback to the user
        showToast('Environment creation initiated...','info');

        // Get the selected website design, if any
        const designInput = document.getElementById('website-design-input');
        const websiteDesign = designInput ? designInput.value : null;

        // Get optional DB name
        const dbInput = document.getElementById('odoo-dbname-input');
        const dbName = dbInput ? dbInput.value.trim() : '';

        // Get the selected Odoo version
        const versionInput = document.getElementById('odoo-version-input');
        const odooVersion = versionInput ? versionInput.value : '19.0'; // Default to 19.0

        // Theming inputs
        const brandName = (document.getElementById('brand-name-input')?.value || '').trim();
        const brandCode = (document.getElementById('brand-code-input')?.value || '').trim();
        const brandPrimary = document.getElementById('brand-primary-input')?.value || '';
        const brandSecondary = document.getElementById('brand-secondary-input')?.value || '';
        const brandLogo = (document.getElementById('brand-logo-input')?.value || '').trim();

        const brandPayload = (brandName || brandCode || brandPrimary || brandSecondary || brandLogo) ? {
            name: brandName || undefined,
            code: brandCode || undefined,
            primary_color: brandPrimary || undefined,
            secondary_color: brandSecondary || undefined,
            logo_url: brandLogo || undefined,
        } : undefined;

        // Ensure we have a module list; fall back to sensible defaults if none
        const modules = (Array.isArray(odooPlannedModules) && odooPlannedModules.length) ? [...odooPlannedModules] : ['base','web','website'];

        // The two required theme modules for this project
        const requiredThemes = ['deployable_brand_theme', 'bluewave_theme'];

        // If website module is part of the plan, ask the user to confirm adding the required themes
        if (modules.includes('website')) {
            // If any required theme is missing, prompt the user
            const missing = requiredThemes.filter(t => !modules.includes(t));
            if (missing.length > 0) {
                const humanNames = missing.join(', ');
                if (!confirm(`This environment requires the following themes: ${humanNames}. Add them to the modules list and proceed?`)) {
                    // User cancelled; re-enable execute button and stop
                    executeBtn.disabled = false;
                    document.getElementById('creation-status').style.display = 'none';
                    return;
                }
                // Add missing themes to modules and update UI list
                missing.forEach(t => {
                    if (!modules.includes(t)) modules.push(t);
                    const moduleList = document.getElementById('module-list');
                    if (moduleList && !Array.from(moduleList.children).some(li => li.textContent.trim() === t)) {
                        const li = document.createElement('li');
                        li.className = 'list-group-item';
                        li.textContent = t;
                        moduleList.appendChild(li);
                    }
                });
            }
        }

        if (brandPayload && !modules.includes('deployable_brand_theme')) {
            modules.push('deployable_brand_theme');
        }

        // Ask the Flask backend to create/start a local Odoo environment
        const payload = {
            odoo_version: odooVersion,
            modules,
            website_design: websiteDesign,
            db_name: dbName || undefined,
            brand: brandPayload,
            // Also send required themes as branding modules so the backend makes a best-effort to install them post-start
            branding_modules: requiredThemes.filter(t => modules.includes(t)),
        };
        // Use the job-based endpoint so the creation runs in background and we can show progress
        fetch('/odoo/execute', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        })
        .then(response => response.json())
        .then(data => {
            if (data && data.job_id) {
                creationLog.textContent = 'Environment creation started (background job).';
                showToast('Environment creation initiated...', 'info');
                // Poll job and show logs
                pollJobStatus(data.job_id);
            } else if (data && data.error) {
                const errMsg = data.message || data.error || 'Environment creation failed.';
                creationLog.textContent = `Error: ${errMsg}`;
                showToast(errMsg, 'danger');
            } else {
                const errMsg = 'Unexpected response from server.';
                creationLog.textContent = `Error: ${errMsg}`;
                showToast(errMsg, 'danger');
            }
        })
        .catch(error => {
            const errMsg = error && error.message ? error.message : 'Network error';
            creationLog.textContent = `Error: ${errMsg}`;
            showToast(`Failed to start environment: ${errMsg}`, 'danger');
        });
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
                            const linkEl = document.getElementById(`${prefix}environment-link`);
                            const containerEl = document.getElementById(`${prefix}environment-link-container`);
                            if (linkEl && containerEl) {
                                linkEl.href = data.url;
                                containerEl.style.display = 'block';
                            }
                            // Also try to automatically open the environment UI in a new tab
                            try {
                                window.open(data.url, '_blank');
                            } catch (e) {
                                console.warn('Unable to auto-open environment UI:', e);
                            }
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

    async function handleWebsiteAudit(formEl) {
        const resultEl = document.getElementById('website-helper-audit-result');
        if (!resultEl) return;
        const cssPath = formEl.querySelector('#css-path-input')?.value?.trim();
        resultEl.innerHTML = '<div class="alert alert-info">Auditing CSS...</div>';
        try {
            const response = await fetch('/website_helper/audit', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ css_path: cssPath })
            });
            const data = await response.json();
            if (!response.ok) {
                resultEl.innerHTML = `<div class="alert alert-danger">${data.message || 'Audit failed.'}</div>`;
                return;
            }
            const findingsHtml = (data.findings || []).map(f => `<li class="list-group-item d-flex justify-content-between"><span>${f.message}</span><span class="badge bg-${f.severity === 'warning' ? 'warning text-dark' : f.severity === 'success' ? 'success' : 'secondary'}">${f.severity}</span></li>`).join('');
            const suggested = data.suggested_css ? `<pre class="mt-3 p-3 bg-light border rounded" style="white-space: pre-wrap;">${data.suggested_css.replace(/</g, '&lt;')}</pre>` : '';
            resultEl.innerHTML = `
                <div class="alert alert-success mb-2">Scanned ${data.path || cssPath} (${data.line_count || '?'} lines)</div>
                <ul class="list-group">${findingsHtml}</ul>
                ${suggested}
            `;
        } catch (err) {
            resultEl.innerHTML = `<div class="alert alert-danger">Audit error: ${err.message}</div>`;
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
            const data = await response.json();
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

            const data = await response.json();
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

    async function handleWebsiteVisualAudit(formEl) {
        const resultEl = document.getElementById('website-helper-visual-result');
        if (!resultEl) return;
        const url = formEl.querySelector('#visual-url-input')?.value || '';
        resultEl.innerHTML = '<div class="alert alert-info">Running headless audit...</div>';
        try {
            const response = await fetch('/website_helper/visual_audit', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url })
            });
            const data = await response.json();
            if (!response.ok) {
                resultEl.innerHTML = `<div class="alert alert-danger">${data.message || 'Visual audit failed.'}</div>`;
                return;
            }

            const navInfo = data.nav && !data.nav.message
                ? `<div class="mt-2">Navbar height: ${data.nav.height || '?'} px<br/>Sample pills: ${(data.nav.pills || []).map(p => `${p.text || '(unnamed)'} (${p.height || '?'} px)`).join(', ')}</div>`
                : `<div class="mt-2 text-muted">${data.nav?.message || 'Navbar info unavailable.'}</div>`;

            const shot = data.screenshot ? `<div class="mt-3"><div class="alert alert-secondary mb-2">Screenshot saved at ${data.screenshot}</div><img src="/${data.screenshot}" alt="visual audit" class="img-fluid rounded border" /></div>` : '';

            resultEl.innerHTML = `
                <div class="alert alert-success">Visual audit completed.</div>
                ${navInfo}
                ${shot}
            `;
        } catch (err) {
            resultEl.innerHTML = `<div class="alert alert-danger">Visual audit error: ${err.message}</div>`;
        }
    }

    async function handleWebsiteInject(formEl) {
        const resultEl = document.getElementById('website-helper-inject-result');
        if (!resultEl) return;
        const css = formEl.querySelector('#inject-css-input')?.value || '';
        const targetPath = formEl.querySelector('#inject-target-input')?.value || '';
        const replace = formEl.querySelector('#inject-replace-toggle')?.checked || false;
        resultEl.innerHTML = '<div class="alert alert-info">Writing CSS...</div>';
        try {
            const response = await fetch('/website_helper/inject', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ css, target_path: targetPath, mode: replace ? 'replace' : 'append' })
            });
            const data = await response.json();
            if (!response.ok) {
                resultEl.innerHTML = `<div class="alert alert-danger">${data.message || 'Inject failed.'}</div>`;
                return;
            }
            resultEl.innerHTML = `<div class="alert alert-success">Injected into ${data.saved_path}</div>`;
        } catch (err) {
            resultEl.innerHTML = `<div class="alert alert-danger">Inject error: ${err.message}</div>`;
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
            const response = await fetch('/edit_app', {
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