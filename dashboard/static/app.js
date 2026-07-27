document.addEventListener('DOMContentLoaded', () => {
    fetchReviews();
    checkAutonomousStatus();
    pollSystemHealth();
    setInterval(pollSystemHealth, 10000);
    
    // Autonomous Toggle logic
    document.getElementById('autonomous-toggle').addEventListener('change', async (e) => {
        const isEnabled = e.target.checked;
        try {
            const res = await fetch('/api/autonomous/toggle', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({enabled: isEnabled})
            });
            if (!res.ok) throw new Error('Toggle failed');
        } catch (error) {
            console.error('Error toggling autonomous mode:', error);
            e.target.checked = !isEnabled; // revert UI on failure
            alert('Failed to switch Autonomous mode.');
        }
    });

    const tabs = ['pending', 'published', 'approved', 'rejected', 'analytics', 'discovered'];
    function switchTab(navId) {
        tabs.forEach(t => {
            const navEl = document.getElementById(`nav-${t}`);
            if (navEl) navEl.classList.remove('active');
            
            const container = document.getElementById(t === 'pending' ? 'cards-container' : (t === 'approved' || t === 'rejected' ? 'history-container' : `${t}-container`));
            if(container) container.classList.add('hidden');
        });
        
        const activeNavEl = document.getElementById(`nav-${navId}`);
        if (activeNavEl) activeNavEl.classList.add('active');
        
        const activeContainer = document.getElementById(navId === 'pending' ? 'cards-container' : (navId === 'approved' || navId === 'rejected' ? 'history-container' : `${navId}-container`));
        if(activeContainer) activeContainer.classList.remove('hidden');
        
        const headerStats = document.getElementById('header-stats');
        if (headerStats) {
            headerStats.style.display = navId === 'pending' ? 'block' : 'none';
        }
    }

    document.getElementById('nav-pending').addEventListener('click', (e) => {
        e.preventDefault();
        switchTab('pending');
        document.getElementById('page-title').textContent = 'AI Draft Reviews';
        document.getElementById('page-subtitle').textContent = 'Review, edit, and approve AI-generated drafts before they are published.';
        fetchReviews();
    });

    document.getElementById('nav-published').addEventListener('click', (e) => {
        e.preventDefault();
        switchTab('published');
        document.getElementById('page-title').textContent = 'Live Backlinks';
        document.getElementById('page-subtitle').textContent = 'Successfully published articles and comments across all platforms.';
        fetchPublishedLinks();
    });
    
    document.getElementById('nav-approved').addEventListener('click', (e) => {
        e.preventDefault();
        switchTab('approved');
        document.getElementById('page-title').textContent = 'Approved History';
        document.getElementById('page-subtitle').textContent = 'Drafts that were approved and sent to the posting queue.';
        fetchHistory('approved');
    });

    document.getElementById('nav-rejected').addEventListener('click', (e) => {
        e.preventDefault();
        switchTab('rejected');
        document.getElementById('page-title').textContent = 'Rejected History';
        document.getElementById('page-subtitle').textContent = 'Drafts that were rejected and archived.';
        fetchHistory('rejected');
    });

    document.getElementById('nav-discovered').addEventListener('click', (e) => {
        e.preventDefault();
        switchTab('discovered');
        document.getElementById('page-title').textContent = 'Discovered Sites';
        document.getElementById('page-subtitle').textContent = 'Review AI-parsed unknown domains to activate them for posting.';
        fetchDiscoveredSites();
    });

    document.getElementById('nav-analytics').addEventListener('click', (e) => {
        e.preventDefault();
        switchTab('analytics');
        document.getElementById('page-title').textContent = 'Analytics Dashboard';
        document.getElementById('page-subtitle').textContent = 'High-level metrics on AI generation and publication success.';
        fetchAnalytics();
    });
});

async function fetchPublishedLinks() {
    const grid = document.getElementById('published-grid');
    const loading = document.getElementById('published-loading');
    
    grid.innerHTML = '';
    loading.classList.remove('hidden');
    
    try {
        const response = await fetch('/api/published');
        const data = await response.json();
        const links = data.published || [];
        
        loading.classList.add('hidden');
        
        if (links.length === 0) {
            grid.innerHTML = '<div style="grid-column: 1/-1; text-align:center; padding: 3rem; color: #8b92a5;">No live backlinks yet. Start approving drafts!</div>';
            return;
        }

        links.forEach((link, index) => {
            const card = document.createElement('div');
            card.className = 'review-card';
            card.style.animationDelay = `${index * 0.05}s`;
            
            const date = new Date(link.posted_at).toLocaleString();
            
            card.innerHTML = `
                <div class="card-header">
                    <span class="platform-badge">${link.platform}</span>
                    <span style="color: #8b92a5; font-size: 0.8rem;">${date}</span>
                </div>
                <div style="padding: 1rem 0;">
                    <h4 style="margin:0 0 0.5rem 0; color: #fff;">${link.title || 'Untitled Post'}</h4>
                    <a href="${link.url}" target="_blank" class="thread-link" style="display: inline-block; padding: 0.5rem 1rem; background: rgba(56, 189, 248, 0.1); border-radius: 4px; margin-top: 0.5rem;">View Live Post ↗</a>
                </div>
            `;
            grid.appendChild(card);
        });

    } catch (error) {
        console.error('Error:', error);
        loading.classList.add('hidden');
        grid.innerHTML = '<p style="color: #ef4444;">Failed to load live backlinks.</p>';
    }
}
async function fetchReviews() {
    const container = document.getElementById('cards-container');
    const loading = document.getElementById('loading-state');
    
    try {
        const response = await fetch('/api/reviews');
        const data = await response.json();
        
        const reviews = data.reviews || [];
        document.getElementById('pending-count').textContent = reviews.length;
        
        loading.style.display = 'none';
        container.innerHTML = '';
        
        if (reviews.length === 0) {
            container.innerHTML = '<div style="text-align:center; padding: 3rem; color: #8b92a5;">No pending reviews in the queue! 🎉</div>';
            return;
        }

        reviews.forEach((review, index) => {
            const card = createCard(review, index);
            container.appendChild(card);
        });

    } catch (error) {
        console.error('Error fetching reviews:', error);
        loading.innerHTML = '<p style="color: #ef4444;">Failed to load reviews. Is the backend running?</p>';
    }
}

function createCard(review, index) {
    const card = document.createElement('div');
    card.className = 'review-card';
    card.style.animationDelay = `${index * 0.1}s`;
    
    card.innerHTML = `
        <div class="card-header">
            <span class="platform-badge">${review.platform}</span>
            <a href="${review.url}" target="_blank" class="thread-link">View Original Thread ↗</a>
        </div>
        
        <div class="draft-section">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.75rem;">
                <div class="draft-label" style="margin-bottom: 0;">AI Drafted Comment</div>
                <button onclick="openFullView('${review.thread_id}')" style="background: rgba(56, 189, 248, 0.1); border: 1px solid rgba(56, 189, 248, 0.2); color: #38bdf8; padding: 0.3rem 0.8rem; border-radius: 4px; cursor: pointer; font-size: 0.8rem; display: flex; align-items: center; gap: 5px;">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 3 21 3 21 9"></polyline><polyline points="9 21 3 21 3 15"></polyline><line x1="21" y1="3" x2="14" y2="10"></line><line x1="3" y1="21" x2="10" y2="14"></line></svg>
                    Full View
                </button>
            </div>
            <textarea class="draft-textarea" id="draft-${review.thread_id}">${review.drafted_comment}</textarea>
        </div>
        
        <div class="card-actions">
            <button class="btn-approve" onclick="handleAction('${review.thread_id}', 'approve')">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>
                Approve & Post
            </button>
            <button class="btn-rewrite" onclick="handleAction('${review.thread_id}', 'rewrite')">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.59-9.21l5.67-5.67"/></svg>
                Rewrite
            </button>
            <button class="btn-reject" onclick="handleAction('${review.thread_id}', 'reject')">
                Reject
            </button>
        </div>
    `;
    
    return card;
}

async function handleAction(threadId, action) {
    const textarea = document.getElementById(`draft-${threadId}`);
    const finalComment = textarea.value;
    
    // Optimistic UI update
    const card = textarea.closest('.review-card');
    card.style.opacity = '0.5';
    card.style.pointerEvents = 'none';

    try {
        const response = await fetch(`/api/reviews/${action}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                thread_id: threadId,
                final_comment: finalComment,
                feedback: action === 'rewrite' ? 'Needs adjustment' : null
            })
        });

        if (response.ok) {
            // Remove card from DOM
            card.style.transition = 'all 0.3s ease';
            card.style.transform = 'scale(0.95)';
            card.style.opacity = '0';
            
            setTimeout(() => {
                card.remove();
                // Update count
                const countEl = document.getElementById('pending-count');
                countEl.textContent = Math.max(0, parseInt(countEl.textContent) - 1);
                
                // Show empty state if needed
                if (document.querySelectorAll('.review-card').length === 0) {
                    document.getElementById('cards-container').innerHTML = '<div style="text-align:center; padding: 3rem; color: #8b92a5;">No pending reviews in the queue! 🎉</div>';
                }
            }, 300);
        } else {
            alert('Action failed. Please try again.');
            card.style.opacity = '1';
            card.style.pointerEvents = 'auto';
        }
    } catch (error) {
        console.error(`Error performing ${action}:`, error);
        alert('Network error. Please try again.');
        card.style.opacity = '1';
        card.style.pointerEvents = 'auto';
    }
}

async function checkAutonomousStatus() {
    try {
        const res = await fetch('/api/autonomous/status');
        const data = await res.json();
        document.getElementById('autonomous-toggle').checked = data.enabled;
    } catch(e) {
        console.error("Failed to fetch autonomous status", e);
    }
}

async function pollSystemHealth() {
    try {
        const res = await fetch('/api/health');
        const health = await res.json();
        
        const dbDot = document.getElementById('status-db');
        if (health.postgres) { dbDot.className = 'status-dot green'; } 
        else { dbDot.className = 'status-dot red'; }
        
        const redisDot = document.getElementById('status-redis');
        if (health.redis) { redisDot.className = 'status-dot green'; } 
        else { redisDot.className = 'status-dot red'; }
        
    } catch (error) {
        document.getElementById('status-db').className = 'status-dot red';
        document.getElementById('status-redis').className = 'status-dot red';
    }
}

async function fetchHistory(status) {
    const grid = document.getElementById('history-grid');
    const loading = document.getElementById('history-loading');
    
    grid.innerHTML = '';
    loading.classList.remove('hidden');
    
    try {
        const response = await fetch(`/api/history/${status}`);
        const data = await response.json();
        const items = data.history || [];
        
        loading.classList.add('hidden');
        
        if (items.length === 0) {
            grid.innerHTML = `<div style="grid-column: 1/-1; text-align:center; padding: 3rem; color: #8b92a5;">No ${status} items found.</div>`;
            return;
        }

        items.forEach((item, index) => {
            const card = document.createElement('div');
            card.className = 'review-card';
            card.style.animationDelay = `${index * 0.05}s`;
            
            const date = item.updated_at ? new Date(item.updated_at).toLocaleString() : 'N/A';
            const statusColor = status === 'approved' ? '#10b981' : '#ef4444';
            
            card.innerHTML = `
                <div class="card-header">
                    <span class="platform-badge">${item.platform}</span>
                    <span style="color: ${statusColor}; font-weight: bold; text-transform: capitalize;">${status}</span>
                </div>
                <div style="padding: 1rem 0;">
                    <h4 style="margin:0 0 0.5rem 0; color: #fff;">${item.title || 'Untitled Post'}</h4>
                    <p style="color: #8b92a5; font-size: 0.8rem; margin-bottom: 0.5rem;">Updated: ${date}</p>
                    <a href="${item.url}" target="_blank" class="thread-link" style="font-size: 0.8rem;">Original Source ↗</a>
                </div>
            `;
            grid.appendChild(card);
        });

    } catch (error) {
        console.error('Error:', error);
        loading.classList.add('hidden');
        grid.innerHTML = '<p style="color: #ef4444;">Failed to load history.</p>';
    }
}

let platformChartInstance = null;

async function fetchAnalytics() {
    try {
        const res = await fetch('/api/analytics');
        const stats = await res.json();
        
        document.getElementById('stat-discovered').textContent = stats.total_discovered || 0;
        document.getElementById('stat-approved').textContent = stats.total_approved || 0;
        document.getElementById('stat-rejected').textContent = stats.total_rejected || 0;
        document.getElementById('stat-published').textContent = stats.total_published || 0;
        
        // Render Chart
        const ctx = document.getElementById('platformChart').getContext('2d');
        
        const labels = Object.keys(stats.platform_breakdown || {});
        const data = Object.values(stats.platform_breakdown || {});
        
        if (platformChartInstance) {
            platformChartInstance.destroy();
        }
        
        platformChartInstance = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels.length > 0 ? labels : ['No Data'],
                datasets: [{
                    label: 'Successful Posts by Platform',
                    data: data.length > 0 ? data : [0],
                    backgroundColor: 'rgba(139, 92, 246, 0.5)',
                    borderColor: 'rgba(139, 92, 246, 1)',
                    borderWidth: 1,
                    borderRadius: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { labels: { color: '#f3f4f6' } }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: { color: '#9ca3af', stepSize: 1 },
                        grid: { color: 'rgba(255,255,255,0.05)' }
                    },
                    x: {
                        ticks: { color: '#9ca3af' },
                        grid: { display: false }
                    }
                }
            }
        });
        
    } catch(e) {
        console.error("Failed to load analytics", e);
    }
}

async function fetchDiscoveredSites() {
    const grid = document.getElementById('discovered-grid');
    const loading = document.getElementById('discovered-loading');
    
    grid.innerHTML = '';
    loading.classList.remove('hidden');
    
    try {
        const response = await fetch('/api/discovered_platforms');
        const data = await response.json();
        const sites = data.platforms || [];
        
        loading.classList.add('hidden');
        
        if (sites.length === 0) {
            grid.innerHTML = '<div style="grid-column: 1/-1; text-align:center; padding: 3rem; color: #8b92a5;">No new sites discovered yet.</div>';
            return;
        }

        sites.forEach((site, index) => {
            const card = document.createElement('div');
            card.className = 'review-card';
            card.style.animationDelay = `${index * 0.05}s`;
            
            card.innerHTML = `
                <div class="card-header">
                    <span class="platform-badge">${site.domain}</span>
                    <a href="${site.sample_url}" target="_blank" class="thread-link">Sample URL ↗</a>
                </div>
                <div style="padding: 1rem 0;">
                    <h4 style="margin:0 0 0.5rem 0; color: #fff;">AI Analysis Summary</h4>
                    <p style="color: #cbd5e1; font-size: 0.9rem; line-height: 1.5; margin-bottom: 1rem;">${site.ai_summary || 'No summary available.'}</p>
                </div>
                <div class="card-actions">
                    <button class="btn-approve" onclick="handleDiscoveredAction('${site.id}', 'approve')">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>
                        Approve Target
                    </button>
                    <button class="btn-reject" onclick="handleDiscoveredAction('${site.id}', 'reject')">
                        Reject
                    </button>
                </div>
            `;
            grid.appendChild(card);
        });

    } catch (error) {
        console.error('Error:', error);
        loading.classList.add('hidden');
        grid.innerHTML = '<p style="color: #ef4444;">Failed to load discovered sites.</p>';
    }
}

async function handleDiscoveredAction(siteId, action) {
    try {
        const response = await fetch(`/api/discovered_platforms/${action}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ id: siteId })
        });
        
        if (response.ok) {
            fetchDiscoveredSites();
        } else {
            alert('Action failed. Please try again.');
        }
    } catch (error) {
        console.error('Error action:', error);
        alert('Network error.');
    }
}
