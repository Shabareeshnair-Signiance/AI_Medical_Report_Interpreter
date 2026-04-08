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
        if (cells.length < 2) return;

        // Since we updated doctor.html, cells[0] is now the 'parameter' (e.g., "Glucose")
        const selectedName = cells[0].innerText.trim();
        let historyData = [];
        let historyLabels = [];

        // Scan the table for all instances of this biomarker to create the line
        const allRows = tableBody.querySelectorAll('tr');
        allRows.forEach((r, index) => {
            const rCells = r.querySelectorAll('td');
            if (rCells.length >= 2) {
                const rowName = rCells[0].innerText.trim();
                
                if (rowName === selectedName) {
                    const valText = rCells[1].innerText.trim();
                    // Robust regex: keeps numbers and decimals, ignores units/alphas
                    const valNum = parseFloat(valText.replace(/[^\d.-]/g, ''));
                    
                    if (!isNaN(valNum)) {
                        historyData.push(valNum);
                        // Using "Point X" or you could use a date if available in the row
                        historyLabels.push(`Point ${historyData.length}`);
                    }
                }
            }
        });

       if (historyData.length > 0 && trendChart) {
            // 1. Clear highlight from all rows
            const allRows = tableBody.querySelectorAll('tr');
            allRows.forEach(r => r.style.backgroundColor = 'transparent');
            
            // 2. Highlight ONLY the clicked row with a distinct color
            selectedRow.style.backgroundColor = '#e7f1ff'; 

            // 3. Update Chart
            trendChart.data.labels = historyLabels;
            trendChart.data.datasets[0].label = `Trend: ${selectedName}`;
            trendChart.data.datasets[0].data = historyData;

            // 4. Force a quick animation to show it updated
            trendChart.update('active'); 
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