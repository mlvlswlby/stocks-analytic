
const { createApp, ref, computed, watch, onMounted, nextTick } = Vue;

const App = {
    setup() {
        // State
        const searchQuery = ref('');
        const searchResults = ref([]);
        const showSuggestions = ref(false);
        const searchDebounce = ref(null);

        const currentStock = ref(null);
        const stockDetails = ref(null);
        const technicals = ref(null);
        const fundamentals = ref(null);
        const loading = ref(false);
        const error = ref(null);
        const activeTab = ref('chart');

        // Dashboard Lists
        const idxStocks = ref([]);
        const usStocks = ref([]);
        const loadingList = ref(false);
        const listProgress = ref('');

        // Chart Info
        let chartInstance = null;
        let candleSeries = null;
        const chartContainer = ref(null);

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

        const onSearchInput = () => {
            if (searchDebounce.value) clearTimeout(searchDebounce.value);
            if (searchQuery.value.length < 1) {
                searchResults.value = [];
                showSuggestions.value = false;
                return;
            }

            searchDebounce.value = setTimeout(async () => {
                try {
                    const data = await fetchAPI(`search?q=${searchQuery.value}`);
                    searchResults.value = data.results;
                    showSuggestions.value = true;
                } catch (e) {
                    console.error("Search failed", e);
                }
            }, 300);
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
            targetRef.value = results.sort((a, b) => b.score - a.score);
        };

        const initDashboard = async () => {
            loadingList.value = true;
            const idxCandidates = [
                'BBCA.JK', 'BBRI.JK', 'BMRI.JK', 'BBNI.JK',
                'TLKM.JK', 'ASII.JK', 'UNVR.JK', 'GOTO.JK',
                'ADRO.JK', 'ICBP.JK'
            ];
            const usCandidates = [
                'NVDA', 'TSLA', 'AAPL', 'MSFT', 'AMZN',
                'GOOGL', 'META', 'AMD', 'NFLX', 'INTC'
            ];

            try {
                await processBatch(idxCandidates, idxStocks);
                await processBatch(usCandidates, usStocks);
            } catch (e) {
                console.error("Dashboard error", e);
            } finally {
                loadingList.value = false;
                listProgress.value = '';
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

            try {
                const [details, tech, fund, chartData] = await Promise.all([
                    fetchAPI(`stock/${ticker}`),
                    fetchAPI(`stock/${ticker}/technicals`),
                    fetchAPI(`stock/${ticker}/fundamentals`),
                    fetchAPI(`stock/${ticker}/chart?range=1y`) // 1y daily
                ]);

                stockDetails.value = details;
                technicals.value = tech;
                fundamentals.value = fund;
                stockDetails.value.chartData = chartData;

                await nextTick();
                if (activeTab.value === 'chart') {
                    renderChart(chartData);
                }

            } catch (e) {
                console.error(e);
                error.value = `Failed to load ${ticker}. ${e.message}`;
            } finally {
                loading.value = false;
            }
        };

        watch(activeTab, async (newTab) => {
            if (newTab === 'chart' && stockDetails.value?.chartData) {
                await nextTick();
                renderChart(stockDetails.value.chartData);
            }
        });

        const renderChart = (data) => {
            if (!chartContainer.value) return;

            // Dispose old chart
            if (chartInstance) {
                chartInstance.remove();
                chartInstance = null;
            }

            // Fallback dimensions if container has no size yet (e.g. hidden tab)
            const clientWidth = chartContainer.value.clientWidth || 600;

            const chartOptions = {
                layout: {
                    textColor: '#94a3b8',
                    background: { type: 'solid', color: '#1e293b' }
                },
                grid: {
                    vertLines: { color: 'rgba(255, 255, 255, 0.05)' },
                    horzLines: { color: 'rgba(255, 255, 255, 0.05)' },
                },
                timeScale: {
                    timeVisible: true,
                    secondsVisible: false,
                },
                width: clientWidth,
                height: 400,
            };

            chartInstance = LightweightCharts.createChart(chartContainer.value, chartOptions);

            candleSeries = chartInstance.addCandlestickSeries({
                upColor: '#10b981',
                downColor: '#ef4444',
                borderVisible: false,
                wickUpColor: '#10b981',
                wickDownColor: '#ef4444'
            });

            candleSeries.setData(data);
            chartInstance.timeScale().fitContent();

            // Resize Observer to handle window resize or tab switch
            const resizeObserver = new ResizeObserver(entries => {
                if (entries.length === 0 || !entries[0].contentRect) return;
                const newRect = entries[0].contentRect;
                if (chartInstance && newRect.width > 0) {
                    chartInstance.applyOptions({ width: newRect.width, height: 400 });
                    chartInstance.timeScale().fitContent();
                }
            });

            resizeObserver.observe(chartContainer.value);

            // Force a resize check in case it rendered with 0 width
            setTimeout(() => {
                if (chartContainer.value && chartInstance) {
                    const w = chartContainer.value.clientWidth;
                    if (w > 0) {
                        chartInstance.applyOptions({ width: w });
                    }
                }
            }, 100);
        };

        const formatNumber = (num) => {
            if (num === null || num === undefined) return '-';
            return new Intl.NumberFormat('en-US', { notation: "compact", maximumFractionDigits: 2 }).format(num);
        };

        const getScoreColor = (score) => {
            if (score >= 80) return 'text-emerald-400 font-black';
            if (score >= 60) return 'text-green-400';
            if (score <= 20) return 'text-rose-500 font-black';
            if (score <= 40) return 'text-red-400';
            return 'text-slate-400';
        };

        const recommendationClass = computed(() => {
            if (!technicals.value) return '';
            const rec = technicals.value.recommendation;
            if (rec.includes('BUY')) return 'text-green-400';
            if (rec.includes('SELL')) return 'text-red-400';
            return 'text-gray-400';
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
            handleSearch,
            chartContainer,
            activeTab,
            recommendationClass,
            formatNumber,
            idxStocks,
            usStocks,
            loadingList,
            listProgress,
            loadStock,
            goBack,
            getScoreColor
        };
    }
};

createApp(App).mount('#app');
