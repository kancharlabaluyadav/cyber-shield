document.addEventListener('DOMContentLoaded', () => {
    const feedInput = document.getElementById('feedCommentInput');
    const charCounter = document.getElementById('feedCharCounter');
    const btnSubmit = document.getElementById('btnSubmitFeedComment');
    const commentsContainer = document.getElementById('commentsContainer');
    const commentCount = document.getElementById('commentCount');

    // Modal elements
    const moderationModal = document.getElementById('moderationModal');
    const modalCategorySub = document.getElementById('modalCategorySub');
    const modalMessage = document.getElementById('modalMessage');
    const modalBadge = document.getElementById('modalBadge');
    const modalConfidence = document.getElementById('modalConfidence');
    const modalRisk = document.getElementById('modalRisk');
    const btnModalEdit = document.getElementById('btnModalEdit');
    const btnModalSubmitReview = document.getElementById('btnModalSubmitReview');
    const btnModalCancel = document.getElementById('btnModalCancel');

    let pendingCommentData = null;
    let currentTotalCount = 3;

    feedInput.addEventListener('input', () => {
        charCounter.textContent = `${feedInput.value.length} / 500`;
    });

    btnSubmit.addEventListener('click', async () => {
        const text = feedInput.value.trim();
        if (!text) {
            alert('Please enter a comment before posting.');
            return;
        }

        try {
            btnSubmit.disabled = true;
            btnSubmit.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Moderating...';

            const response = await fetch('/api/moderate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text: text, username: 'CurrentUser' })
            });

            const data = await response.json();
            btnSubmit.disabled = false;
            btnSubmit.innerHTML = '<i class="fa-solid fa-paper-plane"></i> Post Comment';

            if (!response.ok) {
                alert(data.error || 'Failed to moderate comment.');
                return;
            }

            if (data.allowed) {
                // Post directly to feed
                appendCommentToFeed({
                    user: 'CurrentUser',
                    text: text,
                    category: data.category,
                    status: 'APPROVED',
                    time: 'Just now'
                });
                feedInput.value = '';
                charCounter.textContent = '0 / 500';
            } else {
                // Open flag modal
                pendingCommentData = { text: text, data: data };
                showModerationModal(data);
            }

        } catch (err) {
            btnSubmit.disabled = false;
            btnSubmit.innerHTML = '<i class="fa-solid fa-paper-plane"></i> Post Comment';
            alert('Network error connecting to moderation backend.');
        }
    });

    function showModerationModal(data) {
        modalCategorySub.textContent = data.is_uncertain
            ? 'Uncertain prediction · Human review required'
            : `Flagged Category: ${data.category}`;
        modalMessage.textContent = data.message;
        modalBadge.className = data.is_uncertain ? 'badge badge-UNCERTAIN' : `badge badge-${data.category}`;
        modalBadge.textContent = data.is_uncertain ? 'UNCERTAIN' : data.category.replace('_', ' ');
        modalConfidence.textContent = `${(data.confidence * 100).toFixed(1)}%`;
        modalRisk.textContent = `${data.risk_score} / 100`;

        moderationModal.classList.add('active');
    }

    function hideModerationModal() {
        moderationModal.classList.remove('active');
    }

    btnModalEdit.addEventListener('click', () => {
        hideModerationModal();
        feedInput.focus();
    });

    btnModalCancel.addEventListener('click', () => {
        hideModerationModal();
        pendingCommentData = null;
    });

    btnModalSubmitReview.addEventListener('click', () => {
        if (pendingCommentData) {
            appendCommentToFeed({
                user: 'CurrentUser',
                text: pendingCommentData.text,
                category: pendingCommentData.data.category,
                status: 'FLAGGED',
                time: 'Just now'
            });
            feedInput.value = '';
            charCounter.textContent = '0 / 500';
            pendingCommentData = null;
        }
        hideModerationModal();
    });

    function appendCommentToFeed(commentObj) {
        currentTotalCount++;
        commentCount.textContent = currentTotalCount;

        const isFlagged = commentObj.status === 'FLAGGED';
        const commentDiv = document.createElement('div');
        commentDiv.className = 'comment-item';
        if (isFlagged) {
            commentDiv.style.opacity = '0.75';
        }

        const badgeHTML = isFlagged
            ? `<span class="badge badge-${commentObj.category}"><i class="fa-solid fa-ban"></i> Flagged for Review</span>`
            : `<span class="badge badge-${commentObj.category}"><i class="fa-solid fa-check"></i> Safe</span>`;

        const textHTML = isFlagged
            ? `<div class="comment-text" style="font-style: italic; color: #ef4444;">[This comment was flagged by AI Moderation and is awaiting moderator approval]</div>`
            : `<div class="comment-text">${escapeHTML(commentObj.text)}</div>`;

        commentDiv.innerHTML = `
            <div class="avatar" style="background: ${isFlagged ? '#ef4444' : '#10b981'};">CU</div>
            <div class="comment-body">
                <div class="comment-header">
                    <span class="comment-user">${escapeHTML(commentObj.user)}</span>
                    ${badgeHTML}
                </div>
                ${textHTML}
                <div class="comment-footer-actions">
                    ${isFlagged ? '<span>Held in queue</span>' : '<span class="action-link"><i class="fa-regular fa-thumbs-up"></i> 0 Likes</span>'}
                    <span>${commentObj.time}</span>
                </div>
            </div>
        `;

        commentsContainer.prepend(commentDiv);
    }

    function escapeHTML(str) {
        return str.replace(/[&<>'"]/g, 
            tag => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[tag] || tag)
        );
    }
});
