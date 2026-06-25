const tg = window.Telegram.WebApp;
tg.expand();

let userData = null;
let ws = null;
let chatMessages = [];

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadUserData();
    setupWebSocket();
    setupClicker();
    setupTabs();
});

function loadUserData() {
    fetch('/api/user')
        .then(res => res.json())
        .then(data => {
            userData = data;
            updateUI(data);
        })
        .catch(err => console.error('Error loading user data:', err));
}

function updateUI(data) {
    document.getElementById('coins').textContent = data.coins;
    document.getElementById('exp').textContent = data.exp;
    document.getElementById('level').textContent = data.level;
    document.getElementById('diamonds').textContent = data.diamonds;
    document.getElementById('profileCoins').textContent = data.coins;
    document.getElementById('profileExp').textContent = data.exp;
    document.getElementById('profileLevel').textContent = data.level;
    document.getElementById('profileDiamonds').textContent = data.diamonds;
    document.getElementById('profileClicks').textContent = data.total_clicks || 0;
    document.getElementById('profileName').textContent = data.username || data.first_name;
    document.getElementById('profileTitle').textContent = data.title || '🟢 Yangi o\'yinchi';
    document.getElementById('user-name').textContent = data.first_name || data.username;
    document.getElementById('user-title').textContent = data.title || '🟢 Yangi o\'yinchi';
    
    // Update progress bar
    const levelExp = getLevelExp(data.level);
    const nextLevelExp = getLevelExp(data.level + 1);
    const progress = ((data.exp - levelExp) / (nextLevelExp - levelExp)) * 100;
    document.getElementById('levelProgress').style.width = Math.min(progress, 100) + '%';
    document.getElementById('progressText').textContent = `${data.exp - levelExp} / ${nextLevelExp - levelExp} EXP`;
}

function getLevelExp(level) {
    const expMap = {
        1: 0, 2: 100, 3: 300, 4: 600, 5: 1000,
        6: 1500, 7: 2100, 8: 2800, 9: 3600, 10: 4500
    };
    return expMap[level] || 4500 + (level - 10) * 1000;
}

function setupTabs() {
    document.querySelectorAll('.nav-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
            document.getElementById('tab-' + btn.dataset.tab).classList.add('active');
        });
    });
}

function setupClicker() {
    const btn = document.getElementById('clickBtn');
    let cooldown = false;
    
    btn.addEventListener('click', () => {
        if (cooldown) return;
        cooldown = true;
        
        fetch('/api/click', { method: 'POST' })
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    userData.coins = data.coins;
                    userData.exp = data.exp;
                    userData.level = data.level;
                    updateUI(userData);
                    
                    // Animation
                    btn.style.transform = 'scale(0.9)';
                    setTimeout(() => btn.style.transform = 'scale(1)', 100);
                }
            })
            .catch(err => console.error('Click error:', err))
            .finally(() => {
                setTimeout(() => cooldown = false, 100);
            });
    });
}

function setupWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    ws = new WebSocket(`${protocol}//${window.location.host}/ws`);
    
    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.type === 'chat') {
            addChatMessage(data);
        }
    };
    
    ws.onclose = () => {
        setTimeout(setupWebSocket, 3000);
    };
}

function sendMessage() {
    const input = document.getElementById('chatInput');
    const text = input.value.trim();
    if (!text) return;
    
    ws.send(JSON.stringify({
        type: 'chat',
        message: text
    }));
    
    input.value = '';
}

function addChatMessage(data) {
    const container = document.getElementById('chatMessages');
    const msgDiv = document.createElement('div');
    msgDiv.className = 'chat-message';
    if (data.user_id === tg.initDataUnsafe.user.id) {
        msgDiv.classList.add('own');
    }
    
    const userSpan = document.createElement('div');
    userSpan.className = 'message-user';
    userSpan.innerHTML = `<span style="color: ${data.color || '#00ff88'}">${data.title || '🟢'}</span> ${data.username || data.first_name}`;
    
    const textSpan = document.createElement('div');
    textSpan.className = 'message-text';
    textSpan.textContent = data.message;
    
    const timeSpan = document.createElement('div');
    timeSpan.className = 'message-time';
    timeSpan.textContent = new Date(data.time).toLocaleTimeString();
    
    msgDiv.appendChild(userSpan);
    msgDiv.appendChild(textSpan);
    msgDiv.appendChild(timeSpan);
    container.appendChild(msgDiv);
    container.scrollTop = container.scrollHeight;
}

// Profile functions
function changeTitle() {
    const title = prompt('Yangi unvoningizni kiriting (emoji bilan):');
    if (!title) return;
    
    fetch('/api/title', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title })
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            userData.title = data.title;
            updateUI(userData);
        }
    });
}

function buyDiamond() {
    if (userData.coins < 1500000) {
        alert(`❌ Yetarli tanga yo'q! 1.5 mln tanga kerak. Sizda: ${userData.coins}`);
        return;
    }
    
    if (!confirm('💎 1.5 mln tangaga 1 ta olmos sotib olasizmi?')) return;
    
    fetch('/api/diamond', { method: 'POST' })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                userData.coins = data.coins;
                userData.diamonds = data.diamonds;
                updateUI(userData);
                alert('✅ Olmos sotib olindi!');
            }
        });
}

function sendCoins() {
    const target = prompt('Tangani yubormoqchi bo\'lgan foydalanuvchi ID sini kiriting:');
    if (!target) return;
    const amount = parseInt(prompt('Nechta tanga yubormoqchisiz?'));
    if (!amount || amount <= 0) return;
    if (amount > userData.coins) {
        alert('❌ Yetarli tanga yo\'q!');
        return;
    }
    
    fetch('/api/send', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ target: parseInt(target), amount })
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            userData.coins = data.coins;
            updateUI(userData);
            alert('✅ Tanga yuborildi!');
        } else {
            alert('❌ Xatolik: ' + data.error);
        }
    });
}

function showPromo() {
    const code = prompt('Promokodni kiriting:');
    if (!code) return;
    
    fetch('/api/promo', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code })
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            userData.coins = data.coins;
            userData.exp = data.exp;
            updateUI(userData);
            alert(`✅ Promokod aktivlashtirildi! +${data.added_coins} 🪙, +${data.added_exp} ⭐`);
        } else {
            alert('❌ Xatolik: ' + data.error);
        }
    });
}

function createAuction() {
    const name = prompt('Auktsion nomi:');
    if (!name) return;
    const desc = prompt('Tavsif:');
    const price = parseInt(prompt('Boshlang\'ich narx:'));
    if (!price || price <= 0) return;
    const duration = parseInt(prompt('Davomiyligi (daqiqa):'));
    if (!duration || duration <= 0) return;
    
    fetch('/api/auction/create', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, desc, price, duration })
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            alert('✅ Auktsion yaratildi!');
            refreshAuctions();
        }
    });
}

function refreshAuctions() {
    fetch('/api/auctions')
        .then(res => res.json())
        .then(data => {
            const container = document.getElementById('auctionList');
            container.innerHTML = '';
            data.forEach(item => {
                const div = document.createElement('div');
                div.className = 'auction-item';
                div.innerHTML = `
                    <h4>📦 ${item.item_name}</h4>
                    <p>${item.item_description}</p>
                    <p>💰 Joriy narx: ${item.current_bid || item.start_price}</p>
                    <p>👤 Yaratuvchi: ${item.creator_name}</p>
                    <button onclick="placeBid(${item.id})">💰 Taklif qilish</button>
                `;
                container.appendChild(div);
            });
        });
}

function placeBid(auctionId) {
    const amount = parseInt(prompt('Taklif miqdori:'));
    if (!amount || amount <= 0) return;
    
    fetch('/api/auction/bid', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ auction_id: auctionId, amount })
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            alert('✅ Taklif qabul qilindi!');
            refreshAuctions();
        } else {
            alert('❌ Xatolik: ' + data.error);
        }
    });
}