const tg = window.Telegram.WebApp;
tg.expand();

let userData = null;
let ws = null;
let isConnected = false;
let autoClickerInterval = null;

// ==================== LOCAL STORAGE ====================

function saveToLocalStorage(data) {
    try {
        localStorage.setItem('teleClickData', JSON.stringify(data));
        console.log('Data saved to localStorage');
    } catch (e) {
        console.error('Error saving to localStorage:', e);
    }
}

function loadFromLocalStorage() {
    try {
        const data = localStorage.getItem('teleClickData');
        if (data) {
            return JSON.parse(data);
        }
    } catch (e) {
        console.error('Error loading from localStorage:', e);
    }
    return null;
}

function clearLocalStorage() {
    try {
        localStorage.removeItem('teleClickData');
        console.log('localStorage cleared');
    } catch (e) {
        console.error('Error clearing localStorage:', e);
    }
}

// ==================== INITIALIZATION ====================

document.addEventListener('DOMContentLoaded', () => {
    const urlParams = new URLSearchParams(window.location.search);
    const userId = urlParams.get('user_id');
    
    if (userId) {
        // Try to load from localStorage first
        const savedData = loadFromLocalStorage();
        if (savedData && savedData.user_id == userId) {
            console.log('Loading data from localStorage');
            userData = savedData;
            updateUI(userData);
            // Still fetch from server to get latest data
            loadUserData(userId);
        } else {
            loadUserData(userId);
        }
    } else {
        alert('❌ Xatolik: Foydalanuvchi ID topilmadi!');
    }
    
    setupWebSocket();
    setupClicker();
    setupTabs();
    setupShop();
    setupSkins();
    setupChat();
    setupLeaderboard();
});

// ==================== USER DATA ====================

function loadUserData(userId) {
    fetch(`/api/user?user_id=${userId}`)
        .then(res => res.json())
        .then(data => {
            if (data.error) {
                // Try to create user
                fetch('/api/user', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ user_id: parseInt(userId) })
                })
                .then(res => res.json())
                .then(newData => {
                    if (newData.error) {
                        alert('❌ Xatolik: ' + newData.error);
                        return;
                    }
                    userData = newData;
                    userData.user_id = parseInt(userId);
                    updateUI(userData);
                    saveToLocalStorage(userData);
                    loadShop();
                    loadSkins();
                    loadUserSkins();
                    startAutoClicker();
                })
                .catch(err => {
                    console.error('Error creating user:', err);
                    alert('❌ Xatolik yuz berdi!');
                });
                return;
            }
            
            userData = data;
            userData.user_id = parseInt(userId);
            updateUI(data);
            saveToLocalStorage(data);
            loadShop();
            loadSkins();
            loadUserSkins();
            startAutoClicker();
        })
        .catch(err => {
            console.error('Error loading user data:', err);
            // Try to load from localStorage if fetch fails
            const savedData = loadFromLocalStorage();
            if (savedData) {
                userData = savedData;
                updateUI(userData);
                alert('⚠️ Offline rejimda ishlayapsiz! Ma\'lumotlar yangilanmadi.');
            } else {
                alert('❌ Xatolik yuz berdi!');
            }
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
    
    // Save to localStorage
    saveToLocalStorage(data);
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
            if (btn.dataset.tab === 'leaderboard') {
                loadLeaderboard();
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
                userData.total_clicks = (userData.total_clicks || 0) + 1;
                updateUI(userData);
                saveToLocalStorage(userData);
                
                if (data.leveled_up) {
                    showLevelUp(data.level);
                }
            } else if (data.error) {
                showError(data.error);
            }
        })
        .catch(err => {
            console.error('Click error:', err);
            // Offline mode - update locally
            if (userData) {
                userData.coins = (userData.coins || 0) + (userData.click_power || 1);
                userData.exp = (userData.exp || 0) + 15;
                userData.energy = (userData.energy || 0) - 1;
                userData.total_clicks = (userData.total_clicks || 0) + 1;
                updateUI(userData);
                saveToLocalStorage(userData);
                showError('⚠️ Offline rejim! Ma\'lumotlar mahalliy saqlandi.');
            }
        })
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
                    saveToLocalStorage(userData);
                }
            })
            .catch(err => console.error('Auto click error:', err));
        }
    }, 10000);
}

// ==================== SHOP ====================

function setupShop() {
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
                
                div.innerHTML = `
                    <div class="shop-item-emoji">${item.emoji}</div>
                    <div class="shop-item-name">${item.name}</div>
                    <div class="shop-item-desc">${item.description}</div>
                    <div class="shop-item-price">💰 ${formatNumber(item.price)}</div>
                    <div class="shop-item-level">${levelReq}</div>
                    <button onclick="buyShopItem(${item.id})" 
                            style="${!isAvailable ? 'opacity:0.5;' : ''}
