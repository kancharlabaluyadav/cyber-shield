document.addEventListener('DOMContentLoaded', async () => {
    
    let categoryChartInstance = null;
    let severityChartInstance = null;
    let timeChartInstance = null;
    let actionsChartInstance = null;

    try {
        const response = await fetch('/api/analytics');
        if (!response.ok) throw new Error('Failed to fetch analytics metrics.');
        
        const data = await response.json();
        updateStatCounters(data);
        renderCharts(data);

    } catch (err) {
        console.error('Analytics Error:', err);
    }

    function updateStatCounters(data) {
        document.getElementById('statTotal').textContent = data.total_comments.toLocaleString();
        document.getElementById('statSafe').textContent = data.safe_comments.toLocaleString();
        document.getElementById('statToxic').textContent = data.toxic_comments.toLocaleString();
        document.getElementById('statBullying').textContent = data.bullying_comments.toLocaleString();
        document.getElementById('statSevere').textContent = data.severe_bullying_comments.toLocaleString();
        document.getElementById('statHate').textContent = data.hate_speech_comments.toLocaleString();
        document.getElementById('statSexual').textContent = data.sexual_harassment_comments.toLocaleString();
        document.getElementById('statThreat').textContent = data.threat_comments.toLocaleString();
        document.getElementById('statFlagged').textContent = data.flagged_comments.toLocaleString();
        document.getElementById('statAvgConfidence').textContent = `${(data.average_confidence * 100).toFixed(1)}%`;
    }

    function renderCharts(data) {
        // Chart 1: Category Doughnut
        const catCtx = document.getElementById('categoryDoughnutChart').getContext('2d');
        const catLabels = ['NON_ABUSIVE', 'TOXIC', 'BULLYING', 'SEVERE_BULLYING', 'HATE_SPEECH', 'SEXUAL_HARASSMENT', 'THREAT'];
        const catValues = [
            data.safe_comments,
            data.toxic_comments,
            data.bullying_comments,
            data.severe_bullying_comments,
            data.hate_speech_comments,
            data.sexual_harassment_comments,
            data.threat_comments
        ];

        categoryChartInstance = new Chart(catCtx, {
            type: 'doughnut',
            data: {
                labels: catLabels.map(c => c.replace('_', ' ')),
                datasets: [{
                    data: catValues,
                    backgroundColor: [
                        '#10b981', // Non-abusive
                        '#eab308', // Toxic
                        '#f97316', // Bullying
                        '#ef4444', // Severe Bullying
                        '#a855f7', // Hate Speech
                        '#ec4899', // Sexual Harassment
                        '#991b1b'  // Threat
                    ],
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: 'bottom', labels: { color: '#596474', font: { family: 'Inter' } } }
                }
            }
        });

        // Chart 2: Severity Bar Chart
        const sevCtx = document.getElementById('severityBarChart').getContext('2d');
        const sevData = data.severity_breakdown || { LOW: 10, MODERATE: 3, HIGH: 4, CRITICAL: 3 };
        
        severityChartInstance = new Chart(sevCtx, {
            type: 'bar',
            data: {
                labels: ['LOW', 'MODERATE', 'HIGH', 'CRITICAL'],
                datasets: [{
                    label: 'Comments Count',
                    data: [sevData.LOW, sevData.MODERATE, sevData.HIGH, sevData.CRITICAL],
                    backgroundColor: ['#34d399', '#fde047', '#fb923c', '#f87171'],
                    borderRadius: 6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    x: { ticks: { color: '#596474' }, grid: { display: false } },
                    y: { ticks: { color: '#596474' }, grid: { color: '#e5e8ec' } }
                }
            }
        });

        // Chart 3: Comments Over Time Line Chart
        const timeCtx = document.getElementById('timeLineChart').getContext('2d');
        timeChartInstance = new Chart(timeCtx, {
            type: 'line',
            data: {
                labels: data.activity_labels,
                datasets: [
                    {
                        label: 'Analyzed Comments',
                        data: data.comments_by_day,
                        borderColor: '#6366f1',
                        backgroundColor: 'rgba(99, 102, 241, 0.1)',
                        fill: true,
                        tension: 0.4
                    },
                    {
                        label: 'Flagged Abusive',
                        data: data.flagged_by_day,
                        borderColor: '#ef4444',
                        backgroundColor: 'rgba(239, 68, 68, 0.1)',
                        fill: true,
                        tension: 0.4
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { position: 'top', labels: { color: '#596474' } } },
                scales: {
                    x: { ticks: { color: '#596474' }, grid: { color: '#e5e8ec' } },
                    y: { ticks: { color: '#596474' }, grid: { color: '#e5e8ec' } }
                }
            }
        });

        // Chart 4: Actions Bar Chart
        const actCtx = document.getElementById('actionsBarChart').getContext('2d');
        actionsChartInstance = new Chart(actCtx, {
            type: 'bar',
            data: {
                labels: ['Approved', 'Flagged', 'Pending Review', 'Under Review', 'Removed'],
                datasets: [{
                    label: 'Comments by Status',
                    data: ['APPROVED', 'FLAGGED', 'PENDING_REVIEW', 'UNDER_REVIEW', 'REMOVED'].map(status => data.status_breakdown[status] || 0),
                    backgroundColor: ['#10b981', '#38bdf8', '#818cf8', '#ef4444', '#a855f7'],
                    borderRadius: 6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    x: { ticks: { color: '#596474' }, grid: { display: false } },
                    y: { ticks: { color: '#596474' }, grid: { color: '#e5e8ec' } }
                }
            }
        });
    }
});
