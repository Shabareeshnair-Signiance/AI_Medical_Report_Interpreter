document.addEventListener('DOMContentLoaded', function() {
    const uploadForm = document.querySelector('form');
    const analyzeBtn = document.querySelector('.btn-primary');
    const resultsGrid = document.querySelector('.results-grid');
    const validationBar = document.querySelector('.validation-card');

    // 1. Initialize Trend Graph (Chart.js) - Updated for Split Panel Layout
const ctx = document.getElementById('trendChart');
if (ctx) {
    new Chart(ctx, {
        type: 'line',
        data: {
            labels: ['Jan', 'Feb', 'Mar', 'Apr'], // Replace with actual report dates from your backend
            datasets: [{
                label: 'FBS Level (mg/dL)',
                data: [110, 145, 160, 185], // Replace with historical values from your backend
                borderColor: '#0056b3',
                backgroundColor: 'rgba(0, 86, 179, 0.1)',
                borderWidth: 3,
                tension: 0.4, // Slightly smoother curve for the new layout
                fill: true,
                pointRadius: 6,
                pointHoverRadius: 8,
                pointBackgroundColor: '#0056b3'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false, // Allows it to fill the trend-right-panel correctly
            layout: {
                padding: {
                    top: 10,
                    bottom: 10,
                    left: 5,
                    right: 5
                }
            },
            scales: {
                y: { 
                    beginAtZero: false,
                    grid: {
                        color: 'rgba(0, 0, 0, 0.05)'
                    },
                    title: { display: true, text: 'Value (mg/dL)', font: { weight: 'bold' } }
                },
                x: {
                    grid: {
                        display: false // Cleaner look for the horizontal axis
                    }
                }
            },
            plugins: {
                legend: { 
                    display: true, 
                    position: 'top',
                    labels: {
                        boxWidth: 12,
                        usePointStyle: true
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(0, 0, 0, 0.8)',
                    padding: 12,
                    cornerRadius: 4
                }
            }
        }
    });
}

    // 2. Auto-Scroll to Results
    if (resultsGrid || validationBar) {
        const target = validationBar || resultsGrid;
        target.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }

    // 3. Validation Shake Effect
    if (validationBar && validationBar.classList.contains('val-invalid')) {
        validationBar.style.animation = "shake 0.5s cubic-bezier(.36,.07,.19,.97) both";
    }

    // 4. Form Submission Feedback
    if (uploadForm) {
        uploadForm.addEventListener('submit', function(e) {
            analyzeBtn.disabled = true;
            analyzeBtn.style.backgroundColor = '#6c757d';
            analyzeBtn.style.cursor = 'not-allowed';
            
            analyzeBtn.innerHTML = `
                <span class="loading-spinner">⌛</span> 
                Processing Clinical Data...
            `;

            if (resultsGrid) {
                resultsGrid.style.transition = 'opacity 0.5s ease';
                resultsGrid.style.opacity = '0.3';
                resultsGrid.style.filter = 'grayscale(100%)';
            }
        });
    }

    // 5. CSS Injection for Animations
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
    `;
    document.head.appendChild(style);
});