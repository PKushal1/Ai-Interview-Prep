// Sidebar toggle for small screens
function toggleSidebar() {
  const sidebar = document.querySelector('.sidebar');
  const content = document.querySelector('.content');
  sidebar.classList.toggle('show');
  content.classList.toggle('shift');
}

// Logout function
function logout() {
  localStorage.removeItem("userToken");
  sessionStorage.clear();
  window.location.href = "login.html";
}

// CAMERA SETUP
const video = document.getElementById('video');
const canvas = document.getElementById('canvas');
const photo = document.getElementById('photo');
const captureButton = document.getElementById('capture');

async function startCamera() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
    video.srcObject = stream;
  } catch (err) {
    alert('Could not access the camera: ' + err);
  }
}

captureButton.addEventListener('click', () => {
  const context = canvas.getContext('2d');
  context.drawImage(video, 0, 0, canvas.width, canvas.height);
  const dataURL = canvas.toDataURL('image/png');
  photo.src = dataURL;
  photo.style.display = 'block';
  canvas.style.display = 'none';
});

// Start camera on page load
window.addEventListener('load', () => {
  startCamera();
});

// Voice to text using Web Speech API
const voiceBtn = document.getElementById('voiceBtn');
const voiceStatus = document.getElementById('voiceStatus');
const transcriptDiv = document.getElementById('transcript');

let recognition;
let recognizing = false;

if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  recognition = new SpeechRecognition();

  recognition.continuous = true;
  recognition.interimResults = true;
  recognition.lang = 'en-US';

  recognition.onstart = () => {
    recognizing = true;
    voiceStatus.textContent = 'Listening... Click the button again to stop.';
    voiceBtn.textContent = 'Stop Voice Input';
  };

  recognition.onerror = (event) => {
    console.error('Speech recognition error', event);
    voiceStatus.textContent = 'Error occurred in recognition: ' + event.error;
  };

  recognition.onend = () => {
    recognizing = false;
    voiceStatus.textContent = 'Voice input stopped.';
    voiceBtn.textContent = 'Start Voice Input';
  };

  recognition.onresult = (event) => {
    let interimTranscript = '';
    let finalTranscript = transcriptDiv.textContent || '';

    for (let i = event.resultIndex; i < event.results.length; ++i) {
      if (event.results[i].isFinal) {
        finalTranscript += event.results[i][0].transcript + '\n';
      } else {
        interimTranscript += event.results[i][0].transcript;
      }
    }

    transcriptDiv.textContent = finalTranscript + interimTranscript;
  };

} else {
  voiceStatus.textContent = 'Sorry, your browser does not support Speech Recognition.';
  voiceBtn.disabled = true;
}

voiceBtn.addEventListener('click', () => {
  if (recognizing) {
    recognition.stop();
    return;
  }
  transcriptDiv.textContent = ''; // Clear before starting
  recognition.start();
});
