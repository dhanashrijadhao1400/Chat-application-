 let ws = null;
        let username = '';
        let typingTimeout = null;
        let isTyping = false;

        // Initialize WebSocket connection
        function connectWebSocket() {
            // Change this URL to match your Python server
            ws = new WebSocket('ws://localhost:8765');
            
            ws.onopen = function(event) {
                console.log('Connected to WebSocket server');
                updateConnectionStatus(true);
            };
            
            ws.onmessage = function(event) {
                const data = JSON.parse(event.data);
                handleMessage(data);
            };
            
            ws.onclose = function(event) {
                console.log('Disconnected from WebSocket server');
                updateConnectionStatus(false);
                // Attempt to reconnect after 3 seconds
                setTimeout(connectWebSocket, 3000);
            };
            
            ws.onerror = function(error) {
                console.error('WebSocket error:', error);
                updateConnectionStatus(false);
            };
        }

        function updateConnectionStatus(connected) {
            const statusEl = document.getElementById('connectionStatus');
            if (connected) {
                statusEl.textContent = '● Connected';
                statusEl.className = 'connection-status status-connected';
            } else {
                statusEl.textContent = '● Disconnected';
                statusEl.className = 'connection-status status-disconnected';
            }
        }

        function joinChat() {
            const usernameInput = document.getElementById('usernameInput');
            const enteredUsername = usernameInput.value.trim();
            
            if (enteredUsername === '') {
                alert('Please enter a username');
                return;
            }
            
            if (ws && ws.readyState === WebSocket.OPEN) {
                username = enteredUsername;
                
                // Send join message
                const joinMessage = {
                    type: 'join',
                    username: username,
                    timestamp: new Date().toISOString()
                };
                
                ws.send(JSON.stringify(joinMessage));
                
                // Hide user setup and show chat interface
                document.getElementById('userSetup').classList.add('hidden');
                document.getElementById('chatInput').classList.remove('hidden');
                
                // Focus on message input
                document.getElementById('messageInput').focus();
                
                // Add event listeners
                setupEventListeners();
            } else {
                alert('Not connected to server. Please wait and try again.');
            }
        }

        function setupEventListeners() {
            const messageInput = document.getElementById('messageInput');
            
            // Send message on Enter key
            messageInput.addEventListener('keypress', function(event) {
                if (event.key === 'Enter') {
                    sendMessage();
                }
            });
            
            // Handle typing indicator
            messageInput.addEventListener('input', function() {
                if (!isTyping) {
                    isTyping = true;
                    sendTypingStatus(true);
                }
                
                clearTimeout(typingTimeout);
                typingTimeout = setTimeout(() => {
                    isTyping = false;
                    sendTypingStatus(false);
                }, 1000);
            });
        }

        function sendMessage() {
            const messageInput = document.getElementById('messageInput');
            const messageText = messageInput.value.trim();
            
            if (messageText === '' || !ws || ws.readyState !== WebSocket.OPEN) {
                return;
            }
            
            const message = {
                type: 'message',
                username: username,
                content: messageText,
                timestamp: new Date().toISOString()
            };
            
            ws.send(JSON.stringify(message));
            messageInput.value = '';
            
            // Stop typing indicator
            if (isTyping) {
                isTyping = false;
                sendTypingStatus(false);
            }
        }

        function sendTypingStatus(typing) {
            if (ws && ws.readyState === WebSocket.OPEN) {
                const typingMessage = {
                    type: 'typing',
                    username: username,
                    typing: typing
                };
                ws.send(JSON.stringify(typingMessage));
            }
        }

        function handleMessage(data) {
            switch (data.type) {
                case 'message':
                    displayMessage(data);
                    break;
                case 'join':
                    displaySystemMessage(`${data.username} joined the chat`);
                    break;
                case 'leave':
                    displaySystemMessage(`${data.username} left the chat`);
                    break;
                case 'users_count':
                    updateUsersCount(data.count);
                    break;
                case 'typing':
                    handleTypingIndicator(data);
                    break;
            }
        }

        function displayMessage(data) {
            const messagesContainer = document.getElementById('chatMessages');
            const messageDiv = document.createElement('div');
            
            const isOwnMessage = data.username === username;
            messageDiv.className = `message ${isOwnMessage ? 'own' : 'other'}`;
            
            const time = new Date(data.timestamp).toLocaleTimeString([], {
                hour: '2-digit',
                minute: '2-digit'
            });
            
            messageDiv.innerHTML = `
                ${!isOwnMessage ? `<div class="message-author">${data.username}</div>` : ''}
                <div class="message-content">${escapeHtml(data.content)}</div>
                <div class="message-time">${time}</div>
            `;
            
            messagesContainer.appendChild(messageDiv);
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        }

        function displaySystemMessage(text) {
            const messagesContainer = document.getElementById('chatMessages');
            const messageDiv = document.createElement('div');
            messageDiv.className = 'message system';
            messageDiv.innerHTML = `<div class="message-content">${text}</div>`;
            
            messagesContainer.appendChild(messageDiv);
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        }

        function updateUsersCount(count) {
            document.getElementById('usersOnline').textContent = `👥 Users online: ${count}`;
        }

        function handleTypingIndicator(data) {
            const typingEl = document.getElementById('typingIndicator');
            
            if (data.username !== username) {
                if (data.typing) {
                    typingEl.textContent = `${data.username} is typing...`;
                    typingEl.classList.remove('hidden');
                } else {
                    typingEl.classList.add('hidden');
                }
            }
        }

        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }

        // Initialize connection when page loads
        document.addEventListener('DOMContentLoaded', function() {
            connectWebSocket();
        });