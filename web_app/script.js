const tg = window.Telegram.WebApp;
tg.expand();

let userData = null;
let ws = null;
let isConnected = false;
let autoClickerInterval = null;

// ==================== INITIALIZATION ====================

document.addEventListener('DOMContentLoaded', () => {
    const urlParams = new URLSearchParams(window.location.search);
    const userId = urlParams.get('user_id');
    
    if (userId) {
        loadUserData(userId);
    } else {
        alert('❌ Xatolik: Foydalanuvchi ID topilmadi!');
    }
    
    setupWebSocket();
    setupClicker();
    setupTabs();
    setupShop();
    setupSkins();
    setupChat();
});

// ==================== USER DATA ====================

function loadUserData(userId) {
    fetch('/api/user', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: parseInt(userId) })
    })
    .then(res => res.json())
    .then(data => {
        if (data.error) {
            alert('❌ Xatolik: ' + data.error);
            return;
        }
        userData = data;
        userData.user_id = parseInt(userId);
        updateUI(data);
        loadShop();
        loadSkins();
        loadUserSkins();
        startAutoClicker();
    })
    .catch(err => {
        console.error('Error loading user data:', err);
        alert('❌ Xatolik yuz berdi!');
    });
}

function updateUI(data) {
    // Stats
    document.getElementById('coins').textContent = formatNumber(data.coins || 0);
    document.getElementById('exp').textContent = formatNumber(data.exp || 0);
    document.getElementById('level').textContent = data.level || 1;
    document.getElementById('diamonds').textContent = data.diamonds || 0;
    
    // Energy
    const energy = data.energy || 0;
    const maxEnergy = data.max_energy || 500;
    const energyPercent = (energy / maxEnergy) * 100;
    document.getElementById('energyFill').style.width = Math.min(energyPercent, 100) + '%';
    document.getElementById('energyText').textContent = `⚡ ${Math.floor(energy)} / ${maxEnergy}`;
    
    // Power info
    document.getElementById('clickPower').textContent = data.click_power || 1;
    document.getElementById('multiplierDisplay').textContent = (data.multiplier || 1) + 'x';
    document.getElementById('autoLevel').textContent = data.auto_clicker_level || 0;
    
    // Click info
    const clickPower = data.click_power || 1;
    const multiplier = data.multiplier || 1;
    const totalCoins = clickPower * multiplier;
    document.getElementById('clickInfo').textContent = `+${totalCoins} coin, +10-20 exp`;
    
    // Profile
    document.getElementById('profileCoins').textContent = formatNumber(data.coins || 0);
    document.getElementById('profileExp').textContent = formatNumber(data.exp || 0);
    document.getElementById('profileLevel').textContent = data.level || 1;
    document.getElementById('profileDiamonds').textContent = data.diamonds || 0;
    document.getElementById('profileClicks').textContent = formatNumber(data.total_clicks || 0);
    document.getElementById('profileEnergy').textContent = Math.floor(data.energy || 0);
    
    const name = data.first_name || data.username || 'Foydalanuvchi';
    document.getElementById('profileName').textContent = name;
    document.getElementById('profileTitle').textContent = data.title || '🟢 Yangi o\'yinchi';
    document.getElementById('profileTitle').style.color = data.color || '#00ff88';
    
    document.getElementById('user-name').textContent = name;
    document.getElementById('user-title').textContent = data.title || '🟢 Yangi o\'yinchi';
    document.getElementById('user-title').style.color = data.color || '#00ff88';
    
    // Progress bar
    const level = data.level || 1;
    const exp = data.exp || 0;
    const requiredExp = getRequiredExp(level);
    const nextRequiredExp = getRequiredExp(level + 1);
    const progress = ((exp - requiredExp) / (nextRequiredExp - requiredExp)) * 100;
    document.getElementById('levelProgress').style.width = Math.min(Math.max(progress, 0), 100) + '%';
    document.getElementById('progressText').textContent = 
        `${formatNumber(Math.max(0, exp - requiredExp))} / ${formatNumber(nextRequiredExp - requiredExp)} EXP`;
}

function formatNumber(num) {
    if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
    if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
    return Math.floor(num).toString();
}

function getRequiredExp(level) {
    if (level <= 5) return level * 100;
    else if (level <= 10) return level * 200;
    else if (level <= 15) return level * 300;
    else if (level <= 20) return level * 500;
    else return level * 800;
}

// ==================== TABS ====================

function setupTabs() {
    document.querySelectorAll('.nav-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
            document.getElementById('tab-' + btn.dataset.tab).classList.add('active');
            
            if (btn.dataset.tab === 'auction') {
                refreshAuctions();
            }
            if (btn.dataset.tab === 'shop') {
                loadShop();
            }
            if (btn.dataset.tab === 'skins') {
                loadSkins();
                loadUserSkins();
            }
        });
    });
}

// ==================== CLICKER ====================

function setupClicker() {
    const btn = document.getElementById('clickBtn');
    let cooldown = false;
    
    btn.addEventListener('click', () => {
        if (cooldown) return;
        cooldown = true;
        
        btn.style.transform = 'scale(0.85)';
        setTimeout(() => btn.style.transform = 'scale(1)', 100);
        
        createCoinAnimation(btn);
        
        fetch('/api/click', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: userData.user_id })
        })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                userData.coins = data.coins;
                userData.exp = data.exp;
                userData.level = data.level;
                userData.energy = data.energy;
                userData.max_energy = data.max_energy;
                userData.click_power = data.click_power;
                userData.multiplier = data.multiplier;
                updateUI(userData);
                
                if (data.leveled_up) {
                    showLevelUp(data.level);
                }
            } else if (data.error) {
                showError(data.error);
            }
        })
        .catch(err => console.error('Click error:', err))
        .finally(() => {
            setTimeout(() => cooldown = false, 100);
        });
    });
}

function createCoinAnimation(btn) {
    const rect = btn.getBoundingClientRect();
    const coin = document.createElement('div');
    coin.className = 'coin-animation';
    coin.textContent = '🪙';
    coin.style.cssText = `
        position: fixed;
        left: ${rect.left + rect.width/2 - 20}px;
        top: ${rect.top}px;
        font-size: 36px;
        pointer-events: none;
        transition: all 0.8s ease-out;
        z-index: 1000;
    `;
    document.body.appendChild(coin);
    
    setTimeout(() => {
        coin.style.transform = 'translateY(-200px) rotate(360deg) scale(0.3)';
        coin.style.opacity = '0';
    }, 10);
    
    setTimeout(() => coin.remove(), 800);
}

function showLevelUp(level) {
    const popup = document.createElement('div');
    popup.style.cssText = `
        position: fixed;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        background: #1a1a1a;
        border: 3px solid #ffaa00;
        border-radius: 20px;
        padding: 30px;
        text-align: center;
        z-index: 2000;
        animation: fadeIn 0.5s;
        max-width: 300px;
    `;
    popup.innerHTML = `
        <div style="font-size: 60px;">🎉</div>
        <h2 style="color: #ffaa00;">DARAJANGIZ OSHDI!</h2>
        <p style="font-size: 32px; color: #00ff88;">${level}</p>
        <button onclick="this.parentElement.remove()" style="
            padding: 10px 30px;
            border: none;
            border-radius: 10px;
            background: #00ff88;
            color: #0a0a0a;
            font-weight: bold;
            font-size: 16px;
            cursor: pointer;
            margin-top: 10px;
        ">YOPISH</button>
    `;
    document.body.appendChild(popup);
    setTimeout(() => popup.remove(), 5000);
}

function showError(message) {
    const popup = document.createElement('div');
    popup.style.cssText = `
        position: fixed;
        bottom: 20px;
        left: 50%;
        transform: translateX(-50%);
        background: #ff4444;
        color: #fff;
        padding: 12px 20px;
        border-radius: 10px;
        z-index: 2000;
        animation: fadeIn 0.3s;
        max-width: 90%;
        text-align: center;
    `;
    popup.textContent = '❌ ' + message;
    document.body.appendChild(popup);
    setTimeout(() => popup.remove(), 3000);
}

// ==================== AUTO CLICKER ====================

function startAutoClicker() {
    if (autoClickerInterval) {
        clearInterval(autoClickerInterval);
    }
    
    autoClickerInterval = setInterval(() => {
        if (!userData) return;
        
        const autoLevel = userData.auto_clicker_level || 0;
        if (autoLevel <= 0) return;
        
        // Auto click multiple times
        for (let i = 0; i < autoLevel; i++) {
            fetch('/api/click', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ user_id: userData.user_id })
            })
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    userData.coins = data.coins;
                    userData.exp = data.exp;
                    userData.level = data.level;
                    userData.energy = data.energy;
                    updateUI(userData);
                }
            })
            .catch(err => console.error('Auto click error:', err));
        }
    }, 10000); // Har 10 soniyada
}

// ==================== SHOP ====================

function setupShop() {
    // Category filters
    document.querySelectorAll('.category-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.category-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            
            const category = btn.dataset.category;
            document.querySelectorAll('.shop-item').forEach(item => {
                if (category === 'all' || item.dataset.category === category) {
                    item.style.display = 'block';
                } else {
                    item.style.display = 'none';
                }
            });
        });
    });
}

function loadShop() {
    fetch('/api/shop/items')
        .then(res => res.json())
        .then(items => {
            const container = document.getElementById('shopItems');
            container.innerHTML = '';
            
            if (!items || items.length === 0) {
                container.innerHTML = '<p style="text-align:center;color:#888;padding:20px;">🏪 Hozircha do\'konda hech narsa yo\'q</p>';
                return;
            }
            
            items.forEach(item => {
                const div = document.createElement('div');
                div.className = 'shop-item';
                div.dataset.category = item.category;
                
                const levelReq = item.level_required > 1 ? `📊 ${item.level_required}-daraja` : '🆓 Hech qanday';
                const isAvailable = userData && userData.level >= item.level_required;
                const canAfford = userData && userData.coins >= item.price;
                
                div.innerHTML = `
                    <div class="shop-item-emoji">${item.emoji}</div>
                    <div class="shop-item-name">${item.name}</div>
                    <div class="shop-item-desc">${item.description}</div>
                    <div class="shop-item-price">💰 ${formatNumber(item.price)}</div>
                    <div class="shop-item-level">${levelReq}</div>
                    <button onclick="buyShopItem(${item.id})" 
                            style="${!isAvailable ? 'opacity:0.5;' : ''}">
                        ${isAvailable ? 'Sotib olish' : '🔒 Qulflangan'}
                    </button>
                `;
                container.appendChild(div);
            });
        })
        .catch(err => console.error('Error loading shop:', err));
}

function buyShopItem(itemId) {
    if (!userData) return;
    
    fetch('/api/shop/buy', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            user_id: userData.user_id,
            item_id: itemId
        })
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            userData.coins = data.coins;
            userData.max_energy = data.max_energy;
            userData.click_power = data.click_power;
            userData.auto_clicker_level = data.auto_clicker_level;
            updateUI(userData);
            alert(data.message);
            loadShop();
        } else {
            alert('❌ Xatolik: ' + data.error);
        }
    })
    .catch(err => console.error('Error buying item:', err));
}

// ==================== SKINS ====================

function setupSkins() {
    // Rarity filters
    document.querySelectorAll('.skin-filter-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.skin-filter-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            
            const rarity = btn.dataset.rarity;
            document.querySelectorAll('.skin-item').forEach(item => {
                if (rarity === 'all' || item.dataset.rarity === rarity) {
                    item.style.display = 'block';
                } else {
                    item.style.display = 'none';
                }
            });
        });
    });
}

function loadSkins() {
    fetch('/api/skins')
        .then(res => res.json())
        .then(skins => {
            const container = document.getElementById('skinList');
            container.innerHTML = '';
            
            if (!skins || skins.length === 0) {
                container.innerHTML = '<p style="text-align:center;color:#888;padding:20px;">🎨 Hozircha skinlar yo\'q</p>';
                return;
            }
            
            skins.forEach(skin => {
                const div = document.createElement('div');
                div.className = `skin-item ${skin.rarity}`;
                div.dataset.rarity = skin.rarity;
                
                const isAvailable = userData && userData.level >= skin.level_required;
                const canAfford = userData && userData.coins >= skin.price;
                
                const rarityColors = {
                    'common': '#00ff88',
                    'rare': '#4488ff',
                    'epic': '#aa44ff',
                    'legendary': '#ffaa00'
                };
                
                div.innerHTML = `
                    <div class="skin-emoji">${skin.emoji}</div>
                    <div class="skin-name">${skin.name}</div>
                    <div class="skin-rarity" style="color: ${rarityColors[skin.rarity]}">${skin.rarity.toUpperCase()}</div>
                    <div class="skin-multiplier">${skin.multiplier}x multiplier</div>
                    <div class="skin-level">📊 ${skin.level_required}-daraja</div>
                    <div class="skin-price">💰 ${formatNumber(skin.price)}</div>
                    <button onclick="buySkin(${skin.id})">
                        ${isAvailable ? 'Sotib olish' : '🔒 Qulflangan'}
                    </button>
                `;
                container.appendChild(div);
            });
        })
        .catch(err => console.error('Error loading skins:', err));
}

function loadUserSkins() {
    if (!userData) return;
    
    fetch(`/api/user/skins?user_id=${userData.user_id}`)
        .then(res => res.json())
        .then(skins => {
            // Mark owned skins
            document.querySelectorAll('.skin-item').forEach(item => {
                const btn = item.querySelector('button');
                const skinId = parseInt(btn.getAttribute('onclick').match(/\d+/)[0]);
                
                const owned = skins.find(s => s.skin_id === skinId);
                if (owned) {
                    item.classList.add('owned');
                    if (owned.is_active) {
                        item.classList.add('active-skin');
                        btn.textContent = '✅ Faol';
                        btn.disabled = true;
                        btn.style.opacity = '0.5';
                    } else {
                        btn.textContent = '👔 Kiymoq';
                        btn.className = 'activate-btn';
                        btn.onclick = function() { activateSkin(skinId); };
                    }
                }
            });
        })
        .catch(err => console.error('Error loading user skins:', err));
}

function buySkin(skinId) {
    if (!userData) return;
    
    fetch('/api/skin/buy', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            user_id: userData.user_id,
            skin_id: skinId
        })
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            userData.coins = data.coins;
            updateUI(userData);
            alert(data.message);
            loadSkins();
            loadUserSkins();
        } else {
            alert('❌ Xatolik: ' + data.error);
        }
    })
    .catch(err => console.error('Error buying skin:', err));
}

function activateSkin(skinId) {
    if (!userData) return;
    
    fetch('/api/skin/activate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            user_id: userData.user_id,
            skin_id: skinId
        })
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            alert('✅ Skin faollashtirildi!');
            loadSkins();
            loadUserSkins();
        } else {
            alert('❌ Xatolik: ' + data.error);
        }
    })
    .catch(err => console.error('Error activating skin:', err));
}

// ==================== PROFILE FUNCTIONS ====================

function changeTitle() {
    if (!userData) return;
    const title = prompt('Yangi unvoningizni kiriting (emoji bilan):');
    if (!title) return;
    
    fetch('/api/title', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
            user_id: userData.user_id,
            title: title 
        })
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            userData.title = data.title;
            updateUI(userData);
            alert('✅ Unvon o\'zgartirildi!');
        } else {
            alert('❌ Xatolik: ' + data.error);
        }
    })
    .catch(err => console.error('Error:', err));
}

function buyDiamond() {
    if (!userData) return;
    if (userData.coins < 1500000) {
        alert(`❌ Yetarli tanga yo'q! 1.5 mln tanga kerak. Sizda: ${formatNumber(userData.coins)}`);
        return;
    }
    
    if (!confirm('💎 1.5 mln tangaga 1 ta olmos sotib olasizmi?')) return;
    
    fetch('/api/diamond', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: userData.user_id })
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            userData.coins = data.coins;
            userData.diamonds = data.diamonds;
            updateUI(userData);
            alert('✅ Olmos sotib olindi!');
        } else {
            alert('❌ Xatolik: ' + data.error);
        }
    })
    .catch(err => console.error('Error:', err));
}

function sendCoins() {
    if (!userData) return;
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
        body: JSON.stringify({ 
            user_id: userData.user_id,
            target: parseInt(target), 
            amount: amount 
        })
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
    })
    .catch(err => console.error('Error:', err));
}

function showPromo() {
    if (!userData) return;
    const code = prompt('Promokodni kiriting:');
    if (!code) return;
    
    fetch('/api/promo', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
            user_id: userData.user_id,
            code: code.toUpperCase() 
        })
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            userData.coins = data.coins;
            userData.exp = data.exp;
            updateUI(userData);
            alert(`✅ Promokod aktivlashtirildi! +${formatNumber(data.added_coins)} 🪙, +${formatNumber(data.added_exp)} ⭐`);
        } else {
            alert('❌ Xatolik: ' + data.error);
        }
    })
    .catch(err => console.error('Error:', err));
}

// ==================== CHAT ====================

function setupChat() {
    const input = document.getElementById('chatInput');
    input.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendMessage();
    });
}

function sendMessage() {
    const input = document.getElementById('chatInput');
    const text = input.value.trim();
    if (!text || !isConnected || !userData) return;
    
    ws.send(JSON.stringify({
        type: 'chat',
        user_id: userData.user_id,
        message: text
    }));
    
    input.value = '';
}

function addChatMessage(data) {
    const container = document.getElementById('chatMessages');
    const msgDiv = document.createElement('div');
    msgDiv.className = 'chat-message';
    
    if (data.user_id === userData?.user_id) {
        msgDiv.classList.add('own');
    }
    
    const userSpan = document.createElement('div');
    userSpan.className = 'message-user';
    const name = data.username || data.first_name || 'Foydalanuvchi';
    const displayName = name.length > 20 ? name.substring(0, 17) + '...' : name;
    userSpan.innerHTML = `<span style="color: ${data.color || '#00ff88'}">${data.title || '🟢'}</span> ${displayName}`;
    
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
    
    while (container.children.length > 100) {
        container.removeChild(container.firstChild);
    }
}

// ==================== WEBSOCKET ====================

function setupWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    ws = new WebSocket(`${protocol}//${window.location.host}/ws`);
    
    ws.onopen = () => {
        console.log('WebSocket connected');
        isConnected = true;
        if (userData) {
            ws.send(JSON.stringify({
                type: 'auth',
                user_id: userData.user_id
            }));
        }
    };
    
    ws.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            if (data.type === 'chat') {
                addChatMessage(data);
            }
        } catch (e) {
            console.error('WebSocket message error:', e);
        }
    };
    
    ws.onclose = () => {
        console.log('WebSocket disconnected');
        isConnected = false;
        setTimeout(setupWebSocket, 3000);
    };
    
    ws.onerror = (error) => {
        console.error('WebSocket error:', error);
    };
}

// ==================== AUCTION ====================

function createAuction() {
    if (!userData) return;
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
        body: JSON.stringify({ 
            user_id: userData.user_id,
            name, 
            desc, 
            price, 
            duration 
        })
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            alert('✅ Auktsion yaratildi!');
            refreshAuctions();
            document.querySelector('[data-tab="auction"]').click();
        } else {
            alert('❌ Xatolik: ' + data.error);
        }
    })
    .catch(err => console.error('Error:', err));
}

function refreshAuctions() {
    fetch('/api/auctions')
        .then(res => res.json())
        .then(data => {
            const container = document.getElementById('auctionList');
            container.innerHTML = '';
            
            if (!data || data.length === 0) {
                container.innerHTML = '<p style="text-align:center;color:#888;padding:20px;">🔨 Hozircha faol auktsionlar yo\'q</p>';
                return;
            }
            
            data.forEach(item => {
                const div = document.createElement('div');
                div.className = 'auction-item';
                const timeLeft = getTimeLeft(item.end_time);
                div.innerHTML = `
                    <h4>📦 ${item.item_name}</h4>
                    <p>${item.item_description}</p>
                    <p>💰 Joriy narx: ${formatNumber(item.current_bid || item.start_price)} 🪙</p>
                    <p>👤 Yaratuvchi: ${item.creator_name || item.creator_id}</p>
                    <p>⏰ ${timeLeft}</p>
                    <button onclick="placeBid(${item.id})">💰 Taklif qilish</button>
                `;
                container.appendChild(div);
            });
        })
        .catch(err => console.error('Error loading auctions:', err));
}

function getTimeLeft(endTime) {
    const end = new Date(endTime);
    const now = new Date();
    const diff = end - now;
    
    if (diff <= 0) return '⏰ Tugagan';
    
    const minutes = Math.floor(diff / 60000);
    const seconds = Math.floor((diff % 60000) / 1000);
    
    if (minutes > 60) {
        const hours = Math.floor(minutes / 60);
        return `⏰ ${hours} soat ${minutes % 60} daqiqa`;
    }
    return `⏰ ${minutes} daqiqa ${seconds} soniya`;
}

function placeBid(auctionId) {
    if (!userData) return;
    const amount = parseInt(prompt('Taklif miqdori:'));
    if (!amount || amount <= 0) return;
    
    if (amount > userData.coins) {
        alert('❌ Yetarli tanga yo\'q!');
        return;
    }
    
    fetch('/api/auction/bid', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
            user_id: userData.user_id,
            auction_id: auctionId, 
            amount: amount 
        })
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            alert('✅ Taklif qabul qilindi!');
            userData.coins = data.coins;
            updateUI(userData);
            refreshAuctions();
        } else {
            alert('❌ Xatolik: ' + data.error);
        }
    })
    .catch(err => console.error('Error:', err));
}

// ==================== AUTO REFRESH ====================

// Auto refresh auctions every 30 seconds
setInterval(() => {
    if (document.getElementById('tab-auction').classList.contains('active')) {
        refreshAuctions();
    }
}, 30000);

// Auto refresh energy every 10 seconds
setInterval(() => {
    if (userData) {
        // Energy automatically refills on server side
        // Just update UI to show changes
        fetch('/api/user', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: userData.user_id })
        })
        .then(res => res.json())
        .then(data => {
            if (!data.error) {
                userData.energy = data.energy;
                userData.max_energy = data.max_energy;
                updateUI(userData);
            }
        })
        .catch(err => console.error('Error refreshing energy:', err));
    }
}, 10000);
