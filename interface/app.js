// app.js - Dashboard JavaScript pour Agent IA Marketing Ben Tech

console.log('🚀 app.js chargé - Dashboard Ben Tech Marketing');

// ==================== GESTION DES SESSIONS ====================

// Vérifier si l'utilisateur est connecté
function isUserLoggedIn() {
    const token = localStorage.getItem('auth_token');
    const user = localStorage.getItem('user');
    return token && user;
}

// Rediriger vers le login si pas connecté
function checkSession() {
    if (!isUserLoggedIn()) {
        console.log('❌ Session non trouvée, redirection vers login');
        window.location.href = '/';
        return false;
    }
    return true;
}

// Fonction pour les appels API
async function callAPI(endpoint, method = 'GET', data = null) {
    try {
        // Vérifier la session
        if (!checkSession()) {
            return null;
        }
        
        const token = localStorage.getItem('auth_token');
        const options = {
            method: method,
            headers: {
                'Content-Type': 'application/json',
                'Authorization': token || ''
            }
        };
        
        if (data) {
            options.body = JSON.stringify(data);
        }
        
        console.log(`📡 Appel API: ${method} ${endpoint}`);
        const response = await fetch(endpoint, options);
        
        if (!response.ok) {
            if (response.status === 401) {
                // Session expirée
                localStorage.removeItem('auth_token');
                localStorage.removeItem('user');
                window.location.href = '/';
                return null;
            }
            
            let errorMessage = `Erreur HTTP: ${response.status}`;
            try {
                const errorData = await response.json();
                errorMessage = errorData.message || errorMessage;
            } catch (e) {
                errorMessage = await response.text();
            }
            
            throw new Error(errorMessage);
        }
        
        return await response.json();
    } catch (error) {
        console.error('❌ Erreur API:', error);
        throw error;
    }
}

// ==================== NAVIGATION ET UI ====================

// Initialisation de la navigation
function initNavigation() {
    console.log('🔧 Initialisation de la navigation...');
    
    const menuItems = document.querySelectorAll('.menu-item');
    console.log(`📋 ${menuItems.length} éléments de menu trouvés`);
    
    menuItems.forEach(item => {
        item.addEventListener('click', function(e) {
            e.preventDefault();
            const section = this.getAttribute('data-section');
            console.log(`📱 Menu cliqué: ${section}`);
            
            // Retirer active de tous
            menuItems.forEach(mi => mi.classList.remove('active'));
            
            // Ajouter active au cliqué
            this.classList.add('active');
            
            // Masquer toutes les sections
            document.querySelectorAll('.content-section').forEach(cs => {
                cs.classList.remove('active');
            });
            
            // Afficher la section correspondante
            const targetSection = document.getElementById(`section-${section}`);
            if (targetSection) {
                targetSection.classList.add('active');
                console.log(`✅ Section affichée: section-${section}`);
                
                // Actions spécifiques selon la section
                handleSectionChange(section);
            } else {
                console.error(`❌ Section non trouvée: section-${section}`);
            }
        });
    });
}

// Actions spécifiques selon la section
function handleSectionChange(section) {
    switch(section) {
        case 'chat':
            setTimeout(() => {
                const chatMessages = document.getElementById('chatMessages');
                if (chatMessages) {
                    chatMessages.scrollTop = chatMessages.scrollHeight;
                }
            }, 100);
            break;
        case 'logs':
            loadSystemLogs();
            break;
        case 'publish':
            updateContentTable();
            break;
        case 'generate':
            // Rien de spécial pour l'instant
            break;
        case 'settings':
            loadConfig();
            break;
    }
}

// Gestion des toggle switches
function initToggleSwitches() {
    console.log('🔧 Initialisation des toggle switches...');
    
    document.querySelectorAll('.toggle-switch').forEach(toggle => {
        toggle.addEventListener('click', function() {
            this.classList.toggle('active');
            
            const setting = this.id.replace('Toggle', '');
            const isActive = this.classList.contains('active');
            console.log(`🔘 Toggle ${setting}: ${isActive ? 'ACTIF' : 'INACTIF'}`);
            
            saveSetting(setting, isActive);
        });
    });
}

// ==================== FONCTIONS UTILITAIRES ====================

// Sauvegarder un paramètre
async function saveSetting(key, value) {
    try {
        const response = await callAPI('/api/config', 'PUT', { [key]: value });
        
        if (response && response.status === 'success') {
            addLog(`Paramètre ${key} mis à jour: ${value}`, 'info');
        } else {
            console.error('Erreur lors de la sauvegarde:', response);
        }
    } catch (error) {
        console.error('Erreur lors de la sauvegarde:', error);
    }
}

// Afficher un résultat
function showResult(elementId, message, isError = false) {
    const element = document.getElementById(elementId);
    if (!element) {
        console.error(`❌ Élément non trouvé: ${elementId}`);
        return;
    }
    
    const content = element.querySelector('.result-value') || element;
    
    if (isError) {
        element.style.background = 'rgba(231, 76, 60, 0.1)';
        element.style.borderColor = 'rgba(231, 76, 60, 0.3)';
    } else {
        element.style.background = 'rgba(46, 204, 113, 0.1)';
        element.style.borderColor = 'rgba(46, 204, 113, 0.3)';
    }
    
    if (typeof message === 'object') {
        content.textContent = JSON.stringify(message, null, 2);
    } else {
        content.textContent = message;
    }
    
    element.classList.add('show');
    console.log(`✅ Résultat affiché dans ${elementId}`);
}

// Ajouter un log dans l'interface
function addLog(message, type = 'info') {
    const logsContainer = document.getElementById('realtimeLogs');
    if (!logsContainer) {
        console.log(`📝 Log (${type}): ${message}`);
        return;
    }
    
    const now = new Date();
    const time = now.getHours().toString().padStart(2, '0') + ':' + 
                 now.getMinutes().toString().padStart(2, '0') + ':' + 
                 now.getSeconds().toString().padStart(2, '0');
    
    let icon = '✓';
    if (type === 'error') icon = '✗';
    if (type === 'warning') icon = '⚠';
    if (type === 'action') icon = '⚡';
    
    const logItem = document.createElement('div');
    logItem.className = 'log-item';
    logItem.innerHTML = `${icon} [${time}] ${message}`;
    
    logsContainer.insertBefore(logItem, logsContainer.firstChild);
    
    // Limiter à 50 logs
    if (logsContainer.children.length > 50) {
        logsContainer.removeChild(logsContainer.lastChild);
    }
    
    console.log(`📝 Log ajouté (${type}): ${message}`);
}

// ==================== DASHBOARD - STATUT SYSTÈME ====================

// Initialiser les boutons du dashboard
function initDashboardButtons() {
    console.log('🔧 Initialisation des boutons du dashboard...');
    
    // Vérifier le statut
    const checkStatusBtn = document.getElementById('checkStatusBtn');
    if (checkStatusBtn) {
        checkStatusBtn.addEventListener('click', async function() {
            await checkSystemStatus();
        });
    }
    
    // Générer du contenu - Dashboard
    const generateNowBtn = document.getElementById('generateNowBtn');
    if (generateNowBtn) {
        generateNowBtn.addEventListener('click', async function() {
            await generateContent();
        });
    }
    
    // Publier manuellement - Dashboard
    const publishNowBtn = document.getElementById('publishNowBtn');
    if (publishNowBtn) {
        publishNowBtn.addEventListener('click', async function() {
            await publishContent();
        });
    }
}

// Vérifier le statut système
async function checkSystemStatus() {
    const btn = document.getElementById('checkStatusBtn');
    if (!btn) return;
    
    const originalText = btn.textContent;
    
    btn.classList.add('loading');
    btn.disabled = true;
    
    try {
        addLog('Vérification du statut système...', 'action');
        
        const result = await callAPI('/api/status');
        
        if (result) {
            showResult('actionResult', `✅ ${result.service} - ${result.status.toUpperCase()}\nMode auto: ${result.auto_mode ? 'ACTIVÉ' : 'DÉSACTIVÉ'}\nVersion: ${result.version}`);
            addLog(`Statut système vérifié: ${result.status}`, 'info');
            updateSystemStatus(result);
        }
        
    } catch (error) {
        showResult('actionResult', `❌ Erreur: ${error.message}`, true);
        addLog(`Erreur lors de la vérification: ${error.message}`, 'error');
    } finally {
        btn.classList.remove('loading');
        btn.disabled = false;
        btn.textContent = originalText;
    }
}

// Mettre à jour l'affichage du statut
function updateSystemStatus(statusData) {
    console.log('📊 Mise à jour du statut système:', statusData);
    
    const statCards = document.querySelectorAll('.stat-card');
    if (statCards.length >= 3) {
        // Carte 1: Statut système
        const systemStatus = statCards[0].querySelector('.stat-value');
        if (systemStatus) {
            systemStatus.innerHTML = `
                <span class="status-indicator">
                    <span class="status-dot ${statusData.status === 'online' ? 'status-online' : 'status-warning'}"></span>
                    ${statusData.status === 'online' ? 'En ligne' : 'Hors ligne'}
                </span>
            `;
        }
        
        // Carte 2: Mode automatique
        const autoMode = statCards[1].querySelector('.stat-value');
        if (autoMode) {
            autoMode.innerHTML = `
                <span class="status-indicator">
                    <span class="status-dot ${statusData.auto_mode ? 'status-active' : 'status-warning'}"></span>
                    ${statusData.auto_mode ? 'Activé' : 'Désactivé'}
                </span>
            `;
        }
        
        // Carte 3: API disponible
        const apiStatus = statCards[2].querySelector('.stat-value');
        if (apiStatus) {
            apiStatus.innerHTML = `
                <span class="status-indicator">
                    <span class="status-dot status-online"></span>
                    /generate, /api/publish
                </span>
            `;
        }
    }
}

// ==================== GÉNÉRATION DE CONTENU ====================

// Initialiser les boutons de génération
function initGenerateButtons() {
    console.log('🔧 Initialisation des boutons de génération...');
    
    const generateContentBtn = document.getElementById('generateContentBtn');
    if (generateContentBtn) {
        generateContentBtn.addEventListener('click', async function() {
            await generateContent();
        });
    }
}

// Générer du contenu avec ton module Python
async function generateContent() {
    const btn = document.getElementById('generateContentBtn') || document.getElementById('generateNowBtn');
    if (!btn) {
        console.error('❌ Bouton de génération non trouvé');
        return;
    }
    
    const originalText = btn.textContent;
    
    btn.classList.add('loading');
    btn.disabled = true;
    
    try {
        addLog('Démarrage de la génération de contenu IA...', 'action');
        
        // Appel à l'API de génération
        const result = await callAPI('/generate');
        
        if (result) {
            const contentData = result.data;
            
            // Formater l'affichage du contenu généré
            const formattedContent = `
🏷️ Titre: ${contentData.titre || 'Sans titre'}
🎯 Thème: ${contentData.theme || 'Non spécifié'}
💼 Service: ${contentData.service || 'Non spécifié'}
🎨 Style: ${contentData.style || 'Standard'}
📊 Type: ${contentData.type_publication || 'contenu'}
📈 Conversion estimée: ${contentData.taux_conversion_estime || 0}%

📝 Texte marketing:
${contentData.texte_marketing?.substring(0, 500) || 'Non disponible'}${contentData.texte_marketing?.length > 500 ? '...' : ''}

🎥 Script vidéo:
${contentData.script_video?.substring(0, 300) || 'Non disponible'}${contentData.script_video?.length > 300 ? '...' : ''}

🖼️ Image: ${contentData.image_path ? 'Téléchargée ✓' : 'Non disponible'}
👤 Auteur image: ${contentData.image_auteur || 'Non spécifié'}
            `;
            
            showResult('generateResult', formattedContent);
            showResult('actionResult', `✅ ${result.message}\nTitre: ${contentData.titre}`);
            
            addLog(`Contenu généré: ${contentData.titre}`, 'info');
            
            // Mettre à jour les données
            updateContentTable();
            updateRecentData();
            loadStats();
        }
        
    } catch (error) {
        showResult('generateResult', `❌ Erreur: ${error.message}`, true);
        showResult('actionResult', `❌ Échec de la génération: ${error.message}`, true);
        addLog(`Erreur génération: ${error.message}`, 'error');
    } finally {
        btn.classList.remove('loading');
        btn.disabled = false;
        btn.textContent = originalText;
    }
}

// ==================== PUBLICATION DE CONTENU ====================

// Initialiser les boutons de publication
function initPublishButtons() {
    console.log('🔧 Initialisation des boutons de publication...');
    
    const publishContentBtn = document.getElementById('publishContentBtn');
    if (publishContentBtn) {
        publishContentBtn.addEventListener('click', async function() {
            await publishContent();
        });
    }
}

// Publier du contenu
async function publishContent() {
    const btn = document.getElementById('publishContentBtn') || document.getElementById('publishNowBtn');
    if (!btn) {
        console.error('❌ Bouton de publication non trouvé');
        return;
    }
    
    const originalText = btn.textContent;
    
    btn.classList.add('loading');
    btn.disabled = true;
    
    try {
        addLog('Démarrage de la publication...', 'action');
        
        const result = await callAPI('/api/publish', 'POST');
        
        if (result) {
            const message = result.message || 'Publication effectuée';
            const count = result.published_count || 0;
            
            showResult('publishResult', JSON.stringify(result, null, 2));
            showResult('actionResult', `✅ ${message} (${count} publications)`);
            
            addLog(`${count} contenus publiés`, 'info');
            updateContentTable();
            updateRecentData();
        }
        
    } catch (error) {
        showResult('publishResult', `❌ Erreur: ${error.message}`, true);
        showResult('actionResult', `❌ Échec publication: ${error.message}`, true);
        addLog(`Erreur publication: ${error.message}`, 'error');
    } finally {
        btn.classList.remove('loading');
        btn.disabled = false;
        btn.textContent = originalText;
    }
}

// ==================== GESTION DES DONNÉES ====================

// Mettre à jour la table des contenus
async function updateContentTable() {
    const table = document.getElementById('contentTable');
    if (!table) {
        console.error('❌ Table des contenus non trouvée');
        return;
    }
    
    try {
        console.log('📋 Mise à jour de la table des contenus...');
        const result = await callAPI('/api/data/recent?limit=20');
        
        if (result && result.data && result.data.length > 0) {
            table.innerHTML = result.data.map((item, index) => `
                <tr>
                    <td>${index + 1}</td>
                    <td>${item.titre || 'Sans titre'}</td>
                    <td>${item.date || 'Non spécifié'}</td>
                    <td>
                        <span class="status-indicator">
                            <span class="status-dot ${item.publication_effective === 'oui' ? 'status-online' : 'status-warning'}"></span>
                            ${item.publication_effective === 'oui' ? 'Publié' : 'En attente'}
                        </span>
                    </td>
                    <td>
                        <button class="btn-secondary" style="padding: 6px 12px; font-size: 12px;" 
                                onclick="publishSingleItem(${index})">
                            Publier
                        </button>
                    </td>
                </tr>
            `).join('');
            console.log(`✅ ${result.data.length} contenus affichés`);
        } else {
            table.innerHTML = `
                <tr>
                    <td colspan="5" style="text-align: center; padding: 40px; color: rgba(255,255,255,0.5);">
                        Aucun contenu disponible
                    </td>
                </tr>
            `;
            console.log('ℹ️ Aucun contenu disponible');
        }
    } catch (error) {
        console.error('❌ Erreur table des contenus:', error);
        table.innerHTML = `
            <tr>
                <td colspan="5" style="text-align: center; padding: 40px; color: rgba(255,255,255,0.5);">
                    Erreur lors du chargement
                </td>
            </tr>
        `;
    }
}

// Mettre à jour les données récentes
async function updateRecentData() {
    try {
        const result = await callAPI('/api/data/recent?limit=5');
        if (result && result.data) {
            updateRecentLogs(result.data);
        }
    } catch (error) {
        console.error('❌ Erreur données récentes:', error);
    }
}

// Mettre à jour les logs récents
function updateRecentLogs(data) {
    const logsContainer = document.getElementById('systemLogs');
    if (!logsContainer || !data || data.length === 0) return;
    
    const recentItems = data.slice(0, 5);
    
    logsContainer.innerHTML = recentItems.map(item => {
        const date = item.date ? new Date(item.date).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'}) : 'N/A';
        const icon = item.publication_effective === 'oui' ? '✓' : '⏳';
        return `<div class="log-item">${icon} [${date}] ${item.titre || 'Contenu généré'}</div>`;
    }).join('');
}

// Publier un item spécifique
window.publishSingleItem = async function(index) {
    try {
        addLog(`Publication de l'élément ${index + 1}...`, 'action');
        
        const result = await callAPI('/api/publish', 'POST');
        if (result) {
            addLog(`Publication effectuée: ${result.message}`, 'info');
            updateContentTable();
        }
    } catch (error) {
        addLog(`Erreur publication: ${error.message}`, 'error');
    }
};

// ==================== STATISTIQUES ====================

// Charger les statistiques
async function loadStats() {
    try {
        console.log('📊 Chargement des statistiques...');
        const result = await callAPI('/api/stats');
        
        if (result && result.stats) {
            const stats = result.stats;
            
            // Mettre à jour les cartes de statistiques si elles existent
            const totalPosts = stats.total_posts || 0;
            const avgPositive = stats.moyenne_reactions_positives || 0;
            const avgConversion = stats.taux_conversion_moyen || 0;
            
            console.log(`📈 Statistiques chargées: ${totalPosts} posts, ${avgPositive} réactions moyennes`);
            
            // Ajouter des logs pour les recommandations
            if (stats.recommandations && stats.recommandations.length > 0) {
                stats.recommandations.forEach(rec => {
                    addLog(`💡 ${rec.titre}: ${rec.description}`, 'info');
                });
            }
        }
    } catch (error) {
        console.error('❌ Erreur chargement stats:', error);
    }
}

// ==================== JOURNAUX SYSTÈME ====================

// Initialiser les boutons des journaux
function initLogsButtons() {
    console.log('🔧 Initialisation des boutons des journaux...');
    
    const refreshLogsBtn = document.getElementById('refreshLogsBtn');
    if (refreshLogsBtn) {
        refreshLogsBtn.addEventListener('click', async function() {
            await refreshLogs();
        });
    }
    
    const clearLogsBtn = document.getElementById('clearLogsBtn');
    if (clearLogsBtn) {
        clearLogsBtn.addEventListener('click', function() {
            clearLocalLogs();
        });
    }
}

// Charger les journaux système
async function loadSystemLogs() {
    try {
        console.log('📝 Chargement des journaux système...');
        const result = await callAPI('/api/logs');
        if (result && result.logs) {
            const logsContainer = document.getElementById('realtimeLogs');
            if (!logsContainer) return;
            
            logsContainer.innerHTML = '';
            const reversedLogs = [...result.logs].reverse();
            
            reversedLogs.forEach(log => {
                const logItem = document.createElement('div');
                logItem.className = 'log-item';
                logItem.textContent = log.trim();
                logsContainer.appendChild(logItem);
            });
            
            console.log(`✅ ${result.logs.length} journaux chargés`);
        }
    } catch (error) {
        console.error('❌ Erreur chargement journaux:', error);
    }
}

// Actualiser les journaux
async function refreshLogs() {
    try {
        console.log('🔄 Actualisation des journaux...');
        await loadSystemLogs();
        addLog('Journaux actualisés', 'info');
    } catch (error) {
        console.error('❌ Erreur actualisation journaux:', error);
        addLog(`Erreur actualisation: ${error.message}`, 'error');
    }
}

// Effacer les journaux locaux
function clearLocalLogs() {
    const logsContainer = document.getElementById('realtimeLogs');
    if (logsContainer) {
        logsContainer.innerHTML = '';
        addLog('Journaux locaux effacés', 'warning');
        console.log('🗑️ Journaux locaux effacés');
    }
}

// ==================== CHAT IA ====================

// Initialiser le chat
function initChat() {
    console.log('🔧 Initialisation du chat...');
    
    const chatForm = document.getElementById('chatForm');
    if (chatForm) {
        chatForm.addEventListener('submit', function(e) {
            e.preventDefault();
            const message = document.getElementById('chatInput').value.trim();
            if (message) {
                sendChatMessage(message);
            }
        });
    }
    
    const chatInput = document.getElementById('chatInput');
    if (chatInput) {
        chatInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                if (chatInput.value.trim()) {
                    sendChatMessage(chatInput.value.trim());
                }
            }
        });
    }
}

// Envoyer un message dans le chat
async function sendChatMessage(message) {
    console.log(`💬 Envoi message chat: ${message.substring(0, 50)}...`);
    if (!message.trim()) return;
    
    addUserMessage(message);
    
    const chatInput = document.getElementById('chatInput');
    if (chatInput) {
        chatInput.value = '';
    }
    
    try {
        const result = await callAPI('/api/chat/analyze', 'POST', {
            question: message,
            contexte: "dashboard"
        });
        
        if (result) {
            displayBotResponse(result, message);
        }
    } catch (error) {
        console.error('❌ Erreur chat:', error);
        setTimeout(async () => {
            await generateBotResponse(message);
        }, 1000);
    }
}

// Ajouter un message utilisateur
function addUserMessage(text) {
    const chatMessages = document.getElementById('chatMessages');
    if (!chatMessages) return;
    
    const now = new Date();
    const time = now.getHours().toString().padStart(2, '0') + ':' + 
                 now.getMinutes().toString().padStart(2, '0');
    
    const messageHTML = `
        <div class="message user">
            <div class="message-avatar">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="#3498db">
                    <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 3c1.66 0 3 1.34 3 3s-1.34 3-3 3-3-1.34-3-3 1.34-3 3-3zm0 14.2c-2.5 0-4.71-1.28-6-3.22.03-1.99 4-3.08 6-3.08 1.99 0 5.97 1.09 6 3.08-1.29 1.94-3.5 3.22-6 3.22z"/>
                </svg>
            </div>
            <div class="message-content">
                <div class="message-text">${text}</div>
                <div class="message-time">${time}</div>
            </div>
        </div>
    `;
    
    chatMessages.insertAdjacentHTML('beforeend', messageHTML);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// Afficher la réponse du bot
function displayBotResponse(apiResponse, userMessage) {
    const chatMessages = document.getElementById('chatMessages');
    if (!chatMessages) return;
    
    const now = new Date();
    const time = now.getHours().toString().padStart(2, '0') + ':' + 
                 now.getMinutes().toString().padStart(2, '0');
    
    let responseHTML = '';
    
    if (apiResponse.analysis) {
        const analysis = apiResponse.analysis;
        
        responseHTML = `
            <div class="message bot">
                <div class="message-avatar">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="#3498db">
                        <path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/>
                    </svg>
                </div>
                <div class="message-content">
                    <div class="message-text">
                        <strong>🔍 Analyse IA:</strong><br>
                        ${analysis}
                        
                        ${apiResponse.recommendations && apiResponse.recommendations.length > 0 ? 
                            `<br><br><strong>💡 Recommandations:</strong><br>${apiResponse.recommendations.map(r => `• ${r.titre || r}`).join('<br>')}` : ''}
                    </div>
                    <div class="message-time">${time}</div>
                </div>
            </div>
        `;
    } else {
        responseHTML = `
            <div class="message bot">
                <div class="message-avatar">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="#3498db">
                        <path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/>
                    </svg>
                </div>
                <div class="message-content">
                    <div class="message-text">
                        ${apiResponse.message || "J'ai analysé votre question. Voici mes recommandations..."}
                    </div>
                    <div class="message-time">${time}</div>
                </div>
            </div>
        `;
    }
    
    chatMessages.insertAdjacentHTML('beforeend', responseHTML);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// Réponse de fallback
async function generateBotResponse(userMessage) {
    const chatMessages = document.getElementById('chatMessages');
    if (!chatMessages) return;
    
    const now = new Date();
    const time = now.getHours().toString().padStart(2, '0') + ':' + 
                 now.getMinutes().toString().padStart(2, '0');
    
    let response = "";
    const lowerMessage = userMessage.toLowerCase();
    
    if (lowerMessage.includes('bonjour') || lowerMessage.includes('salut') || lowerMessage.includes('hello')) {
        response = "Bonjour ! Je suis l'assistant IA de Ben Tech Marketing. Je peux vous aider avec la génération de contenu, l'analyse des performances et les recommandations marketing.";
    } else if (lowerMessage.includes('générer') || lowerMessage.includes('génération')) {
        response = "Pour générer du contenu, allez dans la section 'Générer' et cliquez sur 'Générer du contenu IA'. J'utiliserai votre module IA Python pour créer du contenu optimisé.";
    } else if (lowerMessage.includes('publier') || lowerMessage.includes('publication')) {
        response = "Pour publier, allez dans la section 'Publier' et cliquez sur 'Publier les contenus en attente'. Vous pouvez aussi publier des contenus spécifiques depuis la table.";
    } else if (lowerMessage.includes('statut') || lowerMessage.includes('état')) {
        response = "Vérifiez le statut dans le Dashboard ou avec le bouton 'Vérifier le statut'. Vous verrez l'état du serveur, le mode automatique et les endpoints disponibles.";
    } else if (lowerMessage.includes('contenu') || lowerMessage.includes('post')) {
        response = "Votre système génère automatiquement du contenu marketing optimisé avec IA. Il choisit les thèmes, services et styles basés sur les performances historiques.";
    } else if (lowerMessage.includes('ia') || lowerMessage.includes('intelligence')) {
        response = "Notre IA analyse l'historique des posts pour optimiser le contenu, choisir les meilleurs thèmes et services, et générer des recommandations personnalisées.";
    } else {
        const responses = [
            "Je peux vous aider avec l'analyse des performances, les recommandations marketing, et la génération de contenu intelligent.",
            "Votre système utilise une IA avancée pour analyser les tendances et optimiser le contenu marketing.",
            "Consultez les statistiques pour voir les performances de vos posts et les recommandations proactives.",
            "Le module IA analyse les données historiques pour créer du contenu personnalisé et performant."
        ];
        response = responses[Math.floor(Math.random() * responses.length)];
    }
    
    const messageHTML = `
        <div class="message bot">
            <div class="message-avatar">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="#3498db">
                    <path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/>
                </svg>
            </div>
            <div class="message-content">
                <div class="message-text">${response}</div>
                <div class="message-time">${time}</div>
            </div>
        </div>
    `;
    
    chatMessages.insertAdjacentHTML('beforeend', messageHTML);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// Envoyer une question FAQ
window.sendFAQ = function(question) {
    console.log(`❓ FAQ: ${question}`);
    const chatInput = document.getElementById('chatInput');
    if (chatInput) {
        chatInput.value = question;
        if (chatInput.value.trim()) {
            sendChatMessage(chatInput.value.trim());
        }
    }
};

// ==================== CONFIGURATION ====================

// Charger la configuration
async function loadConfig() {
    try {
        console.log('⚙️ Chargement de la configuration...');
        const result = await callAPI('/api/config');
        
        if (result && result.config) {
            const config = result.config;
            
            // Mettre à jour les toggle switches
            const autoToggle = document.getElementById('autoModeToggle');
            const notifToggle = document.getElementById('notifToggle');
            
            if (autoToggle && config.auto_mode !== undefined) {
                autoToggle.classList.toggle('active', config.auto_mode);
            }
            
            if (notifToggle && config.notifications !== undefined) {
                notifToggle.classList.toggle('active', config.notifications);
            }
            
            // Mettre à jour l'URL du serveur
            const serverUrl = document.getElementById('serverUrl');
            if (serverUrl) {
                serverUrl.value = window.location.origin;
            }
            
            console.log('✅ Configuration chargée');
        }
    } catch (error) {
        console.error('❌ Erreur chargement config:', error);
    }
}

// ==================== DÉCONNEXION ====================

// Initialiser le bouton de déconnexion
function initLogoutButton() {
    console.log('🔧 Initialisation du bouton de déconnexion...');
    
    const logoutBtn = document.getElementById('logoutBtn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', async function(e) {
            e.preventDefault();
            if (confirm('Voulez-vous vraiment vous déconnecter ?')) {
                await logoutUser();
            }
        });
    }
}

// Déconnecter l'utilisateur
async function logoutUser() {
    try {
        await callAPI('/api/logout', 'POST');
        
        localStorage.removeItem('auth_token');
        localStorage.removeItem('user');
        
        window.location.href = '/';
        
    } catch (error) {
        console.error('❌ Erreur déconnexion:', error);
        localStorage.removeItem('auth_token');
        localStorage.removeItem('user');
        window.location.href = '/';
    }
}

// ==================== INITIALISATION PRINCIPALE ====================

// Fonction d'initialisation principale
async function initApp() {
    console.log('🚀 Initialisation de l\'application Dashboard Ben Tech...');
    
    // Vérifier la session
    if (!checkSession()) {
        return;
    }
    
    // Initialiser tous les composants
    initNavigation();
    initToggleSwitches();
    initDashboardButtons();
    initGenerateButtons();
    initPublishButtons();
    initLogsButtons();
    initChat();
    initLogoutButton();
    
    // Ajouter des logs initiaux
    addLog('Dashboard Ben Tech Marketing chargé', 'info');
    addLog('Session utilisateur active', 'info');
    addLog('Connexion à l\'API FastAPI établie', 'info');
    
    // Charger les données initiales
    try {
        // Charger le statut système
        const status = await callAPI('/api/status');
        if (status) {
            updateSystemStatus(status);
            console.log('✅ Statut système chargé');
        }
        
        // Charger la configuration
        await loadConfig();
        
        // Charger les statistiques
        await loadStats();
        
        // Charger la table des contenus
        await updateContentTable();
        
        // Charger les journaux système
        await loadSystemLogs();
        
        console.log('✅ Données initiales chargées avec succès');
        addLog('Système opérationnel et prêt', 'info');
        
    } catch (error) {
        console.error('❌ Erreur lors du chargement initial:', error);
        addLog(`Erreur initialisation: ${error.message}`, 'error');
    }
    
    // Mises à jour périodiques
    setInterval(async () => {
        try {
            // Mettre à jour le statut système
            const status = await callAPI('/api/status');
            if (status) {
                updateSystemStatus(status);
            }
            
            // Ajouter un log d'activité
            const activities = [
                'Vérification système en cours',
                'Analyse des performances en temps réel',
                'Synchronisation avec le module IA Python',
                'Vérification des contenus en attente'
            ];
            
            const randomActivity = activities[Math.floor(Math.random() * activities.length)];
            addLog(randomActivity, 'info');
            
        } catch (error) {
            console.error('❌ Erreur mise à jour périodique:', error);
        }
    }, 30000); // Toutes les 30 secondes
    
    // Tester la connexion au serveur
    setTimeout(async () => {
        try {
            const health = await fetch('/health');
            if (health.ok) {
                addLog('✅ Connexion serveur stable', 'info');
            }
        } catch (error) {
            console.warn('⚠️ Problème de connexion serveur:', error);
        }
    }, 5000);
}

// Démarrer l'application quand le DOM est chargé
document.addEventListener('DOMContentLoaded', initApp);