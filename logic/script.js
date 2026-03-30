const form = document.getElementById("uploadForm");
const loader = document.getElementById("loader");

// form.addEventListener("submit", function () {
//     loader.classList.remove("hidden");
// });

if (form && loader) {
    form.addEventListener("submit", function () {
        loader.classList.remove("hidden");
    });
}

async function sendMessage() {
    const input = document.getElementById("userInput");
    const message = input.value.trim();

    if (!message) return;

    const chatbox = document.getElementById("chatbox");

    // User message
    chatbox.innerHTML += `<div><b>You:</b> ${message}</div>`;

    input.value = "";

    try {
        const response = await fetch("/chat", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                message: message,
                analysis: ANALYSIS_DATA
            })
        });

        const data = await response.json();

        // AI response
        chatbox.innerHTML += `<div><b>AI:</b> ${data.response}</div>`;

        chatbox.scrollTop = chatbox.scrollHeight;

    } catch (error) {
        chatbox.innerHTML += `<div>Error occurred</div>`;
    }
}

// 🎤 Speech Recognition
const micBtn = document.getElementById("micBtn");
const inputField = document.getElementById("userInput");

let recognition;

if ('webkitSpeechRecognition' in window && micBtn) {

    recognition = new webkitSpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = "en-IN";

    micBtn.addEventListener("click", () => {
        recognition.start();
        micBtn.innerText = "🎙️ Listening...";
    });

    recognition.onresult = function(event) {
        const transcript = event.results[0][0].transcript;

        inputField.value = transcript;

        micBtn.innerText = "🎤";
    };

    recognition.onerror = function() {
        micBtn.innerText = "🎤";
        alert("Speech recognition error");
    };

    recognition.onend = function() {
        micBtn.innerText = "🎤";
    };

} else {
    if (micBtn) {
        micBtn.style.display = "none"; // hide mic if not supported
    }
}

function toggleGuidance(index, element) {
    const content = document.getElementById("guidance-" + index);
    const arrow = element.querySelector(".arrow");

    if (!content) return;

    if (content.style.display === "none") {
        content.style.display = "block";
        arrow.style.transform = "rotate(90deg)";
    } else {
        content.style.display = "none";
        arrow.style.transform = "rotate(0deg)";
    }
}

function toggleExplanation(index, element) {

    const allContents = document.querySelectorAll('[id^="explanation-"]');
    const allCards = document.querySelectorAll('.explanation-card');
    const allArrows = document.querySelectorAll('.arrow');

    const content = document.getElementById("explanation-" + index);
    const arrow = element.querySelector(".arrow");

    if (!content) return;

    const isOpen = content.style.display === "block";

    // Close all
    allContents.forEach(c => c.style.display = "none");
    allArrows.forEach(a => a.style.transform = "rotate(0deg)");

    // Toggle only clicked
    if (!isOpen) {
        content.style.display = "block";
        if (arrow) arrow.style.transform = "rotate(90deg)";
    }
}
