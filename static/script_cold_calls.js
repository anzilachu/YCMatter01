document.addEventListener("DOMContentLoaded", () => {
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

        $.ajax({
            type: "POST",
            url: "/clear_session_cold_calls/",
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': csrfToken
            },
            success: function(response) {
                console.log("Session data cleared successfully.");
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
        chatDetails.innerHTML = content;  // Render HTML content
        chatDiv.appendChild(chatDetails);
        return chatDiv;
    };

    const scrollToBottom = () => {
        chatContainer.scrollTo(0, chatContainer.scrollHeight);
    };

    const loadChatHistory = () => {
        $.ajax({
            type: "GET",
            url: "/get_conversation_cold_calls/",
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            },
            success: function(response) {
                if (response.length === 0) {
                    // Append the initial AI message with a special class
                    const initialMessage = "Let's prepare a cold call script. What is your product or service? Why is it unique compared to existing products or services? Who are you planning to call (e.g., their business or position)?";
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
    
        const csrfTokenInput = document.querySelector('input[name="csrfmiddlewaretoken"]');
        const csrfToken = csrfTokenInput ? csrfTokenInput.value : null;
    
        $.ajax({
            type: "POST",
            url: "/cold_calls_chat/",
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': csrfToken
            },
            data: {
                message: userMessage
            },
            success: function(response) {
                typingAnimation.remove();
                const assistantChat = document.createElement("div");
                assistantChat.classList.add("chat", "incoming");
                assistantChat.innerHTML = `<div class="chat-content"><div class="chat-details">${response.response_message}</div></div>`;
                chatContainer.appendChild(assistantChat);
                scrollToBottom();
            },
            error: function(xhr, textStatus, errorThrown) {
                console.error("Failed to send message:", errorThrown);
                typingAnimation.remove();
            }
        });
    };

    sendButton.addEventListener("click", sendMessage);
    deleteButton.addEventListener("click", deleteChats);
    themeButton.addEventListener("click", toggleTheme);

    chatInput.addEventListener("keypress", (event) => {
        if (event.key === "Enter" && !event.shiftKey) {
            event.preventDefault();
            sendMessage();
        }
    });

    // Load initial chat history
    loadChatHistory();
});
