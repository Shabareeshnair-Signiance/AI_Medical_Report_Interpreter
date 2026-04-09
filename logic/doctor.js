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

    // 3. Parse ref range — handles ALL medical formats
    function parseRefRange(refRaw, values) {
        let refMin = null;
        let refMax = null;
        let labelText = null;

        if (!refRaw || refRaw === 'N/A' || refRaw.trim() === '') {
            return { refMin, refMax, labelText };
        }

        const clean = refRaw.trim();

        // Format 1: "70 - 100" or "70 – 100" or "70.00 - 100.00 mg/dL"
        const rangeMatch = clean.match(/([\d.]+)\s*[-–]\s*([\d.]+)/);
        if (rangeMatch) {
            refMin = parseFloat(rangeMatch[1]);
            refMax = parseFloat(rangeMatch[2]);
            labelText = `Normal: ${refMin} – ${refMax}`;
            return { refMin, refMax, labelText };
        }

        // Format 2: "< 200" or "<200" or "< 200.00 mg/dL"
        const lessThanMatch = clean.match(/^[<≤]\s*([\d.]+)/);
        if (lessThanMatch) {
            refMin = 0;
            refMax = parseFloat(lessThanMatch[1]);
            labelText = `Normal: < ${refMax}`;
            return { refMin, refMax, labelText };
        }

        // Format 3: "> 40" or ">40" or "> 40.00"
        const greaterThanMatch = clean.match(/^[>≥]\s*([\d.]+)/);
        if (greaterThanMatch) {
            refMin = parseFloat(greaterThanMatch[1]);
            const dataMax = values.length > 0 ? Math.max(...values) : refMin * 2;
            refMax = Math.max(dataMax * 1.5, refMin * 2);
            labelText = `Normal: > ${refMin}`;
            return { refMin, refMax, labelText };
        }

        // Format 4: "Up to 200" or "Upto 150"
        const upToMatch = clean.match(/up\s*to\s*([\d.]+)/i);
        if (upToMatch) {
            refMin = 0;
            refMax = parseFloat(upToMatch[1]);
            labelText = `Normal: Up to ${refMax}`;
            return { refMin, refMax, labelText };
        }

        // Format 5: "0 - 6" written as "00 - 06" (leading zeros)
        const leadingZeroMatch = clean.match(/^(0\d*)\s*[-–]\s*(0\d*)/);
        if (leadingZeroMatch) {
            refMin = parseFloat(leadingZeroMatch[1]);
            refMax = parseFloat(leadingZeroMatch[2]);
            labelText = `Normal: ${refMin} – ${refMax}`;
            return { refMin, refMax, labelText };
        }

        // Format 6: Single number like "< 1.0" written as "<1.0"
        const singleLessMatch = clean.match(/^<\s*([\d.]+)/);
        if (singleLessMatch) {
            refMin = 0;
            refMax = parseFloat(singleLessMatch[1]);
            labelText = `Normal: < ${refMax}`;
            return { refMin, refMax, labelText };
        }

        return { refMin, refMax, labelText };
    }

    // 4. Build graph from TRENDS_DATA JSON (not from DOM table rows)
    function updateGraphForBiomarker(clickedName) {
        if (!trendChart || !TRENDS_DATA || TRENDS_DATA.length === 0) return;

        const normalizedClick = normalizeName(clickedName);

        const matched = TRENDS_DATA.filter(row =>
            normalizeName(row.parameter || '').startsWith(normalizedClick.substring(0, 6))
        );

        if (matched.length === 0) return;

        matched.sort((a, b) => new Date(a.date) - new Date(b.date));

        const labels = matched.map((r, i) => r.date ? r.date : `Point ${i + 1}`);

        // FIX: Filter out non-numeric values like "Positive", "Reactive"
        const values = matched
            .map(r => parseFloat(r.value))
            .filter(v => !isNaN(v));

        if (values.length === 0) return;

        const refRaw = matched[0]?.ref_range || "";
        const { refMin, refMax, labelText } = parseRefRange(refRaw, values);

        // Build annotation config only if we have valid ref range
        const annotations = {};
        if (refMin !== null && refMax !== null && labelText) {
            annotations.refBand = {
                type: 'box',
                yMin: refMin,
                yMax: refMax,
                backgroundColor: 'rgba(40, 167, 69, 0.08)',
                borderColor: 'rgba(40, 167, 69, 0.4)',
                borderWidth: 1,
                label: {
                    display: true,
                    content: labelText,
                    position: 'start',
                    color: '#28a745',
                    font: { size: 11 }
                }
            };
        }

        // FIX: Remove highlight BEFORE updating chart
        document.querySelectorAll('#trendTableBody tr').forEach(r => r.classList.remove('selected-highlight'));

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

        trendChart.options.plugins.annotation = { annotations };
        trendChart.update();
    }

    // 5. Click listener on table rows
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

    // 6. Auto-trigger first row on load
    setTimeout(() => {
        const firstRow = tableBody?.querySelector('tr');
        if (firstRow && firstRow.querySelectorAll('td').length >= 2) {
            const name = firstRow.querySelectorAll('td')[0].innerText.trim();
            firstRow.classList.add('selected-highlight');
            updateGraphForBiomarker(name);
        }
    }, 300);

    // 7. Button loading state
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

// ============================================
// SUMMARY PARSER & RENDERER
// ============================================

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

// ============================================
// HISTORY ROW EXPAND / COLLAPSE
// ============================================

function toggleHistoryRow(index) {
    const detailRow = document.getElementById('historyDetail' + index);
    const arrow = document.getElementById('historyArrow' + index);
    if (!detailRow || !arrow) return;

    const isOpen = detailRow.classList.contains('open');

    // Close all other open rows first
    document.querySelectorAll('.history-detail-row.open').forEach(row => {
        row.classList.remove('open');
    });
    document.querySelectorAll('[id^="historyArrow"]').forEach(a => {
        a.textContent = '▼ View Tests';
    });

    // Toggle clicked row
    if (!isOpen) {
        detailRow.classList.add('open');
        arrow.textContent = '▲ Hide Tests';
    }
}

// CLINICAL DETECTIVE PARSER & RENDERER

const CLINICAL_LABELS = [
    { key: "URGENCY",               icon: "🚨", color: "#dc3545" },
    { key: "PATTERN DETECTED",      icon: "🔗", color: "#6f42c1" },
    { key: "SYSTEM AFFECTED",       icon: "🫀", color: "#0056b3" },
    { key: "ROOT CAUSE HYPOTHESIS", icon: "🧬", color: "#0056b3" },
    { key: "DIFFERENTIAL",          icon: "🔀", color: "#6c757d" },
    { key: "MISSING TEST",          icon: "🔬", color: "#fd7e14" },
    { key: "TREND IMPACT",          icon: "📉", color: "#28a745" },
    { key: "NEXT STEPS",            icon: "📋", color: "#17a2b8" },
    { key: "DOCTOR NOTE",           icon: "💬", color: "#003366" }
];

function parseClinical(text) {
    if (!text) return null;

    const positions = [];
    CLINICAL_LABELS.forEach(label => {
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

function renderClinical() {
    const container = document.getElementById('clinicalParsed');
    const fallback = document.getElementById('clinicalFallback');
    if (!container) return;

    const parts = parseClinical(CLINICAL_TEXT);
    if (!parts || parts.length === 0) {
        if (fallback) fallback.style.display = 'block';
        return;
    }

    container.innerHTML = parts.map((part, index) => {
        const isLast = index === parts.length - 1;
        const isDivider = !isLast;

        return `
        <div style="
            display: flex;
            gap: 14px;
            align-items: flex-start;
            padding: 10px 0;
            ${isDivider ? 'border-bottom: 1px solid #f0f0f0;' : ''}
        ">
            <div style="
                display: flex;
                flex-direction: column;
                align-items: center;
                gap: 0;
                min-width: 32px;
            ">
                <span style="font-size:1.2rem;">${part.label.icon}</span>
                ${isDivider ? `<div style="width:2px; height:100%; min-height:20px; background:${part.label.color}20; margin-top:4px;"></div>` : ''}
            </div>
            <div style="flex:1; padding-bottom: ${isDivider ? '6px' : '0'};">
                <span style="
                    font-size: 0.68rem;
                    font-weight: 900;
                    text-transform: uppercase;
                    color: ${part.label.color};
                    letter-spacing: 0.8px;
                    display: block;
                    margin-bottom: 3px;
                ">${part.label.key}</span>
                <span style="
                    font-size: 0.92rem;
                    color: #2c3e50;
                    line-height: 1.6;
                    white-space: pre-line;
                ">${part.content}</span>
            </div>
        </div>
        `;
    }).join('');
}

// Auto-render on page load
document.addEventListener('DOMContentLoaded', function() {
    renderClinical();
});