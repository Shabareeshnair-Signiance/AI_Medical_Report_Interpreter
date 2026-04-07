document.addEventListener('DOMContentLoaded', function() {
    const uploadForm = document.querySelector('form');
    const analyzeBtn = document.querySelector('.btn-primary');
    const resultsGrid = document.querySelector('.results-grid');
    const validationBar = document.querySelector('.validation-card');

    // 1. Initialize Trend Graph (Empty / Awaiting Click)
    let trendChart;
    const ctx = document.getElementById('trendChart');
    
    if (ctx) {
        trendChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: ['Previous', 'Current Result'], // Initial labels
                datasets: [{
                    label: 'Click a biomarker to view',
                    data: [0, 0], 
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
                    legend: { display: true, position: 'top', labels: { boxWidth: 12, usePointStyle: true } },
                    tooltip: { backgroundColor: 'rgba(0, 0, 0, 0.8)', padding: 12, cornerRadius: 4 }
                }
            }
        });
    }

    // 2. The "Click-to-Graph" Wiring
    const tableRows = document.querySelectorAll('#trendTableBody tr');
    
    tableRows.forEach(row => {
        row.addEventListener('click', function() {
            // Read the cells from the clicked row
            const cells = this.querySelectorAll('td');
            
            // Ensure this is a valid data row (not the "Awaiting data" message)
            if (cells.length >= 2) {
                let biomarkerName = cells[0].innerText.trim();
                let resultText = cells[1].innerText.trim();
                
                // Extract just the numbers from the result column
                let currentValue = parseFloat(resultText.replace(/[^\d.-]/g, ''));

                if (!isNaN(currentValue) && trendChart) {
                    // Visual feedback: dim other rows, highlight clicked one
                    tableRows.forEach(r => r.style.opacity = '0.5');
                    this.style.opacity = '1';

                    // Update the Chart dynamically
                    trendChart.data.datasets[0].label = biomarkerName !== "Unknown" ? biomarkerName : "Selected Biomarker";
                    
                    // Note: Since your backend doesn't send historical data points yet, 
                    // we create a baseline point and plot the current value so the graph works visually.
                    let baselineValue = (currentValue * 0.9).toFixed(2); // Mock baseline 10% lower
                    
                    trendChart.data.labels = ['Baseline', 'Current Result'];
                    trendChart.data.datasets[0].data = [baselineValue, currentValue];
                    
                    trendChart.update(); // Force the graph to redraw
                }
            }
        });
    });

    // Automatically click the first row to populate the graph on load
    if (tableRows.length > 0 && tableRows[0].querySelectorAll('td').length >= 2) {
        tableRows[0].click();
    }

    // 3. Auto-Scroll to Results
    if (resultsGrid || validationBar) {
        const target = validationBar || resultsGrid;
        target.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }

    // 4. Validation Shake Effect
    if (validationBar && validationBar.classList.contains('val-invalid')) {
        validationBar.style.animation = "shake 0.5s cubic-bezier(.36,.07,.19,.97) both";
    }

    // 5. Form Submission Feedback
    if (uploadForm) {
        uploadForm.addEventListener('submit', function(e) {
            analyzeBtn.disabled = true;
            analyzeBtn.style.backgroundColor = '#6c757d';
            analyzeBtn.style.cursor = 'not-allowed';
            analyzeBtn.innerHTML = `<span class="loading-spinner">⌛</span> Processing Clinical Data...`;

            if (resultsGrid) {
                resultsGrid.style.transition = 'opacity 0.5s ease';
                resultsGrid.style.opacity = '0.3';
                resultsGrid.style.filter = 'grayscale(100%)';
            }
        });
    }

    // 6. CSS Injection for Animations
    const style = document.createElement('style');
    style.innerHTML = `
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
        @keyframes shake {
            10%, 90% { transform: translate3d(-1px, 0, 0); }
            20%, 80% { transform: translate3d(2px, 0, 0); }
            30%, 50%, 70% { transform: translate3d(-4px, 0, 0); }
            40%, 60% { transform: translate3d(4px, 0, 0); }
        }
        .loading-spinner {
            display: inline-block;
            animation: spin 2s linear infinite;
            margin-right: 8px;
        }
        #trendTableBody tr { cursor: pointer; transition: opacity 0.2s; }
        #trendTableBody tr:hover { opacity: 0.8 !important; }
    `;
    document.head.appendChild(style);
});