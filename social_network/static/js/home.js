// ==================== МЕНЕДЖЕР МОДАЛЬНЫХ ОКОН ====================
const ModalManager = {
    groups: {
        main: ['menu-toggle', 'profile-toggle', 'setting-toggle', 'form1-toggle', 'form2-toggle', 'color_theme-toggle', 'wallet-toggle', 'other-profile-toggle', 'security-toggle'],
        subscription: ['check-subscription-toggle', 'subscribe-month-toggle', 'subscribe-year-toggle', 'bin_mouth-toggle', 'bin_premium_mouth-toggle', 'bin_years-toggle', 'bin_premium_years-toggle'],
        wallet: ['deposit-toggle', 'add_card-toggle'],
        chat: ['chat-toggle']
    },
    
    closeGroup(groupName) {
        if (this.groups[groupName]) {
            this.groups[groupName].forEach(id => {
                const cb = document.getElementById(id);ъ
                if (cb) cb.checked = false;
            });
        }
    },
    
    closeAllExceptChat() {
        Object.keys(this.groups).forEach(group => {
            if (group !== 'chat') {
                this.closeGroup(group);
            }
        });
    },
    
    closeAll() {
        Object.keys(this.groups).forEach(group => {
            this.closeGroup(group);
        });
    }
};

// ==================== ПЕРЕМЕННЫЕ ЧАТА ====================
let currentChatUser = null;
let chatSocket = null;
let reconnectAttempts = 0;
const maxReconnectAttempts = 5;
const reconnectDelay = 1000;

// ==================== ОСНОВНЫЕ ФУНКЦИИ ====================
document.addEventListener('DOMContentLoaded', function() {
    initializeEventListeners();
    initializeTheme();
    initializeWallet();
    initializeProfilePreview();
    initializeSecurity();
    setupWebSocketReconnect();
    loadRecentContacts();
    
    // Обновляем контакты каждые 30 секунд
    setInterval(loadRecentContacts, 30000);
});

function initializeEventListeners() {
    // Обработчики для оверлеев
    const overlays = document.querySelectorAll('.overlay, .profile-overlay, .other-profile-overlay, .setting-overlay, .form1-overlay, .form2-overlay, .color_theme-overlay, .wallet-overlay, .check-subscription-overlay, .subscribe-month-overlay, .subscribe-year-overlay, .bin_mouth-overlay, .bin_premium_mouth-overlay, .bin_years-overlay, .bin_premium_years-overlay, .deposit-overlay, .add_card-overlay, .security-overlay');
    
    overlays.forEach(overlay => {
        overlay.addEventListener('click', (e) => {
            if (e.target === overlay) {
                ModalManager.closeAllExceptChat(); // Не закрываем чат
            }
        });
    });

    // Обработчик для чата
    const chatOverlay = document.querySelector('.chat-overlay');
    if (chatOverlay) {
        chatOverlay.addEventListener('click', (e) => {
            if (e.target === chatOverlay) {
                closeChat();
            }
        });
    }

    // Обработчики ввода
    const chatInput = document.getElementById('chat-input');
    if (chatInput) {
        chatInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                sendMessage();
            }
        });
    }

    const searchInput = document.getElementById('searchInput');
    if (searchInput) {
        searchInput.addEventListener('input', searchUsers);
        
        document.addEventListener('click', function(e) {
            if (!searchInput.contains(e.target) && !document.getElementById('searchResults').contains(e.target)) {
                document.getElementById('searchResults').innerHTML = '';
                const recentContactsDiv = document.getElementById('recent-contacts');
                if (recentContactsDiv && searchInput.value.trim().length === 0) {
                    recentContactsDiv.style.display = "block";
                }
            }
        });
    }

    // Обработчики для упоминаний
    document.addEventListener('click', function(e) {
        // Упоминания в сообщениях
        if (e.target.matches('.message-mention, .profile-mention')) {
            e.preventDefault();
            e.stopPropagation();
            const username = e.target.getAttribute('data-username')?.replace('@', '');
            if (username) {
                openUserProfile(username);
            }
        }
        
        // Упоминания в профилях
        if (e.target.matches('.other-profile-form .message-mention, .other-profile-form .profile-mention')) {
            e.preventDefault();
            e.stopPropagation();
            const username = e.target.getAttribute('data-username')?.replace('@', '');
            if (username) {
                openUserProfile(username);
            }
        }
        
        // Ссылки в профилях
        if (e.target.matches('.profile-preview-value a[href*="profile="]')) {
            e.preventDefault();
            const url = new URL(e.target.href);
            const profileUsername = url.searchParams.get('profile');
            if (profileUsername) {
                openUserProfile(profileUsername);
            }
        }
    });

    // Закрытие меню при клике на ссылки
    const sideMenuLinks = document.querySelectorAll('.side-menu label, .side-menu a');
    sideMenuLinks.forEach(link => {
        link.addEventListener('click', () => {
            const menuToggle = document.getElementById('menu-toggle');
            if(menuToggle) menuToggle.checked = false;
        });
    });

    // Обработчики для подписок
    setupSubscription('terms-bin', 'subscribe-bin');
    setupSubscription('terms-premium', 'subscribe-premium');
    setupSubscription('terms-bin-year', 'subscribe-bin-year');
    setupSubscription('terms-premium-year', 'subscribe-premium-year');
}

function initializeTheme() {
    const themeSelect = document.getElementById('themeSelect');
    const applyBtn = document.getElementById('applyThemeBtn');
    const userSubscribe = "{{ user.subscribe }}";  
    const body = document.body;

    const savedTheme = localStorage.getItem('selectedTheme');
    if (savedTheme) {
        body.classList.add(`theme-${savedTheme}`);
        if (themeSelect) themeSelect.value = savedTheme;
    }

    if (userSubscribe === "Basic") {
        const pinkOption = themeSelect?.querySelector('option[value="pink"]');
        const greenOption = themeSelect?.querySelector('option[value="green"]');
        if (pinkOption) pinkOption.disabled = true;
        if (greenOption) greenOption.disabled = true;
    }

    if (applyBtn) {
        applyBtn.addEventListener('click', () => {
            const selected = themeSelect.value;

            if ((selected === "pink" || selected === "green") && userSubscribe === "Basic") {
                alert("❌ This theme is available only for subscribers!");
                return;
            }

            body.classList.remove('theme-light', 'theme-dark', 'theme-pink', 'theme-green');
            body.classList.add(`theme-${selected}`);
            localStorage.setItem('selectedTheme', selected);
        });
    }
}

function initializeWallet() {
    setTimeout(() => {
        updateAllCurrenciesFromUserWallet();
        observeWalletChanges();
    }, 100);

    const currencySelect = document.querySelector('select[name="currency"]');
    if (currencySelect) {
        currencySelect.addEventListener('change', function() {
            setTimeout(() => {
                updateAllCurrenciesFromUserWallet();
            }, 500);
        });
    }
}

function initializeProfilePreview() {
    const usernameInput = document.getElementById('username-input');
    const descriptionInput = document.getElementById('description-input');
    const tagInput = document.getElementById('tag-input');
    const birthdayDay = document.getElementById('birthday-day');
    const birthdayMonth = document.getElementById('birthday-month');
    const birthdayYear = document.getElementById('birthday-year');
    const avatarInput = document.getElementById('avatarInput');
    
    const previewUsername = document.getElementById('preview-username');
    const previewDescription = document.getElementById('preview-description');
    const previewTag = document.getElementById('preview-tag');
    const previewBirthday = document.getElementById('preview-birthday');
    const previewAvatar = document.getElementById('preview-avatar');
    const avatarInputImg = document.getElementById('avatarInput-img');

    // Username preview
    if (usernameInput && previewUsername) {
        usernameInput.addEventListener('input', function() {
            const value = this.value.trim();
            previewUsername.textContent = value || '{{ user.username }}';
        });
    }

    // Description preview
    if (descriptionInput && previewDescription) {
        descriptionInput.addEventListener('input', function() {
            const value = this.value.trim();
            previewDescription.textContent = value || 'No description';
        });
    }

    // Tag preview
    if (tagInput && previewTag) {
        tagInput.addEventListener('input', function() {
            const value = this.value.trim();
            previewTag.textContent = value || '{{ user.your_tag }}';
        });
    }

    // Birthday preview
    function updateBirthdayPreview() {
        const day = birthdayDay?.value;
        const month = birthdayMonth?.value;
        const year = birthdayYear?.value;
        
        if (day && month && year && previewBirthday) {
            const monthNames = ['January', 'February', 'March', 'April', 'May', 'June',
                              'July', 'August', 'September', 'October', 'November', 'December'];
            const monthName = monthNames[parseInt(month) - 1];
            previewBirthday.textContent = `${monthName} ${day}, ${year}`;
        }
    }

    if (birthdayDay) birthdayDay.addEventListener('change', updateBirthdayPreview);
    if (birthdayMonth) birthdayMonth.addEventListener('change', updateBirthdayPreview);
    if (birthdayYear) birthdayYear.addEventListener('change', updateBirthdayPreview);

    // Avatar upload
    if (avatarInput && previewAvatar && avatarInputImg) {
        avatarInput.addEventListener('change', function(event) {
            const file = event.target.files[0];
            if (!file) return;

            const allowedTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/webp'];
            if (!allowedTypes.includes(file.type)) {
                alert('⚠️ Only JPG, PNG, GIF or WEBP images are allowed.');
                event.target.value = '';
                return;
            }

            const reader = new FileReader();
            reader.onload = function(e) {
                const imageUrl = e.target.result;
                previewAvatar.src = imageUrl;
                avatarInputImg.src = imageUrl;
            };
            reader.readAsDataURL(file);
        });
    }

    // Background handling
    initializeBackground();
}

function initializeBackground() {
    const backgroundInput = document.getElementById('backgroundInput');
    const previewBackground = document.getElementById('preview-background');
    const mainProfileBackground = document.getElementById('main-profile-background');
    const deleteBackgroundBtn = document.querySelector('.btn-delete-background');
    const userSubscribe = "{{ user.subscribe }}";

    function syncBackgrounds() {
        if (previewBackground && mainProfileBackground) {
            if (previewBackground.style.backgroundImage && previewBackground.style.backgroundImage !== 'none') {
                mainProfileBackground.style.backgroundImage = previewBackground.style.backgroundImage;
                mainProfileBackground.style.display = previewBackground.style.display;
            }
            else if (mainProfileBackground.style.backgroundImage && mainProfileBackground.style.backgroundImage !== 'none') {
                previewBackground.style.backgroundImage = mainProfileBackground.style.backgroundImage;
                previewBackground.style.display = mainProfileBackground.style.display;
            }
        }
        
        if (deleteBackgroundBtn) {
            const hasBackground = (previewBackground && previewBackground.style.backgroundImage && previewBackground.style.backgroundImage !== 'none') ||
                                (mainProfileBackground && mainProfileBackground.style.backgroundImage && mainProfileBackground.style.backgroundImage !== 'none');
            deleteBackgroundBtn.disabled = !hasBackground;
        }
    }

    syncBackgrounds();

    if (backgroundInput) {
        updateBackgroundAccessibility();

        backgroundInput.addEventListener('change', (e) => {
            const file = e.target.files[0];
            if (!file) return;

            if (userSubscribe === 'Basic') {
                alert('Background feature available only for Bin+ and Bin Premium subscriptions');
                e.target.value = '';
                return;
            }
            
            if (userSubscribe === 'Bin+' && file.type === 'image/gif') {
                alert('GIF backgrounds available only for Bin Premium subscription');
                e.target.value = '';
                return;
            }

            const reader = new FileReader();
            reader.onload = function(event) {
                if (previewBackground) {
                    previewBackground.style.backgroundImage = `url('${event.target.result}')`;
                    previewBackground.style.display = 'block';
                }
                
                if (deleteBackgroundBtn) {
                    deleteBackgroundBtn.disabled = false;
                }
                
                syncBackgrounds();
            };
            reader.readAsDataURL(file);
        });
    }
}

function initializeSecurity() {
    const newPassword = document.getElementById('new-password');
    const confirmPassword = document.getElementById('confirm-password');
    
    function validatePasswords() {
        if (newPassword && confirmPassword && newPassword.value !== confirmPassword.value) {
            confirmPassword.setCustomValidity('Passwords do not match');
        } else if (confirmPassword) {
            confirmPassword.setCustomValidity('');
        }
    }
    
    if (newPassword && confirmPassword) {
        newPassword.addEventListener('input', validatePasswords);
        confirmPassword.addEventListener('input', validatePasswords);
    }
    
    document.addEventListener('click', function(e) {
        const passwordSection = document.getElementById('password-section');
        if (passwordSection && passwordSection.classList.contains('expanded') && 
            !passwordSection.contains(e.target)) {
            passwordSection.classList.remove('expanded');
            setTimeout(() => {
                const passwordForm = document.getElementById('password-form');
                if (passwordForm) passwordForm.style.display = 'none';
            }, 300);
        }
    });
}

// ==================== ФУНКЦИИ БЕЗОПАСНОСТИ ====================
function togglePasswordForm() {
    const passwordSection = document.getElementById('password-section');
    const passwordForm = document.getElementById('password-form');
    
    if (!passwordSection || !passwordForm) return;
    
    if (passwordSection.classList.contains('expanded')) {
        passwordSection.classList.remove('expanded');
        setTimeout(() => {
            passwordForm.style.display = 'none';
        }, 300);
    } else {
        passwordForm.style.display = 'block';
        setTimeout(() => {
            passwordSection.classList.add('expanded');
        }, 10);
    }
}

// ==================== ФУНКЦИИ ФОНА ====================
function updateBackgroundAccessibility() {
    const backgroundInput = document.getElementById('backgroundInput');
    const backgroundLabel = backgroundInput ? backgroundInput.closest('label') : null;
    const userSubscribe = "{{ user.subscribe }}";
    
    if (backgroundInput && backgroundLabel) {
        if (userSubscribe === 'Basic') {
            backgroundInput.disabled = true;
            backgroundLabel.style.opacity = '0.6';
            backgroundLabel.style.cursor = 'not-allowed';
            backgroundInput.title = "Background feature available for Bin+ and Bin Premium subscribers";
        } else {
            backgroundInput.disabled = false;
            backgroundLabel.style.opacity = '1';
            backgroundLabel.style.cursor = 'pointer';
            
            if (userSubscribe === 'Bin+') {
                backgroundInput.accept = "image/*";
                backgroundInput.title = "Images only (GIF backgrounds available for Bin Premium)";
            } else if (userSubscribe === 'Bin_premium') {
                backgroundInput.accept = "image/*,image/gif";
                backgroundInput.title = "All image formats including GIF";
            }
        }
    }
}

window.confirmBackgroundReset = function() {
    const lang = "{{ user.language|default:'English' }}";
    const confirmMsg = lang === 'Українська'
        ? "Ви впевнені, що хочете видалити фон профілю?"
        : "Are you sure you want to remove the background?";

    if (confirm(confirmMsg)) {
        const previewBackground = document.getElementById('preview-background');
        const mainProfileBackground = document.getElementById('main-profile-background');
        const deleteBackgroundBtn = document.querySelector('.btn-delete-background');
        
        if (previewBackground) {
            previewBackground.style.backgroundImage = 'none';
            previewBackground.style.display = 'none';
        }
        
        if (mainProfileBackground) {
            mainProfileBackground.style.backgroundImage = 'none';
            mainProfileBackground.style.display = 'none';
        }
        
        if (deleteBackgroundBtn) {
            deleteBackgroundBtn.disabled = true;
        }
        
        let removeBackgroundInput = document.getElementById('remove-background-input');
        if (!removeBackgroundInput) {
            removeBackgroundInput = document.createElement('input');
            removeBackgroundInput.type = 'hidden';
            removeBackgroundInput.name = 'remove_background';
            removeBackgroundInput.id = 'remove-background-input';
            const editProfileForm = document.getElementById('edit-profile-form');
            if (editProfileForm) {
                editProfileForm.appendChild(removeBackgroundInput);
            }
        }
        removeBackgroundInput.value = 'true';
        
        const successMsg = lang === 'Українська' 
            ? 'Фон успішно видалено!' 
            : 'Background successfully removed!';
        alert(successMsg);
    }
};

// ==================== ФУНКЦИИ ГАМАНЦА ====================
function formatNumber(number) {
    return number.toFixed(2).replace(/\d(?=(\d{3})+\.)/g, '$& ');
}

function getUserWalletAmount() {
    const walletText = document.getElementById('wallet-amount')?.textContent;
    if (!walletText) return 0;
    
    const amountMatch = walletText.match(/([\d\s,]+\.?\d*)/);
    if (amountMatch) {
        const amountStr = amountMatch[1].replace(/\s/g, '').replace(',', '');
        return parseFloat(amountStr);
    }
    return 0;
}

function getUserCurrency() {
    const select = document.querySelector('select[name="currency"]');
    return select ? select.value : 'USD';
}

function updateAllCurrenciesFromUserWallet() {
    const userAmount = getUserWalletAmount();
    const userCurrency = getUserCurrency();
    
    if (userAmount === 0) return;
    
    const exchangeRates = {
        'USD': {'USD': 1.0, 'EUR': 0.87, 'GBP': 0.773, 'UAH': 42.1},
        'UAH': {'USD': 0.024, 'EUR': 0.021, 'GBP': 0.0186, 'UAH': 1.0}
    };
    
    const rates = exchangeRates[userCurrency];
    
    const usdAmount = document.getElementById('usd-amount');
    const eurAmount = document.getElementById('eur-amount');
    const gbpAmount = document.getElementById('gbp-amount');
    const uahAmount = document.getElementById('uah-amount');
    
    if (usdAmount) {
        if (userCurrency !== 'USD') {
            usdAmount.textContent = `${formatNumber(userAmount * rates.USD)}$ USD`;
        } else {
            usdAmount.textContent = `${formatNumber(userAmount)}$ USD`;
        }
    }
    
    if (eurAmount) eurAmount.textContent = `${formatNumber(userAmount * rates.EUR)}€ EUR`;
    if (gbpAmount) gbpAmount.textContent = `${formatNumber(userAmount * rates.GBP)}£ GBP`;
    
    if (uahAmount) {
        if (userCurrency !== 'UAH') {
            uahAmount.textContent = `${formatNumber(userAmount * rates.UAH)}₴ UAH`;
        } else {
            uahAmount.textContent = `${formatNumber(userAmount)}₴ UAH`;
        }
    }
}

function observeWalletChanges() {
    const walletElement = document.getElementById('wallet-amount');
    if (walletElement) {
        const observer = new MutationObserver(function(mutations) {
            mutations.forEach(function(mutation) {
                if (mutation.type === 'characterData' || mutation.type === 'childList') {
                    updateAllCurrenciesFromUserWallet();
                }
            });
        });
        
        observer.observe(walletElement, {
            characterData: true,
            childList: true,
            subtree: true
        });
    }
}

// ==================== ФУНКЦИИ ЧАТА ====================
function setupWebSocketReconnect() {
    setInterval(() => {
        if (currentChatUser && (!chatSocket || chatSocket.readyState === WebSocket.CLOSED || chatSocket.readyState === WebSocket.CLOSING)) {
            attemptReconnect();
        }
    }, 5000);
}

function attemptReconnect() {
    if (reconnectAttempts < maxReconnectAttempts && currentChatUser) {
        setTimeout(() => {
            console.log(`Attempting to reconnect... (${reconnectAttempts + 1}/${maxReconnectAttempts})`);
            openChat(currentChatUser);
            reconnectAttempts++;
        }, reconnectDelay * reconnectAttempts);
    }
}

function loadRecentContacts() {
    fetch('/get-recent-contacts/')
        .then(response => response.json())
        .then(contacts => {
            const contactsList = document.getElementById('recent-contacts-list');
            const currentUser = "{{ user.username }}";
            const lang = "{{ user.language|default:'English' }}";
            
            if (!contactsList) return;
            
            const favoriteContact = {
                username: currentUser,
                avatar_url: "/static/pictures/notes.jpg",
                last_message: lang === 'Українська' ? 'Ваши заметки' : 'Your notes',
                last_activity: new Date().toISOString(),
                unread_count: 0
            };
            
            const allContacts = [favoriteContact, ...contacts.filter(contact => contact.username !== currentUser)];
            
            if (allContacts.length === 0) {
                contactsList.innerHTML = '<div style="color:#999; padding:10px; text-align:center;">No recent chats</div>';
                return;
            }
            
            contactsList.innerHTML = allContacts.map(contact => {
                let displayName, lastMessage, avatarUrl;
                if (contact.username === currentUser) {
                    displayName = lang === 'Українська' ? 'Избранное' : 'Notes';
                    lastMessage = getLastNoteMessage() || (lang === 'Українська' ? 'Ваши заметки' : 'Your notes');
                    avatarUrl = "/static/pictures/notes.jpg";
                } else {
                    displayName = contact.username;
                    lastMessage = contact.last_message || 'No messages yet';
                    avatarUrl = contact.avatar_url || '/static/pictures/login.png';
                }
                
                const truncatedMessage = truncateText(lastMessage, 25);
                
                return `
                <div class="recent-contact ${contact.unread_count > 0 ? 'unread' : ''}" 
                     onclick="openChat('${contact.username}')">
                    <div style="display:flex; align-items:center; gap:10px;">
                        <img src="${avatarUrl}" 
                             class="contact-avatar" 
                             alt="${contact.username}">
                        <div class="contact-info">
                            <div class="contact-username">${displayName}</div>
                            <div class="contact-last-message" title="${lastMessage}">
                                ${truncatedMessage}
                            </div>
                        </div>
                        <div style="display:flex; flex-direction:column; align-items:flex-end; gap:2px;">
                            ${contact.last_activity ? `
                                <div class="contact-time">
                                    ${formatTime(contact.last_activity)}
                                </div>
                            ` : ''}
                            ${contact.unread_count > 0 ? `
                                <div class="unread-badge">${contact.unread_count}</div>
                            ` : ''}
                        </div>
                    </div>
                </div>
            `}).join('');
        })
        .catch(error => {
            console.error('Error loading recent contacts:', error);
        });
}

function truncateText(text, maxLength) {
    if (!text || text.length <= maxLength) {
        return text;
    }
    return text.substring(0, maxLength) + '...';
}

function getLastNoteMessage() {
    const notes = JSON.parse(localStorage.getItem('user_notes') || '[]');
    if (notes.length > 0) {
        return notes[notes.length - 1].text;
    }
    return null;
}

function saveNoteToStorage(noteText) {
    const notes = JSON.parse(localStorage.getItem('user_notes') || '[]');
    notes.push({
        text: noteText,
        timestamp: new Date().toISOString()
    });
    localStorage.setItem('user_notes', JSON.stringify(notes));
    
    setTimeout(() => {
        loadRecentContacts();
    }, 100);
}

function formatTime(timestamp) {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);
    
    if (diffMins < 1) return 'now';
    if (diffMins < 60) return `${diffMins}m`;
    if (diffHours < 24) return `${diffHours}h`;
    if (diffDays < 7) return `${diffDays}d`;
    
    return date.toLocaleDateString();
}

function openChat(username) {
    currentChatUser = username;
    const chatUsernameElement = document.getElementById('chat-username');
    if (chatUsernameElement) {
        chatUsernameElement.textContent = username;
    }
    
    const chatToggle = document.getElementById('chat-toggle');
    if (chatToggle) {
        chatToggle.checked = true;
    }

    reconnectAttempts = 0;
    
    if (chatSocket) {
        chatSocket.close();
    }
    
    const currentUser = "{{ user.username }}";
    const roomName = [currentUser, username].sort().join('_').replace(/[^\w]/g, '');
    
    const wsScheme = window.location.protocol === "https:" ? "wss" : "ws";
    const wsPath = wsScheme + '://' + window.location.host + '/ws/chat/' + roomName + '/';
    
    console.log('Connecting to WebSocket:', wsPath);
    
    chatSocket = new WebSocket(wsPath);
    
    chatSocket.onmessage = function(e) {
        try {
            const data = JSON.parse(e.data);
            console.log('Received WebSocket message:', data);
            
            if (data.sender !== "{{ user.username }}") {
                displayMessage(data.message, data.sender, false);
                loadRecentContacts();
            } else {
                console.log('Ignoring own message from WebSocket');
            }
        } catch (error) {
            console.error('Error parsing WebSocket message:', error);
        }
    };
    
    chatSocket.onopen = function(e) {
        console.log('WebSocket connection established successfully');
        loadChatMessages(username);
    };
    
    chatSocket.onclose = function(e) {
        console.log('WebSocket connection closed:', e.code, e.reason);
        if (document.getElementById('chat-toggle')?.checked) {
            setTimeout(() => attemptReconnect(), 2000);
        }
    };
    
    chatSocket.onerror = function(e) {
        console.error('WebSocket error:', e);
    };
    
    loadChatMessages(username);
    markMessagesAsRead(username);
    
    const searchInput = document.getElementById('searchInput');
    if (searchInput) searchInput.value = '';
    
    const searchResults = document.getElementById('searchResults');
    if (searchResults) searchResults.innerHTML = '';
    
    const recentContactsDiv = document.getElementById('recent-contacts');
    if (recentContactsDiv) {
        recentContactsDiv.style.display = "block";
    }
    
    document.addEventListener('keydown', blockEscapeClose);
}

function blockEscapeClose(e) {
    if (e.key === 'Escape' && document.getElementById('chat-toggle')?.checked) {
        e.preventDefault();
        e.stopPropagation();
        showTemporaryMessage("Chat cannot be closed", 2000);
    }
}

function showTemporaryMessage(message, duration) {
    const tempMsg = document.createElement('div');
    tempMsg.textContent = message;
    tempMsg.style.cssText = `
        position: fixed;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        background: rgba(0,0,0,0.8);
        color: white;
        padding: 10px 20px;
        border-radius: 5px;
        z-index: 10000;
    `;
    document.body.appendChild(tempMsg);
    
    setTimeout(() => {
        tempMsg.remove();
    }, duration);
}

function markMessagesAsRead(username) {
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value;
    if (!csrfToken) return;
    
    fetch('/mark-messages-read/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken,
        },
        body: JSON.stringify({
            sender: username
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            loadRecentContacts();
        }
    })
    .catch(error => {
        console.error('Error marking messages as read:', error);
    });
}

function processMentions(text) {
    if (!text) return '';
    
    const mentionRegex = /(@[\wа-яА-ЯёЁ]+)/gi;
    
    return text.replace(mentionRegex, '<span class="message-mention profile-mention" data-username="$1">$1</span>');
}

function addMentionEventListeners(element) {
    const mentions = element.querySelectorAll('.message-mention, .profile-mention');
    
    mentions.forEach(mention => {
        const username = mention.getAttribute('data-username');
        
        if (!isValidMention(username)) {
            mention.classList.remove('message-mention', 'profile-mention');
            mention.style.color = '';
            mention.style.cursor = 'default';
            mention.style.textDecoration = 'none';
            mention.style.backgroundColor = '';
            return;
        }
        
        checkUserExists(username.replace('@', '')).then(exists => {
            if (!exists) {
                mention.classList.remove('message-mention', 'profile-mention');
                mention.style.color = 'inherit';
                mention.style.fontWeight = 'normal';
                mention.style.cursor = 'text';
                mention.style.textDecoration = 'none';
                mention.style.backgroundColor = 'transparent';
                mention.style.padding = '0';
                mention.removeAttribute('data-username');
                return;
            }
            
            mention.addEventListener('click', function(e) {
                e.preventDefault();
                e.stopPropagation();
                const cleanUsername = username.replace('@', '');
                openUserProfile(cleanUsername);
            });
            
            mention.addEventListener('mouseenter', function() {
                this.style.transform = 'translateY(-1px)';
                this.style.cursor = 'pointer';
            });
            
            mention.addEventListener('mouseleave', function() {
                this.style.transform = 'translateY(0)';
            });
        });
    });
}

function displayMessage(text, sender, isSent) {
    const messagesContainer = document.getElementById('chat-messages');
    if (!messagesContainer) {
        console.error('Chat messages container not found');
        return;
    }
    
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${isSent ? 'sent' : 'received'}`;
    
    const senderDiv = document.createElement('div');
    senderDiv.className = 'message-sender';
    senderDiv.textContent = getSenderDisplayName(isSent, sender);
    messageDiv.appendChild(senderDiv);
    
    const textDiv = document.createElement('div');
    
    const processedText = processMentions(text);
    textDiv.innerHTML = processedText;
    
    messageDiv.appendChild(textDiv);
    
    const timeDiv = document.createElement('div');
    timeDiv.className = 'message-time';
    timeDiv.style.fontSize = '11px';
    timeDiv.style.color = '#999';
    timeDiv.style.marginTop = '4px';
    timeDiv.style.textAlign = isSent ? 'right' : 'left';
    timeDiv.textContent = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    messageDiv.appendChild(timeDiv);
    
    const spacer = messagesContainer.querySelector('.chat-messages-spacer');
    if (spacer) {
        messagesContainer.insertBefore(messageDiv, spacer);
    } else {
        messagesContainer.appendChild(messageDiv);
    }
    
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
    
    addMentionEventListeners(messageDiv);
}

function checkUserExists(username) {
    return fetch(`/check-user-exists/?username=${encodeURIComponent(username)}`)
        .then(response => response.json())
        .then(data => {
            return data.exists || false;
        })
        .catch(error => {
            console.error('Error checking user existence:', error);
            return false;
        });
}

function isValidMention(username) {
    if (!username || !username.startsWith('@')) return false;
    
    const cleanUsername = username.replace('@', '');
    return /^[\wа-яА-ЯёЁ_\d]+$/.test(cleanUsername) && cleanUsername.length > 0;
}

function processMentionsStrict(text) {
    if (!text) return '';
    
    if (/<[^>]*>/.test(text)) {
        return text;
    }
    
    const mentionRegex = /(@[\wа-яА-ЯёЁ_\d]+)/gi;
    
    return text.replace(mentionRegex, '<span class="message-mention profile-mention" data-username="$1">$1</span>');
}

function loadChatMessages(username) {
    if (username === "{{ user.username }}") {
        fetch(`/get-notes/`)
            .then(response => {
                if (!response.ok) throw new Error('Network error');
                return response.json();
            })
            .then(notes => {
                displayNotes(notes);
            })
            .catch(error => {
                console.error('Error loading notes from server:', error);
                const localNotes = JSON.parse(localStorage.getItem('user_notes') || '[]');
                displayNotes(localNotes);
            });
        return;
    }
    
    fetch(`/get-chat-messages/?username=${encodeURIComponent(username)}`)
        .then(response => response.json())
        .then(messages => {
            const messagesContainer = document.getElementById('chat-messages');
            if (!messagesContainer) return;
            
            const spacer = messagesContainer.querySelector('.chat-messages-spacer');
            messagesContainer.innerHTML = '';
            if (spacer) {
                messagesContainer.appendChild(spacer);
            } else {
                const newSpacer = document.createElement('div');
                newSpacer.className = 'chat-messages-spacer';
                messagesContainer.appendChild(newSpacer);
            }
            
            messages.forEach(msg => {
                const messageDiv = document.createElement('div');
                messageDiv.className = `message ${msg.is_sent ? 'sent' : 'received'}`;
                
                const textDiv = document.createElement('div');
                
                const processedText = processMentions(msg.text);
                textDiv.innerHTML = processedText;
                
                messageDiv.appendChild(textDiv);
                
                const timeDiv = document.createElement('div');
                timeDiv.className = 'message-time';
                timeDiv.style.fontSize = '11px';
                timeDiv.style.color = '#999';
                timeDiv.style.marginTop = '4px';
                timeDiv.style.textAlign = msg.is_sent ? 'right' : 'left';
                
                const messageDate = new Date(msg.timestamp);
                timeDiv.textContent = messageDate.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
                messageDiv.appendChild(timeDiv);
                
                const spacer = messagesContainer.querySelector('.chat-messages-spacer');
                if (spacer) {
                    messagesContainer.insertBefore(messageDiv, spacer);
                } else {
                    messagesContainer.appendChild(messageDiv);
                }
                
                addMentionEventListeners(messageDiv);
            });
            
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        })
        .catch(error => {
            console.error('Error loading chat messages:', error);
        });
}

function displayNotes(notes) {
    const messagesContainer = document.getElementById('chat-messages');
    if (!messagesContainer) return;
    
    const spacer = messagesContainer.querySelector('.chat-messages-spacer');
    messagesContainer.innerHTML = '';
    if (spacer) {
        messagesContainer.appendChild(spacer);
    } else {
        const newSpacer = document.createElement('div');
        newSpacer.className = 'chat-messages-spacer';
        messagesContainer.appendChild(newSpacer);
    }
    
    notes.forEach(note => {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message sent';
        
        const textDiv = document.createElement('div');
        textDiv.textContent = note.text;
        messageDiv.appendChild(textDiv);
        
        const timeDiv = document.createElement('div');
        timeDiv.className = 'message-time';
        timeDiv.style.fontSize = '11px';
        timeDiv.style.color = '#999';
        timeDiv.style.marginTop = '4px';
        timeDiv.style.textAlign = 'right';
        
        const noteDate = new Date(note.timestamp);
        timeDiv.textContent = noteDate.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        messageDiv.appendChild(timeDiv);
        
        const spacer = messagesContainer.querySelector('.chat-messages-spacer');
        if (spacer) {
            messagesContainer.insertBefore(messageDiv, spacer);
        } else {
            messagesContainer.appendChild(messageDiv);
        }
    });
    
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

function getSenderDisplayName(isSent, sender) {
    const lang = "{{ user.language|default:'English' }}";
    const currentUser = "{{ user.username }}";
    
    if (isSent) {
        return lang === 'Українська' ? 'Избранное' : 'Notes';
    } else {
        return sender;
    }
}

function sendMessage() {
    const input = document.getElementById('chat-input');
    const message = input?.value.trim();
    
    if (!message || !currentChatUser) return;

    displayMessage(message, "{{ user.username }}", true);
    
    input.value = '';

    const updateHistory = () => {
        setTimeout(() => {
            loadRecentContacts();
        }, 100);
    };

    if (chatSocket && chatSocket.readyState === WebSocket.OPEN) {
        try {
            chatSocket.send(JSON.stringify({
                'message': message,
                'sender': "{{ user.username }}",
                'receiver': currentChatUser
            }));
            console.log('Message sent via WebSocket:', message);
            updateHistory();
            
        } catch (error) {
            console.error('WebSocket send error:', error);
            sendMessageViaAJAX(message);
        }
    } else {
        console.error('WebSocket is not connected, falling back to AJAX');
        sendMessageViaAJAX(message);
    }
}

function sendMessageViaAJAX(message) {
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value;
    if (!csrfToken) return;
    
    if (currentChatUser === "{{ user.username }}") {
        sendMessageToSelfViaAJAX(message);
        return;
    }
    
    fetch('/send-message/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken,
        },
        body: JSON.stringify({
            text: message,
            receiver: currentChatUser
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            console.log('Message sent via AJAX:', message);
            loadRecentContacts();
        } else {
            console.error('Failed to send message:', data.error);
        }
    })
    .catch(error => {
        console.error('AJAX send error:', error);
    });
}

function sendMessageToSelfViaAJAX(message) {
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value;
    if (!csrfToken) return;
    
    fetch('/save-note/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken,
        },
        body: JSON.stringify({
            text: message
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            console.log('Note saved:', message);
            saveNoteToStorage(message);
        } else {
            console.error('Failed to save note:', data.error);
        }
    })
    .catch(error => {
        console.error('AJAX save note error:', error);
        saveNoteToStorage(message);
    });
}

function closeChat() {
    const chatToggle = document.getElementById('chat-toggle');
    if (chatToggle) chatToggle.checked = false;
    
    currentChatUser = null;
    if (chatSocket) {
        chatSocket.close();
        chatSocket = null;
    }
}

// ==================== ФУНКЦИИ ПОИСКА И ПРОФИЛЕЙ ====================
function searchUsers() {
    const searchInput = document.getElementById("searchInput");
    const resultsDiv = document.getElementById("searchResults");
    const recentContactsDiv = document.getElementById("recent-contacts");
    const query = searchInput?.value.trim();
    const currentUser = "{{ user.username }}";
    const lang = "{{ user.language|default:'English' }}";
    
    if (!searchInput || !resultsDiv) return;
    
    if (!query || query.length === 0) {
        resultsDiv.innerHTML = "";
        if (recentContactsDiv) {
            recentContactsDiv.style.display = "block";
        }
        return;
    }

    if (recentContactsDiv) {
        recentContactsDiv.style.display = "none";
    }

    fetch(`/search-users/?q=${encodeURIComponent(query)}`)
        .then(response => response.json())
        .then(users => {
            const filteredUsers = users.filter(user => user.username !== currentUser);
            
            const searchTerms = ['избранное', 'заметки', 'notes', 'favorites'];
            const queryLower = query.toLowerCase();
            const shouldShowNotes = searchTerms.some(term => 
                term.includes(queryLower) || queryLower.includes(term)
            );
            
            let resultsHTML = '';
            
            if (shouldShowNotes) {
                const notesDisplayName = lang === 'Українська' ? 'Избранное' : 'Notes';
                const notesDescription = lang === 'Українська' ? 'Ваши заметки' : 'Your notes';
                
                resultsHTML += `
                    <div class="user-search-result" onclick="openChat('${currentUser}')" 
                         style="padding:10px; border:1px solid #ddd; border-radius:8px; margin-bottom:8px; width:250px; cursor:pointer; background:white; transition:all 0.2s;">
                        <div style="display:flex; align-items:center; gap:10px;">
                            <img src="/static/pictures/notes.jpg" 
                                 style="width:40px; height:40px; border-radius:50%; object-fit:cover;">
                            <div>
                                <b style="font-size:14px;">${notesDisplayName}</b>
                                <div style="color:gray; font-size:12px;">${notesDescription}</div>
                            </div>
                        </div>
                    </div>`;
            }
            
            if (filteredUsers.length > 0) {
                resultsHTML += filteredUsers
                    .map(user => `
                        <div class="user-search-result" onclick="openChat('${user.username}')" 
                             style="padding:10px; border:1px solid #ddd; border-radius:8px; margin-bottom:8px; width:250px; cursor:pointer; background:white; transition:all 0.2s;">
                            <div style="display:flex; align-items:center; gap:10px;">
                                <img src="${user.avatar_url || '/static/pictures/login.png'}" 
                                     style="width:40px; height:40px; border-radius:50%; object-fit:cover;">
                                <div>
                                    <b style="font-size:14px;">${user.username}</b>
                                    <div style="color:gray; font-size:12px;">${user.your_tag || user.username}</div>
                                </div>
                            </div>
                        </div>`)
                    .join("");
            }
            
            if (resultsHTML) {
                resultsDiv.innerHTML = resultsHTML;
            } else {
                resultsDiv.innerHTML = `<div style="color:#999; padding:10px;">No users found for "${query}"</div>`;
            }
        })
        .catch(error => {
            console.error('Search error:', error);
            resultsDiv.innerHTML = `<div style="color:red; padding:10px;">Search error</div>`;
        });
}

function openUserProfile(username) {
    if (username === "{{ user.username }}") {
        ModalManager.closeAllExceptChat(); // Не закрываем чат
        document.getElementById('profile-toggle').checked = true;
        return;
    }
    
    ModalManager.closeAllExceptChat(); // Не закрываем чат при открытии профиля
    
    fetch(`/get-user-profile/?username=${encodeURIComponent(username)}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showUserProfileModal(data);
            } else {
                alert('User not found: ' + username);
            }
        })
        .catch(error => {
            console.error('Error loading user profile:', error);
            alert('Error loading user profile');
        });
}

function showUserProfileModal(userData) {
    const otherProfileForm = document.querySelector('.other-profile-form');
    if (otherProfileForm) {
        const avatarImg = otherProfileForm.querySelector('.other-profile-avatar');
        if (avatarImg) {
            avatarImg.src = userData.photo_url;
            avatarImg.alt = userData.username;
        }
        
        const usernameEl = otherProfileForm.querySelector('.other-profile-username');
        if (usernameEl) {
            usernameEl.textContent = userData.username;
        }
        
        const tagEl = otherProfileForm.querySelector('.other-profile-tag');
        if (tagEl) {
            tagEl.textContent = userData.your_tag || userData.username;
        }
        
        const statusEl = otherProfileForm.querySelector('.other-profile-status');
        if (statusEl) {
            statusEl.textContent = userData.status;
            statusEl.className = `status-value ${userData.status === 'Online' ? 'online' : 'offline'}`;
        }
        
        const descriptionEl = otherProfileForm.querySelector('.other-profile-description');
        if (descriptionEl) {
            const processedDescription = processMentionsStrict(userData.description || 'No description');
            descriptionEl.innerHTML = processedDescription;
            addMentionEventListeners(descriptionEl);
        }
        
        const birthdayEl = otherProfileForm.querySelector('.other-profile-birthday');
        if (birthdayEl) {
            birthdayEl.textContent = userData.birthday;
        }
        
        const messageBtn = otherProfileForm.querySelector('.other-profile-message-btn');
        if (messageBtn) {
            messageBtn.onclick = function() {
                openChatWithUser(userData.username);
            };
        }
    }
    
    const otherProfileToggle = document.getElementById('other-profile-toggle');
    if (otherProfileToggle) {
        otherProfileToggle.checked = true;
    }
}

function openChatWithUser(username) {
    const otherProfileToggle = document.getElementById('other-profile-toggle');
    if (otherProfileToggle) {
        otherProfileToggle.checked = false;
    }
    
    openChat(username);
}

function processProfileDescription() {
    const descriptionElements = document.querySelectorAll('.profile-preview-value, .other-profile-description');
    
    descriptionElements.forEach(element => {
        const originalText = element.innerHTML;
        const processedText = processMentionsStrict(originalText);
        element.innerHTML = processedText;
        addMentionEventListeners(element);
    });
}

// ==================== ФУНКЦИИ ПОДПИСОК И КАРТ ====================
function setupSubscription(checkboxId, buttonId) {
    const checkbox = document.getElementById(checkboxId);
    const button = document.getElementById(buttonId);

    if (checkbox && button) {
        button.disabled = true;
        checkbox.addEventListener('change', () => {
            button.disabled = !checkbox.checked;
        });
    }
}

window.confirmAvatarReset = function() {
    const lang = "{{ user.language|default:'English' }}";
    const confirmMsg = lang === 'Українська'
        ? "Ви впевнені, що хочете скинути аватар?"
        : "Are you sure you want to reset your avatar?";

    if (confirm(confirmMsg)) {
        const csrfToken = '{{ csrf_token }}';
        
        fetch('{% url "reset_avatar" %}', {
            method: 'POST',
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': csrfToken,
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: 'action=reset_photo'
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                const defaultAvatarUrl = data.avatar_url + '?t=' + new Date().getTime();
                
                document.querySelectorAll('.avatar, img.avatar').forEach(img => {
                    img.src = defaultAvatarUrl;
                });
                
                const previewAvatar = document.getElementById('preview-avatar');
                if (previewAvatar) previewAvatar.src = defaultAvatarUrl;
                
                const avatarInputImg = document.getElementById('avatarInput-img');
                if (avatarInputImg) avatarInputImg.src = defaultAvatarUrl;
            } else {
                console.error('Error resetting avatar:', data.error);
            }
        })
        .catch(error => {
            console.error('Error:', error);
        });
    }
};

window.deleteCard = function(last4) {
    const lang = "{{ user.language|default:'English' }}";
    const confirmMsg = lang === 'Українська' 
        ? `Ви впевнені, що хочете видалити картку ****${last4}?`
        : `Are you sure you want to delete card ****${last4}?`;
    
    if (!confirm(confirmMsg)) return;

    const csrfInput = document.querySelector('input[name="csrfmiddlewaretoken"]');
    const csrf = csrfInput ? csrfInput.value : '';

    fetch('/delete-card/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest',
            'X-CSRFToken': csrf,
        },
        body: JSON.stringify({ last4: last4 })
    })
    .then(r => r.json())
    .then(data => {
        if (data.error) {
            alert(data.error);
            return;
        }
        
        const cardsList = document.getElementById('cards-list');
        const cardMessages = {
            cards_label: lang === 'Українська' ? 'Картки:' : 'Cards:',
            no_cards: lang === 'Українська' ? 'Карт не додано' : 'No cards added',
        };
        
        if (cardsList && data.cards !== undefined) {
            let html = `<strong>${cardMessages.cards_label}</strong><div style="margin-top:6px;">`;
            if (data.cards.length === 0) {
                html += `<div class="card-item" style="margin-bottom:8px; padding-bottom:8px; border-bottom:1px solid #eee;">${cardMessages.no_cards}</div>`;
            } else {
                data.cards.forEach(c => {
                    html += `<div class="card-item" style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px; padding-bottom:8px; border-bottom:1px solid #eee;">
                        <span>**** **** ****${c.last4} — ${c.cardholder || '-'} — ${c.expiry}</span>
                        <button type="button" onclick="deleteCard('${c.last4}')" style="background:red; color:white; border:none; padding:4px 8px; border-radius:4px; cursor:pointer; font-size:12px;">🗑️</button>
                    </div>`;
                });
            }
            html += '</div>';
            cardsList.innerHTML = html;
        }
        
        const successMsg = lang === 'Українська' ? 'Картку видалено!' : 'Card deleted!';
        alert(successMsg);
    })
    .catch(err => {
        console.error('Delete card failed', err);
        const errorMsg = lang === 'Українська' ? 'Помилка видалення картки' : 'Error deleting card';
        alert(errorMsg);
    });
};

function checkCardsAndOpenDeposit() {
    const cardsList = document.getElementById('cards-list');
    const noCardsMessage = '{% if lang == "Українська" %}Карт не додано{% else %}No cards added{% endif %}';
    
    if (cardsList?.textContent.includes(noCardsMessage)) {
        openAdd_card('add_card');
        const addCardResult = document.getElementById('add-card-result');
        if (addCardResult) {
            addCardResult.textContent = '{% if lang == "Українська" %}Спочатку додайте картку{% else %}Please add a card first{% endif %}';
        }
    } else {
        openSubscribe('deposit');
    }
}

window.performDeposit = function() {
    const depositInput = document.getElementById('deposit-amount');
    const depositWalletSpan = document.getElementById('deposit-wallet');
    const currencySelect = document.querySelector('.wallet form select');
    const depositResult = document.getElementById('deposit-result');
    
    if (!depositInput || !depositWalletSpan) return;
    
    const v = Number(depositInput.value) || 0;
    if (v <= 0) {
        alert('Please enter an amount greater than 0');
        return;
    }

    const depositCurrency = (currencySelect && currencySelect.value) ? currencySelect.value : ("{{ user.currency|default:'USD' }}");

    const csrfInput = document.querySelector('input[name="csrfmiddlewaretoken"]');
    const csrf = csrfInput ? csrfInput.value : '';

    const formData = new FormData();
    formData.append('amount', v);
    formData.append('currency', depositCurrency);

    fetch('{% url "deposit-funds" %}', {
        method: 'POST',
        headers: {
            'X-Requested-With': 'XMLHttpRequest',
            'X-CSRFToken': csrf,
        },
        body: formData,
    })
    .then(resp => {
        if (!resp.ok) throw new Error('Network response was not ok');
        return resp.json();
    })
    .then(data => {
        if (data && data.price_converted) {
            depositWalletSpan.textContent = data.price_converted;
            const walletAmountEl = document.getElementById('wallet-amount');
            if (walletAmountEl) walletAmountEl.textContent = 'Wallet: ' + data.price_converted;
            const depositToggle = document.getElementById('deposit-toggle');
            const walletToggle = document.getElementById('wallet-toggle');
            if (depositToggle) depositToggle.checked = false;
            if (walletToggle) walletToggle.checked = true;
            depositInput.value = '';
            if (depositResult) depositResult.textContent = '';
        } else if (data && data.error) {
            alert('Deposit failed: ' + data.error);
        }
    })
    .catch(err => {
        console.error('Deposit failed:', err);
        alert('Deposit failed');
    });
};

window.openSubscribe = function(period) {
    const monthToggle = document.getElementById('subscribe-month-toggle');
    const yearToggle = document.getElementById('subscribe-year-toggle');
    const depositToggle = document.getElementById('deposit-toggle');

    if (period === 'month') {
        if (monthToggle) monthToggle.checked = true;
        if (yearToggle) yearToggle.checked = false;
        if (depositToggle) depositToggle.checked = false;
    } else if (period === 'year') {
        if (yearToggle) yearToggle.checked = true;
        if (monthToggle) monthToggle.checked = false;
        if (depositToggle) depositToggle.checked = false;
    } else if (period === 'deposit') {
        if (depositToggle) depositToggle.checked = true;
        if (monthToggle) monthToggle.checked = false;
        if (yearToggle) yearToggle.checked = false;
    }
};

window.openAdd_card = function() {
    const addToggle = document.getElementById('add_card-toggle');
    if (addToggle) addToggle.checked = true;
    const monthToggle = document.getElementById('subscribe-month-toggle');
    const yearToggle = document.getElementById('subscribe-year-toggle');
    if (monthToggle) monthToggle.checked = false;
    if (yearToggle) yearToggle.checked = false;
    const depositToggle = document.getElementById('deposit-toggle');
    if (depositToggle) depositToggle.checked = false;
};

window.submitAddCard = function() {
    const numberEl = document.getElementById('card-number');
    const holderEl = document.getElementById('card-cardholder');
    const monthEl = document.getElementById('card-expiry-month');
    const yearEl = document.getElementById('card-expiry-year');
    const resultEl = document.getElementById('add-card-result');

    const cardMessages = {
        invalid_card_number: "{{ card_messages.invalid_card_number }}",
        card_added: "{{ card_messages.card_added }}",
        add_card_failed: "{{ card_messages.add_card_failed }}",
        cards_label: "{{ card_messages.cards_label }}",
        no_cards: "{{ card_messages.no_cards }}",
    };

    if (!numberEl || !monthEl || !yearEl) return;
    const number = (numberEl.value || '').replace(/\s+/g, '');
    const holder = holderEl ? holderEl.value : '';
    const month = monthEl.value;
    const year = yearEl.value;

    if (number.length < 13 || number.length > 16 || !/^[0-9]+$/.test(number)) {
        if (resultEl) resultEl.textContent = cardMessages.invalid_card_number;
        return;
    }

    const csrfInput = document.querySelector('input[name="csrfmiddlewaretoken"]');
    const csrf = csrfInput ? csrfInput.value : '';

    const fd = new FormData();
    fd.append('card_number', number);
    fd.append('cardholder', holder);
    fd.append('expiry_month', month);
    fd.append('expiry_year', year);

    fetch('{% url "add-card" %}', {
        method: 'POST',
        headers: {
            'X-Requested-With': 'XMLHttpRequest',
            'X-CSRFToken': csrf,
        },
        body: fd,
    })
    .then(r => r.json())
    .then(data => {
        if (data.error) {
            if (resultEl) resultEl.textContent = data.error;
            return;
        }
        const cardsList = document.getElementById('cards-list');
        if (cardsList && data.cards) {
            let html = '<strong>' + cardMessages.cards_label + '</strong><div style="margin-top:6px;">';
            if (data.cards.length === 0) html += '<div class="card-item">' + cardMessages.no_cards + '</div>';
            data.cards.forEach(c => {
                html += `<div class="card-item" style="margin-bottom:8px; padding-bottom:8px; border-bottom:1px solid #eee;">**** **** ****${c.last4} — ${c.cardholder || '-'} — ${c.expiry}</div>`;
            });
            html += '</div>';
            cardsList.innerHTML = html;
        }
        const addToggle = document.getElementById('add_card-toggle');
        if (addToggle) addToggle.checked = false;
        if (resultEl) resultEl.textContent = cardMessages.card_added;
        if (numberEl) numberEl.value = '';
        if (holderEl) holderEl.value = '';
    })
    .catch(err => {
        console.error('Add card failed', err);
        if (resultEl) resultEl.textContent = cardMessages.add_card_failed;
    });
};

// ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================
function copyOtherUserTag() {
    const otherProfileTag = document.querySelector('.other-profile-tag');
    if (otherProfileTag) {
        const tagText = otherProfileTag.textContent;
        navigator.clipboard.writeText(tagText)
            .then(() => {
                showCopyNotification('Tag copied!');
            })
            .catch(err => {
                console.error('Error copying tag:', err);
                showCopyNotification('Failed to copy tag');
            });
    }
}

function showCopyNotification(message) {
    const notification = document.createElement('div');
    notification.textContent = message;
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: #4CAF50;
        color: white;
        padding: 15px 20px;
        border-radius: 8px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        z-index: 10000;
        animation: slideIn 0.3s;
    `;
    
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s';
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 300);
    }, 2000);
}

// Добавляем стили для уведомлений
const notificationStyles = `
    @keyframes slideIn {
        from { transform: translateX(100%); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
    @keyframes slideOut {
        from { transform: translateX(0); opacity: 1; }
        to { transform: translateX(100%); opacity: 0; }
    }
`;

const styleElement = document.createElement('style');
styleElement.textContent = notificationStyles;
document.head.appendChild(styleElement);

// Инициализация обработки описаний профилей
document.addEventListener('DOMContentLoaded', processProfileDescription);

// Обработка таймера подписки
{% if user.subscription_end %}
const endDate = new Date("{{ user.subscription_end|date:'Y-m-d H:i:s' }}").getTime();
const countdownEl = document.getElementById('countdown');

if (countdownEl) {
    function updateCountdown() {
        const now = new Date().getTime();
        const distance = endDate - now;

        if (distance < 0) {
            countdownEl.innerHTML = "Expired";
            location.reload();
            return;
        }

        const days = Math.floor(distance / (1000 * 60 * 60 * 24));
        const hours = Math.floor((distance % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
        const minutes = Math.floor((distance % (1000 * 60 * 60)) / (1000 * 60));
        const seconds = Math.floor((distance % (1000 * 60)) / 1000);

        countdownEl.innerHTML = `${days}d ${hours}h ${minutes}m ${seconds}s`;
    }

    updateCountdown();
    setInterval(updateCountdown, 1000);
}
{% endif %}