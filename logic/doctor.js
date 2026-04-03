document.addEventListener('DOMContentLoaded', function() {
    const uploadForm = document.querySelector('form');
    const analyzeBtn = document.querySelector('.btn-primary');
    const resultsGrid = document.querySelector('.results-grid');
    const validationBar = document.querySelector('.validation-bar');

    // 1. Auto-Scroll to Results
    // Scrolls to the validation bar or results smoothly upon load
    if (resultsGrid || validationBar) {
        const target = validationBar || resultsGrid;
        target.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }

    // 2. Validation Shake Effect
    // If a report is invalid (Red Bar), give it a subtle shake to alert the doctor
    if (validationBar && validationBar.classList.contains('status-invalid')) {
        validationBar.style.animation = "shake 0.5s cubic-bezier(.36,.07,.19,.97) both";
    }

    if (uploadForm) {
        uploadForm.addEventListener('submit', function(e) {
            // Visual Feedback: Prevent multiple clicks and show progress
            analyzeBtn.disabled = true;
            analyzeBtn.style.backgroundColor = '#6c757d';
            analyzeBtn.style.cursor = 'not-allowed';
            
            // Spinning effect for the button
            analyzeBtn.innerHTML = `
                <span class="loading-spinner">⌛</span> 
                Processing Clinical Data...
            `;

            // UI Transition: Dim old results to show "new work" is starting
            if (resultsGrid) {
                resultsGrid.style.transition = 'opacity 0.5s ease';
                resultsGrid.style.opacity = '0.3';
                resultsGrid.style.filter = 'grayscale(100%)';
            }
        });
    }

    // 3. Table Row Highlighting
    const rows = document.querySelectorAll('tbody tr');
    rows.forEach(row => {
        row.addEventListener('mouseenter', () => {
            row.style.backgroundColor = '#f0f7ff';
            row.style.transition = 'background-color 0.2s ease';
        });
        row.addEventListener('mouseleave', () => {
            row.style.backgroundColor = '';
        });
    });

    // 4. CSS Injection for Animations (Spin & Shake)
    const style = document.createElement('style');
    style.innerHTML = `
        @keyframes spin {
            from { transform: rotate(0deg); }
            to { transform: rotate(360deg); }
        }
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

// 5. Global Error Recovery
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