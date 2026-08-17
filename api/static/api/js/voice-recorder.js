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

    } catch (error) {
      alert('Microphone access denied. Please allow microphone access.');
      console.error('Microphone error:', error);
    }
  }

  stopRecording() {
    if (this.isRecording && this.mediaRecorder) {
      this.isRecording = false;
      this.mediaRecorder.stop();
      this.mediaRecorder.onstop = () => {
        this.handleRecordingComplete();
      };
    }
  }

  handleRecordingComplete() {
    this.stopBtn.style.display = 'none';
    this.playBtn.style.display = 'inline-block';
    this.deleteBtn.style.display = 'inline-block';
    this.recordingIndicator.style.display = 'none';
    this.stopTimer();

    // Transcribe audio
    this.transcribeAudio();
  }

  async transcribeAudio() {
    const audioBlob = new Blob(this.audioChunks, { type: 'audio/webm' });
    
    this.transcriptionLoading.style.display = 'flex';
    this.transcriptionContainer.style.display = 'none';
    this.transcriptionEditContainer.style.display = 'none';
    this.transcriptionStatus.textContent = 'Converting voice to text...';

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
      this.transcribedTextEdit.value = data.transcribed_text;
      this.confidenceDisplay.textContent = Math.round(data.confidence * 100);
      this.transcriptionStatus.textContent = '✓ Transcription complete';

    } catch (error) {
      console.error('Transcription error:', error);
      this.transcriptionLoading.style.display = 'none';
      alert(`Transcription failed: ${error.message}`);
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
  new VoiceRecorder();
  
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
      document.getElementById('text-mode').style.display = mode === 'text' ? 'block' : 'none';
      document.getElementById('voice-mode').style.display = mode === 'voice' ? 'block' : 'none';
    });
  });
});
