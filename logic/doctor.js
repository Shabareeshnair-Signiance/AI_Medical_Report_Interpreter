document.addEventListener('DOMContentLoaded', function() {
    const uploadForm = document.querySelector('form');
    const analyzeBtn = document.querySelector('.btn-primary');

    if (uploadForm) {
        uploadForm.addEventListener('submit', function(e) {
            // 1. Visual Feedback: Show the doctor the system is processing
            analyzeBtn.disabled = true;
            analyzeBtn.innerHTML = '<span class="spinner">⌛</span> Analyzing Clinical Data...';
            analyzeBtn.style.backgroundColor = '#6c757d';
            analyzeBtn.style.cursor = 'not-allowed';

            // 2. Clear previous results if they exist to show "fresh" work
            const resultsGrid = document.querySelector('.results-grid');
            if (resultsGrid) {
                resultsGrid.style.opacity = '0.5';
            }
        });
    }

    // 3. Simple Table Search (Optional Feature for the Doctor)
    const historyTable = document.querySelector('table');
    if (historyTable) {
        console.log("Doctor History Table loaded and ready.");
    }
});

// 4. Error Handling for File Upload
window.addEventListener('error', function(e) {
    console.error("UI Error detected:", e.message);
    const btn = document.querySelector('.btn-primary');
    if (btn) {
        btn.disabled = false;
        btn.innerHTML = 'Analyze Report';
        btn.style.backgroundColor = '#0056b3';
    }
});