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

    // 3. Parse ref range — handles ALL medical formats robustly
    function parseRefRange(refRaw, values) {
        let refMin = null;
        let refMax = null;
        let labelText = null;

        if (!refRaw || refRaw === 'N/A' || refRaw.trim() === '') {
            return { refMin, refMax, labelText };
        }

        const clean = refRaw.trim();

        // Format 1: "70 - 100", "70 to 100" (Handles newlines and spaces automatically)
        const rangeMatch = clean.match(/([\d.]+)\s*(?:[-–]|to)\s*([\d.]+)/i);
        if (rangeMatch) {
            refMin = parseFloat(rangeMatch[1]);
            refMax = parseFloat(rangeMatch[2]);
            labelText = `Normal: ${refMin} – ${refMax}`;
            return { refMin, refMax, labelText };
        }

        // Format 2: "< 200" or "Less than 80"
        const lessThanMatch = clean.match(/[<≤]\s*([\d.]+)/);
        if (lessThanMatch) {
            refMin = 0;
            refMax = parseFloat(lessThanMatch[1]);
            labelText = `Normal: < ${refMax}`;
            return { refMin, refMax, labelText };
        }

        // Format 3: "> 40" 
        const greaterThanMatch = clean.match(/[>≥]\s*([\d.]+)/);
        if (greaterThanMatch) {
            refMin = parseFloat(greaterThanMatch[1]);
            const dataMax = values.length > 0 ? Math.max(...values) : refMin * 2;
            refMax = Math.max(dataMax * 1.5, refMin * 2);
            labelText = `Normal: > ${refMin}`;
            return { refMin, refMax, labelText };
        }

        // Format 4: "Up to 200"
        const upToMatch = clean.match(/up\s*to\s*([\d.]+)/i);
        if (upToMatch) {
            refMin = 0;
            refMax = parseFloat(upToMatch[1]);
            labelText = `Normal: Up to ${refMax}`;
            return { refMin, refMax, labelText };
        }

        // Format 5: "0 - 6" written as "00 - 06" or "00 to 06" (leading zeros)
        const leadingZeroMatch = clean.match(/^(0\d*)\s*(?:[-–]|to)\s*(0\d*)/i);
        if (leadingZeroMatch) {
            refMin = parseFloat(leadingZeroMatch[1]);
            refMax = parseFloat(leadingZeroMatch[2]);
            labelText = `Normal: ${refMin} – ${refMax}`;
            return { refMin, refMax, labelText };
        }

        // Format 6: Standalone symbols like "< 1.0" or "<1.0"
        const singleLessMatch = clean.match(/[<≤]\s*([\d.]+)/);
        if (singleLessMatch) {
            refMin = 0;
            refMax = parseFloat(singleLessMatch[1]);
            labelText = `Normal: < ${refMax}`;
            return { refMin, refMax, labelText };
        }

        // Format 7: Standalone number fallback
        const standaloneMatch = clean.match(/^([\d.]+)$/);
        if (standaloneMatch) {
            refMin = 0;
            refMax = parseFloat(standaloneMatch[1]);
            labelText = `Normal: < ${refMax}`;
            return { refMin, refMax, labelText };
        }

        // Final Fallback: If nothing matches, return the empty values
        return { refMin, refMax, labelText };
    }

    // 4. Build graph from TRENDS_DATA JSON (The Upgraded Ultimate Version)
    function updateGraphForBiomarker(clickedName) {
        if (!trendChart || !TRENDS_DATA || TRENDS_DATA.length === 0) return;

        // Cleanup any old overlays from previous iterations
        const oldOverlay = document.getElementById('qualitative-overlay');
        if (oldOverlay) oldOverlay.remove();

        // FIX: Remove highlight BEFORE updating chart (Retained from your UI logic)
        document.querySelectorAll('#trendTableBody tr').forEach(r => r.classList.remove('selected-highlight'));

        const normalizedClick = normalizeName(clickedName);

        
            // 1. SMART FUZZY MATCHING (Fixes "Missing Comparison" and LDL bugs)
        let matched = TRENDS_DATA.filter(row => {
            const nRow = normalizeName(row.parameter || '');
            if (nRow === normalizedClick) return true; // Exact match always works
            
            // If slightly different, see if one starts with the other
            if (nRow.startsWith(normalizedClick) || normalizedClick.startsWith(nRow)) {
                // Anti-Mix Guards: Prevent grouping distinct tests
                const guards = ['ratio', 'direct', 'indirect', 'total ', 'non', 'vldl'];
                for (let guard of guards) {
                    if (nRow.includes(guard) !== normalizedClick.includes(guard)) return false;
                }
                return true;
            }
            return false;
        });

        if (matched.length === 0) return;

        
            // 2. SAFE DATE SORTING (Handles DD-MM-YYYY and YYYY-MM-DD)
        function parseSafeDate(dStr) {
            if (!dStr) return 0;
            const parts = dStr.split(/[-/.]/);
            if (parts.length === 3) {
                return parts[0].length === 4 
                    ? new Date(`${parts[0]}-${parts[1]}-${parts[2]}`).getTime() 
                    : new Date(`${parts[2]}-${parts[1]}-${parts[0]}`).getTime();
            }
            return new Date(dStr).getTime() || 0;
        }

        const dateMap = new Map();
        matched.forEach(row => dateMap.set(row.date || 'unknown', row));
        matched = Array.from(dateMap.values());
        
        // Sort historical dates strictly left-to-right
        matched.sort((a, b) => parseSafeDate(a.date) - parseSafeDate(b.date));

        const labels = matched.map((r, i) => r.date ? r.date : `Point ${i + 1}`);

        
            // 3. SAFE NUMBER EXTRACTION & TEXT-TO-NUMBER ENGINE
        const rawValues = matched.map(r => r.result_value || r.value || '');
        
        // Smart extractor: grabs "130" even if the string says "< 130 mg/dL"
        const numericValues = rawValues.map(v => {
            const m = String(v).match(/[-+]?[\d]*\.?[\d]+/);
            return m ? parseFloat(m[0]) : NaN;
        });

        // If no numbers exist at all, this is a qualitative text test
        const isQualitative = numericValues.every(v => isNaN(v));

        let plotValues = [];
        let annotations = {};
        const refRaw = matched[0]?.ref_range || "";

        if (isQualitative) {
            // Map words to a severity curve so Chart.js can draw lines
            function mapQualitative(str) {
                const s = String(str).toLowerCase();
                if (s.includes('nil') || s.includes('negative') || s.includes('absent') || s.includes('normal') || s.includes('clear')) return 0;
                if (s.includes('trace') || s.includes('occasional') || s.includes('rare') || s.includes('slight')) return 1;
                if (s.includes('1+') || s === '+' || s.includes('mild') || s.includes('few')) return 2;
                if (s.includes('2+') || s === '++' || s.includes('moderate')) return 3;
                if (s.includes('3+') || s === '+++' || s.includes('many')) return 4;
                if (s.includes('4+') || s === '++++' || s.includes('severe')) return 5;
                if (s.includes('positive') || s.includes('reactive')) return 3; 
                return 0; 
            }
            plotValues = rawValues.map(v => mapQualitative(v));

            trendChart.options.scales.y.min = 0;
            trendChart.options.scales.y.max = 5;
            trendChart.options.scales.y.ticks = {
                stepSize: 1,
                callback: function(value) {
                    const catLabels = ['Negative', 'Trace', '1+ (Mild)', '2+ (Mod)', '3+ (High)', '4+ (Severe)'];
                    return catLabels[value] || '';
                }
            };
            trendChart.options.plugins.tooltip.callbacks = {
                label: function(context) { return `Result: ${rawValues[context.dataIndex]}`; }
            };

            const refNum = mapQualitative(refRaw);
            if (refNum === 0) {
                annotations.refBand = {
                    type: 'box', yMin: -0.4, yMax: 0.4,
                    backgroundColor: 'rgba(40, 167, 69, 0.08)', borderColor: 'rgba(40, 167, 69, 0.4)', borderWidth: 1,
                    label: { display: true, content: `Normal: ${refRaw}`, position: 'start', color: '#28a745', font: { size: 11 } }
                };
            }
        } else {
            // STANDARD NUMERICAL DATA
            // Keep NaN as 'null' so Chart.js doesn't shift points to the wrong dates
            plotValues = numericValues.map(v => isNaN(v) ? null : v);

            delete trendChart.options.scales.y.min;
            delete trendChart.options.scales.y.max;
            delete trendChart.options.scales.y.ticks.stepSize;
            delete trendChart.options.scales.y.ticks.callback; 
            delete trendChart.options.plugins.tooltip.callbacks; 

            // Calculate green reference band
            const { refMin, refMax, labelText } = parseRefRange(refRaw, plotValues.filter(v => v !== null));
            if (refMin !== null && refMax !== null && labelText) {
                annotations.refBand = {
                    type: 'box', yMin: refMin, yMax: refMax,
                    backgroundColor: 'rgba(40, 167, 69, 0.08)', borderColor: 'rgba(40, 167, 69, 0.4)', borderWidth: 1,
                    label: { display: true, content: labelText, position: 'start', color: '#28a745', font: { size: 11 } }
                };
            }
        }

    
            // 4. DRAW THE CHART
        trendChart.options.scales.x.display = true;
        trendChart.options.scales.y.display = true;
        trendChart.data.labels = labels;
        trendChart.data.datasets = [{
            label: clickedName,
            data: plotValues,
            borderColor: '#0056b3',
            backgroundColor: 'rgba(0, 86, 179, 0.1)',
            borderWidth: 3,
            tension: 0.3,
            fill: true,
            pointRadius: 6,
            pointBackgroundColor: '#0056b3',
            pointHoverRadius: 8,
            spanGaps: true // Connects the line even if a historical point is missing
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
            
            // FIX: Clear all highlights immediately before applying the new one
            document.querySelectorAll('#trendTableBody tr').forEach(r => r.classList.remove('selected-highlight'));
            row.classList.add('selected-highlight');
            
            const name = cells[0].innerText.trim();
            updateGraphForBiomarker(name);
        });
    }

    // 6. Auto-trigger first row on load
    setTimeout(() => {
        const firstRow = tableBody?.querySelector('tr');
        if (firstRow && firstRow.querySelectorAll('td').length >= 2) {
            
            // FIX: Clear before highlighting
            document.querySelectorAll('#trendTableBody tr').forEach(r => r.classList.remove('selected-highlight'));
            firstRow.classList.add('selected-highlight');
            
            const name = firstRow.querySelectorAll('td')[0].innerText.trim();
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

// ============================================
// CLINICAL DETECTIVE PARSER & RENDERER (USING MARKED.JS)
// ============================================

function renderClinical() {
    const container = document.getElementById('clinicalParsed');
    const fallback = document.getElementById('clinicalFallback');
    if (!container) return;

    // If there is no text, show fallback
    if (!CLINICAL_TEXT || CLINICAL_TEXT.trim() === '') {
        if (fallback) fallback.style.display = 'block';
        return;
    }

    // Configure marked.js to render line breaks cleanly
    marked.setOptions({
        breaks: true,
        gfm: true
    });

    // Parse the Markdown from the Python backend into HTML
    const htmlOutput = marked.parse(CLINICAL_TEXT);

    // Inject into the UI
    container.innerHTML = `<div class="markdown-body">${htmlOutput}</div>`;
}

// Auto-render on page load
document.addEventListener('DOMContentLoaded', function() {
    renderClinical();
});

// ============================================
// SIMPLE MARKDOWN RENDERER
// ============================================
function renderMarkdown(text) {
    return text
        .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')   // **bold**
        .replace(/\*(.+?)\*/g, '<em>$1</em>')                // *italic*
        .replace(/^#{1,3}\s+(.+)$/gm, '<strong>$1</strong>') // # headings
        .replace(/^[-•]\s+(.+)$/gm, '<li>$1</li>')           // - bullet
        .replace(/(<li>.*<\/li>)/gs, '<ul>$1</ul>')           // wrap bullets
        .replace(/\n{2,}/g, '</p><p>')                        // paragraphs
        .replace(/\n/g, '<br>')                               // line breaks
        .replace(/^(.+)$/, '<p>$1</p>');                      // wrap in p
}

// FLOATING CHATBOT

function toggleChatbot() {
    const win = document.getElementById('chatbot-window');
    const fab = document.getElementById('chatbot-fab');
    if (!win) return;

    win.classList.toggle('open');

    if (win.classList.contains('open')) {
        // Position window just above the FAB's current position
        const fabRect = fab.getBoundingClientRect();

        const winWidth = 360;
        const winHeight = 480;

        let left = fabRect.left + fabRect.width / 2 - winWidth / 2;
        let top = fabRect.top - winHeight - 10;

        // Keep within screen bounds
        left = Math.max(10, Math.min(left, window.innerWidth - winWidth - 10));
        top = Math.max(10, Math.min(top, window.innerHeight - winHeight - 10));

        win.style.position = 'fixed';
        win.style.bottom = 'auto';
        win.style.right = 'auto';
        win.style.left = left + 'px';
        win.style.top = top + 'px';

        setTimeout(() => document.getElementById('chatbot-input')?.focus(), 100);
    }
}

// clearChat will now properly restores default chips
function clearChat() {
    const messages = document.getElementById('chatbot-messages');
    if (!messages) return;
    messages.innerHTML = `
        <div class="chat-msg bot">
            Hello Doctor 👋 I have access to the current patient report. Ask me anything about the findings, test results or next steps.
        </div>`;
        
    const chips = document.getElementById('chat-chips-bar');
    if (chips) {
        // Restore the original default chips on clear
        const defaultChips = [
            '📋 Summarize findings',
            '🚨 What is abnormal?',
            '🔬 Suggest next tests',
            '💊 Recommend next steps'
        ];
        chips.innerHTML = defaultChips.map(c =>
            `<button class="chat-chip" onclick="sendChatMessage('${c.replace(/'/g, "\\'")}')">${c}</button>`
        ).join('');
        chips.style.display = 'flex';
    }
}


// sendChatMessage now extracts and renders dynamic next chips
async function sendChatMessage(prefillText) {
    const input = document.getElementById('chatbot-input');
    const messages = document.getElementById('chatbot-messages');
    const sendBtn = document.getElementById('chatbot-send');
    const chips = document.getElementById('chat-chips-bar'); // Get the chips bar container
    if (!input || !messages) return;

    const userText = prefillText || input.value.trim();
    if (!userText) return;

    // Hide chips immediately when the user sends a message
    if (chips) chips.style.display = 'none';

    // Append user bubble
    messages.innerHTML += `
        <div class="chat-msg-wrapper user-wrapper">
            <div class="chat-msg user">${userText}</div>
        </div>`;
    input.value = '';
    sendBtn.disabled = true;

    // Typing indicator
    const typingId = 'typing-' + Date.now();
    messages.innerHTML += `<div class="chat-msg typing" id="${typingId}">⌛ Thinking...</div>`;
    messages.scrollTop = messages.scrollHeight;

    try {
        const response = await fetch('/chatbot', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message: userText,
                context: PATIENT_CONTEXT
            })
        });

        const data = await response.json();
        
        // Extract the reply AND the dynamic chips from the backend
        const reply = data?.reply || 'Sorry, I could not generate a response.';
        const nextChipsArray = data?.next_chips || []; 

        const msgId = 'msg-' + Date.now();
        document.getElementById(typingId)?.remove();

        // Render Bot Reply
        messages.innerHTML += `
            <div class="chat-msg-wrapper">
                <div class="chat-msg bot" id="${msgId}">${renderMarkdown(reply)}</div>
                <button class="copy-btn" onclick="copyMessage('${msgId}', this)">
                    📋 Copy
                </button>
            </div>`;

        // Render the new dynamic Action Chips
        if (chips && nextChipsArray.length > 0) {
            chips.innerHTML = nextChipsArray.map(c =>
                // using replace to escape any quotes inside the chip text
                `<button class="chat-chip" onclick="sendChatMessage('${c.replace(/'/g, "\\'")}')">${c}</button>`
            ).join('');
            chips.style.display = 'flex'; // Un-hide the bar to show the new chips
        }

    } catch (err) {
        document.getElementById(typingId)?.remove();
        messages.innerHTML += `<div class="chat-msg bot" style="color:#dc3545;">⚠️ Error connecting to AI. Please try again.</div>`;
        
        // Fallback chip if API fails
        if (chips) {
            chips.innerHTML = `<button class="chat-chip" onclick="sendChatMessage('Retry the previous request')">🔄 Retry</button>`;
            chips.style.display = 'flex';
        }
    }

    sendBtn.disabled = false;
    messages.scrollTop = messages.scrollHeight;
    input.focus();
}

// ============================================
// QUICK CHIPS + COPY BUTTON
// ============================================

function copyMessage(msgId, btn) {
    const el = document.getElementById(msgId);
    if (!el) return;
    navigator.clipboard.writeText(el.innerText).then(() => {
        btn.textContent = '✅ Copied';
        btn.classList.add('copied');
        setTimeout(() => {
            btn.textContent = '📋 Copy';
            btn.classList.remove('copied');
        }, 2000);
    });
}

function initChatChips() {
    const win = document.getElementById('chatbot-window');
    const contextBar = document.getElementById('chatbot-context-bar');
    if (!win || !contextBar) return;

    const chips = [
        '📋 Summarize findings',
        '🚨 What is abnormal?',
        '🔬 Suggest next tests',
        '💊 Recommend next steps'
    ];

    const bar = document.createElement('div');
    bar.className = 'chat-chips';
    bar.id = 'chat-chips-bar';
    bar.innerHTML = chips.map(c =>
        `<button class="chat-chip" onclick="sendChatMessage('${c}')">${c}</button>`
    ).join('');

    contextBar.insertAdjacentElement('afterend', bar);
}

// Init chips when page loads
document.addEventListener('DOMContentLoaded', initChatChips);

// ============================================
// DRAGGABLE CHATBOT WINDOW
// ============================================

document.addEventListener('DOMContentLoaded', function () {
    const win = document.getElementById('chatbot-window');
    const header = document.getElementById('chatbot-header');
    const fab = document.getElementById('chatbot-fab');
    if (!win || !header || !fab) return;

    // ── Shared drag logic ──────────────────────────
    function makeDraggable(handle, target, onDragEnd) {
        let isDragging = false;
        let offsetX = 0;
        let offsetY = 0;

        handle.addEventListener('mousedown', function (e) {
            if (e.target.closest('#chatbot-header-btns')) return;
            isDragging = true;

            const rect = target.getBoundingClientRect();
            target.style.position = 'fixed';
            target.style.bottom = 'auto';
            target.style.right = 'auto';
            target.style.top = rect.top + 'px';
            target.style.left = rect.left + 'px';

            offsetX = e.clientX - rect.left;
            offsetY = e.clientY - rect.top;
            document.body.style.userSelect = 'none';
            e.preventDefault();
        });

        document.addEventListener('mousemove', function (e) {
            if (!isDragging) return;
            let newLeft = e.clientX - offsetX;
            let newTop = e.clientY - offsetY;
            newLeft = Math.max(0, Math.min(newLeft, window.innerWidth - target.offsetWidth));
            newTop = Math.max(0, Math.min(newTop, window.innerHeight - target.offsetHeight));
            target.style.left = newLeft + 'px';
            target.style.top = newTop + 'px';
            if (onDragEnd) onDragEnd(newLeft, newTop);
        });

        document.addEventListener('mouseup', function () {
            if (isDragging && onDragEnd) {
                const rect = target.getBoundingClientRect();
                onDragEnd(rect.left, rect.top);
            }
            isDragging = false;
            document.body.style.userSelect = '';
        });
    }

    // ── Drag the window → FAB follows below it ─────
    makeDraggable(header, win, function (winLeft, winTop) {
        const winRect = win.getBoundingClientRect();
        fab.style.position = 'fixed';
        fab.style.bottom = 'auto';
        fab.style.right = 'auto';
        fab.style.left = (winLeft + winRect.width / 2 - fab.offsetWidth / 2) + 'px';
        fab.style.top = (winTop + win.offsetHeight + 10) + 'px';
    });

    // ── Drag the FAB alone (when window is closed) ─
    makeDraggable(fab, fab, null);
});