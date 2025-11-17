// Instagram Suite JavaScript - Continuation
// Add this to handle content generation

// Content Generation Handlers
document.getElementById('image-post-form')?.addEventListener('submit', function(e) {
    e.preventDefault();
    const btn = this.querySelector('button[type="submit"]');
    const spinner = btn.querySelector('.spinner-border');
    
    spinner.style.display = 'inline-block';
    btn.disabled = true;
    
    const formData = {
        topic: document.getElementById('image-topic').value,
        style: document.getElementById('image-style').value,
        caption_hint: document.getElementById('image-caption-hint').value
    };
    
    fetch('/social/instagram/generate_image', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(formData)
    })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                showNotification('Error: ' + data.error, 'danger');
                return;
            }
            
            displayGeneratedImage(data);
            addToContentList('image', data);
            showNotification('✨ Image post generated!', 'success');
        })
        .catch(error => {
            console.error('Error:', error);
            showNotification('Failed to generate image', 'danger');
        })
        .finally(() => {
            spinner.style.display = 'none';
            btn.disabled = false;
        });
});

document.getElementById('reel-script-form')?.addEventListener('submit', function(e) {
    e.preventDefault();
    const btn = this.querySelector('button[type="submit"]');
    const spinner = btn.querySelector('.spinner-border');
    
    spinner.style.display = 'inline-block';
    btn.disabled = true;
    
    const formData = {
        topic: document.getElementById('reel-topic').value,
        length: document.getElementById('reel-length').value,
        tone: document.getElementById('reel-tone').value
    };
    
    fetch('/social/instagram/generate_reel_script', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(formData)
    })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                showNotification('Error: ' + data.error, 'danger');
                return;
            }
            
            displayReelScript(data);
            addToContentList('reel', data);
            showNotification('🎬 Reel script generated!', 'success');
        })
        .catch(error => {
            console.error('Error:', error);
            showNotification('Failed to generate reel script', 'danger');
        })
        .finally(() => {
            spinner.style.display = 'none';
            btn.disabled = false;
        });
});

function displayGeneratedImage(data) {
    const preview = document.getElementById('image-preview');
    preview.innerHTML = `
        <div class="card border-success">
            <div class="card-header bg-success text-white">
                <strong>✅ Generated Image Post</strong>
            </div>
            <div class="card-body">
                <div class="mb-3">
                    <img src="${data.image_url}" class="img-fluid rounded" alt="Generated post" 
                         onerror="this.src='data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 width=%22400%22 height=%22400%22%3E%3Crect fill=%22%23ddd%22 width=%22400%22 height=%22400%22/%3E%3Ctext fill=%22%23999%22 x=%2250%25%22 y=%2250%25%22 text-anchor=%22middle%22 dy=%22.3em%22 font-size=%2224%22%3E${data.style} Post%3C/text%3E%3C/svg%3E'">
                </div>
                <h6>Caption:</h6>
                <p class="text-muted small">${data.caption}</p>
                <h6>Hashtags:</h6>
                <p class="small">${data.hashtags.join(' ')}</p>
                <p class="text-muted small"><strong>Best posting time:</strong> ${data.best_posting_time}</p>
                <button class="btn btn-sm btn-primary" onclick="copyToClipboard('${data.caption.replace(/'/g, "\\'")}')">
                    📋 Copy Caption
                </button>
            </div>
        </div>
    `;
    preview.style.display = 'block';
}

function displayReelScript(data) {
    const output = document.getElementById('reel-script-output');
    output.innerHTML = `
        <div class="card border-danger">
            <div class="card-header bg-danger text-white">
                <strong>✅ Generated Reel Script</strong>
            </div>
            <div class="card-body">
                <h6>🎯 Hook:</h6>
                <p class="fw-bold">${data.hook}</p>
                
                <h6>📝 Script:</h6>
                <p class="text-muted small" style="white-space: pre-line;">${data.script}</p>
                
                <h6>💡 Call to Action:</h6>
                <p class="fw-bold">${data.cta}</p>
                
                <h6>🎵 Hashtags:</h6>
                <p class="small">${data.hashtags.join(' ')}</p>
                
                ${data.tips ? `
                    <h6>💫 Pro Tips:</h6>
                    <ul class="small">
                        ${data.tips.map(tip => `<li>${tip}</li>`).join('')}
                    </ul>
                ` : ''}
                
                <button class="btn btn-sm btn-danger" onclick="copyToClipboard('${(data.hook + '\\n\\n' + data.script + '\\n\\n' + data.cta).replace(/'/g, "\\'")}')">
                    📋 Copy Script
                </button>
            </div>
        </div>
    `;
    output.style.display = 'block';
}

let generatedContent = [];

function addToContentList(type, data) {
    const timestamp = new Date().toLocaleString();
    generatedContent.push({ type, data, timestamp });
    
    const listContainer = document.getElementById('generated-content-list');
    const icon = type === 'image' ? '🖼️' : '🎬';
    const title = type === 'image' ? data.topic : data.topic || 'Reel Script';
    
    if (generatedContent.length === 1) {
        listContainer.innerHTML = ''; // Clear placeholder
    }
    
    const itemHtml = `
        <div class="list-group-item">
            <div class="d-flex justify-content-between align-items-start">
                <div>
                    <h6 class="mb-1">${icon} ${title}</h6>
                    <small class="text-muted">${timestamp}</small>
                </div>
                <span class="badge bg-${type === 'image' ? 'primary' : 'danger'}">${type.toUpperCase()}</span>
            </div>
        </div>
    `;
    
    listContainer.insertAdjacentHTML('beforeend', itemHtml);
}

function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        showNotification('📋 Copied to clipboard!', 'success');
    }).catch(err => {
        showNotification('Failed to copy', 'danger');
    });
}

// Logout handler
document.getElementById('ig-logout-btn')?.addEventListener('click', function() {
    if (confirm('Are you sure you want to logout?')) {
        fetch('/auth/instagram/logout', { method: 'POST' })
            .then(() => {
                location.reload();
            });
    }
});

// Refresh data button
document.getElementById('refresh-data-btn')?.addEventListener('click', function() {
    showNotification('🔄 Refreshing data...', 'info');
    fetchInstagramAccountData();
});

// Check session when opening Instagram tool
document.getElementById('show-instagram-manager')?.addEventListener('click', function() {
    setTimeout(() => checkInstagramSession(), 100);
});
