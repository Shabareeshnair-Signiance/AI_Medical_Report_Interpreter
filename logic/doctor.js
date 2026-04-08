document.addEventListener('DOMContentLoaded', function () {
    const tableBody = document.getElementById('trendTableBody');
    const ctx = document.getElementById('trendChart');
    let trendChart;

    // 1. Initialize Chart
    if (ctx) {
        trendChart = new Chart(ctx, {
            type: 'line',
            data: { labels: [], datasets: [] },
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
                        title: { display: true, text: 'Report Date' }
                    }
                },
                plugins: {
                    legend: { display: true, position: 'top' },
                    tooltip: { mode: 'index', intersect: false }
                }
            }
        });
    }

    // 2. Normalize names so "GLUCOSE, FASTING" matches "Glucose, Fasting, Plasma"
    function normalizeName(name) {
        return name.toLowerCase()
                   .replace(/[^a-z0-9\s]/g, '')  // remove punctuation
                   .replace(/\s+/g, ' ')           // collapse spaces
                   .trim();
    }

    // 3. Build graph from TRENDS_DATA JSON (not from DOM table rows)
    function updateGraphForBiomarker(clickedName) {
    if (!trendChart || !TRENDS_DATA || TRENDS_DATA.length === 0) return;

    const normalizedClick = normalizeName(clickedName);

    const matched = TRENDS_DATA.filter(row =>
        normalizeName(row.parameter || '').startsWith(normalizedClick.substring(0, 6))
    );

    if (matched.length === 0) return;

    matched.sort((a, b) => new Date(a.date) - new Date(b.date));

    const labels = matched.map((r, i) => r.date ? r.date : `Point ${i + 1}`);
    const values = matched.map(r => parseFloat(r.value));

    // Parse ref_range like "70.00 - 100.00 mg/dL" or "13.0 - 16.5"
    let refMin = null;
    let refMax = null;
    const refRaw = matched[0]?.ref_range || "";
    const refMatch = refRaw.match(/([\d.]+)\s*[-–]\s*([\d.]+)/);
    if (refMatch) {
        refMin = parseFloat(refMatch[1]);
        refMax = parseFloat(refMatch[2]);
    }

    // Build annotation config only if we have valid ref range
    const annotations = {};
    if (refMin !== null && refMax !== null) {
        annotations.refBand = {
            type: 'box',
            yMin: refMin,
            yMax: refMax,
            backgroundColor: 'rgba(40, 167, 69, 0.08)',
            borderColor: 'rgba(40, 167, 69, 0.4)',
            borderWidth: 1,
            label: {
                display: true,
                content: `Normal: ${refMin} – ${refMax}`,
                position: 'start',
                color: '#28a745',
                font: { size: 11 }
            }
        };
    }

    trendChart.data.labels = labels;
    trendChart.data.datasets = [{
        label: clickedName,
        data: values,
        borderColor: '#0056b3',
        backgroundColor: 'rgba(0, 86, 179, 0.1)',
        borderWidth: 3,
        tension: 0.3,
        fill: true,
        pointRadius: 6,
        pointBackgroundColor: '#0056b3',
        pointHoverRadius: 8
    }];

    // Update the annotation config dynamically
    trendChart.options.plugins.annotation = { annotations };
    trendChart.update();

    document.querySelectorAll('#trendTableBody tr').forEach(r => r.classList.remove('selected-highlight'));
}

    // 4. Click listener on table rows
    if (tableBody) {
        tableBody.addEventListener('click', function (e) {
            const row = e.target.closest('tr');
            if (!row) return;
            const cells = row.querySelectorAll('td');
            if (cells.length < 1) return;
            const name = cells[0].innerText.trim();
            row.classList.add('selected-highlight');
            updateGraphForBiomarker(name);
        });
    }

    // 5. Auto-trigger first row on load
    setTimeout(() => {
        const firstRow = tableBody?.querySelector('tr');
        if (firstRow && firstRow.querySelectorAll('td').length >= 2) {
            const name = firstRow.querySelectorAll('td')[0].innerText.trim();
            firstRow.classList.add('selected-highlight');
            updateGraphForBiomarker(name);
        }
    }, 300);

    // 6. Button loading state
    const uploadForm = document.querySelector('form');
    const analyzeBtn = document.querySelector('.btn-primary');
    if (uploadForm && analyzeBtn) {
        uploadForm.addEventListener('submit', () => {
            analyzeBtn.disabled = true;
            analyzeBtn.style.opacity = '0.7';
            analyzeBtn.innerHTML = '<span>⌛ Analyzing...</span>';
        });
    }
});

// SUMMARY PARSER & RENDERER

const SUMMARY_LABELS = [
    { key: "FINDINGS",      icon: "🔴", color: "#dc3545" },
    { key: "SIGNIFICANCE",  icon: "🧠", color: "#0056b3" },
    { key: "BASELINE NOTE", icon: "📌", color: "#6c757d" },
    { key: "CHANGE",        icon: "📊", color: "#0056b3" },
    { key: "DIRECTION",     icon: "📈", color: "#28a745" },
    { key: "ACTION",        icon: "⚡", color: "#fd7e14" }
];

function parseSummary(text) {
    if (!text) return null;

    const positions = [];
    SUMMARY_LABELS.forEach(label => {
        const idx = text.indexOf(label.key + ":");
        if (idx !== -1) positions.push({ idx, label });
    });

    positions.sort((a, b) => a.idx - b.idx);
    if (positions.length === 0) return null;

    const parts = [];
    positions.forEach((pos, i) => {
        const start = pos.idx + pos.label.key.length + 1;
        const end = i + 1 < positions.length ? positions[i + 1].idx : text.length;
        const content = text.slice(start, end).trim();
        parts.push({ label: pos.label, content });
    });

    return parts;
}

function renderSummary() {
    const container = document.getElementById('summaryParsed');
    const fallback = document.getElementById('summaryFallback');
    if (!container) return;

    const parts = parseSummary(SUMMARY_TEXT);
    if (!parts || parts.length === 0) {
        if (fallback) fallback.style.display = 'block';
        return;
    }

    container.innerHTML = parts.map(part => `
        <div style="
            display: flex;
            gap: 12px;
            align-items: flex-start;
            padding: 8px 10px;
            margin-bottom: 6px;
            background: #ffffff;
            border-radius: 6px;
            border-left: 4px solid ${part.label.color};
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        ">
            <span style="font-size:1.1rem; margin-top:1px;">${part.label.icon}</span>
            <div>
                <span style="
                    font-size: 0.7rem;
                    font-weight: 800;
                    text-transform: uppercase;
                    color: ${part.label.color};
                    letter-spacing: 0.5px;
                    display: block;
                    margin-bottom: 2px;
                ">${part.label.key}</span>
                <span style="font-size: 0.9rem; color: #333; line-height: 1.5;">${part.content}</span>
            </div>
        </div>
    `).join('');
}

function toggleSummary() {
    const content = document.getElementById('summaryContent');
    const arrow = document.getElementById('summaryArrow');
    if (!content || !arrow) return;

    if (content.style.display === 'none') {
        content.style.display = 'block';
        arrow.textContent = '▲ Hide';
        renderSummary();
    } else {
        content.style.display = 'none';
        arrow.textContent = '▼ Show';
    }
}