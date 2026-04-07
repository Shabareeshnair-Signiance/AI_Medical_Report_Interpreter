document.addEventListener('DOMContentLoaded', function() {
    const uploadForm = document.querySelector('form');
    const analyzeBtn = document.querySelector('.btn-primary');
    const resultsGrid = document.querySelector('.results-grid');
    const validationBar = document.querySelector('.validation-card');

    // 1. Initialize Trend Graph
    let trendChart;
    const ctx = document.getElementById('trendChart');
    
    if (ctx) {
        trendChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: ['Current Result'], // Removed "Previous" until real data is sent from app.py
                datasets: [{
                    label: 'Select a biomarker to view trend', // Removed hardcoded FBS label
                    data: [0], 
                    borderColor: '#0056b3',
                    backgroundColor: 'rgba(0, 86, 179, 0.1)',
                    borderWidth: 3,
                    tension: 0.4,
                    fill: true,
                    pointRadius: 6,
                    pointHoverRadius: 8,
                    pointBackgroundColor: '#0056b3'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                layout: { padding: { top: 10, bottom: 10, left: 5, right: 5 } },
                scales: {
                    y: { 
                        beginAtZero: false,
                        grid: { color: 'rgba(0, 0, 0, 0.05)' },
                        title: { display: true, text: 'Value', font: { weight: 'bold' } }
                    },
                    x: { grid: { display: false } }
                },
                plugins: {
                    legend: { display: true, position: 'top', labels: { boxWidth: 12, usePointStyle: true } }
                }
            }
        });
    }

    // 2. Updated "Click-to-Graph" Wiring
    // NOTE: Ensure your <tbody> in HTML has id="trendTableBody"
    const tableRows = document.querySelectorAll('#trendTableBody tr');
    
    tableRows.forEach(row => {
        row.style.cursor = 'pointer'; // Make it look clickable
        row.addEventListener('click', function() {
            const cells = this.querySelectorAll('td');
            
            if (cells.length >= 2) {
                let biomarkerName = cells[0].innerText.trim();
                let resultText = cells[1].innerText.trim();
                
                // Extract number (handles "245.00", "31 mg/dL", etc.)
                let currentValue = parseFloat(resultText.replace(/[^\d.-]/g, ''));

                if (!isNaN(currentValue) && trendChart) {
                    // UI Feedback
                    tableRows.forEach(r => r.style.backgroundColor = 'transparent');
                    this.style.backgroundColor = 'rgba(0, 86, 179, 0.05)';

                    // Update Graph Title (Removes the "FBS" default)
                    trendChart.data.datasets[0].label = biomarkerName !== "Unknown" ? biomarkerName : "Biomarker Value";
                    
                    // Update Graph Data
                    // For now, we show one solid point. When you send app.py, we will add real history.
                    trendChart.data.labels = ['Current Result'];
                    trendChart.data.datasets[0].data = [currentValue];
                    
                    trendChart.update();
                }
            }
        });
    });

    // Auto-click first valid row on load
    if (tableRows.length > 0 && tableRows[0].querySelectorAll('td').length >= 2) {
        tableRows[0].click();
    }

    // 3. UI Fixes (Scroll & Shake)
    if (resultsGrid || validationBar) {
        const target = validationBar || resultsGrid;
        target.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }

    if (validationBar && validationBar.classList.contains('val-invalid')) {
        validationBar.style.animation = "shake 0.5s cubic-bezier(.36,.07,.19,.97) both";
    }

    // 4. Form Submission
    if (uploadForm) {
        uploadForm.addEventListener('submit', function() {
            analyzeBtn.disabled = true;
            analyzeBtn.innerHTML = `<span class="loading-spinner">⌛</span> Processing...`;
        });
    }

    // 5. Necessary CSS for interactions
    const style = document.createElement('style');
    style.innerHTML = `
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
        @keyframes shake {
            10%, 90% { transform: translate3d(-1px, 0, 0); }
            20%, 80% { transform: translate3d(2px, 0, 0); }
            30%, 50%, 70% { transform: translate3d(-4px, 0, 0); }
            40%, 60% { transform: translate3d(4px, 0, 0); }
        }
        .loading-spinner { display: inline-block; animation: spin 2s linear infinite; margin-right: 8px; }
        #trendTableBody tr:hover { background-color: #f8f9fa !important; }
    `;
    document.head.appendChild(style);
});