document.addEventListener('DOMContentLoaded', function() {
    // We target the rows specifically inside the body to avoid header issues
    const tableBody = document.getElementById('trendTableBody');
    const ctx = document.getElementById('trendChart');
    let trendChart;

    // 1. Initialize Chart
    if (ctx) {
        trendChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [], 
                datasets: [{
                    label: 'Biomarker Level',
                    data: [],
                    borderColor: '#0056b3',
                    backgroundColor: 'rgba(0, 86, 179, 0.1)',
                    borderWidth: 3,
                    tension: 0.3,
                    fill: true,
                    pointRadius: 6,
                    pointBackgroundColor: '#0056b3',
                    pointHoverRadius: 8
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: { 
                        beginAtZero: false, 
                        grid: { color: 'rgba(0,0,0,0.05)' },
                        title: { display: true, text: 'Result Value', font: { weight: 'bold' } } 
                    },
                    x: { 
                        grid: { display: false },
                        title: { display: true, text: 'Report Sequence' }
                    }
                },
                plugins: {
                    legend: { display: true, position: 'top' },
                    tooltip: { mode: 'index', intersect: false }
                }
            }
        });
    }

    // 2. The Trend Logic
    function updateGraphForBiomarker(selectedRow) {
    const cells = selectedRow.querySelectorAll('td');
    const selectedName = cells[0].innerText.trim();
    
    let historyData = [];
    let historyLabels = [];

    // Filter only rows that match the specific biomarker name clicked
    const allRows = document.querySelectorAll('#trendTableBody tr');
    allRows.forEach((r) => {
        const name = r.querySelectorAll('td')[0].innerText.trim();
        if (name === selectedName) {
            const valText = r.querySelectorAll('td')[1].innerText.trim();
            const valNum = parseFloat(valText.replace(/[^\d.-]/g, ''));
            
            if (!isNaN(valNum)) {
                historyData.push(valNum);
                historyLabels.push(`Point ${historyData.length}`);
            }
        }
    });

    if (trendChart && historyData.length > 0) {
        // Visual feedback for selection
        allRows.forEach(row => row.classList.remove('selected-highlight'));
        selectedRow.classList.add('selected-highlight');

        trendChart.data.labels = historyLabels;
        trendChart.data.datasets[0].label = selectedName;
        trendChart.data.datasets[0].data = historyData;
        trendChart.update();
    }
}

    // 3. Attach Listeners to dynamic rows
    if (tableBody) {
        tableBody.addEventListener('click', function(e) {
            const row = e.target.closest('tr');
            if (row) updateGraphForBiomarker(row);
        });
    }

    // 4. Auto-trigger first row
    setTimeout(() => {
        const firstRow = tableBody?.querySelector('tr');
        if (firstRow && firstRow.querySelectorAll('td').length >= 2) {
            updateGraphForBiomarker(firstRow);
        }
    }, 500);

    // 5. Button Loading State
    const uploadForm = document.querySelector('form');
    const analyzeBtn = document.querySelector('.btn-primary');
    if (uploadForm && analyzeBtn) {
        uploadForm.addEventListener('submit', () => {
            analyzeBtn.disabled = true;
            analyzeBtn.style.opacity = "0.7";
            analyzeBtn.innerHTML = `<span>⌛ Analyzing...</span>`;
        });
    }
});