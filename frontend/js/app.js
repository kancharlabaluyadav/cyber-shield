document.addEventListener('DOMContentLoaded', () => {
    const commentInput = document.getElementById('commentText');
    const charCounter = document.getElementById('charCounter');
    const liveStatusContainer = document.getElementById('liveStatusContainer');
    const liveStatusText = document.getElementById('liveStatusText');
    const btnAnalyze = document.getElementById('btnAnalyze');
    const btnPost = document.getElementById('btnPost');

    // UI Result Nodes
    const categoryBadge = document.getElementById('categoryBadge');
    const confidenceValue = document.getElementById('confidenceValue');
    const riskValue = document.getElementById('riskValue');
    const riskBar = document.getElementById('riskBar');
    const severityPill = document.getElementById('severityPill');
    const explanationText = document.getElementById('explanationText');
    const recommendIcon = document.getElementById('recommendIcon');
    const recommendText = document.getElementById('recommendText');

    let debounceTimer = null;

    // Character counter listener
    commentInput.addEventListener('input', () => {
        const len = commentInput.value.length;
        charCounter.textContent = `${len} / 500 characters`;

        if (len === 0) {
            liveStatusContainer.style.display = 'none';
            resetResultCard();
            return;
        }

        // Live status typing indicator
        liveStatusContainer.style.display = 'flex';
        liveStatusText.textContent = 'Analyzing keystrokes...';

        // 600ms Debounce
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(() => {
            runAnalysis(commentInput.value);
        }, 600);
    });

    btnAnalyze.addEventListener('click', () => {
        if (!commentInput.value.trim()) {
            alert('Please enter a comment before analyzing.');
            return;
        }
        runAnalysis(commentInput.value);
    });

    btnPost.addEventListener('click', async () => {
        const text = commentInput.value.trim();
        if (!text) {
            alert('Please enter a comment to post.');
            return;
        }

        try {
            btnPost.disabled = true;
            btnPost.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Processing...';
            
            const response = await fetch('/api/moderate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text: text, username: 'User123' })
            });

            const data = await response.json();
            btnPost.disabled = false;
            btnPost.innerHTML = '<i class="fa-solid fa-paper-plane"></i> Post Comment';

            if (!response.ok) {
                alert(data.error || 'Failed to moderate comment.');
                return;
            }

            if (data.allowed) {
                alert(`âœ… Comment Published Successfully!\n\nCategory: ${data.category}\nSeverity: ${data.severity}\nRisk Score: ${data.risk_score}/100`);
                commentInput.value = '';
                charCounter.textContent = '0 / 500 characters';
                resetResultCard();
            } else if (data.is_uncertain) {
                alert('The model is uncertain about this comment. It has been held for human review.');
            } else {
                alert(`âš ï¸ Moderation Notice:\n${data.message}\n\nCategory: ${data.category}\nAction Taken: ${data.action}`);
            }

        } catch (err) {
            btnPost.disabled = false;
            btnPost.innerHTML = '<i class="fa-solid fa-paper-plane"></i> Post Comment';
            alert('Network error communicating with moderation server.');
        }
    });

    async function runAnalysis(text) {
        if (!text.trim()) return;

        try {
            const response = await fetch('/api/predict', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text: text })
            });

            if (!response.ok) {
                const errData = await response.json();
                liveStatusText.textContent = `Error: ${errData.error || 'Analysis failed'}`;
                return;
            }

            const data = await response.json();
            updateUIResults(data);

            if (data.is_uncertain) {
                liveStatusText.textContent = `Uncertain result (${(data.confidence * 100).toFixed(1)}% confidence); human review recommended`;
            } else if (data.category === 'NON_ABUSIVE') {
                liveStatusText.textContent = 'âœ“ Looks safe to publish';
            } else {
                liveStatusText.textContent = `âš  Potentially harmful (${data.category})`;
            }

        } catch (err) {
            liveStatusText.textContent = 'Server connection error';
        }
    }

    function updateUIResults(data) {
        const cat = data.category;
        const confPercent = (data.confidence * 100).toFixed(1);
        const risk = data.risk_score;
        const severity = data.severity;

        // Avoid presenting a low-confidence guess as a confirmed harmful category.
        if (data.is_uncertain) {
            categoryBadge.className = 'badge badge-UNCERTAIN';
            categoryBadge.innerHTML = '<i class="fa-solid fa-circle-question"></i> UNCERTAIN';
        } else {
            categoryBadge.className = `badge badge-${cat}`;
            categoryBadge.innerHTML = `<i class="fa-solid ${getCategoryIcon(cat)}"></i> ${cat.replace('_', ' ')}`;
        }

        // Confidence
        confidenceValue.textContent = `${confPercent}%`;

        // Risk & Bar
        riskValue.textContent = `${risk}/100`;
        riskBar.style.width = `${risk}%`;
        riskBar.style.backgroundColor = getRiskColor(risk);

        // Severity
        severityPill.className = `severity-pill severity-${severity}`;
        severityPill.textContent = severity;

        // Explanation
        explanationText.textContent = data.explanation;

        // Recommendation
        recommendText.textContent = data.is_uncertain
            ? 'Human review recommended'
            : (data.recommended_action || 'Review before publishing');
        recommendIcon.innerHTML = `<i class="fa-solid ${data.is_uncertain ? 'fa-circle-question' : getCategoryIcon(cat)}"></i>`;
        recommendIcon.style.color = getRiskColor(risk);
    }

    function resetResultCard() {
        categoryBadge.className = 'badge';
        categoryBadge.innerHTML = '<i class="fa-regular fa-hourglass"></i> Awaiting comment';
        confidenceValue.textContent = '—';
        riskValue.textContent = '—';
        riskBar.style.width = '0%';
        riskBar.style.backgroundColor = '#9aa2ad';
        severityPill.className = 'severity-pill';
        severityPill.textContent = '—';
        explanationText.textContent = 'Add a comment and choose Check comment to see the moderation result.';
        recommendText.textContent = 'Waiting for a comment';
        recommendIcon.style.color = '#7b8491';
    }

    function getCategoryIcon(cat) {
        switch (cat) {
            case 'NON_ABUSIVE': return 'fa-circle-check';
            case 'TOXIC': return 'fa-triangle-exclamation';
            case 'BULLYING': return 'fa-user-slash';
            case 'SEVERE_BULLYING': return 'fa-skull-crossbones';
            case 'HATE_SPEECH': return 'fa-hand-middle-finger';
            case 'SEXUAL_HARASSMENT': return 'fa-eye-slash';
            case 'THREAT': return 'fa-shield-cat';
            default: return 'fa-shield-halved';
        }
    }

    function getRiskColor(risk) {
        if (risk <= 20) return '#34d399'; // Green
        if (risk <= 50) return '#fde047'; // Yellow
        if (risk <= 75) return '#fb923c'; // Orange
        return '#ef4444'; // Red
    }
});
