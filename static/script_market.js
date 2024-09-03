document.addEventListener("DOMContentLoaded", () => {
    const getIdeaId = () => {
        const bodyElement = document.body;
        const ideaId = bodyElement.dataset.ideaId;
        if (!ideaId) {
            console.error("Idea ID not found in body data attribute");
            return null;
        }
        return ideaId;
    };

    const chatContainer = document.querySelector(".chat-container");
    const chatInput = document.querySelector("#chat-input");
    const sendButton = document.querySelector("#send-btn");
    const deleteButton = document.querySelector("#delete-btn");
    const themeButton = document.querySelector("#theme-btn");

    const toggleTheme = () => {
        document.body.classList.toggle("light-mode");
        themeButton.innerText = document.body.classList.contains("light-mode") ? "dark_mode" : "light_mode";
    };

    const getCookie = (name) => {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    };

    const csrfToken = getCookie('csrftoken');

    const deleteChats = () => {
        const chats = document.querySelectorAll(".chat");
        chats.forEach(chat => chat.remove());

        const ideaId = getIdeaId();
        if (!ideaId) return;

        $.ajax({
            type: "POST",
            url: `/idea/${ideaId}/clear_session_market/`,
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': csrfToken
            },
            success: function(response) {
                console.log("Session data cleared successfully.");
                loadChatHistory(); // Reload the initial message after clearing
            },
            error: function(xhr, textStatus, errorThrown) {
                console.error("Failed to clear session data:", errorThrown);
            }
        });
    };

    const createChatElement = (content, className) => {
        const chatDiv = document.createElement("div");
        chatDiv.classList.add("chat", className);
        const chatDetails = document.createElement("div");
        chatDetails.classList.add("chat-details");
        const chatText = document.createElement("p");
        chatText.innerHTML = content;  // Use innerHTML instead of textContent
        chatDetails.appendChild(chatText);
        chatDiv.appendChild(chatDetails);
        return chatDiv;
    };

    const scrollToBottom = () => {
        chatContainer.scrollTo(0, chatContainer.scrollHeight);
    };

    const loadChatHistory = () => {
        const ideaId = getIdeaId();
        if (!ideaId) return;

        $.ajax({
            type: "GET",
            url: `/idea/${ideaId}/get_conversation_market/`,
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            },
            success: function(response) {
                chatContainer.innerHTML = ''; // Clear existing chats
                if (response.length === 0) {
                    // Append the initial AI message with a special class
                    const initialMessage = "What is your Market strategy?";
                    const initialChatElement = createChatElement(initialMessage, "incoming");
                    initialChatElement.classList.add("initial-message");
                    chatContainer.appendChild(initialChatElement);
                } else {
                    response.forEach((message, index) => {
                        const className = message.role === "user" ? "outgoing" : "incoming";
                        const chatElement = createChatElement(message.content, className);
                        if (index === 0 && message.role === "assistant") {
                            chatElement.classList.add("initial-message");
                        }
                        chatContainer.appendChild(chatElement);
                    });
                }
                // Add a small delay before scrolling to the bottom to ensure rendering is complete
                setTimeout(scrollToBottom, 100);
            },
            error: function(xhr, textStatus, errorThrown) {
                console.error("Failed to load chat history:", errorThrown);
            }
        });
    };

    const sendMessage = () => {
        const userMessage = chatInput.value.trim();
        if (userMessage === "") return;

        const defaultTitle = document.querySelector(".default-title");
        if (defaultTitle) defaultTitle.remove();

        const userChat = createChatElement(userMessage, "outgoing");
        chatContainer.appendChild(userChat);

        chatInput.value = "";

        const typingAnimation = document.createElement("div");
        typingAnimation.classList.add("chat", "incoming");
        typingAnimation.innerHTML = `
            <div class="chat-content">
                <div class="chat-details">
                    <div class="typing-animation">
                        <div class="typing-dot" style="--delay: 0.2s"></div>
                        <div class="typing-dot" style="--delay: 0.3s"></div>
                        <div class="typing-dot" style="--delay: 0.4s"></div>
                    </div>
                </div>
            </div>`;
        chatContainer.appendChild(typingAnimation);
        scrollToBottom();

        const ideaId = getIdeaId();
        if (!ideaId) return;

        $.ajax({
            type: "POST",
            url: `/idea/${ideaId}/market_chat/`,
            data: {
                message: userMessage,
                csrfmiddlewaretoken: csrfToken
            },
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': csrfToken
            },
            success: function(response) {
                typingAnimation.remove();
                const botMessage = response.response_message;
                const botChat = createChatElement(botMessage, "incoming");
                chatContainer.appendChild(botChat);
                scrollToBottom();
            },
            error: function(xhr, textStatus, errorThrown) {
                typingAnimation.remove();
                const errorMessage = "An error occurred. Please try again.";
                const errorChat = createChatElement(errorMessage, "incoming");
                chatContainer.appendChild(errorChat);
                scrollToBottom();
            }
        });
    };

    themeButton.addEventListener("click", toggleTheme);
    deleteButton.addEventListener("click", deleteChats);
    sendButton.addEventListener("click", sendMessage);
    chatInput.addEventListener("keypress", (event) => {
        if (event.key === "Enter" && !event.shiftKey) {
            event.preventDefault();
            sendMessage();
        }
    });

    loadChatHistory();
});