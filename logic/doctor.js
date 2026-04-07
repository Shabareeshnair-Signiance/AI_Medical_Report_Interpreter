document.addEventListener('DOMContentLoaded', function() {
    const tableRows = document.querySelectorAll('#trendTableBody tr');
    const ctx = document.getElementById('trendChart');
    let trendChart;

    // 1. Initialize Chart with medical-friendly defaults
    if (ctx) {
        trendChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [], 
                datasets: [{
                    label: 'Biomarker Trend',
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
                        title: { display: true, text: 'Value', font: { weight: 'bold' } } 
                    },
                    x: { grid: { display: false } }
                },
                plugins: {
                    legend: { display: true, position: 'top' }
                }
            }
        });
    }

    // 2. The Trend Logic: Scan the table for historical matches
    function updateGraphForBiomarker(selectedRow) {
        const cells = selectedRow.querySelectorAll('td');
        if (cells.length < 2) return;

        const selectedName = cells[0].innerText.trim();
        let historyData = [];
        let historyLabels = [];

        // Loop through the WHOLE table to find every instance of this test
        tableRows.forEach((r) => {
            const rCells = r.querySelectorAll('td');
            if (rCells.length >= 2) {
                const rowName = rCells[0].innerText.trim();
                
                if (rowName === selectedName) {
                    const valText = rCells[1].innerText.trim();
                    // Regex removes units like "mg/dL" or "%" to get just the number
                    const valNum = parseFloat(valText.replace(/[^\d.-]/g, ''));
                    
                    if (!isNaN(valNum)) {
                        historyData.push(valNum);
                        historyLabels.push(`Record ${historyData.length}`);
                    }
                }
            }
        });

        if (historyData.length > 0 && trendChart) {
            // UI Feedback: Highlight the active row
            tableRows.forEach(r => r.style.backgroundColor = 'transparent');
            selectedRow.style.backgroundColor = 'rgba(0, 86, 179, 0.05)';

            // Update Chart Data
            trendChart.data.labels = historyLabels;
            trendChart.data.datasets[0].label = selectedName;
            trendChart.data.datasets[0].data = historyData;
            
            // Adjust scale so single points don't vanish
            const min = Math.min(...historyData);
            const max = Math.max(...historyData);
            trendChart.options.scales.y.suggestedMin = min * 0.9;
            trendChart.options.scales.y.suggestedMax = max * 1.1;

            trendChart.update();
        }
    }

    // 3. Attach Click Listeners
    tableRows.forEach(row => {
        row.style.cursor = 'pointer';
        row.addEventListener('click', function() {
            updateGraphForBiomarker(this);
        });
    });

    // 4. Auto-trigger first valid row after a short delay
    if (tableRows.length > 0) {
        setTimeout(() => {
            const firstRow = Array.from(tableRows).find(r => r.querySelectorAll('td').length >= 2);
            if (firstRow) firstRow.click();
        }, 400); 
    }

    // 5. Loading State for the Analyze Button
    const uploadForm = document.querySelector('form');
    const analyzeBtn = document.querySelector('.btn-primary');
    if (uploadForm && analyzeBtn) {
        uploadForm.addEventListener('submit', () => {
            analyzeBtn.disabled = true;
            analyzeBtn.innerHTML = `⌛ Processing...`;
        });
    }
});