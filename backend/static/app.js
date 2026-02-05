
const { createApp, ref, computed, watch, onMounted, nextTick } = Vue;

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
        const activeTimeframe = ref('1y'); // Track active timeframe

        // Trade Sim State
        const showTradeSim = ref(false);
        const tradeSimTicker = ref('');
        const tradeSimPrice = ref(null);
        const loadingTradeSim = ref(false);
        const tradePlan = ref(null);

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

        // API Helper
        const fetchAPI = async (endpoint) => {
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 20000); // 20s timeout

            try {
                const res = await fetch(`/api/${endpoint}`, { signal: controller.signal });
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

        const analyzeTrade = async () => {
            if (!tradeSimTicker.value || !tradeSimPrice.value) return;

            loadingTradeSim.value = true;
            tradePlan.value = null;

            try {
                const ticker = tradeSimTicker.value.toUpperCase();
                const price = tradeSimPrice.value;
                const plan = await fetchAPI(`analyze-trade?ticker=${ticker}&avg_price=${price}`);
                tradePlan.value = plan;
            } catch (e) {
                console.error("Trade Sim Error", e);
                alert("Failed to analyze trade. Please check ticker.");
            } finally {
                loadingTradeSim.value = false;
            }
        };

        const onSearchInput = () => {
            // ... (keep existing)
            if (searchDebounce.value) clearTimeout(searchDebounce.value);
            if (searchQuery.value.length < 1) {
                searchResults.value = [];
                showSuggestions.value = false;
                return;
            }

            loadingSearch.value = true;
            searchDebounce.value = setTimeout(async () => {
                try {
                    const data = await fetchAPI(`search?q=${searchQuery.value}`);
                    searchResults.value = data.results;
                    showSuggestions.value = true;
                } catch (e) {
                    console.error("Search failed", e);
                } finally {
                    loadingSearch.value = false;
                }
            }, 500); // 500ms debounce
        };



        const selectSuggestion = (symbol) => {
            searchQuery.value = symbol;
            showSuggestions.value = false;
            loadStock(symbol);
        };

        const loadQuickAnalysis = async (ticker) => {
            try {
                const tech = await fetchAPI(`stock/${ticker}/technicals`);
                return { symbol: ticker, ...tech };
            } catch (e) {
                // Return placeholder
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
                // Custom Priority: Buy > Neutral > Sell
                const getPriority = (rec) => {
                    if (rec.includes('STRONG BUY')) return 5;
                    if (rec.includes('BUY')) return 4;
                    if (rec.includes('NEUTRAL')) return 3;
                    if (rec.includes('SELL')) return 2; // Sell
                    return 1; // Strong Sell
                };

                const prioA = getPriority(a.recommendation);
                const prioB = getPriority(b.recommendation);

                if (prioA !== prioB) return prioB - prioA; // Descending Priority
                return b.score - a.score; // Tie-break with Score
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
            if (searchQuery.value.length < 1) return;
            selectSuggestion(searchQuery.value.toUpperCase());
        };

        const goBack = () => {
            currentStock.value = null;
            stockDetails.value = null;
            searchQuery.value = '';
            showSuggestions.value = false;
            activeTab.value = 'chart';
            if (chartInstance) {
                chartInstance.remove();
                chartInstance = null;
            }
        };

        const loadStock = async (ticker) => {
            loading.value = true;
            error.value = null;
            currentStock.value = ticker;
            stockDetails.value = null;
            technicals.value = null;
            fundamentals.value = null;
            activeTimeframe.value = '1y'; // Reset timeframe on new stock

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

                // Fetch extra data for tabs
                // We do it non-blocking or just wait? Let's wait to be simple
                const [forecast, seasonal] = await Promise.all([
                    fetchAPI(`stock/${ticker}/forecast`),
                    fetchAPI(`stock/${ticker}/seasonal`)
                ]);
                stockDetails.value.forecastData = forecast;
                stockDetails.value.seasonalData = seasonal;

                await nextTick();
                if (activeTab.value === 'chart') {
                    // Small delay to ensure v-show has applied layout
                    setTimeout(() => renderMainChart(chartData), 50);
                } else if (activeTab.value === 'forecasting') {
                    setTimeout(() => renderForecastChart(chartData, forecast), 50);
                } else if (activeTab.value === 'seasonal') {
                    setTimeout(() => renderSeasonalChart(seasonal), 50);
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
            activeTimeframe.value = range; // Update active state
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

        // Chart.js Implementations
        const renderMainChart = (data) => {
            if (!mainChartCanvas.value || !data) return;
            if (mainChart) mainChart.destroy();

            const ctx = mainChartCanvas.value.getContext('2d');
            const dates = data.map(d => d.time);
            const prices = data.map(d => d.close);

            // Create Gradient
            const gradient = ctx.createLinearGradient(0, 0, 0, 400);
            gradient.addColorStop(0, 'rgba(59, 130, 246, 0.5)'); // Blue
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

            // Check if history is valid
            if (!history || history.length === 0) return;

            const histData = history.map(d => d.close).slice(-60); // Last 60 points
            const histLabels = history.map(d => d.time).slice(-60);

            // Forecast data
            const forecastValues = forecast.map(d => d.value);
            const forecastLabels = forecast.map(d => d.time);

            // Connect: The forecast line typically starts from the last history point
            // We can pad the forecast dataset with nulls for the history period
            // Or just concat the labels and have two datasets

            const labels = [...histLabels, ...forecastLabels];
            const dataset1 = [...histData, ...new Array(forecastValues.length).fill(null)];

            // Dataset 2 needs to start at the last point of dataset 1 for continuity
            // Let's create a null-padded array for dataset 2
            const dataset2 = new Array(histData.length - 1).fill(null);
            dataset2.push(histData[histData.length - 1]); // Connection point
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

            // Use longest dataset for labels
            const longestKey = keys.reduce((a, b) => seasonalData[a].length > seasonalData[b].length ? a : b);
            const labels = seasonalData[longestKey].map(d => d.label);

            const colors = ['#3b82f6', '#10b981', '#f59e0b']; // Blue, Green, Amber

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

            // Special handling for Indonesia
            if (currentStock.value && (currentStock.value.endsWith('.JK') || currentStock.value.endsWith('.ID'))) {
                // Manual format for " Rp." request
                return ' Rp. ' + new Intl.NumberFormat('id-ID', {
                    minimumFractionDigits: 0,
                    maximumFractionDigits: 0
                }).format(num);
            }

            // Default USD
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
            return 'text-gray-500 font-medium'; // Neutral - Distinct Gray
        };

        const recommendationClass = computed(() => {
            if (!technicals.value) return '';
            const rec = technicals.value.recommendation;
            if (rec.includes('STRONG BUY')) return 'text-emerald-400 font-black';
            if (rec.includes('BUY')) return 'text-green-400';
            if (rec.includes('STRONG SELL')) return 'text-rose-500 font-black';
            if (rec.includes('SELL')) return 'text-red-400';
            return 'text-gray-500 font-bold'; // Neutral
        });

        onMounted(() => {
            initDashboard();
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
            analyzeTrade
        };
    }
};

createApp(App).mount('#app');
