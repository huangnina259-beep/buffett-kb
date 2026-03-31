let chatHistory = [];
let lastSources = [];
let isGenerating = false;

function switchToChatView() {
    document.getElementById('home-view').style.display = 'none';
    document.getElementById('chat-view').style.display = 'flex';
}

function openSidebar(idx, num) {
    const sidebar = document.getElementById('sidebar');
    const content = document.getElementById('sidebar-content');
    const title = document.getElementById('sidebar-title');
    
    const source = lastSources[idx];
    if (!source) return;

    title.textContent = `Source [${num}]`;
    
    let metaHtml = `<div class="sidebar-source-meta">
        <strong>Source:</strong> ${source.label}<br>
        <strong>Section:</strong> ${source.section || 'N/A'}<br>
        ${source.year ? `<strong>Year:</strong> ${source.year}<br>` : ''}
        ${source.url ? `<a href="${source.url}" target="_blank" style="color: #1a73e8; text-decoration: none; margin-top: 8px; display: inline-block;">View on CNBC Archive ↗</a>` : ''}
    </div>`;

    let displayText = source.text;
    if (source.full_context) {
        // Escape special regex characters in the source text for safe replacement
        const escapeRegExp = (string) => string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        const searchPattern = new RegExp(escapeRegExp(source.text), 'g');
        
        // Wrap the exact matched chunk in a highlight span
        if (searchPattern.test(source.full_context)) {
            displayText = source.full_context.replace(searchPattern, `<span class="highlight-quote">$&</span>`);
        } else {
            // fallback if exact match fails due to whitespace formatting
            displayText = source.full_context;
        }
    } else {
        displayText = `<span class="highlight-quote">${source.text}</span>`;
    }

    // Fix hard-wrapped lines and convert double newlines (even with spaces) to paragraphs
    let paragraphs = displayText.replace(/\r/g, '').split(/\n\s*\n/);
    
    // Process each paragraph
    paragraphs = paragraphs.map(p => {
        // Split into lines, trim each line, and join with a space to fix hard wraps
        return p.split('\n')
                .map(line => line.trim())
                .filter(line => line.length > 0)
                .join(' ');
    }).filter(p => p.length > 0);

    // Join as proper HTML paragraphs
    displayText = paragraphs.map(p => `<p>${p}</p>`).join('');

    content.innerHTML = metaHtml + `<div class="source-text">${displayText}</div>`;
    sidebar.classList.add('active');

    // Auto-scroll to highlight
    setTimeout(() => {
        const highlight = content.querySelector('.highlight-quote');
        if (highlight) {
            highlight.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
    }, 350); // Wait for sidebar transition
}

function closeSidebar() {
    document.getElementById('sidebar').classList.remove('active');
}

function formatCitations(html, sources) {
    if (sources) lastSources = sources; // Update global sources for sidebar
    
    // 1. Normalize adjacent tags: [来源1][来源2] -> [来源1, 2]
    let normalizedHtml = html.replace(/(?:\[(?:来源|Sources?)\s*([\d\s,、]+)\][\s,、]*)+/ig, (match) => {
        let nums = [];
        let r = /\[(?:来源|Sources?)\s*([\d\s,、]+)\]/ig;
        let m;
        while ((m = r.exec(match)) !== null) {
            let parts = m[1].split(/[,、\s]+/).map(n => parseInt(n)).filter(n => !isNaN(n));
            nums.push(...parts);
        }
        nums = [...new Set(nums)];
        return `[来源${nums.join(',')}]`;
    });

    // 2. Parse groups
    return normalizedHtml.replace(/\[(?:来源|Sources?)\s*([\d\s,、]+)\]/ig, (match, p1) => {
        const nums = p1.split(/[,、\s]+/).map(n => parseInt(n)).filter(n => !isNaN(n));
        if (nums.length === 0) return match;
        
        const createTag = (num) => {
            const idx = num - 1;
            const source = sources && sources[idx];
            let tooltipHtml = '';
            
            if (source) {
                let safeText = source.text.replace(/"/g, '&quot;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
                const safeLabel = source.label.replace(/"/g, '&quot;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
                const yearInfo = source.year ? ` • ${source.year}` : '';
                tooltipHtml = `
                    <div class="cite-tooltip">
                        <div class="cite-text">"${safeText}"</div>
                        <div class="cite-meta">${safeLabel}${yearInfo}</div>
                    </div>`;
            } else {
                tooltipHtml = `
                    <div class="cite-tooltip">
                        <div class="cite-text">Detailed source text for this citation is currently unavailable in the local cache.</div>
                        <div class="cite-meta">Reference [Source ${num}]</div>
                    </div>`;
            }

            return `<span class="cite-tag" onclick="event.stopPropagation(); openSidebar(${idx}, ${num})">
                <span class="cite-num">${num}</span>
                ${tooltipHtml}
            </span>`;
        };

        if (nums.length === 1) {
            return `<span class="cite-group">${createTag(nums[0])}</span>`;
        } else {
            let firstTag = createTag(nums[0]);
            let hiddenTags = nums.slice(1).map(createTag).join('');
            return `<span class="cite-group">
                ${firstTag}
                <span class="cite-ellipsis" onclick="this.parentElement.classList.add('expanded'); event.stopPropagation();">···</span>
                <span class="cite-hidden">${hiddenTags}</span>
            </span>`;
        }
    });
}

function renderMessage(role, content, sources = null, searchParams = null) {
    const historyDiv = document.getElementById('chat-history');
    const row = document.createElement('div');
    row.className = `message-row ${role}`;
    
    const bubble = document.createElement('div');
    bubble.className = 'message-bubble';
    
    if (role === 'user') {
        bubble.textContent = content;
    } else {
        if (searchParams) {
            let intentHtml = `<div class="search-intent-status">
                <span>🔍 Search Intent:</span>
                <span class="intent-tag">Keywords: ${searchParams.query}</span>
                ${searchParams.year ? `<span class="intent-tag">Year: ${searchParams.year}</span>` : ''}
                ${searchParams.doc_type ? `<span class="intent-tag">Type: ${searchParams.doc_type.replace('_', ' ')}</span>` : ''}
            </div>`;
            bubble.innerHTML = intentHtml + '<div class="answer-text"></div>';
        } else {
            bubble.innerHTML = '<div class="answer-text">' + formatCitations(marked.parse(content), sources) + '</div>';
        }
    }
    
    row.appendChild(bubble);
    historyDiv.appendChild(row);
    historyDiv.scrollTop = historyDiv.scrollHeight;
    return bubble;
}

function showLoading() {
    const historyDiv = document.getElementById('chat-history');
    const row = document.createElement('div');
    row.className = 'message-row assistant loading-row';
    row.id = 'loading-indicator';
    
    const bubble = document.createElement('div');
    bubble.className = 'message-bubble';
    bubble.innerHTML = '<div class="loading-spinner"><div class="dot-flashing"></div><span style="margin-left:16px">Analyzing wisdom sources...</span></div>';
    
    row.appendChild(bubble);
    historyDiv.appendChild(row);
    historyDiv.scrollTop = historyDiv.scrollHeight;
}

function removeLoading() {
    const indicator = document.getElementById('loading-indicator');
    if (indicator) indicator.remove();
}

let currentAbortController = null;
let currentTypingInterval = null;

const sendSvg = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="3" stroke-linecap="round" stroke-linejoin="round">
    <line x1="12" y1="19" x2="12" y2="5"></line>
    <polyline points="5 12 12 5 19 12"></polyline>
</svg>`;

const stopSvg = `<svg width="18" height="18" viewBox="0 0 24 24" fill="#fff" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    <rect x="6" y="6" width="12" height="12" rx="2" ry="2"></rect>
</svg>`;

function stopGeneration() {
    if (currentAbortController) {
        currentAbortController.abort();
        currentAbortController = null;
    }
    if (currentTypingInterval) {
        clearInterval(currentTypingInterval);
        currentTypingInterval = null;
    }
    isGenerating = false;
    updateButtonsState();
    removeLoading();
}

function updateButtonsState() {
    const homeBtn = document.getElementById('home-submit-btn');
    const chatBtn = document.getElementById('chat-submit-btn');
    const homeInput = document.getElementById('home-search-input');
    const chatInput = document.getElementById('chat-search-input');

    if (isGenerating) {
        homeBtn.innerHTML = stopSvg;
        chatBtn.innerHTML = stopSvg;
        homeBtn.classList.add('active', 'stop-mode');
        chatBtn.classList.add('active', 'stop-mode');
    } else {
        homeBtn.innerHTML = sendSvg;
        chatBtn.innerHTML = sendSvg;
        homeBtn.classList.remove('stop-mode');
        chatBtn.classList.remove('stop-mode');
        
        if (homeInput.value.trim().length > 0) homeBtn.classList.add('active');
        else homeBtn.classList.remove('active');
        
        if (chatInput.value.trim().length > 0) chatBtn.classList.add('active');
        else chatBtn.classList.remove('active');
    }
}

async function sendQuery(queryText) {
    if (!queryText.trim() || isGenerating) return;
    isGenerating = true;
    updateButtonsState();
    
    switchToChatView();
    
    document.getElementById('home-search-input').value = '';
    document.getElementById('chat-search-input').value = '';
    
    renderMessage('user', queryText);
    showLoading();
    
    currentAbortController = new AbortController();
    
    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                query: queryText,
                history: chatHistory
            }),
            signal: currentAbortController.signal
        });
        
        const data = await response.json();
        removeLoading();
        
        if (data.error) {
            renderMessage('assistant', `**Error:** ${data.error}`);
            isGenerating = false;
            updateButtonsState();
            return;
        }
        
        const bubble = renderMessage('assistant', '', data.sources, data.search_params);
        const answerContainer = bubble.querySelector('.answer-text');
        let answer = data.answer;
        let i = 0;
        
        currentTypingInterval = setInterval(() => {
            let currentText = answer.substring(0, i);
            answerContainer.innerHTML = formatCitations(marked.parse(currentText), data.sources) + '<span style="display:inline-block;width:4px;height:14px;background:#0d0d0d;margin-left:2px;animation:blink 1s step-end infinite;"></span>';
            i += 2;
            
            const historyDiv = document.getElementById('chat-history');
            historyDiv.scrollTop = historyDiv.scrollHeight;
            
            if (i >= answer.length) {
                clearInterval(currentTypingInterval);
                currentTypingInterval = null;
                answerContainer.innerHTML = formatCitations(marked.parse(answer), data.sources);
                chatHistory.push({"role": "user", "content": queryText});
                chatHistory.push({"role": "assistant", "content": answer, "sources": data.sources});
                
                if (data.follow_ups && data.follow_ups.length > 0) {
                    setTimeout(() => {
                        const fuRow = document.createElement('div');
                        fuRow.className = 'message-row assistant';
                        let html = '<div style="display: flex; flex-direction: column; gap: 8px; margin-top: 12px; align-items: flex-start; max-width: 100%;">';
                        data.follow_ups.forEach(fq => {
                            html += `<button class="chip" style="text-align: left; height: auto; padding: 10px 16px;" onclick="submitChatQuery('${fq.replace(/'/g, "\\'")}')">${fq}</button>`;
                        });
                        html += '</div>';
                        fuRow.innerHTML = html;
                        historyDiv.appendChild(fuRow);
                        historyDiv.scrollTop = historyDiv.scrollHeight;
                        isGenerating = false;
                        updateButtonsState();
                    }, 500);
                } else {
                    isGenerating = false;
                    updateButtonsState();
                }
            }
        }, 15);
        
    } catch (error) {
        removeLoading();
        if (error.name !== 'AbortError') {
            renderMessage('assistant', `**Network Error:** Could not reach the server.`);
        }
        isGenerating = false;
        updateButtonsState();
    }
}

function submitHomeQuery(text) {
    if (isGenerating) return;
    sendQuery(text);
}

function submitChatQuery(text) {
    if (isGenerating) return;
    if(!text) text = document.getElementById('chat-search-input').value;
    sendQuery(text);
}

function handleBtnClick(inputId) {
    if (isGenerating) {
        stopGeneration();
    } else {
        const val = document.getElementById(inputId).value;
        if (val.trim().length > 0) sendQuery(val);
    }
}

document.getElementById('home-search-input').addEventListener('input', (e) => {
    if (isGenerating) return;
    const btn = document.getElementById('home-submit-btn');
    if (e.target.value.trim().length > 0) btn.classList.add('active');
    else btn.classList.remove('active');
});
document.getElementById('home-search-input').addEventListener('keypress', (e) => {
    if (e.key === 'Enter' && e.target.value.trim().length > 0) {
        if (!isGenerating) sendQuery(e.target.value);
    }
});
document.getElementById('home-submit-btn').addEventListener('click', () => handleBtnClick('home-search-input'));

document.getElementById('chat-search-input').addEventListener('input', (e) => {
    if (isGenerating) return;
    const btn = document.getElementById('chat-submit-btn');
    if (e.target.value.trim().length > 0) btn.classList.add('active');
    else btn.classList.remove('active');
});
document.getElementById('chat-search-input').addEventListener('keypress', (e) => {
    if (e.key === 'Enter' && e.target.value.trim().length > 0) {
        if (!isGenerating) sendQuery(e.target.value);
    }
});
document.getElementById('chat-submit-btn').addEventListener('click', () => handleBtnClick('chat-search-input'));

// File upload logic
document.querySelectorAll('.plus-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        document.getElementById('file-upload').click();
    });
});

document.getElementById('file-upload').addEventListener('change', (e) => {
    const files = e.target.files;
    if (files.length > 0) {
        const fileNames = Array.from(files).map(f => f.name).join(', ');
        alert(`You selected: ${fileNames}\n(File upload backend logic to be implemented)`);
    }
});