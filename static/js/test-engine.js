/**
 * SSC CGL Examination Engine
 * Handles interactive mock tests, question palette, timer, instant feedback,
 * auto-saving, review flags, and final score calculations.
 */

let examData = {
    attemptId: null,
    attempt: null,
    questions: [],
    currentIndex: 0,
    remainingSeconds: 3600,
    timerInterval: null,
    isSubmitting: false,
    currentSubjectFilter: 'ALL'
};

document.addEventListener('DOMContentLoaded', () => {
    const appEl = document.getElementById('exam-app');
    if (!appEl) return;

    examData.attemptId = appEl.getAttribute('data-attempt-id');
    initExamEngine();

    // Prevent accidental navigation
    window.addEventListener('beforeunload', handleBeforeUnload);
});

function handleBeforeUnload(e) {
    if (examData.attempt && examData.attempt.status === 'in_progress' && !examData.isSubmitting) {
        e.preventDefault();
        e.returnValue = 'You have an active mock test in progress. Leaving will not pause your timer.';
        return e.returnValue;
    }
}

async function initExamEngine() {
    try {
        const resp = await fetch(`/api/attempt/${examData.attemptId}/state`);
        if (!resp.ok) throw new Error('Failed to load test state');
        const data = await resp.json();

        examData.attempt = data.attempt;
        examData.questions = data.questions;
        examData.remainingSeconds = data.remaining_seconds;
        examData.currentIndex = data.attempt.current_question_index || 0;

        // Ensure current index is within bounds
        if (examData.currentIndex >= examData.questions.length) {
            examData.currentIndex = 0;
        }

        document.getElementById('loading-state').classList.add('hidden');
        document.getElementById('question-content').classList.remove('hidden');

        renderSectionTabs();
        buildQuestionPalette();
        renderCurrentQuestion();
        startTimer();
    } catch (err) {
        console.error('Exam initialization error:', err);
        alert('Could not initialize examination session. Please reload or check your connection.');
    }
}

// -------------------------------------------------------------
// Timer Logic
// -------------------------------------------------------------
function startTimer() {
    updateTimerDisplay();
    examData.timerInterval = setInterval(() => {
        examData.remainingSeconds--;

        if (examData.remainingSeconds <= 0) {
            clearInterval(examData.timerInterval);
            examData.remainingSeconds = 0;
            updateTimerDisplay();
            alert('Time has expired! Your test is being submitted automatically.');
            executeFinalSubmit(true);
            return;
        }

        updateTimerDisplay();
    }, 1000);
}

function updateTimerDisplay() {
    const timerDisplay = document.getElementById('timer-display');
    const timerBox = document.getElementById('timer-box');
    const timerIcon = document.getElementById('timer-icon');

    const m = Math.floor(examData.remainingSeconds / 60);
    const s = examData.remainingSeconds % 60;
    const formatted = `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;

    if (timerDisplay) {
        timerDisplay.textContent = formatted;
    }

    // Danger style if less than 5 minutes
    if (examData.remainingSeconds <= 300) {
        timerBox?.classList.remove('bg-slate-900');
        timerBox?.classList.add('bg-rose-600', 'animate-pulse');
        timerIcon?.classList.replace('text-blue-400', 'text-white');
    }
}

// -------------------------------------------------------------
// Section Tabs
// -------------------------------------------------------------
function renderSectionTabs() {
    const tabsContainer = document.getElementById('section-tabs');
    if (!tabsContainer) return;

    // Collect distinct subjects
    const subjects = new Map();
    examData.questions.forEach(q => {
        if (!subjects.has(q.subject_code)) {
            subjects.set(q.subject_code, q.subject_name);
        }
    });

    let html = `
        <button type="button" onclick="filterBySection('ALL')" 
            class="section-tab-btn px-3 py-1.5 rounded-lg font-semibold transition-colors whitespace-nowrap ${examData.currentSubjectFilter === 'ALL' ? 'bg-blue-600 text-white shadow-sm' : 'bg-slate-100 text-slate-700 hover:bg-slate-200'}">
            All Sections (${examData.questions.length})
        </button>
    `;

    subjects.forEach((name, code) => {
        const count = examData.questions.filter(q => q.subject_code === code).length;
        const isActive = examData.currentSubjectFilter === code;
        html += `
            <button type="button" onclick="filterBySection('${code}')" 
                class="section-tab-btn px-3 py-1.5 rounded-lg font-semibold transition-colors whitespace-nowrap ${isActive ? 'bg-blue-600 text-white shadow-sm' : 'bg-slate-100 text-slate-700 hover:bg-slate-200'}">
                ${name} (${count})
            </button>
        `;
    });

    tabsContainer.innerHTML = html;
}

function filterBySection(code) {
    examData.currentSubjectFilter = code;
    renderSectionTabs();

    // Jump to first question of this section
    if (code !== 'ALL') {
        const firstIdx = examData.questions.findIndex(q => q.subject_code === code);
        if (firstIdx !== -1) {
            goToQuestion(firstIdx);
        }
    }
}

// -------------------------------------------------------------
// Render Current Question
// -------------------------------------------------------------
function renderCurrentQuestion() {
    const q = examData.questions[examData.currentIndex];
    if (!q) return;

    // Badges & Meta
    document.getElementById('q-number-badge').textContent = `Question ${examData.currentIndex + 1} of ${examData.questions.length}`;
    document.getElementById('q-subject-badge').textContent = q.subject_name;
    document.getElementById('q-topic-badge').textContent = q.topic || 'General';
    document.getElementById('q-id-badge').textContent = `ID: #${q.id}`;
    
    // Difficulty
    const diffBadge = document.getElementById('q-diff-badge');
    diffBadge.textContent = q.difficulty;
    diffBadge.className = `px-2 py-0.5 rounded text-[11px] font-semibold ${
        q.difficulty === 'Easy' ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' :
        q.difficulty === 'Hard' ? 'bg-rose-50 text-rose-700 border border-rose-200' :
        'bg-amber-50 text-amber-700 border border-amber-200'
    }`;

    // Provenance
    const typeBadge = document.getElementById('q-type-badge');
    if (q.question_type === 'official_pyq') {
        typeBadge.textContent = 'Official PYQ';
        typeBadge.className = 'px-2 py-0.5 rounded bg-emerald-50 text-emerald-700 border border-emerald-200 text-[11px] font-semibold';
    } else {
        typeBadge.textContent = 'Model Question';
        typeBadge.className = 'px-2 py-0.5 rounded bg-indigo-50 text-indigo-700 border border-indigo-200 text-[11px] font-semibold';
    }

    // Question Text
    document.getElementById('q-text').textContent = q.question_text;

    // Optional Image
    const imgContainer = document.getElementById('q-image-container');
    const imgEl = document.getElementById('q-image');
    if (q.question_image) {
        imgEl.src = q.question_image;
        imgContainer.classList.remove('hidden');
    } else {
        imgContainer.classList.add('hidden');
    }

    // Render Options
    renderOptions(q);

    // Render Instant Feedback Box (if already submitted)
    renderInstantFeedback(q);

    // Update Nav Buttons
    document.getElementById('btn-prev').disabled = (examData.currentIndex === 0);
    const nextBtn = document.getElementById('btn-next');
    if (examData.currentIndex === examData.questions.length - 1) {
        nextBtn.innerHTML = `<span>Review / Finish</span> <i class="fa-solid fa-flag-checkered text-[10px]"></i>`;
    } else {
        nextBtn.innerHTML = `<span>Next</span> <i class="fa-solid fa-chevron-right text-[10px]"></i>`;
    }

    // Mark for review button state
    const markBtn = document.getElementById('btn-mark-review');
    const markText = document.getElementById('mark-review-text');
    if (q.is_marked_for_review) {
        markBtn.classList.remove('bg-amber-50', 'text-amber-800');
        markBtn.classList.add('bg-amber-500', 'text-white');
        markText.textContent = 'Marked for Review';
    } else {
        markBtn.classList.remove('bg-amber-500', 'text-white');
        markBtn.classList.add('bg-amber-50', 'text-amber-800');
        markText.textContent = 'Mark for Review';
    }

    // Submit Answer button state
    const submitAnswerBtn = document.getElementById('btn-submit-answer');
    if (q.is_submitted) {
        submitAnswerBtn.disabled = true;
        submitAnswerBtn.classList.add('opacity-50', 'cursor-not-allowed');
        submitAnswerBtn.innerHTML = `<i class="fa-solid fa-check text-xs"></i> <span>Submitted</span>`;
    } else {
        submitAnswerBtn.disabled = !q.selected_option;
        if (!q.selected_option) {
            submitAnswerBtn.classList.add('opacity-60');
        } else {
            submitAnswerBtn.classList.remove('opacity-60', 'cursor-not-allowed');
        }
        submitAnswerBtn.innerHTML = `<i class="fa-solid fa-check-double text-xs"></i> <span>Submit Answer</span>`;
    }

    updatePaletteView();
}

function renderOptions(q) {
    const container = document.getElementById('options-container');
    const options = [
        { key: 'A', text: q.option_a },
        { key: 'B', text: q.option_b },
        { key: 'C', text: q.option_c },
        { key: 'D', text: q.option_d },
    ];

    const isLocked = Boolean(q.is_submitted);

    let html = '';
    options.forEach(opt => {
        const isSelected = (q.selected_option === opt.key);
        let extraClasses = '';
        let badgeClasses = 'bg-slate-100 text-slate-700 border-slate-300';
        let statusIcon = '';

        if (isLocked) {
            extraClasses += ' locked cursor-default ';
            if (q.correct_option === opt.key) {
                // Correct answer is always green
                extraClasses += ' correct-opt border-emerald-500 bg-emerald-50 text-emerald-950 font-medium ';
                badgeClasses = 'bg-emerald-600 text-white border-emerald-600';
                statusIcon = '<i class="fa-solid fa-circle-check text-emerald-600 ml-auto text-base"></i>';
            } else if (isSelected && !q.is_correct) {
                // Chosen wrong answer is red
                extraClasses += ' wrong-opt border-rose-500 bg-rose-50 text-rose-950 font-medium ';
                badgeClasses = 'bg-rose-600 text-white border-rose-600';
                statusIcon = '<i class="fa-solid fa-circle-xmark text-rose-600 ml-auto text-base"></i>';
            }
        } else if (isSelected) {
            extraClasses += ' selected border-blue-600 bg-blue-50/70 ';
            badgeClasses = 'bg-blue-600 text-white border-blue-600';
        }

        html += `
            <div onclick="selectOption('${opt.key}')" 
                 class="option-card p-3.5 sm:p-4 rounded-xl border border-slate-200 bg-white flex items-center space-x-3.5 select-none ${extraClasses}">
                <div class="w-8 h-8 rounded-lg flex items-center justify-center font-bold text-xs border ${badgeClasses} transition-colors">
                    ${opt.key}
                </div>
                <div class="text-sm sm:text-base leading-snug flex-grow">
                    ${opt.text}
                </div>
                ${statusIcon}
            </div>
        `;
    });

    container.innerHTML = html;
}

function renderInstantFeedback(q) {
    const feedbackBox = document.getElementById('instant-feedback-box');
    if (!feedbackBox) return;

    if (!q.is_submitted) {
        feedbackBox.classList.add('hidden');
        return;
    }

    feedbackBox.classList.remove('hidden');

    const titleEl = document.getElementById('feedback-title');
    const subtitleEl = document.getElementById('feedback-subtitle');
    const userAnsEl = document.getElementById('feedback-user-ans-text');
    const correctAnsEl = document.getElementById('feedback-correct-ans-text');
    const explanationEl = document.getElementById('feedback-explanation');

    const optMap = { 'A': q.option_a, 'B': q.option_b, 'C': q.option_c, 'D': q.option_d };

    if (q.is_correct) {
        // Section 8: Green = Correct
        feedbackBox.className = 'mt-6 rounded-xl p-5 border bg-emerald-50/80 border-emerald-300 text-emerald-950';
        titleEl.className = 'flex items-center space-x-2 mb-1 font-bold text-base text-emerald-800';
        titleEl.innerHTML = `<i class="fa-solid fa-circle-check text-emerald-600"></i> <span>✅ Correct Answer</span>`;
        subtitleEl.textContent = 'Great job! Your answer is correct.';
        subtitleEl.className = 'text-xs mb-3 font-semibold text-emerald-700';
    } else {
        // Section 8: Red = Wrong
        feedbackBox.className = 'mt-6 rounded-xl p-5 border bg-rose-50/80 border-rose-300 text-rose-950';
        titleEl.className = 'flex items-center space-x-2 mb-1 font-bold text-base text-rose-800';
        titleEl.innerHTML = `<i class="fa-solid fa-circle-xmark text-rose-600"></i> <span>❌ Wrong Answer</span>`;
        subtitleEl.textContent = 'Your answer is incorrect. Review the solution below.';
        subtitleEl.className = 'text-xs mb-3 font-semibold text-rose-700';
    }

    userAnsEl.textContent = `Option ${q.selected_option}: ${optMap[q.selected_option] || 'None'}`;
    correctAnsEl.textContent = `Option ${q.correct_option}: ${optMap[q.correct_option] || 'None'}`;
    explanationEl.textContent = q.explanation || 'No detailed explanation provided for this question.';
}

// -------------------------------------------------------------
// User Actions: Select Option & Submit Answer
// -------------------------------------------------------------
function selectOption(optKey) {
    const q = examData.questions[examData.currentIndex];
    if (!q || q.is_submitted) return; // Cannot change after submit

    q.selected_option = optKey;
    renderOptions(q);

    // Enable submit button
    const submitAnswerBtn = document.getElementById('btn-submit-answer');
    submitAnswerBtn.disabled = false;
    submitAnswerBtn.classList.remove('opacity-60', 'cursor-not-allowed');

    // Auto-save selection to server
    saveStateAsync(q.id, optKey, q.is_marked_for_review);
    updatePaletteView();
}

function clearAnswer() {
    const q = examData.questions[examData.currentIndex];
    if (!q || q.is_submitted) return;

    q.selected_option = null;
    renderOptions(q);

    const submitAnswerBtn = document.getElementById('btn-submit-answer');
    submitAnswerBtn.disabled = true;
    submitAnswerBtn.classList.add('opacity-60');

    saveStateAsync(q.id, null, q.is_marked_for_review);
    updatePaletteView();
}

function toggleMarkReview() {
    const q = examData.questions[examData.currentIndex];
    if (!q) return;

    q.is_marked_for_review = q.is_marked_for_review ? 0 : 1;
    saveStateAsync(q.id, q.selected_option, q.is_marked_for_review);
    renderCurrentQuestion();
    updatePaletteView();
}

// Submit Answer for Immediate Feedback (Section 8)
async function submitCurrentAnswer() {
    const q = examData.questions[examData.currentIndex];
    if (!q || !q.selected_option || q.is_submitted) return;

    try {
        const submitBtn = document.getElementById('btn-submit-answer');
        submitBtn.disabled = true;
        submitBtn.innerHTML = `<i class="fa-solid fa-circle-notch fa-spin text-xs"></i> <span>Checking...</span>`;

        const resp = await fetch(`/api/attempt/${examData.attemptId}/submit_answer`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                question_id: q.id,
                selected_option: q.selected_option,
                time_spent_seconds: 5
            })
        });

        const result = await resp.json();
        if (!result.success) throw new Error(result.error || 'Submission failed');

        // Update local object
        q.is_submitted = 1;
        q.is_correct = result.is_correct ? 1 : 0;
        q.correct_option = result.correct_option;
        q.explanation = result.explanation;

        renderCurrentQuestion();
        updatePaletteView();

        // Smooth scroll to feedback box
        document.getElementById('instant-feedback-box')?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });

    } catch (err) {
        console.error('Submit answer error:', err);
        alert('Could not verify answer. Please try again.');
        renderCurrentQuestion();
    }
}

// -------------------------------------------------------------
// Navigation
// -------------------------------------------------------------
function goToPrevQuestion() {
    if (examData.currentIndex > 0) {
        goToQuestion(examData.currentIndex - 1);
    }
}

function goToNextQuestion() {
    if (examData.currentIndex < examData.questions.length - 1) {
        goToQuestion(examData.currentIndex + 1);
    } else {
        // Last question: show confirmation to submit test
        confirmSubmitTest();
    }
}

function goToQuestion(idx) {
    if (idx >= 0 && idx < examData.questions.length) {
        examData.currentIndex = idx;
        renderCurrentQuestion();
        saveStateAsync(null, null, null);
    }
}

// -------------------------------------------------------------
// Auto-Save Helper
// -------------------------------------------------------------
async function saveStateAsync(questionId, selectedOption, isMarkedForReview) {
    try {
        const saveStatus = document.getElementById('save-status');
        if (saveStatus) {
            saveStatus.innerHTML = `<i class="fa-solid fa-spinner fa-spin text-[10px]"></i> Saving...`;
            saveStatus.className = 'text-amber-500 font-medium flex items-center gap-1';
        }

        await fetch(`/api/attempt/${examData.attemptId}/update_state`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                question_id: questionId,
                selected_option: selectedOption,
                is_marked_for_review: isMarkedForReview,
                current_index: examData.currentIndex,
                time_spent_seconds: 2
            })
        });

        if (saveStatus) {
            saveStatus.innerHTML = `<i class="fa-solid fa-cloud-arrow-up text-[10px]"></i> Auto-saved`;
            saveStatus.className = 'text-emerald-600 font-medium flex items-center gap-1';
        }
    } catch (e) {
        console.warn('Auto-save background sync warning:', e);
    }
}

// -------------------------------------------------------------
// Question Palette View
// -------------------------------------------------------------
function buildQuestionPalette() {
    const grid = document.getElementById('palette-grid');
    const mobileGrid = document.getElementById('mobile-palette-grid');
    if (!grid) return;

    let html = '';
    examData.questions.forEach((q, idx) => {
        html += `
            <button type="button" id="palette-btn-${idx}" onclick="goToQuestion(${idx})"
                class="palette-btn h-9 w-full rounded-lg border font-bold text-xs flex items-center justify-center transition-all unanswered">
                ${idx + 1}
            </button>
        `;
    });

    grid.innerHTML = html;
    if (mobileGrid) mobileGrid.innerHTML = html;
    updatePaletteView();
}

function updatePaletteView() {
    let attempted = 0;
    let unattempted = 0;
    let marked = 0;

    examData.questions.forEach((q, idx) => {
        const btn = document.getElementById(`palette-btn-${idx}`);
        const mobileBtn = document.querySelector(`#mobile-palette-grid #palette-btn-${idx}`);

        let stateClass = 'unanswered';

        if (q.is_marked_for_review) {
            stateClass = 'marked';
            marked++;
        } else if (q.is_submitted) {
            stateClass = q.is_correct ? 'answered' : 'wrong-submitted';
            attempted++;
        } else if (q.selected_option) {
            stateClass = 'answered';
            attempted++;
        } else {
            stateClass = 'unanswered';
            unattempted++;
        }

        const isCurrent = (idx === examData.currentIndex);

        [btn, mobileBtn].forEach(b => {
            if (b) {
                b.className = `palette-btn h-9 w-full rounded-lg border font-bold text-xs flex items-center justify-center transition-all ${stateClass} ${isCurrent ? 'current ring-2 ring-blue-600 font-extrabold shadow-sm' : ''}`;
            }
        });
    });

    document.getElementById('stat-attempted').textContent = attempted;
    document.getElementById('stat-unattempted').textContent = unattempted;
    document.getElementById('stat-marked').textContent = marked;
    document.getElementById('stat-current').textContent = examData.currentIndex + 1;

    // Update modal counters
    document.getElementById('modal-attempted-count').textContent = attempted;
    document.getElementById('modal-unattempted-count').textContent = unattempted;
    document.getElementById('modal-review-count').textContent = marked;
}

function toggleMobilePalette() {
    const drawer = document.getElementById('mobile-palette-drawer');
    drawer.classList.toggle('hidden');
}

// -------------------------------------------------------------
// Test Submission (Section 10 Requirement)
// -------------------------------------------------------------
function confirmSubmitTest() {
    updatePaletteView();
    const modal = document.getElementById('submit-confirm-modal');
    modal.classList.remove('hidden');
}

function closeConfirmModal() {
    const modal = document.getElementById('submit-confirm-modal');
    modal.classList.add('hidden');
}

async function executeFinalSubmit(isAuto = false) {
    if (examData.isSubmitting) return;
    examData.isSubmitting = true;

    // Remove beforeunload warning
    window.removeEventListener('beforeunload', handleBeforeUnload);

    const btn = document.getElementById('btn-final-submit');
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = `<i class="fa-solid fa-circle-notch fa-spin mr-1"></i> Generating Result...`;
    }

    try {
        const resp = await fetch(`/api/attempt/${examData.attemptId}/finish`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });

        const data = await resp.json();
        if (data.redirect) {
            window.location.href = data.redirect;
        } else {
            throw new Error(data.error || 'Failed to submit test');
        }
    } catch (err) {
        console.error('Final submit error:', err);
        alert('Error submitting test. Please try again.');
        examData.isSubmitting = false;
        if (btn) btn.disabled = false;
    }
}
