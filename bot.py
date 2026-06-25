const tg = window.Telegram.WebApp;
tg.expand();

let userData = null;
let ws = null;
let isConnected = false;
let autoClickerInterval = null;
let adminUsers = [];
let adminCurrentPage = 0;
const ADMIN_USERS_PER_PAGE = 20;

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

// ==================== INITIALIZATION ====================

document.addEventListener('DOMContentLoaded', () => {
    const urlParams = new URLSearchParams(window.location.search);
    const userId = urlParams.get('user_id');
    
    if (userId) {
        const savedData = loadFromLocalStorage();
        if (savedData && savedData.user_id == userId) {
            console.log('Loading data from localStorage');
            userData = savedData;
            updateUI(userData);
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
    setupAdmin();
});

// ==================== USER DATA ====================

function loadUserData(userId) {
    fetch(`/api/user?user_id=${userId}`)
        .then(res => res.json())
        .then(data => {
            if (data.error) {
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
                    checkAdminAccess();
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
            checkAdminAccess();
        })
        .catch(err => {
            console.error('Error loading user data:', err);
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

// ==================== ADMIN ACCESS ====================

function checkAdminAccess() {
    if (userData && userData.user_id) {
        fetch(`/api/admin/users?user_id=${userData.user_id}&limit=1`)
            .then(res => res.json())
            .then(data => {
                if (!data.error) {
                    document.querySelector('.admin-tab').style.display = 'block';
                }
            })
            .catch(() => {});
    }
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
            if (btn.dataset.tab === 'admin') {
                adminLoadAllUsers();
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
                const canAfford = userData && userData.coins >= item.price;
                
                div.innerHTML = `
                    <div class="shop-item-emoji">${item.emoji}</div>
                    <div class="shop-item-name">${item.name}</div>
                    <div class="shop-item-desc">${item.description}</div>
                    <div class="shop-item-price">💰 ${formatNumber(item.price)}</div>
                    <div class="shop-item-level">${levelReq}</div>
                    <button onclick="buyShopItem(${item.id})" 
                            style="${!isAvailable ? 'opacity:0.5;cursor:not-allowed;' : ''}">
                        ${isAvailable ? (canAfford ? 'Sotib olish' : '💰 Yetarli emas') : '🔒 Qulflangan'}
                    </button>
                `;
                container.appendChild(div);
            });
        })
        .catch(err => console.error('Error loading shop:', err));
}

function buyShopItem(itemId) {
    if (!userData) {
        alert('❌ Iltimos, avval profilingizni yuklang!');
        return;
    }
    
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
            saveToLocalStorage(userData);
            alert(data.message);
            loadShop();
        } else {
            alert('❌ Xatolik: ' + data.error);
        }
    })
    .catch(err => {
        console.error('Error buying item:', err);
        alert('❌ Xatolik yuz berdi!');
    });
}

// ==================== SKINS ====================

function setupSkins() {
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
                    <button onclick="buySkin(${skin.id})" 
                            style="${!isAvailable ? 'opacity:0.5;cursor:not-allowed;' : ''}">
                        ${isAvailable ? (canAfford ? 'Sotib olish' : '💰 Yetarli emas') : '🔒 Qulflangan'}
                    </button>
                `;
                container.appendChild(div);
            });
            
            loadUserSkins();
        })
        .catch(err => console.error('Error loading skins:', err));
}

function loadUserSkins() {
    if (!userData) return;
    
    fetch(`/api/user/skins?user_id=${userData.user_id}`)
        .then(res => res.json())
        .then(skins => {
            document.querySelectorAll('.skin-item').forEach(item => {
                const btn = item.querySelector('button');
                if (!btn) return;
                
                const match = btn.getAttribute('onclick');
                if (!match) return;
                
                const skinId = parseInt(match.match(/\d+/)[0]);
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
                        btn.disabled = false;
                        btn.onclick = function() { activateSkin(skinId); };
                    }
                }
            });
        })
        .catch(err => console.error('Error loading user skins:', err));
}

function buySkin(skinId) {
    if (!userData) {
        alert('❌ Iltimos, avval profilingizni yuklang!');
        return;
    }
    
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
            saveToLocalStorage(userData);
            alert(data.message);
            loadSkins();
            loadUserSkins();
        } else {
            alert('❌ Xatolik: ' + data.error);
        }
    })
    .catch(err => {
        console.error('Error buying skin:', err);
        alert('❌ Xatolik yuz berdi!');
    });
}

function activateSkin(skinId) {
    if (!userData) {
        alert('❌ Iltimos, avval profilingizni yuklang!');
        return;
    }
    
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
    .catch(err => {
        console.error('Error activating skin:', err);
        alert('❌ Xatolik yuz berdi!');
    });
}

// ==================== PROFILE FUNCTIONS ====================

function changeTitle() {
    if (!userData) {
        alert('❌ Iltimos, avval profilingizni yuklang!');
        return;
    }
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
            saveToLocalStorage(userData);
            alert('✅ Unvon o\'zgartirildi!');
        } else {
            alert('❌ Xatolik: ' + data.error);
        }
    })
    .catch(err => {
        console.error('Error:', err);
        alert('❌ Xatolik yuz berdi!');
    });
}

function buyDiamond() {
    if (!userData) {
        alert('❌ Iltimos, avval profilingizni yuklang!');
        return;
    }
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
            saveToLocalStorage(userData);
            alert('✅ Olmos sotib olindi!');
        } else {
            alert('❌ Xatolik: ' + data.error);
        }
    })
    .catch(err => {
        console.error('Error:', err);
        alert('❌ Xatolik yuz berdi!');
    });
}

function sendCoins() {
    if (!userData) {
        alert('❌ Iltimos, avval profilingizni yuklang!');
        return;
    }
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
            saveToLocalStorage(userData);
            alert('✅ Tanga yuborildi!');
        } else {
            alert('❌ Xatolik: ' + data.error);
        }
    })
    .catch(err => {
        console.error('Error:', err);
        alert('❌ Xatolik yuz berdi!');
    });
}

function showPromo() {
    if (!userData) {
        alert('❌ Iltimos, avval profilingizni yuklang!');
        return;
    }
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
            saveToLocalStorage(userData);
            alert(`✅ Promokod aktivlashtirildi! +${formatNumber(data.added_coins)} 🪙, +${formatNumber(data.added_exp)} ⭐`);
        } else {
            alert('❌ Xatolik: ' + data.error);
        }
    })
    .catch(err => {
        console.error('Error:', err);
        alert('❌ Xatolik yuz berdi!');
    });
}

// ==================== LEADERBOARD ====================

let currentLeaderboardType = 'current';

function setupLeaderboard() {
    document.querySelectorAll('.lb-tab-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.lb-tab-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentLeaderboardType = btn.dataset.lb;
            loadLeaderboard();
        });
    });
    
    loadLeaderboard();
}

function loadLeaderboard() {
    const endpoint = currentLeaderboardType === 'current' 
        ? '/api/leaderboard/current' 
        : '/api/leaderboard/total';
    
    fetch(endpoint)
        .then(res => res.json())
        .then(data => {
            const container = document.getElementById('leaderboardList');
            container.innerHTML = '';
            
            if (!data || data.length === 0) {
                container.innerHTML = '<p style="text-align:center;color:#888;padding:20px;">🏆 Hozircha hech kim yo\'q</p>';
                return;
            }
            
            data.forEach(item => {
                const div = document.createElement('div');
                div.className = 'lb-item';
                if (item.user_id === userData?.user_id) {
                    div.classList.add('lb-self');
                }
                
                let rankClass = '';
                if (item.rank === 1) rankClass = 'gold';
                else if (item.rank === 2) rankClass = 'silver';
                else if (item.rank === 3) rankClass = 'bronze';
                
                const rankDisplay = item.rank <= 3 ? '🏆' : `#${item.rank}`;
                
                let valueDisplay = '';
                if (currentLeaderboardType === 'current') {
                    valueDisplay = `🪙 ${formatNumber(item.coins)}`;
                } else {
                    valueDisplay = `🖱️ ${formatNumber(item.clicks || item.total_clicks)}`;
                }
                
                div.innerHTML = `
                    <div class="lb-rank ${rankClass}">${rankDisplay}</div>
                    <div class="lb-info">
                        <div class="lb-name">${item.name}</div>
                        <div class="lb-details">📊 ${item.level}-daraja • ${valueDisplay}</div>
                    </div>
                    <div class="lb-value">${valueDisplay}</div>
                `;
                container.appendChild(div);
            });
        })
        .catch(err => console.error('Error loading leaderboard:', err));
    
    // Load user rank
    if (userData) {
        fetch(`/api/leaderboard/rank?user_id=${userData.user_id}`)
            .then(res => res.json())
            .then(data => {
                const rankContainer = document.getElementById('leaderboardRank');
                if (data.current_rank && data.total_rank) {
                    rankContainer.innerHTML = `
                        <p style="color:#888;font-size:12px;">👤 Sizning o'rningiz</p>
                        <div style="display:flex;justify-content:center;gap:20px;margin-top:4px;">
                            <div>
                                <div class="rank-number">#${data.current_rank}</div>
                                <div style="font-size:10px;color:#888;">💰 Hozirgi</div>
                            </div>
                            <div>
                                <div class="rank-number">#${data.total_rank}</div>
                                <div style="font-size:10px;color:#888;">📈 Umumiy</div>
                            </div>
                        </div>
                    `;
                } else {
                    rankContainer.innerHTML = `
                        <p style="color:#888;font-size:12px;">👤 Siz hali reytingda yo'qsiz</p>
                    `;
                }
            })
            .catch(() => {});
    }
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
    if (!text) {
        alert('❌ Iltimos, xabar yozing!');
        return;
    }
    if (!isConnected) {
        alert('❌ Chatga ulanish yo\'q! Qayta urining...');
        return;
    }
    if (!userData) {
        alert('❌ Foydalanuvchi ma\'lumotlari topilmadi!');
        return;
    }
    
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
    try {
        const date = new Date(data.time);
        timeSpan.textContent = date.toLocaleTimeString();
    } catch {
        timeSpan.textContent = new Date().toLocaleTimeString();
    }
    
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
    const wsUrl = `${protocol}//${window.location.host}/ws`;
    console.log('Connecting to WebSocket:', wsUrl);
    
    ws = new WebSocket(wsUrl);
    
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
            } else if (data.type === 'system') {
                console.log('System message:', data.message);
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
    if (!userData) {
        alert('❌ Iltimos, avval profilingizni yuklang!');
        return;
    }
    
    const name = prompt('📦 Auktsion nomi:');
    if (!name || name.trim() === '') return;
    
    const desc = prompt('📝 Tavsif:');
    if (!desc || desc.trim() === '') return;
    
    const price = parseInt(prompt('💰 Boshlang\'ich narx:'));
    if (!price || price <= 0) {
        alert('❌ Narx 0 dan katta bo\'lishi kerak!');
        return;
    }
    
    if (price > userData.coins) {
        alert(`❌ Yetarli tanga yo'q! Sizda: ${formatNumber(userData.coins)}`);
        return;
    }
    
    const duration = parseInt(prompt('⏰ Davomiyligi (daqiqa):'));
    if (!duration || duration <= 0) {
        alert('❌ Davomiylik 0 dan katta bo\'lishi kerak!');
        return;
    }
    
    fetch('/api/auction/create', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
            user_id: userData.user_id,
            name: name.trim(), 
            desc: desc.trim(), 
            price: price, 
            duration: duration 
        })
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            userData.coins = data.coins;
            updateUI(userData);
            saveToLocalStorage(userData);
            alert(data.message || '✅ Auktsion yaratildi!');
            refreshAuctions();
            document.querySelector('[data-tab="auction"]').click();
        } else {
            alert('❌ Xatolik: ' + data.error);
        }
    })
    .catch(err => {
        console.error('Error creating auction:', err);
        alert('❌ Xatolik yuz berdi!');
    });
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
    if (!userData) {
        alert('❌ Iltimos, avval profilingizni yuklang!');
        return;
    }
    const amount = parseInt(prompt('💰 Taklif miqdori:'));
    if (!amount || amount <= 0) {
        alert('❌ Taklif 0 dan katta bo\'lishi kerak!');
        return;
    }
    
    if (amount > userData.coins) {
        alert(`❌ Yetarli tanga yo'q! Sizda: ${formatNumber(userData.coins)}`);
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
            userData.coins = data.coins;
            updateUI(userData);
            saveToLocalStorage(userData);
            alert(data.message || '✅ Taklif qabul qilindi!');
            refreshAuctions();
        } else {
            alert('❌ Xatolik: ' + data.error);
        }
    })
    .catch(err => {
        console.error('Error placing bid:', err);
        alert('❌ Xatolik yuz berdi!');
    });
}

// ==================== ADMIN ====================

function setupAdmin() {
    document.getElementById('adminSearchInput').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') adminSearchUsers();
    });
}

function adminSearchUsers() {
    const input = document.getElementById('adminSearchInput');
    const query = input.value.trim();
    
    if (!query || query.length < 2) {
        alert('❌ Iltimos, kamida 2 ta harf kiriting!');
        return;
    }
    
    if (!userData) {
        alert('❌ Foydalanuvchi ma\'lumotlari topilmadi!');
        return;
    }
    
    fetch('/api/admin/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            user_id: userData.user_id,
            query: query
        })
    })
    .then(res => res.json())
    .then(data => {
        if (data.error) {
            alert('❌ Xatolik: ' + data.error);
            return;
        }
        
        adminUsers = data.users || [];
        renderAdminUsers();
        
        document.getElementById('adminPagination').innerHTML = `
            <span style="color:#888;font-size:12px;">
                Qidiruv natijasi: ${adminUsers.length} ta foydalanuvchi
            </span>
        `;
    })
    .catch(err => {
        console.error('Error searching users:', err);
        alert('❌ Xatolik yuz berdi!');
    });
}

function adminLoadAllUsers() {
    if (!userData) {
        alert('❌ Foydalanuvchi ma\'lumotlari topilmadi!');
        return;
    }
    
    const offset = adminCurrentPage * ADMIN_USERS_PER_PAGE;
    
    fetch(`/api/admin/users?user_id=${userData.user_id}&limit=${ADMIN_USERS_PER_PAGE}&offset=${offset}`)
        .then(res => res.json())
        .then(data => {
            if (data.error) {
                alert('❌ Xatolik: ' + data.error);
                return;
            }
            
            adminUsers = data.users || [];
            renderAdminUsers();
            
            const total = data.total || 0;
            const totalPages = Math.ceil(total / ADMIN_USERS_PER_PAGE);
            document.getElementById('adminPagination').innerHTML = `
                <span style="color:#888;font-size:12px;">
                    Sahifa ${adminCurrentPage + 1} / ${totalPages || 1} (Jami: ${total} foydalanuvchi)
                </span>
                <div style="display:flex;gap:4px;margin-top:4px;justify-content:center;">
                    <button onclick="adminPrevPage()" ${adminCurrentPage <= 0 ? 'disabled' : ''} 
                            style="padding:4px 12px;border:none;border-radius:4px;background:#2a2a2a;color:#fff;cursor:pointer;">
                        ⬅️
                    </button>
                    <button onclick="adminNextPage()" ${adminCurrentPage >= totalPages - 1 ? 'disabled' : ''}
                            style="padding:4px 12px;border:none;border-radius:4px;background:#2a2a2a;color:#fff;cursor:pointer;">
                        ➡️
                    </button>
                </div>
            `;
        })
        .catch(err => {
            console.error('Error loading users:', err);
            alert('❌ Xatolik yuz berdi!');
        });
}

function adminPrevPage() {
    if (adminCurrentPage > 0) {
        adminCurrentPage--;
        adminLoadAllUsers();
    }
}

function adminNextPage() {
    adminCurrentPage++;
    adminLoadAllUsers();
}

function renderAdminUsers() {
    const container = document.getElementById('adminUserList');
    
    if (!adminUsers || adminUsers.length === 0) {
        container.innerHTML = '<p style="text-align:center;color:#888;padding:20px;">👤 Hech qanday foydalanuvchi topilmadi</p>';
        return;
    }
    
    container.innerHTML = '';
    
    adminUsers.forEach(user => {
        const div = document.createElement('div');
        div.className = 'admin-user-item';
        
        const name = user.first_name || user.username || `ID:${user.user_id}`;
        
        div.innerHTML = `
            <div class="admin-user-info">
                <div class="admin-user-name">${name}</div>
                <div class="admin-user-details">
                    🆔 ${user.user_id} • 📊 ${user.level || 1}-daraja • 🪙 ${formatNumber(user.coins || 0)} • 🖱️ ${formatNumber(user.total_clicks || 0)}
                </div>
            </div>
            <div class="admin-user-actions">
                <button class="btn-coins" onclick="adminAddCoins(${user.user_id})">+🪙</button>
                <button class="btn-exp" onclick="adminAddExp(${user.user_id})">+⭐</button>
                <button class="btn-energy" onclick="adminAddEnergy(${user.user_id})">+⚡</button>
            </div>
        `;
        container.appendChild(div);
    });
}

function adminAddCoins(userId) {
    const amount = parseInt(prompt(`🪙 ${userId} ga nechta tanga qo'shmoqchisiz?`));
    if (!amount || amount <= 0) return;
    
    if (!userData) {
        alert('❌ Foydalanuvchi ma\'lumotlari topilmadi!');
        return;
    }
    
    fetch('/api/admin/add_coins', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            admin_id: userData.user_id,
            target_id: userId,
            amount: amount
        })
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            alert(data.message);
            const query = document.getElementById('adminSearchInput').value.trim();
            if (query) {
                adminSearchUsers();
            } else {
                adminLoadAllUsers();
            }
        } else {
            alert('❌ Xatolik: ' + data.error);
        }
    })
    .catch(err => {
        console.error('Error adding coins:', err);
        alert('❌ Xatolik yuz berdi!');
    });
}

function adminAddExp(userId) {
    const amount = parseInt(prompt(`⭐ ${userId} ga nechta EXP qo'shmoqchisiz?`));
    if (!amount || amount <= 0) return;
    
    if (!userData) {
        alert('❌ Foydalanuvchi ma\'lumotlari topilmadi!');
        return;
    }
    
    fetch('/api/admin/add_exp', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            admin_id: userData.user_id,
            target_id: userId,
            amount: amount
        })
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            alert(data.message);
            const query = document.getElementById('adminSearchInput').value.trim();
            if (query) {
                adminSearchUsers();
            } else {
                adminLoadAllUsers();
            }
        } else {
            alert('❌ Xatolik: ' + data.error);
        }
    })
    .catch(err => {
        console.error('Error adding exp:', err);
        alert('❌ Xatolik yuz berdi!');
    });
}

function adminAddEnergy(userId) {
    const amount = parseInt(prompt(`⚡ ${userId} ga nechta energiya qo'shmoqchisiz?`));
    if (!amount || amount <= 0) return;
    
    if (!userData) {
        alert('❌ Foydalanuvchi ma\'lumotlari topilmadi!');
        return;
    }
    
    fetch('/api/admin/add_energy', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            admin_id: userData.user_id,
            target_id: userId,
            amount: amount
        })
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            alert(data.message);
            const query = document.getElementById('adminSearchInput').value.trim();
            if (query) {
                adminSearchUsers();
            } else {
                adminLoadAllUsers();
            }
        } else {
            alert('❌ Xatolik: ' + data.error);
        }
    })
    .catch(err => {
        console.error('Error adding energy:', err);
        alert('❌ Xatolik yuz berdi!');
    });
}

// ==================== AUTO REFRESH ====================

setInterval(() => {
    if (document.getElementById('tab-auction').classList.contains('active')) {
        refreshAuctions();
    }
}, 30000);

setInterval(() => {
    if (userData) {
        fetch(`/api/user?user_id=${userData.user_id}`)
            .then(res => res.json())
            .then(data => {
                if (!data.error) {
                    userData.energy = data.energy;
                    userData.max_energy = data.max_energy;
                    updateUI(userData);
                    saveToLocalStorage(userData);
                }
            })
            .catch(err => console.error('Error refreshing energy:', err));
    }
}, 10000);

setInterval(() => {
    if (document.getElementById('tab-leaderboard').classList.contains('active')) {
        loadLeaderboard();
    }
}, 60000);
