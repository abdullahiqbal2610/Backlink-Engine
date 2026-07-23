// ==========================================
// INIT
// ==========================================
document.addEventListener('DOMContentLoaded', () => {
    fetchReviews();
    checkAutonomousStatus();
    pollSystemHealth();
    pollJobStatus();
    setInterval(pollSystemHealth, 10000);
    setInterval(pollJobStatus, 20000);

    // Autonomous Toggle
    document.getElementById('autonomous-toggle').addEventListener('change', async (e) => {
        const isEnabled = e.target.checked;
        try {
            const res = await fetch('/api/autonomous/toggle', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({enabled: isEnabled})
            });
            if (!res.ok) throw new Error('Toggle failed');
        } catch (err) {
            console.error(err);
            e.target.checked = !isEnabled;
            alert('Failed to switch Autopilot mode.');
        }
    });

    // File input display name
    document.getElementById('cookie-file').addEventListener('change', (e) => {
        const name = e.target.files[0]?.name || 'No file selected';
        document.getElementById('selected-file-name').textContent = name;
    });

    // Tab switching
    setupNavTabs();
});

function setupNavTabs() {
    const navMap = {
        'nav-pending':   { container: 'cards-container',    title: 'AI Draft Reviews',     subtitle: 'Review, edit, and approve AI-generated drafts before they are published.', load: fetchReviews },
        'nav-published': { container: 'published-container', title: 'Live Backlinks',        subtitle: 'Successfully published articles across all platforms.', load: fetchPublishedLinks },
        'nav-approved':  { container: 'history-container',   title: 'Approved History',      subtitle: 'Drafts that were approved and sent to the posting queue.', load: () => fetchHistory('approved') },
        'nav-rejected':  { container: 'history-container',   title: 'Rejected History',      subtitle: 'Drafts that were rejected and archived.', load: () => fetchHistory('rejected') },
        'nav-analytics': { container: 'analytics-container', title: 'Analytics Dashboard',   subtitle: 'High-level metrics on AI generation and publication success.', load: fetchAnalytics },
        'nav-logs':      { container: 'logs-container',      title: 'Live Cloud Run Logs',   subtitle: 'Real-time logs from Discovery, LLM, and Posting jobs.', load: fetchLogs },
    };

    const allContainers = [...new Set(Object.values(navMap).map(v => v.container))];

    Object.entries(navMap).forEach(([navId, config]) => {
        document.getElementById(navId).addEventListener('click', (e) => {
            e.preventDefault();

            // Deactivate all nav items
            Object.keys(navMap).forEach(id => document.getElementById(id).classList.remove('active'));
            // Hide all containers
            allContainers.forEach(id => document.getElementById(id)?.classList.add('hidden'));
            // Activate
            document.getElementById(navId).classList.add('active');
            document.getElementById(config.container).classList.remove('hidden');
            document.getElementById('page-title').textContent = config.title;
            document.getElementById('page-subtitle').textContent = config.subtitle;
            document.getElementById('header-stats').style.display = navId === 'nav-pending' ? 'block' : 'none';

            config.load();
        });
    });
}

// ==========================================
// PENDING REVIEWS
// ==========================================
async function fetchReviews() {
    const container = document.getElementById('cards-container');
    const loading = document.getElementById('loading-state');

    try {
        const response = await fetch('/api/reviews');
        const data = await response.json();
        const reviews = data.reviews || [];

        document.getElementById('pending-count').textContent = reviews.length;
        document.getElementById('pending-badge').textContent = reviews.length;

        loading.style.display = 'none';
        container.innerHTML = '';

        if (reviews.length === 0) {
            container.innerHTML = '<div style="text-align:center; padding:4rem; color:#64748b; font-size:0.95rem;">No pending reviews in the queue! 🎉<br><small style="color:#334155">Run Discovery to generate new drafts.</small></div>';
            return;
        }

        reviews.forEach((review, index) => {
            container.appendChild(createCard(review, index));
        });

    } catch (error) {
        console.error('Error fetching reviews:', error);
        loading.innerHTML = '<p style="color:#ef4444">Failed to load reviews. Is the backend running?</p>';
    }
}

function createCard(review, index) {
    const card = document.createElement('div');
    card.className = 'review-card';
    card.style.animationDelay = `${index * 0.08}s`;

    // Give platform badge a class for color
    const platformClass = review.platform?.toLowerCase().replace('_', '') || '';

    card.innerHTML = `
        <div class="card-header">
            <span class="platform-badge ${platformClass}">${review.platform || 'unknown'}</span>
            <a href="${review.url}" target="_blank" class="thread-link">View Original Thread ↗</a>
        </div>

        <div class="draft-section">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.6rem;">
                <div class="draft-label">AI Drafted Comment</div>
                <button onclick="openFullView('${review.thread_id}')" style="background:rgba(56,189,248,0.1); border:1px solid rgba(56,189,248,0.2); color:#38bdf8; padding:0.25rem 0.7rem; border-radius:5px; cursor:pointer; font-size:0.78rem; display:flex; align-items:center; gap:5px;">
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="15 3 21 3 21 9"/><polyline points="9 21 3 21 3 15"/><line x1="21" y1="3" x2="14" y2="10"/><line x1="3" y1="21" x2="10" y2="14"/></svg>
                    Full View
                </button>
            </div>
            <textarea class="draft-textarea" id="draft-${review.thread_id}">${review.drafted_comment || ''}</textarea>
        </div>

        <div class="card-actions">
            <button class="btn-approve" onclick="handleAction('${review.thread_id}', 'approve')">
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>
                Approve &amp; Post
            </button>
            <button class="btn-rewrite" onclick="handleAction('${review.thread_id}', 'rewrite')">
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.59-9.21"/></svg>
                Rewrite
            </button>
            <button class="btn-reject" onclick="handleAction('${review.thread_id}', 'reject')">Reject</button>
        </div>
    `;

    return card;
}

async function handleAction(threadId, action) {
    const textarea = document.getElementById(`draft-${threadId}`);
    const finalComment = textarea?.value || '';
    const card = textarea?.closest('.review-card');

    if (card) { card.style.opacity = '0.5'; card.style.pointerEvents = 'none'; }

    try {
        const res = await fetch(`/api/reviews/${action}`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ thread_id: threadId, final_comment: finalComment, feedback: action === 'rewrite' ? 'Needs adjustment' : null })
        });

        if (res.ok) {
            if (card) {
                card.style.transition = 'all 0.3s ease';
                card.style.transform = 'scale(0.96)';
                card.style.opacity = '0';
                setTimeout(() => {
                    card.remove();
                    const countEl = document.getElementById('pending-count');
                    const badgeEl = document.getElementById('pending-badge');
                    const newCount = Math.max(0, parseInt(countEl.textContent) - 1);
                    countEl.textContent = newCount;
                    badgeEl.textContent = newCount;
                    if (document.querySelectorAll('.review-card').length === 0) {
                        document.getElementById('cards-container').innerHTML = '<div style="text-align:center;padding:4rem;color:#64748b;">All reviews processed! 🎉</div>';
                    }
                }, 300);
            }
        } else {
            alert('Action failed. Please try again.');
            if (card) { card.style.opacity = '1'; card.style.pointerEvents = 'auto'; }
        }
    } catch (err) {
        console.error(err);
        alert('Network error. Please try again.');
        if (card) { card.style.opacity = '1'; card.style.pointerEvents = 'auto'; }
    }
}

// ==========================================
// FULL VIEW MODAL
// ==========================================
let fullViewThreadId = null;

function openFullView(threadId) {
    fullViewThreadId = threadId;
    const textarea = document.getElementById(`draft-${threadId}`);
    document.getElementById('fullViewTextarea').value = textarea?.value || '';
    document.getElementById('fullViewModal').classList.remove('hidden');
}

function closeFullView() {
    document.getElementById('fullViewModal').classList.add('hidden');
    fullViewThreadId = null;
}

function saveFullView() {
    if (!fullViewThreadId) return;
    const newContent = document.getElementById('fullViewTextarea').value;
    const textarea = document.getElementById(`draft-${fullViewThreadId}`);
    if (textarea) textarea.value = newContent;
    closeFullView();
}

// ==========================================
// PUBLISHED LINKS
// ==========================================
async function fetchPublishedLinks() {
    const grid = document.getElementById('published-grid');
    const loading = document.getElementById('published-loading');
    grid.innerHTML = '';
    loading.classList.remove('hidden');

    try {
        const res = await fetch('/api/published');
        const data = await res.json();
        const links = data.published || [];
        loading.classList.add('hidden');

        if (links.length === 0) {
            grid.innerHTML = '<div style="grid-column:1/-1;text-align:center;padding:3rem;color:#64748b;">No live backlinks yet. Start approving drafts!</div>';
            return;
        }

        links.forEach((link, i) => {
            const card = document.createElement('div');
            card.className = 'review-card';
            card.style.animationDelay = `${i * 0.05}s`;
            const date = link.posted_at ? new Date(link.posted_at).toLocaleString() : 'N/A';
            const platformClass = link.platform?.toLowerCase().replace('_','') || '';
            card.innerHTML = `
                <div class="card-header">
                    <span class="platform-badge ${platformClass}">${link.platform}</span>
                    <span style="color:#64748b;font-size:0.78rem;">${date}</span>
                </div>
                <h4 style="margin:0.5rem 0 0.75rem;color:#e2e8f0;font-size:0.9rem;">${link.title || 'Published Post'}</h4>
                <a href="${link.url}" target="_blank" class="thread-link" style="font-size:0.82rem;">View Live Post ↗</a>
            `;
            grid.appendChild(card);
        });
    } catch (err) {
        loading.classList.add('hidden');
        grid.innerHTML = '<p style="color:#ef4444">Failed to load live backlinks.</p>';
    }
}

// ==========================================
// HISTORY
// ==========================================
async function fetchHistory(status) {
    const grid = document.getElementById('history-grid');
    const loading = document.getElementById('history-loading');
    grid.innerHTML = '';
    loading.classList.remove('hidden');

    try {
        const res = await fetch(`/api/history/${status}`);
        const data = await res.json();
        const items = data.history || [];
        loading.classList.add('hidden');

        if (items.length === 0) {
            grid.innerHTML = `<div style="grid-column:1/-1;text-align:center;padding:3rem;color:#64748b;">No ${status} items found.</div>`;
            return;
        }

        items.forEach((item, i) => {
            const card = document.createElement('div');
            card.className = 'review-card';
            card.style.animationDelay = `${i * 0.05}s`;
            const date = item.updated_at ? new Date(item.updated_at).toLocaleString() : 'N/A';
            const statusColor = status === 'approved' ? '#10b981' : '#ef4444';
            const platformClass = item.platform?.toLowerCase().replace('_','') || '';
            card.innerHTML = `
                <div class="card-header">
                    <span class="platform-badge ${platformClass}">${item.platform}</span>
                    <span style="color:${statusColor};font-weight:600;font-size:0.82rem;text-transform:capitalize;">${status}</span>
                </div>
                <h4 style="margin:0.5rem 0 0.4rem;color:#e2e8f0;font-size:0.9rem;">${item.title || 'Untitled'}</h4>
                <p style="color:#64748b;font-size:0.75rem;margin-bottom:0.5rem;">${date}</p>
                <a href="${item.url}" target="_blank" class="thread-link" style="font-size:0.78rem;">Original Source ↗</a>
            `;
            grid.appendChild(card);
        });
    } catch (err) {
        loading.classList.add('hidden');
        grid.innerHTML = '<p style="color:#ef4444">Failed to load history.</p>';
    }
}

// ==========================================
// ANALYTICS
// ==========================================
let platformChartInstance = null;

async function fetchAnalytics() {
    try {
        const res = await fetch('/api/analytics');
        const stats = await res.json();

        document.getElementById('stat-discovered').textContent = stats.total_discovered || 0;
        document.getElementById('stat-approved').textContent   = stats.total_approved  || 0;
        document.getElementById('stat-rejected').textContent   = stats.total_rejected  || 0;
        document.getElementById('stat-published').textContent  = stats.total_published || 0;

        const ctx = document.getElementById('platformChart').getContext('2d');
        const labels = Object.keys(stats.platform_breakdown || {});
        const data   = Object.values(stats.platform_breakdown || {});

        if (platformChartInstance) platformChartInstance.destroy();

        platformChartInstance = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels.length ? labels : ['No Data'],
                datasets: [{
                    label: 'Successful Posts by Platform',
                    data: data.length ? data : [0],
                    backgroundColor: ['rgba(139,92,246,0.6)','rgba(6,182,212,0.6)','rgba(16,185,129,0.6)','rgba(245,158,11,0.6)'],
                    borderColor: ['rgba(139,92,246,1)','rgba(6,182,212,1)','rgba(16,185,129,1)','rgba(245,158,11,1)'],
                    borderWidth: 1,
                    borderRadius: 6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { labels: { color: '#9ca3af', font: { family: 'Outfit' } } } },
                scales: {
                    y: { beginAtZero: true, ticks: { color: '#64748b', stepSize: 1 }, grid: { color: 'rgba(255,255,255,0.04)' } },
                    x: { ticks: { color: '#64748b' }, grid: { display: false } }
                }
            }
        });
    } catch (err) { console.error('Failed to load analytics', err); }
}

// ==========================================
// SYSTEM HEALTH
// ==========================================
async function pollSystemHealth() {
    try {
        const res = await fetch('/api/health');
        const h = await res.json();
        document.getElementById('status-db').className    = 'status-dot ' + (h.postgres ? 'green' : 'red');
        document.getElementById('status-redis').className = 'status-dot ' + (h.redis    ? 'green' : 'red');
    } catch {
        document.getElementById('status-db').className    = 'status-dot red';
        document.getElementById('status-redis').className = 'status-dot red';
    }
}

async function checkAutonomousStatus() {
    try {
        const res = await fetch('/api/autonomous/status');
        const data = await res.json();
        document.getElementById('autonomous-toggle').checked = data.enabled;
    } catch(e) { console.error(e); }
}

async function pollJobStatus() {
    try {
        const res  = await fetch('/api/jobs/status');
        const data = await res.json();
        const dot  = document.getElementById('router-status-dot');
        const text = document.getElementById('router-status-text');
        const llm    = data.llm_job    || {};
        const router = data.router_job || {};
        const bothOk = llm.ok && router.ok;
        const anyErr = (!llm.ok && llm.state !== 'No executions') || (!router.ok && router.state !== 'No executions');
        dot.className = 'status-dot ' + (bothOk ? 'green' : anyErr ? 'red' : 'orange');
        text.textContent = bothOk ? 'Jobs: All Good' : `LLM: ${llm.state||'?'} | Router: ${router.state||'?'}`;
    } catch {
        document.getElementById('router-status-dot').className = 'status-dot red';
        document.getElementById('router-status-text').textContent = 'Jobs: Unknown';
    }
}

async function triggerJob(type) {
    const statusEl = document.getElementById('trigger-status');
    const btn = document.getElementById(`btn-run-${type}`);
    btn.disabled = true;
    btn.style.opacity = '0.6';
    statusEl.style.color = '#94a3b8';
    statusEl.textContent = `Launching ${type}...`;

    try {
        const res  = await fetch(`/api/trigger/${type}`, { method: 'POST' });
        const data = await res.json();
        if (data.status === 'triggered') {
            statusEl.style.color = '#10b981';
            statusEl.textContent = `${type} job launched! ✓`;
        } else {
            statusEl.style.color = '#ef4444';
            statusEl.textContent = data.message || 'Failed to trigger.';
        }
    } catch {
        statusEl.style.color = '#ef4444';
        statusEl.textContent = 'Network error.';
    } finally {
        btn.disabled = false;
        btn.style.opacity = '1';
        setTimeout(() => { statusEl.textContent = ''; }, 6000);
        pollJobStatus();
    }
}

// ==========================================
// COOKIE UPLOAD
// ==========================================
async function uploadCookies() {
    const fileInput  = document.getElementById('cookie-file');
    const platform   = document.getElementById('cookie-platform').value;
    const statusMsg  = document.getElementById('cookie-status');

    if (!fileInput.files || fileInput.files.length === 0) {
        alert('Please select a JSON cookies file first.');
        return;
    }

    const formData = new FormData();
    formData.append('file', fileInput.files[0]);

    statusMsg.style.color = '#94a3b8';
    statusMsg.textContent = 'Uploading...';

    try {
        const res = await fetch(`/api/upload-cookies/${platform}`, { method: 'POST', body: formData });
        if (res.ok) {
            statusMsg.style.color = '#10b981';
            statusMsg.textContent = '✓ Uploaded!';
            fileInput.value = '';
            document.getElementById('selected-file-name').textContent = 'No file selected';
            setTimeout(() => { statusMsg.textContent = ''; }, 4000);
        } else {
            const err = await res.json();
            statusMsg.style.color = '#ef4444';
            statusMsg.textContent = err.detail || 'Upload failed';
        }
    } catch {
        statusMsg.style.color = '#ef4444';
        statusMsg.textContent = 'Connection error';
    }
}

// ==========================================
// LIVE LOGS TERMINAL
// ==========================================
let currentLogTab = 'llm';

function switchLogTab(tabName) {
    currentLogTab = tabName;
    document.getElementById('tab-llm').classList.toggle('active',    tabName === 'llm');
    document.getElementById('tab-router').classList.toggle('active', tabName === 'router');
    fetchLogs();
}

async function fetchLogs() {
    try {
        const endpoint = currentLogTab === 'llm' ? '/api/logs/discovery' : '/api/logs/router';
        const res  = await fetch(endpoint);
        const data = await res.json();
        const pre  = document.getElementById('log-output');

        if (data.logs && data.logs.length > 0) {
            const html = data.logs.map(line => {
                const escaped = line.replace(/</g, '&lt;').replace(/>/g, '&gt;');
                if (line.includes('[-]') || line.toLowerCase().includes('error') || line.toLowerCase().includes('failed'))
                    return `<span class="log-error">${escaped}</span>`;
                if (line.includes('[!]') || line.toLowerCase().includes('warning'))
                    return `<span class="log-warning">${escaped}</span>`;
                if (line.includes('[+]') || line.includes('===') || line.includes('successfully'))
                    return `<span class="log-success">${escaped}</span>`;
                if (line.includes('[*]') || line.includes('[>]') || line.includes('[>>]'))
                    return `<span class="log-system">${escaped}</span>`;
                return escaped;
            }).join('\n');

            pre.innerHTML = html;
            const body = document.getElementById('terminal-body');
            body.scrollTop = body.scrollHeight;
        } else {
            pre.textContent = '[System] No logs found yet...';
        }
    } catch (e) {
        document.getElementById('log-output').textContent = '[!] Network error fetching logs.';
    }
}

// Poll logs every 4s
setInterval(fetchLogs, 4000);
fetchLogs();
