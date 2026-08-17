document.addEventListener('DOMContentLoaded', () => {
    // Score Color Coding
    const updateScoreColors = () => {
        document.querySelectorAll('.score-display, .score-display-sm, .score-badge').forEach(el => {
            const score = parseInt(el.getAttribute('data-score')) || 0;
            let colorClass = '';
            let textClass = '';
            let bgClass = '';
            let borderClass = '';
            
            if (score >= 75) {
                colorClass = 'text-green-600'; textClass = 'text-green-800'; bgClass = 'bg-green-100'; borderClass = 'border-green-400';
            } else if (score >= 50) {
                colorClass = 'text-amber-500'; textClass = 'text-amber-800'; bgClass = 'bg-amber-100'; borderClass = 'border-amber-400';
            } else {
                colorClass = 'text-red-500'; textClass = 'text-red-800'; bgClass = 'bg-red-100'; borderClass = 'border-red-400';
            }

            if (el.classList.contains('score-display')) {
                const textEl = el.querySelector('.score-text');
                if (textEl) textEl.className = `score-text ${colorClass} ${textEl.className.replace(/text-(green|amber|red)-(500|600)/, '')}`;
                if (el.classList.contains('score-border')) el.classList.add(borderClass);
            } else if (el.classList.contains('score-badge')) {
                el.classList.add(bgClass, textClass);
            } else {
                el.classList.add(colorClass);
            }
        });
    };

    // Run initially
    updateScoreColors();

    // HTMX Events
    document.body.addEventListener('htmx:afterSwap', (event) => {
        if (event.detail.target.id === 'feedback-container') {
            updateScoreColors();
            
            // Auto-scroll to feedback
            setTimeout(() => {
                event.detail.target.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }, 100);
            
            // Disable the textarea and submit button after successful submission
            const form = document.getElementById('practice-form');
            if (form) {
                const textarea = form.querySelector('textarea');
                const btn = form.querySelector('button[type="submit"]');
                if (textarea) {
                    textarea.disabled = true;
                    textarea.classList.add('bg-gray-50', 'text-gray-500');
                }
                if (btn) btn.disabled = true;
            }
        }
    });

    document.body.addEventListener('htmx:beforeRequest', (event) => {
        const btn = document.getElementById('submit-answer-btn');
        if (btn) {
            btn.disabled = true;
            btn.classList.add('opacity-75', 'cursor-not-allowed');
            // Change text temporarily (optional, indicator handles visual)
            const span = btn.querySelector('span');
            if (span) span.innerText = 'Evaluating...';
        }
    });
});
