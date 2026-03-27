/* Voice search using Web Speech API */
(function () {
  document.addEventListener("DOMContentLoaded", function () {
    var btn = document.getElementById("voiceSearchBtn");
    var input = document.querySelector('input[name="q"]');
    var form = input ? input.closest("form") : null;

    if (!btn || !input || !form) return;

    var SpeechRecognition =
      window.SpeechRecognition || window.webkitSpeechRecognition;

    if (!SpeechRecognition) {
      btn.style.display = "none";
      return;
    }

    var recognition = new SpeechRecognition();
    recognition.lang = "en-US";
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;

    var listening = false;

    btn.addEventListener("click", function () {
      if (listening) {
        recognition.stop();
        return;
      }
      recognition.start();
    });

    recognition.addEventListener("start", function () {
      listening = true;
      btn.classList.add("btn-danger");
      btn.classList.remove("btn-outline-secondary");
      btn.querySelector("i").className = "bi bi-mic-fill";
      btn.setAttribute("title", "Listening… click to stop");
    });

    recognition.addEventListener("end", function () {
      listening = false;
      btn.classList.remove("btn-danger");
      btn.classList.add("btn-outline-secondary");
      btn.querySelector("i").className = "bi bi-mic";
      btn.setAttribute("title", "Voice search");
    });

    recognition.addEventListener("result", function (e) {
      var transcript = e.results[0][0].transcript.trim();
      if (transcript) {
        input.value = transcript;
        input.focus();
        setTimeout(function () {
          form.submit();
        }, 800);
      }
    });

    recognition.addEventListener("error", function (e) {
      console.warn("Voice recognition error:", e.error);
      if (e.error === "not-allowed") {
        alert("Microphone access denied. Please allow microphone permission.");
      }
    });
  });
})();
