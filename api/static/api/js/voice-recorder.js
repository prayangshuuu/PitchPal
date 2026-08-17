class VoiceRecorder {
  constructor() {
    this.mediaRecorder = null;
    this.audioChunks = [];
    this.isRecording = false;
    this.recordingStartTime = null;
    this.timerInterval = null;
    this.audioContext = null;
    this.analyser = null;
    this.dataArray = null;
    this.animationId = null;

    // Live (in-browser) speech-to-text state
    this.recognition = null;
    this.recognitionActive = false;
    this.speechSupported = false;
    this.finalTranscript = '';
    this.interimTranscript = '';
    this.userEditedTranscript = false;

    this.init();
  }

  init() {
    this.setupElements();
    this.setupEventListeners();
  }

  setupElements() {
    this.startBtn = document.getElementById('start-recording-btn');
    this.stopBtn = document.getElementById('stop-recording-btn');
    this.playBtn = document.getElementById('play-recording-btn');
    this.deleteBtn = document.getElementById('delete-recording-btn');
    this.submitBtn = document.getElementById('submit-voice-btn');
    this.timerDisplay = document.getElementById('recording-timer');
    this.canvas = document.getElementById('waveform-canvas');
    this.transcriptionContainer = document.getElementById('transcription-container');
    this.transcriptionEditContainer = document.getElementById('transcription-edit-container');
    this.transcriptionLoading = document.getElementById('transcription-loading');
    this.transcribedTextDisplay = document.getElementById('transcribed-text');
    this.transcribedTextEdit = document.getElementById('transcription-edit-text');
    this.confidenceDisplay = document.getElementById('confidence-value');
    this.recordingIndicator = document.getElementById('recording-dot');
    this.transcriptionStatus = document.getElementById('transcription-status');
  }

  setupEventListeners() {
    if (this.startBtn) this.startBtn.addEventListener('click', () => this.startRecording());
    if (this.stopBtn) this.stopBtn.addEventListener('click', () => this.stopRecording());
    if (this.playBtn) this.playBtn.addEventListener('click', () => this.playRecording());
    if (this.deleteBtn) this.deleteBtn.addEventListener('click', () => this.deleteRecording());
    if (this.submitBtn) this.submitBtn.addEventListener('click', () => this.submitVoiceAnswer());
    // Once the user manually edits the transcript, stop overwriting it with
    // live/server transcription updates.
    if (this.transcribedTextEdit) {
      this.transcribedTextEdit.addEventListener('input', () => {
        this.userEditedTranscript = true;
      });
    }
  }

  async startRecording() {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      
      this.mediaRecorder = new MediaRecorder(stream);
      this.audioChunks = [];
      this.isRecording = true;
      this.recordingStartTime = Date.now();

      // Setup audio visualization
      this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
      this.analyser = this.audioContext.createAnalyser();
      const source = this.audioContext.createMediaStreamSource(stream);
      source.connect(this.analyser);
      this.analyser.fftSize = 256;
      this.dataArray = new Uint8Array(this.analyser.frequencyBinCount);

      // Collect audio data
      this.mediaRecorder.ondataavailable = (event) => {
        this.audioChunks.push(event.data);
      };

      this.mediaRecorder.start();
      this.startBtn.style.display = 'none';
      this.stopBtn.style.display = 'inline-block';
      this.recordingIndicator.style.display = 'inline-block';
      this.startTimer();
      this.drawWaveform();
      this.startLiveTranscription();

    } catch (error) {
      alert('Microphone access denied. Please allow microphone access.');
      console.error('Microphone error:', error);
    }
  }

  stopRecording() {
    if (this.isRecording && this.mediaRecorder) {
      this.isRecording = false;
      // Stop live recognition first so it has a moment to flush its last
      // final result before we read this.finalTranscript below.
      this.stopLiveTranscription();
      this.mediaRecorder.stop();
      this.mediaRecorder.onstop = () => {
        this.handleRecordingComplete();
      };
    }
  }

  // --- Live (in-browser) speech-to-text ---------------------------------
  // Uses the Web Speech API so the user sees a transcript appear while they
  // are still talking, instead of waiting for the recording to be uploaded
  // and run through server-side transcription. Falls back cleanly (no-op)
  // in browsers that don't support it (e.g. Firefox) — the existing
  // server-side transcription in transcribeAudio() still runs regardless.
  startLiveTranscription() {
    const SpeechRecognitionImpl = window.SpeechRecognition || window.webkitSpeechRecognition;
    this.finalTranscript = '';
    this.interimTranscript = '';
    this.userEditedTranscript = false;
    this.recognitionActive = false;
    this.speechSupported = !!SpeechRecognitionImpl;

    if (!this.speechSupported) return;

    this.recognition = new SpeechRecognitionImpl();
    this.recognition.continuous = true;
    this.recognition.interimResults = true;
    this.recognition.lang = (navigator.language || 'en-US');
    this.recognition.maxAlternatives = 1;

    this.recognition.onresult = (event) => {
      let interim = '';
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const transcript = event.results[i][0].transcript;
        if (event.results[i].isFinal) {
          this.finalTranscript += (this.finalTranscript ? ' ' : '') + transcript.trim();
        } else {
          interim += transcript;
        }
      }
      this.interimTranscript = interim;
      this.updateLiveTranscript();
    };

    this.recognition.onstart = () => {
      // Confirms the mic is actually being listened to — fires before any
      // words are recognized, so the user gets feedback immediately instead
      // of a blank screen until their first words resolve.
      if (!this.finalTranscript && !this.interimTranscript) {
        if (this.transcriptionContainer.style.display === 'none') {
          this.transcriptionContainer.style.display = 'block';
          this.transcriptionEditContainer.style.display = 'block';
          this.transcriptionLoading.style.display = 'none';
        }
        this.transcriptionStatus.textContent = '🎙️ Listening…';
      }
    };

    this.recognition.onerror = (event) => {
      console.warn('Speech recognition error:', event.error);
      if (event.error === 'not-allowed' || event.error === 'service-not-allowed') {
        // Permission denied specifically for speech recognition — stop
        // trying; the recording itself is unaffected.
        this.speechSupported = false;
      }
      // Other errors (e.g. 'no-speech', 'network', 'aborted') are recoverable:
      // onend fires next and, while still recording, we restart below.
    };

    this.recognition.onend = () => {
      this.recognitionActive = false;
      if (this.isRecording && this.speechSupported) {
        // Chrome/Edge stop the recognizer after a pause in speech; restart
        // it immediately so live transcription keeps running for the whole
        // recording, not just the first utterance.
        setTimeout(() => this.startRecognitionInstance(), 250);
      }
    };

    this.startRecognitionInstance();
  }

  startRecognitionInstance() {
    if (!this.isRecording || !this.recognition || this.recognitionActive) return;
    try {
      this.recognition.start();
      this.recognitionActive = true;
    } catch (e) {
      // start() throws if invoked while already running; safe to ignore.
    }
  }

  stopLiveTranscription() {
    if (this.recognition) {
      try { this.recognition.stop(); } catch (e) { /* already stopped */ }
    }
  }

  updateLiveTranscript() {
    const combined = `${this.finalTranscript} ${this.interimTranscript}`.trim();
    if (!combined) return;

    if (this.transcriptionContainer.style.display === 'none') {
      this.transcriptionContainer.style.display = 'block';
      this.transcriptionEditContainer.style.display = 'block';
      this.transcriptionLoading.style.display = 'none';
    }

    this.transcribedTextDisplay.value = combined;
    if (!this.userEditedTranscript) {
      this.transcribedTextEdit.value = combined;
    }
    this.transcriptionStatus.textContent = '🎙️ Listening… transcribing live';
    this.confidenceDisplay.textContent = '~90';
  }

  handleRecordingComplete() {
    this.stopBtn.style.display = 'none';
    this.playBtn.style.display = 'inline-block';
    this.deleteBtn.style.display = 'inline-block';
    this.recordingIndicator.style.display = 'none';
    this.stopTimer();

    const liveText = this.finalTranscript.trim();
    if (liveText) {
      this.transcriptionLoading.style.display = 'none';
      this.transcriptionContainer.style.display = 'block';
      this.transcriptionEditContainer.style.display = 'block';
      this.transcribedTextDisplay.value = liveText;
      if (!this.userEditedTranscript) this.transcribedTextEdit.value = liveText;
      this.transcriptionStatus.textContent = 'Refining transcript…';
    }

    // Always run server-side (Gemini) transcription too: it's more accurate
    // for accents/background noise and is the only source of text in
    // browsers without live speech recognition support.
    this.transcribeAudio(!!liveText);
  }

  async transcribeAudio(hasLiveDraft = false) {
    const audioBlob = new Blob(this.audioChunks, { type: 'audio/webm' });

    if (!hasLiveDraft) {
      this.transcriptionLoading.style.display = 'flex';
      this.transcriptionContainer.style.display = 'none';
      this.transcriptionEditContainer.style.display = 'none';
      this.transcriptionStatus.textContent = 'Converting voice to text...';
    }

    try {
      const formData = new FormData();
      formData.append('audio_file', audioBlob, 'recording.webm');

      // Get session ID from URL or form
      const sessionId = document.querySelector('[data-session-id]')?.dataset.sessionId ||
                        window.location.pathname.split('/')[2];

      const response = await fetch(`/sessions/${sessionId}/transcribe-voice/`, {
        method: 'POST',
        body: formData,
        headers: {
          // fetch takes care of multipart/form-data boundary
        }
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error || 'Transcription failed');
      }

      const data = await response.json();

      this.transcriptionLoading.style.display = 'none';
      this.transcriptionContainer.style.display = 'block';
      this.transcriptionEditContainer.style.display = 'block';

      this.transcribedTextDisplay.value = data.transcribed_text;
      if (!this.userEditedTranscript) {
        this.transcribedTextEdit.value = data.transcribed_text;
      }
      this.confidenceDisplay.textContent = Math.round(data.confidence * 100);
      this.transcriptionStatus.textContent = '✓ Transcription complete';

    } catch (error) {
      console.error('Transcription error:', error);
      this.transcriptionLoading.style.display = 'none';
      if (hasLiveDraft) {
        // We already have a usable live transcript — don't block the user
        // with an alert, just let them know the server refinement failed.
        this.transcriptionContainer.style.display = 'block';
        this.transcriptionEditContainer.style.display = 'block';
        this.transcriptionStatus.textContent = '⚠ Using live transcript (server refinement unavailable)';
      } else {
        alert(`Transcription failed: ${error.message}`);
      }
    }
  }

  playRecording() {
    if (this.audioChunks.length === 0) return;
    const audioBlob = new Blob(this.audioChunks, { type: 'audio/webm' });
    const audioUrl = URL.createObjectURL(audioBlob);
    const audio = new Audio(audioUrl);
    audio.play();
  }

  deleteRecording() {
    this.audioChunks = [];
    this.isRecording = false;
    this.stopLiveTranscription();
    this.finalTranscript = '';
    this.interimTranscript = '';
    this.userEditedTranscript = false;
    this.transcriptionContainer.style.display = 'none';
    this.transcriptionEditContainer.style.display = 'none';
    this.playBtn.style.display = 'none';
    this.deleteBtn.style.display = 'none';
    this.startBtn.style.display = 'inline-block';
    this.timerDisplay.textContent = '0:00';
    if (this.audioContext) {
      this.audioContext.close();
      this.audioContext = null;
    }
    const ctx = this.canvas.getContext('2d');
    ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
  }

  async submitVoiceAnswer() {
    const transcribedText = this.transcribedTextEdit.value;
    
    if (!transcribedText.trim()) {
      alert('Please record an answer first');
      return;
    }

    const sessionId = document.querySelector('[data-session-id]')?.dataset.sessionId || 
                      window.location.pathname.split('/')[2];
    const questionId = document.querySelector('[data-question-id]')?.dataset.questionId;

    const formData = new FormData();
    formData.append('question_id', questionId);
    formData.append('answer_text', transcribedText);
    formData.append('answer_type', 'voice');

    const submitBtn = this.submitBtn;
    const originalText = submitBtn.textContent;
    submitBtn.textContent = 'Submitting...';
    submitBtn.disabled = true;

    try {
      const response = await fetch(`/sessions/${sessionId}/submit/`, {
        method: 'POST',
        body: formData,
        headers: {
          'X-CSRFToken': PracticeUI.getCookie('csrftoken')
        }
      });

      if (!response.ok) {
        throw new Error('Failed to submit answer');
      }

      const data = await response.json();
      const feedbackDiv = document.getElementById('feedback-container');
      feedbackDiv.innerHTML = PracticeUI.renderFeedback(data.session_id, data);

      // Hide the practice container
      document.querySelector('.session-practice-container').style.display = 'none';

    } catch (error) {
      console.error('Submit error:', error);
      alert('Failed to submit answer. Please try again.');
    } finally {
      submitBtn.textContent = originalText;
      submitBtn.disabled = false;
    }
  }

  startTimer() {
    this.timerInterval = setInterval(() => {
      const elapsed = Math.floor((Date.now() - this.recordingStartTime) / 1000);
      const minutes = Math.floor(elapsed / 60);
      const seconds = elapsed % 60;
      this.timerDisplay.textContent = `${minutes}:${seconds.toString().padStart(2, '0')}`;

      // Auto-stop at 5 minutes
      if (elapsed >= 300) {
        this.stopRecording();
      }
    }, 100);
  }

  stopTimer() {
    clearInterval(this.timerInterval);
  }

  drawWaveform() {
    if (!this.isRecording) return;

    const ctx = this.canvas.getContext('2d');
    
    // Resize canvas if needed
    const rect = this.canvas.getBoundingClientRect();
    if (this.canvas.width !== rect.width || this.canvas.height !== rect.height) {
        this.canvas.width = rect.width;
        this.canvas.height = rect.height;
    }
    
    this.analyser.getByteFrequencyData(this.dataArray);

    ctx.fillStyle = '#F9FAFB';
    ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);

    ctx.strokeStyle = '#3B82F6';
    ctx.lineWidth = 2;
    ctx.beginPath();

    const sliceWidth = this.canvas.width / this.dataArray.length;
    let x = 0;

    for (let i = 0; i < this.dataArray.length; i++) {
      const v = this.dataArray[i] / 128.0;
      const y = (v * this.canvas.height) / 2;

      if (i === 0) {
        ctx.moveTo(x, y);
      } else {
        ctx.lineTo(x, y);
      }

      x += sliceWidth;
    }

    ctx.lineTo(this.canvas.width, this.canvas.height / 2);
    ctx.stroke();

    this.animationId = requestAnimationFrame(() => this.drawWaveform());
  }

}

// Initialize on DOM load
document.addEventListener('DOMContentLoaded', () => {
  const voiceRecorder = new VoiceRecorder();

  // Toggle between text and voice mode
  document.querySelectorAll('.mode-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
      // Prevent default form submission or other actions if this is inside a form
      e.preventDefault();

      document.querySelectorAll('.mode-btn').forEach(b => {
          b.classList.remove('active', 'bg-blue-100', 'text-blue-700');
          b.classList.add('text-gray-600', 'hover:bg-gray-100');
      });

      e.target.classList.remove('text-gray-600', 'hover:bg-gray-100');
      e.target.classList.add('active', 'bg-blue-100', 'text-blue-700');

      const mode = e.target.dataset.mode;

      // Switching away from voice mode mid-recording would otherwise leave
      // the mic and live speech recognition running invisibly in the background.
      if (mode !== 'voice' && voiceRecorder.isRecording) {
        voiceRecorder.stopRecording();
      }

      document.getElementById('text-mode').style.display = mode === 'text' ? 'block' : 'none';
      document.getElementById('voice-mode').style.display = mode === 'voice' ? 'block' : 'none';
    });
  });
});
