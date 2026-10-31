document.addEventListener('DOMContentLoaded', () => {
    const tableBody = document.getElementById('queueTableBody');
    const statusTabs = document.getElementById('statusTabs');
    const searchInput = document.getElementById('queueSearch');

    // Detail Modal Elements
    const detailModal = document.getElementById('detailModal');
    const detailCommentId = document.getElementById('detailCommentId');
    const detailText = document.getElementById('detailText');
    const detailCategory = document.getElementById('detailCategory');
    const detailRiskConf = document.getElementById('detailRiskConf');
    const detailExplanation = document.getElementById('detailExplanation');
    const btnDetailClose = document.getElementById('btnDetailClose');

    let currentStatus = 'ALL';
    let currentSearch = '';
    let queueDataCache = [];

    // Tab Filter Listener
    statusTabs.addEventListener('click', (e) => {
        if (e.target.classList.contains('tab-btn')) {
            document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
            e.target.classList.add('active');
            currentStatus = e.target.getAttribute('data-status');
            loadQueue();
        }
    });

    // Search Input Listener with Debounce
    let searchDebounce = null;
    searchInput.addEventListener('input', () => {
        clearTimeout(searchDebounce);
        searchDebounce = setTimeout(() => {
            currentSearch = searchInput.value.trim();
            loadQueue();
        }, 300);
    });

    btnDetailClose.addEventListener('click', () => {
        detailModal.classList.remove('active');
    });

    // Initial Load
    loadQueue();

    async function loadQueue() {
        try {
            tableBody.innerHTML = `
                <tr>
                    <td colspan="9" style="text-align: center; padding: 2rem; color: var(--text-muted);">
                        <i class="fa-solid fa-spinner fa-spin" style="font-size: 1.5rem; margin-bottom: 0.5rem; display: block;"></i>
                        Fetching moderation queue...
                    </td>
                </tr>
            `;

            let url = `/api/moderation/queue?status=${currentStatus}`;
            if (currentSearch) {
                url += `&search=${encodeURIComponent(currentSearch)}`;
            }

            const response = await fetch(url);
            if (!response.ok) throw new Error('Failed to load moderation queue');

            queueDataCache = await response.json();
            renderTable(queueDataCache);

        } catch (err) {
            tableBody.innerHTML = `
                <tr>
                    <td colspan="9" style="text-align: center; padding: 2rem; color: #ef4444;">
                        <i class="fa-solid fa-triangle-exclamation" style="font-size: 1.5rem; margin-bottom: 0.5rem; display: block;"></i>
                        Failed to load moderation queue from server.
                    </td>
                </tr>
            `;
        }
    }

    function renderTable(comments) {
        if (!comments || comments.length === 0) {
            tableBody.innerHTML = `
                <tr>
                    <td colspan="9" style="text-align: center; padding: 2rem; color: var(--text-muted);">
                        No comments found in this queue state.
                    </td>
                </tr>
            `;
            return;
        }

        tableBody.innerHTML = '';
        comments.forEach(item => {
            const tr = document.createElement('tr');
            const confPercent = (item.confidence * 100).toFixed(1);

            tr.innerHTML = `
                <td style="font-family: monospace; font-weight: 600; color: var(--accent-blue);">${item.comment_id}</td>
                <td style="font-weight: 600; color: var(--text-primary);">${escapeHTML(item.username)}</td>
                <td class="comment-preview" title="${escapeHTML(item.text)}">${escapeHTML(item.text)}</td>
                <td><span class="badge badge-${item.category}">${item.category.replace('_', ' ')}</span></td>
                <td style="font-weight: 600; color: var(--accent-blue);">${confPercent}%</td>
                <td style="font-weight: 700; color: ${getRiskColor(item.risk_score)};">${item.risk_score}/100</td>
                <td><span class="severity-pill severity-${item.severity}">${item.severity}</span></td>
                <td><span class="severity-pill ${getStatusClass(item.status)}">${item.status}</span></td>
                <td>
                    <div class="table-actions">
                        <button class="btn btn-secondary btn-xs btn-view" data-id="${item.comment_id}"><i class="fa-solid fa-eye"></i></button>
                        <button class="btn btn-primary btn-xs btn-approve" data-id="${item.comment_id}" title="Approve Comment"><i class="fa-solid fa-check"></i></button>
                        <button class="btn btn-danger btn-xs btn-remove" data-id="${item.comment_id}" title="Move Comment to Removed" aria-label="Move comment ${item.comment_id} to Removed"><i class="fa-solid fa-trash"></i></button>
                        <button class="btn btn-secondary btn-xs btn-escalate" data-id="${item.comment_id}" style="background: #a855f7; color: #fff;" title="Escalate"><i class="fa-solid fa-arrow-up-right-from-square"></i></button>
                    </div>
                </td>
            `;

            tableBody.appendChild(tr);
        });

        // Event delegation for table action buttons
        tableBody.querySelectorAll('.btn-view').forEach(btn => {
            btn.addEventListener('click', () => openDetailModal(btn.getAttribute('data-id')));
        });

        tableBody.querySelectorAll('.btn-approve').forEach(btn => {
            btn.addEventListener('click', () => takeAction(btn.getAttribute('data-id'), 'APPROVE'));
        });

        tableBody.querySelectorAll('.btn-remove').forEach(btn => {
            btn.addEventListener('click', () => takeAction(btn.getAttribute('data-id'), 'REMOVE'));
        });

        tableBody.querySelectorAll('.btn-escalate').forEach(btn => {
            btn.addEventListener('click', () => takeAction(btn.getAttribute('data-id'), 'ESCALATE'));
        });
    }

    async function takeAction(commentId, action) {
        try {
            const response = await fetch('/api/moderation/action', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    comment_id: commentId,
                    action: action,
                    performed_by: 'Admin_Moderator'
                })
            });

            if (!response.ok) throw new Error('Action failed');

            if (action === 'REMOVE') {
                currentStatus = 'REMOVED';
                statusTabs.querySelectorAll('.tab-btn').forEach(tab => {
                    const isRemovedTab = tab.getAttribute('data-status') === 'REMOVED';
                    tab.classList.toggle('active', isRemovedTab);
                });
            }

            // Show removed comments in the Removed tab immediately after the action.
            loadQueue();

        } catch (err) {
            alert(`Failed to perform ${action} on comment ${commentId}.`);
        }
    }

    function openDetailModal(commentId) {
        const item = queueDataCache.find(c => c.comment_id === commentId);
        if (!item) return;

        detailCommentId.textContent = item.comment_id;
        detailText.textContent = item.text;
        detailCategory.innerHTML = `<span class="badge badge-${item.category}">${item.category.replace('_', ' ')}</span>`;
        detailRiskConf.textContent = `Confidence: ${(item.confidence * 100).toFixed(1)}% | Risk Score: ${item.risk_score}/100`;
        detailExplanation.textContent = `The comment was flagged under category ${item.category} with severity level ${item.severity} and risk score ${item.risk_score}/100. Policy recommendation: ${item.recommended_action}.`;

        detailModal.classList.add('active');
    }

    function getRiskColor(risk) {
        if (risk <= 20) return '#34d399';
        if (risk <= 50) return '#fde047';
        if (risk <= 75) return '#fb923c';
        return '#ef4444';
    }

    function getStatusClass(status) {
        switch (status) {
            case 'APPROVED': return 'severity-LOW';
            case 'FLAGGED': return 'severity-HIGH';
            case 'PENDING_REVIEW': return 'severity-MODERATE';
            case 'UNDER_REVIEW': return 'severity-CRITICAL';
            case 'REMOVED': return 'severity-CRITICAL';
            default: return 'severity-LOW';
        }
    }

    function escapeHTML(str) {
        if (!str) return '';
        return str.replace(/[&<>'"]/g, 
            tag => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[tag] || tag)
        );
    }
});
