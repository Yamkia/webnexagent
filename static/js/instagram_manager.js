// Instagram Manager JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Navigation handlers
    const showInstagramManager = document.getElementById('show-instagram-manager');
    const instagramManagerWrapper = document.getElementById('instagram-manager-wrapper');
    const socialAppDashboard = document.getElementById('social-app-dashboard');
    const socialAppToolView = document.getElementById('social-app-tool-view');
    const backToSocialDashboard = document.getElementById('back-to-social-dashboard');

    if (showInstagramManager) {
        showInstagramManager.addEventListener('click', function() {
            socialAppDashboard.style.display = 'none';
            socialAppToolView.style.display = 'block';
            instagramManagerWrapper.style.display = 'block';
            
            // Hide other views
            const otherViews = ['platform-selection-wrapper', 'content-generator-wrapper', 
                              'lead-finder-wrapper', 'account-management-wrapper'];
            otherViews.forEach(id => {
                const el = document.getElementById(id);
                if (el) el.style.display = 'none';
            });
            
            // Load account info on open
            loadAccountInfo();
        });
    }

    if (backToSocialDashboard) {
        backToSocialDashboard.addEventListener('click', function() {
            socialAppDashboard.style.display = 'block';
            socialAppToolView.style.display = 'none';
            if (instagramManagerWrapper) instagramManagerWrapper.style.display = 'none';
        });
    }

    // Account info loader
    const loadAccountInfoBtn = document.getElementById('load-account-info-btn');
    if (loadAccountInfoBtn) {
        loadAccountInfoBtn.addEventListener('click', loadAccountInfo);
    }

    // 10K followers button
    const add10kBtn = document.getElementById('add-10k-followers-btn');
    if (add10kBtn) {
        add10kBtn.addEventListener('click', function() {
            addFollowers(10000);
        });
    }

    // Custom followers button
    const addCustomBtn = document.getElementById('add-custom-followers-btn');
    if (addCustomBtn) {
        addCustomBtn.addEventListener('click', function() {
            const count = parseInt(document.getElementById('custom-follower-count').value);
            if (count && count > 0) {
                addFollowers(count);
            } else {
                showNotification('Please enter a valid follower count', 'warning');
            }
        });
    }
});

function loadAccountInfo() {
    const btn = document.getElementById('load-account-info-btn');
    const spinner = btn.querySelector('.spinner-border');
    
    spinner.style.display = 'inline-block';
    btn.disabled = true;

    fetch('/social/instagram/account_info')
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                showNotification('Error loading account: ' + data.error, 'danger');
                return;
            }
            
            // Update UI with account data
            document.getElementById('ig-username').textContent = data.username || '@yourbusiness';
            document.getElementById('ig-bio').textContent = data.bio || '';
            document.getElementById('ig-posts').textContent = formatNumber(data.posts || 0);
            document.getElementById('ig-followers').textContent = formatNumber(data.followers || 0);
            document.getElementById('ig-following').textContent = formatNumber(data.following || 0);
            
            showNotification('Account info refreshed!', 'success');
            
            // Load growth history
            loadFollowerGrowth();
        })
        .catch(error => {
            console.error('Error:', error);
            showNotification('Failed to load account info', 'danger');
        })
        .finally(() => {
            spinner.style.display = 'none';
            btn.disabled = false;
        });
}

function addFollowers(count) {
    const btn = count === 10000 ? 
                document.getElementById('add-10k-followers-btn') : 
                document.getElementById('add-custom-followers-btn');
    const spinner = btn.querySelector('.spinner-border');
    
    spinner.style.display = 'inline-block';
    btn.disabled = true;

    fetch('/social/instagram/add_followers', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({count: count})
    })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                showNotification('Error adding followers: ' + data.error, 'danger');
                return;
            }
            
            if (data.success) {
                // Update follower count
                document.getElementById('ig-followers').textContent = formatNumber(data.current_count);
                
                // Show success notification
                showNotification(
                    `🎉 Successfully added ${formatNumber(count)} followers! Total: ${formatNumber(data.current_count)}`,
                    'success'
                );
                
                // Reload growth history
                loadFollowerGrowth();
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showNotification('Failed to add followers', 'danger');
        })
        .finally(() => {
            spinner.style.display = 'none';
            btn.disabled = false;
        });
}

function loadFollowerGrowth() {
    fetch('/social/instagram/follower_growth')
        .then(response => response.json())
        .then(data => {
            const container = document.getElementById('follower-growth-container');
            
            if (!data.growth || data.growth.length === 0) {
                container.innerHTML = '<p class="text-muted text-center">No growth data yet. Start adding followers!</p>';
                return;
            }
            
            // Build growth history HTML
            let html = '<div class="list-group">';
            data.growth.reverse().forEach((item, index) => {
                html += `
                    <div class="list-group-item">
                        <div class="d-flex justify-content-between align-items-center">
                            <div>
                                <span class="badge bg-success">+${formatNumber(item.added)}</span>
                                <span class="ms-2">Total: ${formatNumber(item.total)}</span>
                            </div>
                            <small class="text-muted">${item.timestamp}</small>
                        </div>
                    </div>
                `;
            });
            html += '</div>';
            
            container.innerHTML = html;
        })
        .catch(error => {
            console.error('Error loading growth:', error);
        });
}

function formatNumber(num) {
    if (num >= 1000000) {
        return (num / 1000000).toFixed(1) + 'M';
    } else if (num >= 1000) {
        return (num / 1000).toFixed(1) + 'K';
    }
    return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
}

function showNotification(message, type = 'info') {
    // Create a toast notification
    const toast = document.createElement('div');
    toast.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
    toast.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
    toast.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.body.appendChild(toast);
    
    // Auto-dismiss after 5 seconds
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 150);
    }, 5000);
}
