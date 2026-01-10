/* static/dashboard.js */

// 1. MENU & NAVIGATIE
function toggleMenu() {
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('overlay');
    sidebar.classList.toggle('active');
    
    if (sidebar.classList.contains('active')) {
        overlay.style.display = 'block';
    } else {
        overlay.style.display = 'none';
    }
}

function veranderDatum(input) { 
    window.location.href = '/?datum=' + input.value; 
}


// 2. GRAFIEKEN TEKENEN
function initGrafieken(liveData, teleData, limits) {
    const canvasLive = document.getElementById('liveChart');
    if (!canvasLive) return; 

    const grensDuur = limits.duur;
    
    // Instellingen
    const gridConfig = { color: (ctx) => (ctx.tick && ctx.tick.value === 0 ? '#FFFFFF' : '#333'), lineWidth: (ctx) => (ctx.tick && ctx.tick.value === 0 ? 2 : 1) };
    const yAxisConfig = { grid: gridConfig, suggestedMin: -10, suggestedMax: 10, ticks: { color: '#CCC', font: {weight:'bold'} }, border: {display:false} };
    const xAxisConfig = { grid: { display: false }, ticks: { color: '#999', maxTicksLimit: 8 } };

    // --- Live Grafiek ---
    const ctxLive = canvasLive.getContext('2d');
    const grad = ctxLive.createLinearGradient(0,0,0,400);
    grad.addColorStop(0, 'rgba(41, 181, 232, 0.3)');
    grad.addColorStop(1, 'rgba(41, 181, 232, 0)');

    new Chart(ctxLive, {
        type: 'line',
        data: {
            labels: liveData.tijden,
            datasets: [{
                data: liveData.prijzen,
                borderColor: '#29B5E8', 
                segment: { borderColor: ctx => ctx.p0.parsed.y < 0 && ctx.p1.parsed.y < 0 ? '#00CC96' : undefined },
                backgroundColor: grad, fill: true, borderWidth: 2, pointRadius: 0, tension: 0.3
            }]
        },
        options: { 
            maintainAspectRatio: false, 
            scales: { x: xAxisConfig, y: yAxisConfig },
            interaction: { mode: 'index', intersect: false },
            plugins: {
                legend: {display:false},
                annotation: { annotations: { line1: { type: 'line', yMin: grensDuur, yMax: grensDuur, borderColor: '#FF4B4B', borderWidth: 2, borderDash: [5, 5] } } }
            } 
        }
    });

    // --- Telegram (Kwartier) Grafiek ---
    const ctxTele = document.getElementById('teleChart').getContext('2d');
    const gradTele = ctxTele.createLinearGradient(0,0,0,300);
    gradTele.addColorStop(0, 'rgba(0, 204, 150, 0.3)');
    gradTele.addColorStop(1, 'rgba(0, 204, 150, 0)');

    new Chart(ctxTele, {
        type: 'line',
        data: {
            labels: teleData.tijden,
            datasets: [{
                data: teleData.prijzen,
                borderColor: '#00CC96', backgroundColor: gradTele, fill: true,
                borderWidth: 2, pointRadius: 4, pointBackgroundColor: '#00CC96', tension: 0
            }]
        },
        options: { 
            maintainAspectRatio: false, 
            scales: { x: xAxisConfig, y: yAxisConfig }, 
            interaction: { mode: 'index', intersect: false }, 
            plugins: {legend: {display:false}} 
        }
    });
}

// 3. AUTO REFRESH
function startAutoRefresh(isLive) {
    let refreshTimer;
    const toggleBtn = document.getElementById('autoRefreshToggle');
    
    function startTimer() {
        if (toggleBtn && toggleBtn.checked) {
            refreshTimer = setTimeout(() => location.reload(), 60000); 
        }
    }

    if (isLive) startTimer();

    if (toggleBtn) {
        toggleBtn.addEventListener('change', function() { 
            if (this.checked) startTimer(); 
            else clearTimeout(refreshTimer); 
        });
    }
}