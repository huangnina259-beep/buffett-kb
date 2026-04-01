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

// ─── Training Mode ─────────────────────────────────────────────────────────────

const TRAINING_CASES = {
    'coca-cola': {
        title: 'Coca-Cola, 1988',
        subtitle: 'How Buffett Made His Biggest Bet',
        steps: [
            {
                theme: 'Business Model',
                context: "It's 1988. Warren Buffett is reading Coca-Cola's annual report. The company earns most of its revenue by selling syrup concentrate to independent bottlers worldwide. Those bottlers handle all the capital-intensive manufacturing, canning, and distribution.",
                question: "What makes Coca-Cola's core business model economically powerful?",
                options: [
                    "It owns and operates every bottling plant worldwide, giving it total supply-chain control.",
                    "It sells high-margin syrup concentrate to bottlers, keeping the business asset-light with exceptional returns on invested capital.",
                    "Its advantage comes from access to cheap sugar and water inputs that competitors can't match.",
                    "It runs a diversified conglomerate spanning beverages, food, and entertainment."
                ],
                correct: 1,
                insight: "Coca-Cola's genius is structural: it sells concentrate at high margins while independent bottlers absorb the capital-intensive manufacturing. This asset-light model earns extraordinary returns on invested capital. Buffett estimated Coke earned roughly $1 on every $2 of tangible assets deployed — a return profile most businesses can't approach.",
                attribution: "Buffett has praised this model repeatedly in shareholder letters, noting the \"fountainhead of value\" created by brand plus asset-light structure."
            },
            {
                theme: 'Competitive Moat',
                context: "In blind taste tests — including the famous Pepsi Challenge — Pepsi consistently outperforms Coke in head-to-head sips. Yet Coca-Cola outsells Pepsi globally by a wide margin, across more than 200 countries.",
                question: "What type of competitive moat does the Pepsi Challenge paradox reveal?",
                options: [
                    "Cost moat — Coke produces its product cheaper than any competitor.",
                    "Network effects — more Coke drinkers make the product more valuable for each drinker.",
                    "Intangible brand moat — emotional habit, identity, and memory that persists despite taste preference.",
                    "Switching cost moat — consumers face significant friction when trying to switch beverages."
                ],
                correct: 2,
                insight: "The Pepsi Challenge paradox is the clearest illustration of brand moat. People buy Coke for reasons entirely disconnected from the liquid — ritual, identity, global ubiquity, memory. Buffett called this \"share of mind.\" A brand embedded in the habits of billions compounds its moat with every generation. The cost to replicate it: incalculable.",
                attribution: "Buffett, 1993 Letter: \"Coca-Cola... has the most powerful brand in the world.\""
            },
            {
                theme: 'Management & Capital Allocation',
                context: "Roberto Goizueta became Coca-Cola's CEO in 1981. He sold the film studio Columbia Pictures, refocused the company entirely on beverages, expanded into new global markets, and aggressively repurchased Coca-Cola shares throughout the decade.",
                question: "What does Goizueta's capital allocation track record reveal?",
                options: [
                    "Selling assets and buying back stock signals a company that has run out of growth ideas.",
                    "Diversifying into film showed bold, forward-thinking strategic leadership.",
                    "He identified that Coke's highest-return use of capital was buying back its own undervalued stock rather than diversifying into unrelated businesses.",
                    "Share repurchases primarily benefit executives holding stock options, not ordinary shareholders."
                ],
                correct: 2,
                insight: "Buffett considers capital allocation the single most important skill of a CEO. Goizueta's discipline — divest unrelated businesses, reinvest in the core franchise, return capital via buybacks when the stock is cheap — is the playbook. The result: Coke's intrinsic value grew roughly 7× between 1981 and 1988. Buffett specifically cited Goizueta's management as central to his investment conviction.",
                attribution: "Buffett, 1989 Letter: \"Roberto Goizueta... has led Coca-Cola with extraordinary skill.\""
            },
            {
                theme: 'Valuation & Margin of Safety',
                context: "Buffett paid roughly 15× earnings for Coca-Cola in 1988. The S&P 500 averaged about 11× earnings at the time. Several Wall Street analysts questioned whether this was truly a value investment given the premium to the market.",
                question: "For a business with Coke's durability and growth profile, where is the real margin of safety?",
                options: [
                    "There is none — paying 15× was a violation of Graham's core principles.",
                    "Safety comes from the hard asset value on the balance sheet — buildings, equipment, inventory.",
                    "For a predictable, durable compounder, the safety lives in earnings power over a 10–20 year horizon, not the entry price alone.",
                    "Safety comes from Coke's commodity hedges on sugar and aluminum prices."
                ],
                correct: 2,
                insight: "This is where Buffett diverged from Graham's strict asset-based framework, heavily influenced by Munger. A business growing earnings reliably at 15% per year, bought at 15×, compounds dramatically over decades. Buffett later crystallized it: \"It's far better to buy a wonderful company at a fair price than a fair company at a wonderful price.\" Price is what you pay once. Earnings power works for you every year.",
                attribution: "Buffett, 1992 Letter — describing the shift from cigar-butt investing to quality compounders."
            },
            {
                theme: 'The Hold Decision',
                context: "By 1998, Buffett's $1 billion Coca-Cola position had grown to over $13 billion — a 13× return in 10 years. The stock now traded at approximately 50× earnings, far above any conventional valuation threshold. By every standard metric, it appeared significantly overvalued.",
                question: "What is the rational case for NOT selling at 50× earnings?",
                options: [
                    "Buffett was anchored to his cost basis — a well-known psychological bias that prevents rational selling.",
                    "Realizing a $12B gain triggers massive capital gains tax, and redeploying that capital into a business of comparable quality is extraordinarily difficult. The friction cost of switching is high.",
                    "Value investors hold forever regardless of price — that is the core philosophy.",
                    "Selling was restricted by Berkshire's regulatory disclosure obligations to the SEC."
                ],
                correct: 1,
                insight: "The hidden friction in selling great businesses is enormous. Capital gains tax on a 10× gain means receiving only ~75 cents per dollar sold. You must then find a business of comparable quality to redeploy into — an extremely rare thing. \"Our favorite holding period is forever\" is not sentimentality. It is the deliberate recognition that activity has tax and opportunity costs, and that inaction with a great business is itself an active strategy.",
                attribution: "Buffett, 1988 Letter: \"When we own portions of outstanding businesses... our favorite holding period is forever.\""
            }
        ]
    }
};

let trainingState = {
    caseId: null,
    step: 0,
    selected: null,
    answers: []
};

function startTraining(caseId) {
    trainingState = { caseId, step: 0, selected: null, answers: [] };
    switchToTrainingView();
    renderTrainingStep();
}

function switchToTrainingView() {
    document.getElementById('home-view').style.display = 'none';
    document.getElementById('chat-view').style.display = 'none';
    document.getElementById('training-view').style.display = 'flex';
}

function exitTraining() {
    document.getElementById('training-view').style.display = 'none';
    document.getElementById('home-view').style.display = 'flex';
}

function renderTrainingStep() {
    const caseData = TRAINING_CASES[trainingState.caseId];
    const steps = caseData.steps;
    const stepData = steps[trainingState.step];
    const total = steps.length;
    const current = trainingState.step + 1;

    document.getElementById('training-step-label').textContent = `Step ${current} of ${total}`;
    document.getElementById('training-progress-fill').style.width = `${((current - 1) / total) * 100}%`;

    const optionsHtml = stepData.options.map((opt, i) => `
        <button class="training-option" data-idx="${i}" onclick="selectTrainingOption(${i})">
            <span class="training-option-letter">${String.fromCharCode(65 + i)}</span>
            <span class="training-option-text">${opt}</span>
        </button>
    `).join('');

    document.getElementById('training-body').innerHTML = `
        <div class="training-step-card">
            <div class="training-theme-tag">${stepData.theme}</div>
            <div class="training-context">${stepData.context}</div>
            <div class="training-question">${stepData.question}</div>
            <div class="training-options">${optionsHtml}</div>
            <div class="training-insight" id="training-insight" style="display:none;">
                <div class="training-insight-label">Buffett's Perspective</div>
                <div class="training-insight-body">${stepData.insight}</div>
                ${stepData.attribution ? `<div class="training-attribution">${stepData.attribution}</div>` : ''}
            </div>
            <div class="training-actions" id="training-actions" style="display:none;">
                <button class="training-continue-btn" onclick="advanceTraining()">
                    ${trainingState.step < total - 1 ? 'Continue →' : 'See Summary →'}
                </button>
            </div>
        </div>
    `;

    document.getElementById('training-body').scrollTop = 0;
}

function selectTrainingOption(idx) {
    if (trainingState.selected !== null) return;
    trainingState.selected = idx;

    const stepData = TRAINING_CASES[trainingState.caseId].steps[trainingState.step];
    trainingState.answers.push({ step: trainingState.step, selected: idx, correct: stepData.correct });

    document.querySelectorAll('.training-option').forEach((btn, i) => {
        btn.disabled = true;
        if (i === stepData.correct) {
            btn.classList.add('training-option--correct');
        } else if (i === idx) {
            btn.classList.add('training-option--other');
        } else {
            btn.classList.add('training-option--dim');
        }
    });

    document.getElementById('training-insight').style.display = 'block';
    document.getElementById('training-actions').style.display = 'flex';

    setTimeout(() => {
        document.getElementById('training-insight').scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }, 100);
}

function advanceTraining() {
    const steps = TRAINING_CASES[trainingState.caseId].steps;
    if (trainingState.step < steps.length - 1) {
        trainingState.step++;
        trainingState.selected = null;
        renderTrainingStep();
    } else {
        renderTrainingSummary();
    }
}

function renderTrainingSummary() {
    const caseData = TRAINING_CASES[trainingState.caseId];
    const answers = trainingState.answers;
    const matched = answers.filter(a => a.selected === a.correct).length;
    const total = caseData.steps.length;

    document.getElementById('training-step-label').textContent = 'Complete';
    document.getElementById('training-progress-fill').style.width = '100%';

    const rowsHtml = answers.map(a => {
        const step = caseData.steps[a.step];
        const isMatch = a.selected === a.correct;
        return `
            <div class="summary-row ${isMatch ? 'summary-row--match' : 'summary-row--diff'}">
                <div class="summary-row-theme">${step.theme}</div>
                <div class="summary-row-detail">
                    <span class="summary-your-pick">You: ${step.options[a.selected]}</span>
                    ${!isMatch ? `<span class="summary-buffett-pick">Buffett's key factor: ${step.options[a.correct]}</span>` : ''}
                </div>
                <span class="summary-icon">${isMatch ? '✓' : '◎'}</span>
            </div>
        `;
    }).join('');

    document.getElementById('training-body').innerHTML = `
        <div class="training-summary">
            <div class="summary-header">
                <div class="summary-title">${caseData.title}</div>
                <div class="summary-score">${matched} of ${total} steps aligned with Buffett's framework</div>
                <div class="summary-subtitle">Agreement doesn't mean right or wrong — this is about understanding how the framework works.</div>
            </div>
            <div class="summary-rows">${rowsHtml}</div>
            <div class="summary-actions">
                <button class="training-continue-btn training-continue-btn--secondary" onclick="exitTraining()">← Back to Home</button>
                <button class="training-continue-btn" onclick="exitTrainingToChat()">Ask Buffett KB a Question →</button>
            </div>
        </div>
    `;

    document.getElementById('training-body').scrollTop = 0;
}

function exitTrainingToChat() {
    document.getElementById('training-view').style.display = 'none';
    document.getElementById('home-view').style.display = 'flex';
    setTimeout(() => document.getElementById('home-search-input').focus(), 100);
}