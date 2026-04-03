document.addEventListener('DOMContentLoaded', function() {
    const uploadForm = document.querySelector('form');
    const analyzeBtn = document.querySelector('.btn-primary');
    const resultsGrid = document.querySelector('.results-grid');
    const validationBar = document.querySelector('.validation-bar');

    // 1. Auto-Scroll to Results
    // If results just loaded, scroll down smoothly so the doctor sees them immediately
    if (resultsGrid || validationBar) {
        const target = validationBar || resultsGrid;
        target.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }

    if (uploadForm) {
        uploadForm.addEventListener('submit', function(e) {
            // 2. Visual Feedback: Prevent multiple clicks and show progress
            analyzeBtn.disabled = true;
            analyzeBtn.style.backgroundColor = '#6c757d';
            analyzeBtn.style.cursor = 'not-allowed';
            
            // Add a spinning effect to the emoji
            analyzeBtn.innerHTML = `
                <span class="loading-spinner">⌛</span> 
                Processing Clinical Data...
            `;

            // 3. UI Transition: Dim old results to show "new work" is starting
            if (resultsGrid) {
                resultsGrid.style.transition = 'opacity 0.5s ease';
                resultsGrid.style.opacity = '0.3';
                resultsGrid.style.filter = 'grayscale(100%)';
            }
        });
    }

    // 4. Table Row Highlighting
    // Makes it easier for doctors to track which historical row they are looking at
    const rows = document.querySelectorAll('tbody tr');
    rows.forEach(row => {
        row.addEventListener('mouseenter', () => {
            row.style.backgroundColor = '#f0f7ff';
            row.style.cursor = 'pointer';
        });
        row.addEventListener('mouseleave', () => {
            row.style.backgroundColor = '';
        });
    });

    // 5. CSS Injection for the Spinner Animation
    const style = document.createElement('style');
    style.innerHTML = `
        @keyframes spin {
            from { transform: rotate(0deg); }
            to { transform: rotate(360deg); }
        }
        .loading-spinner {
            display: inline-block;
            animation: spin 2s linear infinite;
            margin-right: 8px;
        }
    `;
    document.head.appendChild(style);
});

// 6. Global Error Recovery
window.addEventListener('error', function(e) {
    console.error("Clinical Dashboard Error:", e.message);
    const btn = document.querySelector('.btn-primary');
    if (btn) {
        btn.disabled = false;
        btn.innerHTML = 'Analyze Report';
        btn.style.backgroundColor = '#0056b3';
        btn.style.cursor = 'pointer';
    }
});