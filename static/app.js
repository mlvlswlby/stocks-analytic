
const { createApp, ref, computed, watch, onMounted, nextTick } = Vue;

const App = {
    setup() {
        // State
        const searchQuery = ref('');
        const searchResults = ref([]);
        const currentStock = ref(null);
        const stockDetails = ref(null);
        const technicals = ref(null);
        const fundamentals = ref(null);
        const loading = ref(false);
        const error = ref(null);
        const activeTab = ref('chart'); // chart, technicals, fundamentals

        // Chart Info
        let chartInstance = null;
        let candleSeries = null;
        const chartContainer = ref(null);

        // API Helper
        const fetchAPI = async (endpoint) => {
            const res = await fetch(`/api/${endpoint}`);
            if (!res.ok) throw new Error(await res.text());
            return res.json();
        };

        // Actions
        const handleSearch = async () => {
            if (searchQuery.value.length < 1) return;
            // For now, just a direct search, assuming user types ticker
            // In a real app we would have an autocomplete
            const ticker = searchQuery.value.toUpperCase();
            loadStock(ticker);
        };

        const loadStock = async (ticker) => {
            loading.value = true;
            error.value = null;
            currentStock.value = ticker;
            searchResults.value = [];

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

                await nextTick();
                renderChart(chartData);
            } catch (e) {
                console.error(e);
                error.value = "Failed to load stock data. Check ticker symbol.";
            } finally {
                loading.value = false;
            }
        };

        const renderChart = (data) => {
            if (!chartContainer.value) return;

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
                }
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

        // Computed styles
        const recommendationClass = computed(() => {
            if (!technicals.value) return '';
            const rec = technicals.value.recommendation;
            if (rec.includes('BUY')) return 'text-green-400';
            if (rec.includes('SELL')) return 'text-red-400';
            return 'text-gray-400';
        });

        // Initial Load (Demo)
        onMounted(() => {
            // Demo ticker
            loadStock('AAPL');
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
            formatNumber
        };
    }
};

createApp(App).mount('#app');
