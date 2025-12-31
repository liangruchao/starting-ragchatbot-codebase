// API base URL - use relative path to work from any host
const API_URL = '/api';

// Global state
let currentSessionId = null;

// DOM elements
let chatMessages, chatInput, sendButton, totalCourses, courseTitles;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    // Get DOM elements after page loads
    chatMessages = document.getElementById('chatMessages');
    chatInput = document.getElementById('chatInput');
    sendButton = document.getElementById('sendButton');
    totalCourses = document.getElementById('totalCourses');
    courseTitles = document.getElementById('courseTitles');

    setupEventListeners();
    initializeTheme();
    createNewSession();
    loadCourseStats();
});

// Event Listeners
function setupEventListeners() {
    // Chat functionality
    sendButton.addEventListener('click', sendMessage);
    chatInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendMessage();
    });

    // New Chat button
    const newChatButton = document.getElementById('newChatButton');
    newChatButton.addEventListener('click', () => {
        createNewSession();
    });

    // Suggested questions
    document.querySelectorAll('.suggested-item').forEach(button => {
        button.addEventListener('click', (e) => {
            const question = e.target.getAttribute('data-question');
            chatInput.value = question;
            sendMessage();
        });
    });
}


// Chat Functions
async function sendMessage() {
    const query = chatInput.value.trim();
    if (!query) return;

    // Disable input
    chatInput.value = '';
    chatInput.disabled = true;
    sendButton.disabled = true;

    // Add user message
    addMessage(query, 'user');

    // Add loading message - create a unique container for it
    const loadingMessage = createLoadingMessage();
    chatMessages.appendChild(loadingMessage);
    chatMessages.scrollTop = chatMessages.scrollHeight;

    try {
        const response = await fetch(`${API_URL}/query`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                query: query,
                session_id: currentSessionId
            })
        });

        if (!response.ok) throw new Error('Query failed');

        const data = await response.json();

        // Update session ID if new
        if (!currentSessionId) {
            currentSessionId = data.session_id;
        }

        // Replace loading message with response
        loadingMessage.remove();
        addMessage(data.answer, 'assistant', data.sources);

    } catch (error) {
        // Replace loading message with error
        loadingMessage.remove();
        addMessage(`Error: ${error.message}`, 'assistant');
    } finally {
        chatInput.disabled = false;
        sendButton.disabled = false;
        chatInput.focus();
    }
}

function createLoadingMessage() {
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message assistant';
    messageDiv.innerHTML = `
        <div class="message-content">
            <div class="loading">
                <span></span>
                <span></span>
                <span></span>
            </div>
        </div>
    `;
    return messageDiv;
}

function addMessage(content, type, sources = null, isWelcome = false) {
    const messageId = Date.now();
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${type}${isWelcome ? ' welcome-message' : ''}`;
    messageDiv.id = `message-${messageId}`;

    // Convert markdown to HTML for assistant messages
    const displayContent = type === 'assistant' ? marked.parse(content) : escapeHtml(content);

    let html = `<div class="message-content">${displayContent}</div>`;

    if (sources && sources.length > 0) {
        // Render sources as clickable links or plain text
        const sourcesHtml = sources.map(source => {
            // Handle both new format (object with has_link) and old format (string)
            if (typeof source === 'object' && source.has_link) {
                return `<a href="${source.url}" target="_blank" rel="noopener noreferrer" class="source-link">${escapeHtml(source.text)} 📺</a>`;
            } else if (typeof source === 'object' && source.text) {
                return `<span class="source-text">${escapeHtml(source.text)}</span>`;
            } else {
                // Old format: plain string
                return `<span class="source-text">${escapeHtml(source)}</span>`;
            }
        }).join(', ');

        html += `
            <details class="sources-collapsible">
                <summary class="sources-header">Sources</summary>
                <div class="sources-content">${sourcesHtml}</div>
            </details>
        `;
    }

    messageDiv.innerHTML = html;
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;

    return messageId;
}

// Helper function to escape HTML for user messages
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Removed removeMessage function - no longer needed since we handle loading differently

async function createNewSession() {
    currentSessionId = null;
    chatMessages.innerHTML = '';
    addMessage('Welcome to the Course Materials Assistant! I can help you with questions about courses, lessons and specific content. What would you like to know?', 'assistant', null, true);
}

// Load course statistics
async function loadCourseStats() {
    try {
        console.log('Loading course stats...');
        const response = await fetch(`${API_URL}/courses`);
        if (!response.ok) throw new Error('Failed to load course stats');
        
        const data = await response.json();
        console.log('Course data received:', data);
        
        // Update stats in UI
        if (totalCourses) {
            totalCourses.textContent = data.total_courses;
        }
        
        // Update course titles
        if (courseTitles) {
            if (data.course_titles && data.course_titles.length > 0) {
                courseTitles.innerHTML = data.course_titles
                    .map(title => `<div class="course-title-item">${title}</div>`)
                    .join('');
            } else {
                courseTitles.innerHTML = '<span class="no-courses">No courses available</span>';
            }
        }
        
    } catch (error) {
        console.error('Error loading course stats:', error);
        // Set default values on error
        if (totalCourses) {
            totalCourses.textContent = '0';
        }
        if (courseTitles) {
            courseTitles.innerHTML = '<span class="error">Failed to load courses</span>';
        }
    }
}

// Theme Functions
// Theme state
let themeState = {
    mode: 'system', // 'light', 'dark', 'system'
    colorScheme: 'blue', // 'blue', 'green', 'purple', 'rose'
    highContrast: false,
    sepia: false
};

function initializeTheme() {
    // Load saved theme state
    const savedState = localStorage.getItem('themeState');
    if (savedState) {
        try {
            themeState = { ...themeState, ...JSON.parse(savedState) };
        } catch (e) {
            console.error('Error parsing theme state:', e);
        }
    }

    applyTheme();
    setupThemeListeners();
    updateThemeUI();
}

function applyTheme() {
    const root = document.documentElement;

    // Apply theme mode
    if (themeState.sepia) {
        root.setAttribute('data-theme', 'sepia');
    } else if (themeState.mode === 'system') {
        const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
        root.setAttribute('data-theme', prefersDark ? 'dark' : 'light');
    } else {
        root.setAttribute('data-theme', themeState.mode);
    }

    // Apply color scheme
    root.setAttribute('data-color-scheme', themeState.colorScheme);

    // Apply high contrast
    root.setAttribute('data-high-contrast', themeState.highContrast.toString());

    // Save to localStorage
    localStorage.setItem('themeState', JSON.stringify(themeState));
}

function toggleTheme() {
    const dropdown = document.getElementById('themeDropdown');
    const isHidden = dropdown.getAttribute('aria-hidden') === 'true';
    dropdown.setAttribute('aria-hidden', !isHidden);
}

function setThemeMode(mode) {
    themeState.mode = mode;
    themeState.sepia = false; // Clear sepia when changing mode
    applyTheme();
    updateThemeUI();
}

function setColorScheme(color) {
    themeState.colorScheme = color;
    applyTheme();
    updateThemeUI();
}

function setHighContrast(enabled) {
    themeState.highContrast = enabled;
    applyTheme();
    updateThemeUI();
}

function setSepia(enabled) {
    themeState.sepia = enabled;
    if (enabled) {
        themeState.mode = 'light'; // Sepia is based on light mode
    }
    applyTheme();
    updateThemeUI();
}

function updateThemeUI() {
    // Update mode buttons
    document.querySelectorAll('.theme-mode-btn').forEach(btn => {
        const mode = btn.getAttribute('data-mode');
        btn.classList.toggle('active', mode === themeState.mode);
    });

    // Update color scheme buttons
    document.querySelectorAll('.color-scheme-btn').forEach(btn => {
        const color = btn.getAttribute('data-color');
        btn.classList.toggle('active', color === themeState.colorScheme);
    });

    // Update checkboxes
    document.getElementById('highContrastToggle').checked = themeState.highContrast;
    document.getElementById('sepiaToggle').checked = themeState.sepia;

    // Disable color scheme and mode buttons when sepia is active
    const sepiaActive = themeState.sepia;
    document.querySelectorAll('.theme-mode-btn').forEach(btn => {
        btn.style.opacity = sepiaActive ? '0.5' : '1';
        btn.style.pointerEvents = sepiaActive ? 'none' : 'auto';
    });
    document.querySelectorAll('.color-scheme-btn').forEach(btn => {
        btn.style.opacity = sepiaActive ? '0.5' : '1';
        btn.style.pointerEvents = sepiaActive ? 'none' : 'auto';
    });
}

function setupThemeListeners() {
    // Theme toggle button - opens dropdown
    const themeToggle = document.getElementById('themeToggle');
    const dropdown = document.getElementById('themeDropdown');

    console.log('Setting up theme listeners...', themeToggle, dropdown);

    if (!themeToggle || !dropdown) {
        console.error('Theme elements not found!', themeToggle, dropdown);
        return;
    }

    themeToggle.addEventListener('click', (e) => {
        console.log('Theme toggle clicked');
        e.stopPropagation();
        toggleTheme();
    });

    // Keyboard accessibility
    themeToggle.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            toggleTheme();
        }
    });

    // Close dropdown when clicking outside
    document.addEventListener('click', (e) => {
        const dropdown = document.getElementById('themeDropdown');
        const controls = document.querySelector('.theme-controls');
        if (!controls.contains(e.target)) {
            dropdown.setAttribute('aria-hidden', 'true');
        }
    });

    // Theme mode buttons
    document.querySelectorAll('.theme-mode-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const mode = btn.getAttribute('data-mode');
            setThemeMode(mode);
        });
    });

    // Color scheme buttons
    document.querySelectorAll('.color-scheme-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const color = btn.getAttribute('data-color');
            setColorScheme(color);
        });
    });

    // High contrast toggle
    document.getElementById('highContrastToggle').addEventListener('change', (e) => {
        setHighContrast(e.target.checked);
    });

    // Sepia toggle
    document.getElementById('sepiaToggle').addEventListener('change', (e) => {
        setSepia(e.target.checked);
    });

    // Listen for system theme changes
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
        if (themeState.mode === 'system') {
            applyTheme();
        }
    });
}