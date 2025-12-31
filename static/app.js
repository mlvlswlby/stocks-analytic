
const { createApp, ref, computed, watch, onMounted, nextTick } = Vue;

const App = {
    setup() {
        // State
        const searchQuery = ref('');
        const currentStock = ref(null);
        const stockDetails = ref(null);
        const technicals = ref(null);
        const fundamentals = ref(null);
        const loading = ref(false);
        const error = ref(null);
        const activeTab = ref('chart'); // chart, technicals, fundamentals, about

        // Dashboard Lists
        const idxStocks = ref([]);
        const usStocks = ref([]);
        const loadingList = ref(false);

        // Chart Info
        let chartInstance = null;
        let candleSeries = null;
        const chartContainer = ref(null);

        // API Helper
        const fetchAPI = async (endpoint) => {
            const res = await fetch(`/api/${endpoint}`);
            if (!res.ok) {
                const txt = await res.text();
                // If 404, just return null or throw depending on need
                throw new Error(txt || res.statusText);
            }
            return res.json();
        };

        const loadQuickAnalysis = async (ticker) => {
            try {
                // Just get technicals for the list item score
                const tech = await fetchAPI(`stock/${ticker}/technicals`);
                return { symbol: ticker, ...tech };
            } catch (e) {
                console.error(`Failed to load ${ticker}`, e);
                return { symbol: ticker, score: 0, recommendation: 'N/A', indicators: {} };
            }
        };

        const initDashboard = async () => {
            loadingList.value = true;
            const idxTickers = ['BBCA.JK', 'BBRI.JK', 'BMRI.JK', 'TLKM.JK', 'ASII.JK', 'GOTO.JK'];
            const usTickers = ['AAPL', 'MSFT', 'NVDA', 'TSLA', 'AMZN', 'GOOGL'];

            try {
                // We fetch them in parallel groups
                idxStocks.value = await Promise.all(idxTickers.map(t => loadQuickAnalysis(t)));
                usStocks.value = await Promise.all(usTickers.map(t => loadQuickAnalysis(t)));
            } catch (e) {
                console.error("Dashboard load partial error", e);
            } finally {
                loadingList.value = false;
            }
        };

        // Actions
        const handleSearch = () => {
            if (searchQuery.value.length < 1) return;
            loadStock(searchQuery.value.toUpperCase());
        };

        const goBack = () => {
            currentStock.value = null;
            stockDetails.value = null;
            searchQuery.value = '';
            // destroy chart
            if (chartInstance) {
                chartInstance.remove();
                chartInstance = null;
            }
        };

        const loadStock = async (ticker) => {
            loading.value = true;
            error.value = null;
            currentStock.value = ticker;
            // Clear previous data
            stockDetails.value = null;
            technicals.value = null;
            fundamentals.value = null;

            try {
                // Parallel fetch
                const [details, tech, fund, chartData] = await Promise.all([
                    fetchAPI(`stock/${ticker}`),
                    fetchAPI(`stock/${ticker}/technicals`),
                    fetchAPI(`stock/${ticker}/fundamentals`),
                    fetchAPI(`stock/${ticker}/chart?range=1y`)
                ]);

                stockDetails.value = details;
                technicals.value = tech;
                fundamentals.value = fund;

                // Wait for DOM update so container exists
                await nextTick();
                // Double check container visibility
                if (activeTab.value === 'chart') {
                    renderChart(chartData);
                } else {
                    // store data for later rendering if tab switches
                    stockDetails.value.chartData = chartData;
                }

                stockDetails.value.chartData = chartData; // Save it

            } catch (e) {
                console.error(e);
                error.value = `Failed to load ${ticker}. ${e.message}`;
            } finally {
                loading.value = false;
            }
        };

        // Watch tab change to re-render chart if needed
        watch(activeTab, async (newTab) => {
            if (newTab === 'chart' && stockDetails.value?.chartData) {
                await nextTick();
                renderChart(stockDetails.value.chartData);
            }
        });

        const renderChart = (data) => {
            if (!chartContainer.value) {
                console.warn("Chart container missing");
                return;
            }

            // Dispose old chart
            if (chartInstance) {
                chartInstance.remove();
                chartInstance = null;
            }

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

            // Handle resize
            window.addEventListener('resize', () => {
                if (chartContainer.value) {
                    chartInstance.resize(chartContainer.value.clientWidth, 400);
                }
            });
        };

        const formatNumber = (num) => {
            if (num === null || num === undefined) return '-';
            return new Intl.NumberFormat('en-US', { notation: "compact", maximumFractionDigits: 2 }).format(num);
        };

        const getScoreColor = (score) => {
            if (score >= 70) return 'text-green-400';
            if (score <= 30) return 'text-red-400';
            return 'text-slate-400';
        };

        const recommendationClass = computed(() => {
            if (!technicals.value) return '';
            const rec = technicals.value.recommendation;
            if (rec.includes('BUY')) return 'text-green-400';
            if (rec.includes('SELL')) return 'text-red-400';
            return 'text-gray-400';
        });

        // Initial Load
        onMounted(() => {
            initDashboard();
        });

        return {
            searchQuery,
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
            loadStock,
            goBack,
            getScoreColor
        };
    }
};

createApp(App).mount('#app');
