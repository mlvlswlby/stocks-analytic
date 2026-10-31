if (typeof Vue === 'undefined') {
    console.error("Vue library is not available.");
    const splash = document.getElementById('app-loading');
    if (splash) {
        splash.innerHTML = `
            <div class="text-center p-8 bg-slate-800 rounded-2xl border border-rose-500/50 max-w-md mx-4 shadow-2xl">
                <div class="text-5xl mb-4">&#9888;&#65039;</div>
                <h2 class="text-white font-bold text-xl mb-2">Koneksi CDN Terhambat</h2>
                <p class="text-slate-300 text-sm mb-6 leading-relaxed">Komponen antarmuka pengguna gagal diunduh oleh browser. Silakan muat ulang halaman.</p>
                <button onclick="window.location.reload(true)" class="px-6 py-2.5 bg-blue-600 hover:bg-blue-500 text-white rounded-xl text-sm font-bold shadow-lg shadow-blue-500/30 transition-all">Muat Ulang Halaman</button>
            </div>
        `;
    }
}

const { createApp, ref, computed, watch, onMounted, nextTick } = window.Vue || Vue || {};

// Curated High-Resolution Corporate Logos (Vector SVG & 500px Wikimedia transparent PNGs)
const KNOWN_LOGOS = {
    // IDX Top Banking & Finance
    'BBCA': 'https://upload.wikimedia.org/wikipedia/commons/thumb/5/5c/Bank_Central_Asia.svg/500px-Bank_Central_Asia.svg.png',
    'BBRI': 'https://upload.wikimedia.org/wikipedia/commons/thumb/9/9a/BRI_2025_%28with_full_name%29.svg/500px-BRI_2025_%28with_full_name%29.svg.png',
    'BMRI': 'https://upload.wikimedia.org/wikipedia/commons/thumb/a/ad/Bank_Mandiri_logo_2016.svg/500px-Bank_Mandiri_logo_2016.svg.png',
    'BBNI': 'https://upload.wikimedia.org/wikipedia/en/thumb/5/5a/Bank_Negara_Indonesia_logo.svg/500px-Bank_Negara_Indonesia_logo.svg.png',
    'BBTN': 'https://unavatar.io/btn.co.id',
    'BRIS': 'https://unavatar.io/bankbsi.co.id',
    'ARTO': 'https://unavatar.io/jago.com',
    'BTPS': 'https://unavatar.io/btpnsyariah.com',
    'BDMN': 'https://unavatar.io/danamon.co.id',
    'BNGA': 'https://unavatar.io/cimbniaga.co.id',

    // IDX Telco & Tech
    'TLKM': 'https://thumb.wikimedia.org/wikipedia/id/thumb/c/c4/Telkom_Indonesia_2013.svg/langid-500px-Telkom_Indonesia_2013.svg.png',
    'ISAT': 'https://unavatar.io/ioh.co.id',
    'EXCL': 'https://unavatar.io/xl.co.id',
    'GOTO': 'https://upload.wikimedia.org/wikipedia/commons/thumb/3/30/GoTo_logo.svg/500px-GoTo_logo.svg.png',
    'BUKA': 'https://unavatar.io/bukalapak.com',
    'EMTK': 'https://unavatar.io/emtek.co.id',
    'TOWR': 'https://unavatar.io/protelindo.net',
    'TBIG': 'https://unavatar.io/tower-bersama.com',

    // IDX Consumer & Retail
    'ASII': 'https://upload.wikimedia.org/wikipedia/commons/thumb/7/7b/Astra_International_logo.svg/500px-Astra_International_logo.svg.png',
    'UNVR': 'https://upload.wikimedia.org/wikipedia/en/thumb/e/e4/Unilever.svg/500px-Unilever.svg.png',
    'ICBP': 'https://unavatar.io/indofoodcbp.com',
    'INDF': 'https://unavatar.io/indofood.com',
    'AMRT': 'https://upload.wikimedia.org/wikipedia/commons/thumb/8/86/Alfamart_logo.svg/500px-Alfamart_logo.svg.png',
    'MIDI': 'https://unavatar.io/alfamidiku.com',
    'MYOR': 'https://unavatar.io/mayora.com',
    'CPIN': 'https://unavatar.io/cp.co.id',
    'JPFA': 'https://unavatar.io/japfacomfeed.co.id',
    'KLBF': 'https://unavatar.io/kalbe.co.id',
    'SIDO': 'https://unavatar.io/sidomuncul.co.id',
    'ACES': 'https://unavatar.io/aspirasi.co.id',
    'MAPI': 'https://unavatar.io/map.co.id',
    'ERAA': 'https://unavatar.io/erajaya.com',
    'GGRM': 'https://unavatar.io/gudanggaramtbk.com',
    'HMSP': 'https://unavatar.io/sampoerna.com',

    // IDX Energy, Mining, Commodities
    'ADRO': 'https://unavatar.io/adaro.com',
    'PTBA': 'https://unavatar.io/ptba.co.id',
    'ITMG': 'https://unavatar.io/itmg.co.id',
    'PGAS': 'https://unavatar.io/pgn.co.id',
    'ANTM': 'https://unavatar.io/antam.com',
    'MDKA': 'https://unavatar.io/merdekacoppergold.com',
    'INCO': 'https://unavatar.io/vale.com',
    'MEDC': 'https://unavatar.io/medcoenergi.com',
    'AKRA': 'https://unavatar.io/akr.co.id',
    'HRUM': 'https://unavatar.io/harumenergy.com',
    'AALI': 'https://unavatar.io/astra-agro.co.id',

    // IDX Industry, Materials & Property
    'SMGR': 'https://unavatar.io/sig.id',
    'INTP': 'https://unavatar.io/indocement.co.id',
    'UNTR': 'https://unavatar.io/unitedtractors.com',
    'BRPT': 'https://unavatar.io/barito-pacific.com',
    'TPIA': 'https://unavatar.io/chandra-asri.com',
    'INKP': 'https://unavatar.io/app.co.id',
    'TKIM': 'https://unavatar.io/tjiwikimia.co.id',
    'CTRA': 'https://unavatar.io/ciputra.com',
    'BSDE': 'https://unavatar.io/sinarmasland.com',
    'SMRA': 'https://unavatar.io/summarecon.com',
    'PWON': 'https://unavatar.io/pakuwonjati.com',
    'HEAL': 'https://unavatar.io/herminahospitals.com',
    'MIKA': 'https://unavatar.io/mitrakeluarga.com',
    'SILO': 'https://unavatar.io/siloamhospitals.com',

    // US Mega-Cap & Popular Global Stocks
    'AAPL': 'https://s3-symbol-logo.tradingview.com/apple--big.svg',
    'MSFT': 'https://s3-symbol-logo.tradingview.com/microsoft--big.svg',
    'NVDA': 'https://s3-symbol-logo.tradingview.com/nvidia--big.svg',
    'TSLA': 'https://s3-symbol-logo.tradingview.com/tesla--big.svg',
    'AMZN': 'https://s3-symbol-logo.tradingview.com/amazon--big.svg',
    'GOOGL': 'https://s3-symbol-logo.tradingview.com/alphabet--big.svg',
    'GOOG': 'https://s3-symbol-logo.tradingview.com/alphabet--big.svg',
    'META': 'https://s3-symbol-logo.tradingview.com/meta--big.svg',
    'NFLX': 'https://s3-symbol-logo.tradingview.com/netflix--big.svg',
    'AMD': 'https://s3-symbol-logo.tradingview.com/advanced-micro-devices--big.svg',
    'INTC': 'https://s3-symbol-logo.tradingview.com/intel--big.svg',
    'ORCL': 'https://s3-symbol-logo.tradingview.com/oracle--big.svg',
    'CRM': 'https://s3-symbol-logo.tradingview.com/salesforce--big.svg',
    'ADBE': 'https://s3-symbol-logo.tradingview.com/adobe--big.svg',
    'PYPL': 'https://s3-symbol-logo.tradingview.com/paypal--big.svg',
    'UBER': 'https://s3-symbol-logo.tradingview.com/uber--big.svg',
    'COIN': 'https://s3-symbol-logo.tradingview.com/coinbase--big.svg',
    'PLTR': 'https://s3-symbol-logo.tradingview.com/palantir--big.svg'
};

const KNOWN_IDX_LIST = [
    'BBCA', 'BBRI', 'BMRI', 'BBNI', 'TLKM', 'ASII', 'UNVR', 'GOTO', 'ICBP', 'INDF',
    'ADRO', 'PTBA', 'ITMG', 'PGAS', 'ANTM', 'MDKA', 'INKP', 'TKIM', 'KLBF', 'SMGR',
    'INTP', 'BRPT', 'TPIA', 'AMRT', 'MIDI', 'HMSP', 'GGRM', 'CPIN', 'JPFA', 'TOWR',
    'EXCL', 'ISAT', 'UNTR', 'HEXA', 'MEDC', 'AKRA', 'ARTO', 'BUKA', 'EMTK', 'BBTN',
    'BRIS', 'ACES', 'MAPI', 'MYOR', 'ERAA', 'SIDO', 'HEAL', 'MIKA', 'SILO', 'CTRA',
    'BSDE', 'SMRA', 'PWON', 'MNCN', 'SCMA', 'AALI', 'HRUM', 'BTPS', 'BDMN', 'BNGA'
];

const cleanTicker = (sym) => {
    if (!sym) return '';
    return String(sym).trim().toUpperCase().replace(/\.JK$/i, '');
};

const isIdx = (sym) => {
    if (!sym) return false;
    const str = String(sym).toUpperCase();
    return str.endsWith('.JK') || str.endsWith('.ID') || KNOWN_IDX_LIST.includes(cleanTicker(str));
};

// Generates an ultra-crisp, modern corporate gradient vector SVG
const generateSvgLogo = (symbol, name = '') => {
    const clean = cleanTicker(symbol) || 'STK';
    const palettes = [
        ['#2563eb', '#1d4ed8', '#60a5fa'], // Sapphire Blue
        ['#059669', '#047857', '#34d399'], // Emerald Green
        ['#7c3aed', '#6d28d9', '#a78bfa'], // Royal Violet
        ['#d97706', '#b45309', '#fbbf24'], // Amber Gold
        ['#e11d48', '#be123c', '#fb7185'], // Crimson
        ['#0891b2', '#0e7490', '#22d3ee'], // Cyan / Teal
        ['#4f46e5', '#4338ca', '#818cf8']  // Indigo
    ];
    let hash = 0;
    for (let i = 0; i < clean.length; i++) hash = clean.charCodeAt(i) + ((hash << 5) - hash);
    const [c1, c2, accent] = palettes[Math.abs(hash) % palettes.length];
    const fontSize = clean.length <= 4 ? '42' : '32';

    const svg = `
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 128 128" width="128" height="128">
        <defs>
            <linearGradient id="g_${clean}" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stop-color="${c1}" />
                <stop offset="100%" stop-color="${c2}" />
            </linearGradient>
        </defs>
        <rect width="128" height="128" rx="28" fill="url(#g_${clean})" />
        <circle cx="64" cy="64" r="54" fill="none" stroke="${accent}" stroke-width="2.5" stroke-opacity="0.35" />
        <text x="64" y="64" dy=".35em" fill="#ffffff" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif" font-weight="900" font-size="${fontSize}" text-anchor="middle" letter-spacing="1">${clean}</text>
    </svg>`.trim();

    return 'data:image/svg+xml;utf8,' + encodeURIComponent(svg);
};

const getCompanyLogo = (symbol, item = {}) => {
    if (!symbol) return generateSvgLogo('STK');
    const clean = cleanTicker(symbol);

    if (KNOWN_LOGOS[clean]) return KNOWN_LOGOS[clean];
    if (item.logo_url && typeof item.logo_url === 'string' && item.logo_url.startsWith('http')) {
        return item.logo_url;
    }
    if (item.domain || item.website) {
        const dom = item.domain || (item.website ? item.website.replace(/^https?:\/\//i, '').split('/')[0] : '');
        if (dom) return `https://unavatar.io/${dom}`;
    }
    if (!isIdx(symbol)) {
        return `https://s3-symbol-logo.tradingview.com/${clean.toLowerCase()}--big.svg`;
    }
    return generateSvgLogo(clean, item.name);
};

const getDetailLogo = (details) => {
    if (!details) return generateSvgLogo('STK');
    const clean = cleanTicker(details.symbol);

    if (KNOWN_LOGOS[clean]) return KNOWN_LOGOS[clean];
    if (details.logo_url && typeof details.logo_url === 'string' && details.logo_url.startsWith('http')) {
        return details.logo_url;
    }
    if (details.domain) {
        return `https://unavatar.io/${details.domain}`;
    }
    if (!isIdx(details.symbol)) {
        return `https://s3-symbol-logo.tradingview.com/${clean.toLowerCase()}--big.svg`;
    }
    return generateSvgLogo(clean, details.name);
};

const handleLogoError = (event, symbol) => {
    if (!event || !event.target) return;
    const img = event.target;
    if (img.dataset.failed) return;
    img.dataset.failed = "true";
    img.src = generateSvgLogo(symbol);
};

const App = {
    setup() {
        // State
        const searchQuery = ref('');
        const searchResults = ref([]);
        const showSuggestions = ref(false);
        const searchDebounce = ref(null);
        const loadingSearch = ref(false);

        const currentStock = ref(null);
        const stockDetails = ref(null);
        const technicals = ref(null);
        const fundamentals = ref(null);
        const loading = ref(false);
        const error = ref(null);
        const activeTab = ref('chart');
        const activeTimeframe = ref('1y');

        // Trade Sim (Analyze My Position) State
        const showTradeSim = ref(false);
        const tradeSimTicker = ref('');
        const tradeSimPrice = ref(null);
        const loadingTradeSim = ref(false);
        const tradePlan = ref(null);
        const tradeSimSuggestions = ref([]);
        const showTradeSimSuggestions = ref(false);
        const loadingTradeSimSearch = ref(false);
        const tradeSimDebounce = ref(null);

        // Entry Plan Tab State
        const entryPlan = ref(null);
        const loadingEntryPlan = ref(false);

        // Dashboard Lists
        const idxStocks = ref([]);
        const usStocks = ref([]);
        const loadingList = ref(false);
        const listProgress = ref('');

        // Chart Info
        let mainChart = null;
        let forecastChart = null;
        let seasonalChart = null;
        const chartContainer = ref(null);
        const mainChartCanvas = ref(null);
        const forecastChartCanvas = ref(null);
        const seasonalChartCanvas = ref(null);

        const API_BASE_URL = "";

        // API Helper
        const fetchAPI = async (endpoint) => {
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 20000);

            try {
                const url = API_BASE_URL ? `${API_BASE_URL}/api/${endpoint}` : `/api/${endpoint}`;
                const res = await fetch(url, { signal: controller.signal });
                clearTimeout(timeoutId);
                if (!res.ok) {
                    throw new Error(res.statusText);
                }
                return await res.json();
            } catch (e) {
                clearTimeout(timeoutId);
                throw e;
            }
        };

        const onTradeSimInput = () => {
            if (tradeSimDebounce.value) clearTimeout(tradeSimDebounce.value);
            const q = tradeSimTicker.value ? tradeSimTicker.value.trim() : '';
            if (q.length < 1) {
                tradeSimSuggestions.value = [];
                showTradeSimSuggestions.value = false;
                return;
            }
            loadingTradeSimSearch.value = true;
            tradeSimDebounce.value = setTimeout(async () => {
                try {
                    const data = await fetchAPI(`search?q=${encodeURIComponent(q)}`);
                    tradeSimSuggestions.value = data.results || [];
                    showTradeSimSuggestions.value = true;
                } catch (e) {
                    console.error("Trade Sim search error", e);
                } finally {
                    loadingTradeSimSearch.value = false;
                }
            }, 300);
        };

        const selectTradeSimSuggestion = (item) => {
            tradeSimTicker.value = cleanTicker(item.display_symbol || item.symbol);
            showTradeSimSuggestions.value = false;
        };

        const analyzeTrade = async () => {
            if (!tradeSimTicker.value || !tradeSimPrice.value) return;

            loadingTradeSim.value = true;
            tradePlan.value = null;
            showTradeSimSuggestions.value = false;

            try {
                const ticker = tradeSimTicker.value.trim().toUpperCase();
                const price = tradeSimPrice.value;
                const plan = await fetchAPI(`analyze-trade?ticker=${encodeURIComponent(ticker)}&avg_price=${price}`);
                tradePlan.value = plan;
            } catch (e) {
                console.error("Trade Sim Error", e);
                alert("Failed to analyze trade. Please check ticker.");
            } finally {
                loadingTradeSim.value = false;
            }
        };

        const onSearchInput = () => {
            if (searchDebounce.value) clearTimeout(searchDebounce.value);
            const q = searchQuery.value ? searchQuery.value.trim() : '';
            if (q.length < 1) {
                searchResults.value = [];
                showSuggestions.value = false;
                return;
            }

            loadingSearch.value = true;
            searchDebounce.value = setTimeout(async () => {
                try {
                    const data = await fetchAPI(`search?q=${encodeURIComponent(q)}`);
                    searchResults.value = data.results || [];
                    showSuggestions.value = true;
                } catch (e) {
                    console.error("Search failed", e);
                } finally {
                    loadingSearch.value = false;
                }
            }, 350);
        };

        const selectSuggestion = (symbol) => {
            searchQuery.value = cleanTicker(symbol);
            showSuggestions.value = false;
            loadStock(symbol);
        };

        const loadQuickAnalysis = async (ticker) => {
            try {
                const tech = await fetchAPI(`stock/${ticker}/technicals`);
                return { symbol: ticker, ...tech };
            } catch (e) {
                return null;
            }
        };

        const processBatch = async (tickers, targetRef) => {
            const batchSize = 3;
            const results = [];
            for (let i = 0; i < tickers.length; i += batchSize) {
                const batch = tickers.slice(i, i + batchSize);
                listProgress.value = `Analyzing ${Math.min(i + batchSize, tickers.length)} / ${tickers.length}...`;
                const batchResults = await Promise.all(batch.map(t => loadQuickAnalysis(t)));
                results.push(...batchResults.filter(r => r !== null));
                await new Promise(r => setTimeout(r, 500));
            }
            targetRef.value = results.sort((a, b) => {
                const getPriority = (rec) => {
                    if (rec.includes('STRONG BUY')) return 5;
                    if (rec.includes('BUY')) return 4;
                    if (rec.includes('NEUTRAL')) return 3;
                    if (rec.includes('SELL')) return 2;
                    return 1;
                };

                const prioA = getPriority(a.recommendation);
                const prioB = getPriority(b.recommendation);

                if (prioA !== prioB) return prioB - prioA;
                return b.score - a.score;
            });
        };

        // Dashboard Lists
        const marketData = ref({ idx: [], nasdaq: [] });
        const loadingMarket = ref(true);

        const initDashboard = async () => {
            loadingMarket.value = true;
            try {
                const data = await fetchAPI('market-summary');
                marketData.value = data;
            } catch (e) {
                console.error("Market Summary Error", e);
            } finally {
                loadingMarket.value = false;
            }
        };

        // Actions
        const handleSearch = () => {
            if (!searchQuery.value || searchQuery.value.trim().length < 1) return;
            selectSuggestion(searchQuery.value.trim().toUpperCase());
        };

        const goBack = () => {
            currentStock.value = null;
            stockDetails.value = null;
            searchQuery.value = '';
            showSuggestions.value = false;
            activeTab.value = 'chart';
        };

        const loadStock = async (ticker) => {
            loading.value = true;
            error.value = null;
            currentStock.value = ticker;
            searchQuery.value = cleanTicker(ticker);
            stockDetails.value = null;
            technicals.value = null;
            fundamentals.value = null;
            entryPlan.value = null;
            activeTimeframe.value = '1y';

            // Destroy old charts
            if (mainChart) { mainChart.destroy(); mainChart = null; }
            if (forecastChart) { forecastChart.destroy(); forecastChart = null; }
            if (seasonalChart) { seasonalChart.destroy(); seasonalChart = null; }

            try {
                const [details, tech, fund, chartData] = await Promise.all([
                    fetchAPI(`stock/${ticker}`),
                    fetchAPI(`stock/${ticker}/technicals`),
                    fetchAPI(`stock/${ticker}/fundamentals`),
                    fetchAPI(`stock/${ticker}/chart?range=1y`)
                ]);

                stockDetails.value = details;
                technicals.value = tech;
                fundamentals.value = fund;
                stockDetails.value.chartData = chartData;

                loadingEntryPlan.value = true;
                Promise.all([
                    fetchAPI(`stock/${ticker}/forecast`).catch(() => null),
                    fetchAPI(`stock/${ticker}/seasonal`).catch(() => null),
                    fetchAPI(`stock/${ticker}/entry-plan`).catch((e) => ({ error: true, traceback: e.toString(), from_fetch: true }))
                ]).then(([forecast, seasonal, entry]) => {
                    if (currentStock.value === ticker) {
                        if (stockDetails.value) {
                            stockDetails.value.forecastData = forecast;
                            stockDetails.value.seasonalData = seasonal;
                        }
                        entryPlan.value = entry;
                        
                        if (activeTab.value === 'forecasting') setTimeout(() => renderForecastChart(chartData, forecast), 50);
                        if (activeTab.value === 'seasonal') setTimeout(() => renderSeasonalChart(seasonal), 50);
                    }
                }).catch((err) => {
                    console.error("Tab data loading error:", err);
                    if (currentStock.value === ticker) {
                        entryPlan.value = { error: true, traceback: err.toString(), from_fetch: true };
                    }
                }).finally(() => {
                    if (currentStock.value === ticker) {
                        loadingEntryPlan.value = false;
                    }
                });

                await nextTick();
                if (activeTab.value === 'chart') {
                    setTimeout(() => renderMainChart(chartData), 50);
                }

            } catch (e) {
                console.error(e);
                error.value = `Failed to load ${ticker}. ${e.message}`;
            } finally {
                loading.value = false;
            }
        };

        const changeTimeframe = async (range) => {
            if (!currentStock.value) return;
            activeTimeframe.value = range;
            try {
                const data = await fetchAPI(`stock/${currentStock.value}/chart?range=${range}`);
                if (stockDetails.value) {
                    stockDetails.value.chartData = data;
                }
                renderMainChart(data);
            } catch (e) {
                console.error("Failed to change timeframe", e);
            }
        };

        watch(activeTab, async (newTab) => {
            await nextTick();
            if (newTab === 'chart') renderMainChart(stockDetails.value?.chartData);
            if (newTab === 'forecasting') renderForecastChart(stockDetails.value?.chartData, stockDetails.value?.forecastData);
            if (newTab === 'seasonal') renderSeasonalChart(stockDetails.value?.seasonalData);
        });

        const renderMainChart = (data) => {
            if (!mainChartCanvas.value || !data) return;
            if (mainChart) mainChart.destroy();

            const ctx = mainChartCanvas.value.getContext('2d');
            const dates = data.map(d => d.time);
            const prices = data.map(d => d.close);

            const gradient = ctx.createLinearGradient(0, 0, 0, 400);
            gradient.addColorStop(0, 'rgba(59, 130, 246, 0.5)');
            gradient.addColorStop(1, 'rgba(59, 130, 246, 0.0)');

            mainChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: dates,
                    datasets: [{
                        label: 'Close Price',
                        data: prices,
                        borderColor: '#3b82f6',
                        backgroundColor: gradient,
                        borderWidth: 2,
                        fill: true,
                        pointRadius: 0,
                        pointHoverRadius: 4,
                        tension: 0.1
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    interaction: { mode: 'index', intersect: false },
                    plugins: {
                        legend: { display: false },
                        tooltip: { mode: 'index', intersect: false }
                    },
                    scales: {
                        x: { display: true, grid: { color: 'rgba(255,255,255,0.05)' } },
                        y: { display: true, grid: { color: 'rgba(255,255,255,0.05)' } }
                    }
                }
            });
        };

        const renderForecastChart = (history, forecast) => {
            if (!forecastChartCanvas.value || !history || !forecast) return;
            if (forecastChart) forecastChart.destroy();

            if (!history || history.length === 0) return;

            const histData = history.map(d => d.close).slice(-60);
            const histLabels = history.map(d => d.time).slice(-60);

            const forecastValues = forecast.map(d => d.value);
            const forecastLabels = forecast.map(d => d.time);

            const labels = [...histLabels, ...forecastLabels];
            const dataset1 = [...histData, ...new Array(forecastValues.length).fill(null)];

            const dataset2 = new Array(histData.length - 1).fill(null);
            dataset2.push(histData[histData.length - 1]);
            dataset2.push(...forecastValues);

            const ctx = forecastChartCanvas.value.getContext('2d');
            forecastChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: labels,
                    datasets: [
                        {
                            label: 'History',
                            data: dataset1,
                            borderColor: '#94a3b8',
                            borderWidth: 2,
                            pointRadius: 0,
                            fill: false
                        },
                        {
                            label: 'Forecast (3 Months)',
                            data: dataset2,
                            borderColor: '#10b981',
                            borderWidth: 2,
                            borderDash: [5, 5],
                            pointRadius: 0,
                            fill: false
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    interaction: { mode: 'index', intersect: false },
                    plugins: { legend: { display: true, labels: { color: '#cbd5e1' } } },
                    scales: {
                        x: { grid: { color: 'rgba(255,255,255,0.05)' } },
                        y: { grid: { color: 'rgba(255,255,255,0.05)' } }
                    }
                }
            });
        };

        const renderSeasonalChart = (seasonalData) => {
            if (!seasonalChartCanvas.value || !seasonalData) return;
            if (seasonalChart) seasonalChart.destroy();

            const keys = Object.keys(seasonalData).sort().reverse();
            if (keys.length === 0) return;

            const longestKey = keys.reduce((a, b) => seasonalData[a].length > seasonalData[b].length ? a : b);
            const labels = seasonalData[longestKey].map(d => d.label);

            const colors = ['#3b82f6', '#10b981', '#f59e0b'];

            const datasets = keys.map((year, idx) => ({
                label: year,
                data: seasonalData[year].map(d => d.value),
                borderColor: colors[idx % colors.length],
                borderWidth: 2,
                pointRadius: 0,
                tension: 0.3,
                fill: false
            }));

            const ctx = seasonalChartCanvas.value.getContext('2d');
            seasonalChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: labels,
                    datasets: datasets
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    interaction: { mode: 'index', intersect: false },
                    plugins: { legend: { display: true, labels: { color: '#cbd5e1' } } },
                    scales: {
                        x: { grid: { color: 'rgba(255,255,255,0.05)' } },
                        y: { grid: { color: 'rgba(255,255,255,0.05)' } }
                    }
                }
            });
        };

        const formatNumber = (num, symbol) => {
            if (num === null || num === undefined) return '-';

            const s = symbol || currentStock.value || tradeSimTicker.value;
            if (s && isIdx(s)) {
                return ' Rp. ' + new Intl.NumberFormat('id-ID', {
                    minimumFractionDigits: 0,
                    maximumFractionDigits: 0
                }).format(num);
            }

            return new Intl.NumberFormat('en-US', {
                style: 'currency',
                currency: 'USD',
                maximumFractionDigits: 2
            }).format(num);
        };

        const formatCompactNumber = (num) => {
            if (num === null || num === undefined) return '-';
            return new Intl.NumberFormat('en-US', {
                notation: "compact",
                maximumFractionDigits: 2
            }).format(num);
        };

        const getScoreColor = (score) => {
            if (score >= 80) return 'text-emerald-400 font-black';
            if (score >= 60) return 'text-green-400';
            if (score <= 20) return 'text-rose-500 font-black';
            if (score <= 40) return 'text-red-400';
            return 'text-gray-500 font-medium';
        };

        const recommendationClass = computed(() => {
            if (!technicals.value) return '';
            const rec = technicals.value.recommendation;
            if (rec.includes('STRONG BUY')) return 'text-emerald-400 font-black';
            if (rec.includes('BUY')) return 'text-green-400';
            if (rec.includes('STRONG SELL')) return 'text-rose-500 font-black';
            if (rec.includes('SELL')) return 'text-red-400';
            return 'text-gray-500 font-bold';
        });

        const fetchEntryPlan = async (ticker = currentStock.value) => {
            if (!ticker) return;
            loadingEntryPlan.value = true;
            try {
                const entry = await fetchAPI(`stock/${ticker}/entry-plan`);
                if (currentStock.value === ticker) {
                    entryPlan.value = entry;
                }
            } catch (e) {
                console.error("Entry plan fetch error:", e);
                if (currentStock.value === ticker) {
                    entryPlan.value = { error: true, traceback: e.toString(), from_fetch: true };
                }
            } finally {
                if (currentStock.value === ticker) {
                    loadingEntryPlan.value = false;
                }
            }
        };

        watch(activeTab, (newTab) => {
            if (newTab === 'trading_plan' && (!entryPlan.value || entryPlan.value.error) && !loadingEntryPlan.value && currentStock.value) {
                fetchEntryPlan(currentStock.value);
            }
        });

        onMounted(() => {
            initDashboard();
            const splash = document.getElementById('app-loading');
            if (splash) {
                splash.style.opacity = '0';
                setTimeout(() => splash.remove(), 350);
            }
        });

        return {
            searchQuery,
            searchResults,
            showSuggestions,
            onSearchInput,
            selectSuggestion,
            currentStock,
            stockDetails,
            technicals,
            fundamentals,
            loading,
            error,
            loadingSearch,
            handleSearch,
            chartContainer,
            activeTab,
            activeTimeframe,
            recommendationClass,
            formatNumber,
            formatCompactNumber,
            marketData,
            loadingMarket,
            loadStock,
            goBack,
            changeTimeframe,
            getScoreColor,
            mainChartCanvas,
            forecastChartCanvas,
            seasonalChartCanvas,
            // Trade Sim
            showTradeSim,
            tradeSimTicker,
            tradeSimPrice,
            loadingTradeSim,
            tradePlan,
            analyzeTrade,
            tradeSimSuggestions,
            showTradeSimSuggestions,
            loadingTradeSimSearch,
            onTradeSimInput,
            selectTradeSimSuggestion,
            // Logo & Ticker helpers
            cleanTicker,
            isIdx,
            getCompanyLogo,
            getDetailLogo,
            handleLogoError,
            // Entry Plan Tab (Trading Plan)
            entryPlan,
            loadingEntryPlan,
            fetchEntryPlan
        };
    }
};

if (typeof createApp === 'function') {
    createApp(App).mount('#app');
    const splash = document.getElementById('app-loading');
    if (splash) {
        splash.style.opacity = '0';
        setTimeout(() => splash.remove(), 350);
    }
}
