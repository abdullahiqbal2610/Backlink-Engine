document.addEventListener('DOMContentLoaded', () => {
    fetchReviews();
    
    // Tab switching logic
    document.getElementById('nav-pending').addEventListener('click', (e) => {
        e.preventDefault();
        document.getElementById('nav-pending').classList.add('active');
        document.getElementById('nav-published').classList.remove('active');
        
        document.getElementById('cards-container').classList.remove('hidden');
        document.getElementById('published-container').classList.add('hidden');
        
        document.getElementById('page-title').textContent = 'AI Draft Reviews';
        document.getElementById('page-subtitle').textContent = 'Review, edit, and approve AI-generated drafts before they are published.';
        document.getElementById('header-stats').style.display = 'block';
        
        fetchReviews();
    });

    document.getElementById('nav-published').addEventListener('click', (e) => {
        e.preventDefault();
        document.getElementById('nav-published').classList.add('active');
        document.getElementById('nav-pending').classList.remove('active');
        
        document.getElementById('published-container').classList.remove('hidden');
        document.getElementById('cards-container').classList.add('hidden');
        
        document.getElementById('page-title').textContent = 'Live Backlinks';
        document.getElementById('page-subtitle').textContent = 'Successfully published articles and comments across all platforms.';
        document.getElementById('header-stats').style.display = 'none';
        
        fetchPublishedLinks();
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
            <div class="draft-label">AI Drafted Comment</div>
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
