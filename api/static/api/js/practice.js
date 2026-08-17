window.PracticeUI = (function () {
  function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
      const cookies = document.cookie.split(';');
      for (let cookie of cookies) {
        cookie = cookie.trim();
        if (cookie.substring(0, name.length + 1) === (name + '=')) {
          cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
          break;
        }
      }
    }
    return cookieValue;
  }

  function escapeHtml(value) {
    const div = document.createElement('div');
    div.textContent = value == null ? '' : String(value);
    return div.innerHTML;
  }

  function renderBadgeList(items, emptyText, badgeClass) {
    if (!items || items.length === 0) {
      return `<li class="text-sm text-gray-500 italic">${emptyText}</li>`;
    }
    return items
      .map(
        (item) => `
        <li class="flex items-start">
            <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${badgeClass}">
                ${escapeHtml(item)}
            </span>
        </li>`
      )
      .join('');
  }

  // Renders the same markup the old server-rendered partials/feedback.html produced,
  // now built client-side from the JSON the submit endpoint returns.
  function renderFeedback(sessionId, feedback) {
    const strengthsHtml = renderBadgeList(feedback.strengths, 'None identified', 'bg-green-100 text-green-800');
    const improvementsHtml = renderBadgeList(feedback.improvements, 'None identified', 'bg-amber-100 text-amber-800');
    const actionHtml = feedback.is_last_question
      ? `<a href="/sessions/${sessionId}/results/" class="inline-flex items-center px-6 py-3 border border-transparent text-base font-medium rounded-lg shadow-sm text-white bg-blue-600 hover:bg-blue-700">Finish &amp; View Results &rarr;</a>`
      : `<a href="/sessions/${sessionId}/practice/?q=${feedback.next_question}" class="inline-flex items-center px-6 py-3 border border-transparent text-base font-medium rounded-lg shadow-sm text-white bg-blue-600 hover:bg-blue-700">Next Question &rarr;</a>`;

    return `
    <div class="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden mb-8 slide-down">
        <div class="p-6 sm:p-8">
            <div class="flex flex-col sm:flex-row justify-between items-start sm:items-center border-b border-gray-100 pb-6 mb-6 gap-4">
                <div>
                    <h3 class="text-xl font-bold text-gray-900">AI Feedback</h3>
                    <p class="text-sm text-gray-500 mt-1">Evaluated on clarity, depth, and communication.</p>
                </div>
                <div class="flex flex-col items-center score-display" data-score="${feedback.overall_score}">
                    <div class="text-4xl font-extrabold score-text">${feedback.overall_score}</div>
                    <div class="text-xs font-semibold uppercase tracking-wide mt-1 text-gray-500">Overall Score</div>
                </div>
            </div>

            <div class="grid grid-cols-3 gap-4 mb-8">
                <div class="bg-gray-50 p-4 rounded-lg text-center">
                    <div class="text-2xl font-bold score-display-sm" data-score="${feedback.clarity_score}">${feedback.clarity_score}</div>
                    <div class="text-xs text-gray-500 font-medium uppercase mt-1">Clarity</div>
                </div>
                <div class="bg-gray-50 p-4 rounded-lg text-center">
                    <div class="text-2xl font-bold score-display-sm" data-score="${feedback.depth_score}">${feedback.depth_score}</div>
                    <div class="text-xs text-gray-500 font-medium uppercase mt-1">Depth</div>
                </div>
                <div class="bg-gray-50 p-4 rounded-lg text-center">
                    <div class="text-2xl font-bold score-display-sm" data-score="${feedback.communication_score}">${feedback.communication_score}</div>
                    <div class="text-xs text-gray-500 font-medium uppercase mt-1">Comm</div>
                </div>
            </div>

            <div class="prose prose-sm max-w-none text-gray-700 mb-8">
                <p>${escapeHtml(feedback.text_feedback)}</p>
            </div>

            <div class="grid grid-cols-1 sm:grid-cols-2 gap-6">
                <div>
                    <h4 class="flex items-center text-sm font-bold text-gray-900 mb-3">Strengths</h4>
                    <ul class="space-y-2">${strengthsHtml}</ul>
                </div>
                <div>
                    <h4 class="flex items-center text-sm font-bold text-gray-900 mb-3">To Improve</h4>
                    <ul class="space-y-2">${improvementsHtml}</ul>
                </div>
            </div>
        </div>

        <div class="bg-gray-50 px-6 py-4 sm:px-8 border-t border-gray-200 flex justify-end">
            ${actionHtml}
        </div>
    </div>`;
  }

  return { getCookie, renderFeedback };
})();

document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('practice-form');
  if (!form) return;

  form.addEventListener('submit', async (e) => {
    e.preventDefault();

    const submitBtn = document.getElementById('submit-answer-btn');
    const spinner = document.getElementById('loading-spinner');
    const submitUrl = form.dataset.submitUrl;

    submitBtn.disabled = true;
    if (spinner) spinner.style.display = 'inline-block';

    try {
      const response = await fetch(submitUrl, {
        method: 'POST',
        body: new FormData(form),
        headers: {
          'X-CSRFToken': PracticeUI.getCookie('csrftoken'),
        },
      });

      if (!response.ok) {
        throw new Error('Failed to submit answer');
      }

      const feedback = await response.json();
      const feedbackContainer = document.getElementById('feedback-container');
      feedbackContainer.innerHTML = PracticeUI.renderFeedback(feedback.session_id, feedback);

      const practiceContainer = document.querySelector('.session-practice-container');
      if (practiceContainer) practiceContainer.style.display = 'none';
    } catch (error) {
      console.error('Submit error:', error);
      alert('Failed to submit answer. Please try again.');
    } finally {
      submitBtn.disabled = false;
      if (spinner) spinner.style.display = 'none';
    }
  });
});
