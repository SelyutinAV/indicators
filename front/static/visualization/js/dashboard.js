/**
 * Инициализация дашборда с графиками Chart.js
 */

// Цвета для статусов
const STATUS_COLORS = {
    'green': 'rgb(76, 175, 80)',
    'yellow': 'rgb(255, 193, 7)',
    'red': 'rgb(244, 67, 54)',
    'gray': 'rgb(158, 158, 158)'
};

// Цвета для графиков (если нет статусов)
const CHART_COLORS = [
    'rgb(75, 192, 192)',
    'rgb(54, 162, 235)',
    'rgb(255, 99, 132)',
    'rgb(255, 159, 64)',
    'rgb(153, 102, 255)',
    'rgb(201, 203, 207)',
    'rgb(255, 205, 86)',
    'rgb(255, 99, 255)'
];

/**
 * Загружает данные показателя через API
 */
async function loadIndicatorData(indicatorId, daysBack, aggregation, filters, startDate, endDate, cumulative) {
    const url = `/visualization/api/indicator/${indicatorId}/data/`;
    const params = new URLSearchParams({
        days_back: daysBack,
        aggregation: aggregation || 'day',
        filters: JSON.stringify(filters || {})
    });
    
    // Добавляем фильтры по датам если указаны
    if (startDate) {
        params.append('start_date', startDate);
    }
    if (endDate) {
        params.append('end_date', endDate);
    }
    
    // Добавляем параметр нарастающего итога
    if (cumulative) {
        params.append('cumulative', 'true');
    }
    
    try {
        const fullUrl = `${url}?${params}`;
        console.log('Запрос данных:', fullUrl);
        
        const response = await fetch(fullUrl);
        
        if (!response.ok) {
            console.error('HTTP ошибка:', response.status, response.statusText);
            return null;
        }
        
        const data = await response.json();
        console.log('Получены данные:', data);
        
        if (data.success) {
            return data;
        } else {
            console.error('Ошибка загрузки данных:', data.error);
            return null;
        }
    } catch (error) {
        console.error('Ошибка при запросе данных:', error);
        return null;
    }
}

/**
 * Создает конфигурацию графика для Chart.js
 */
function createChartConfig(chartType, indicatorData, showLegend, showGrid, statuses) {
    const dates = indicatorData.data.dates;
    const values = indicatorData.data.values;
    
    // Определяем цвета
    let backgroundColor, borderColor;
    
    if (statuses && statuses.length > 0) {
        // Используем цвета статусов
        backgroundColor = statuses.map(s => STATUS_COLORS[s] || STATUS_COLORS.gray);
        borderColor = statuses.map(s => STATUS_COLORS[s] || STATUS_COLORS.gray);
    } else {
        // Используем стандартные цвета
        const colorIndex = 0;
        backgroundColor = CHART_COLORS[colorIndex % CHART_COLORS.length];
        borderColor = CHART_COLORS[colorIndex % CHART_COLORS.length];
    }
    
    // Определяем тип графика и настройки dataset
    let graphType = chartType;
    const dataset = {
        label: indicatorData.indicator.name,
        data: values,
        borderWidth: 2
    };
    
    // Настройки в зависимости от типа графика
    switch (chartType) {
        case 'line':
            graphType = 'line';
            dataset.borderColor = Array.isArray(borderColor) ? borderColor[0] : borderColor;
            dataset.backgroundColor = 'rgba(75, 192, 192, 0.1)';
            dataset.fill = false;
            break;
            
        case 'bar':
            graphType = 'bar';
            dataset.backgroundColor = Array.isArray(backgroundColor) ? backgroundColor : backgroundColor.replace('rgb', 'rgba').replace(')', ', 0.7)');
            dataset.borderColor = Array.isArray(borderColor) ? borderColor[0] : borderColor;
            break;
            
        case 'area':
            graphType = 'line';
            dataset.borderColor = Array.isArray(borderColor) ? borderColor[0] : borderColor;
            dataset.backgroundColor = Array.isArray(backgroundColor) 
                ? backgroundColor.map(c => c.replace('rgb', 'rgba').replace(')', ', 0.3)'))
                : backgroundColor.replace('rgb', 'rgba').replace(')', ', 0.3)');
            dataset.fill = true;
            break;
            
        case 'scatter':
            graphType = 'scatter';
            dataset.borderColor = Array.isArray(borderColor) ? borderColor[0] : borderColor;
            dataset.backgroundColor = Array.isArray(backgroundColor) ? backgroundColor[0] : backgroundColor;
            break;
            
        case 'pie':
            // Для pie chart нужна другая структура - возвращаем сразу
            const pieColors = Array.isArray(backgroundColor) 
                ? backgroundColor 
                : CHART_COLORS.slice(0, Math.min(values.length, CHART_COLORS.length));
            return {
                type: 'pie',
                data: {
                    labels: dates,
                    datasets: [{
                        label: indicatorData.indicator.name,
                        data: values,
                        backgroundColor: pieColors,
                        borderColor: '#fff',
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: true,
                    plugins: {
                        legend: {
                            display: showLegend,
                            position: 'bottom'
                        },
                        tooltip: {
                            enabled: true,
                            callbacks: {
                                label: function(context) {
                                    let label = context.label || '';
                                    if (label) {
                                        label += ': ';
                                    }
                                    label += context.parsed !== null ? context.parsed.toFixed(2) : '';
                                    label += ' ' + indicatorData.indicator.unit;
                                    return label;
                                }
                            }
                        }
                    }
                }
            };
            
        default:
            graphType = 'line';
            dataset.borderColor = Array.isArray(borderColor) ? borderColor[0] : borderColor;
            dataset.backgroundColor = 'rgba(75, 192, 192, 0.1)';
    }
    
    return {
        type: graphType,
        data: {
            labels: dates,
            datasets: [dataset]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    display: showLegend,
                    position: 'bottom'
                },
                tooltip: {
                    enabled: true,
                    callbacks: {
                        label: function(context) {
                            let label = context.dataset.label || '';
                            if (label) {
                                label += ': ';
                            }
                            label += context.parsed.y !== null ? context.parsed.y.toFixed(2) : '';
                            label += ' ' + indicatorData.indicator.unit;
                            return label;
                        }
                    }
                }
            },
            scales: chartType === 'pie' ? {} : {
                x: {
                    display: true,
                    title: {
                        display: true,
                        text: 'Дата'
                    },
                    grid: {
                        display: showGrid
                    }
                },
                y: {
                    display: true,
                    title: {
                        display: true,
                        text: indicatorData.indicator.unit
                    },
                    beginAtZero: false,
                    grid: {
                        display: showGrid
                    }
                }
            }
        }
    };
}

/**
 * Рендерит график на canvas элементе
 */
async function renderChart(canvasElement, chartCard) {
    const indicatorId = chartCard.dataset.indicatorId;
    const chartType = chartCard.dataset.chartType;
    const daysBack = parseInt(chartCard.dataset.daysBack) || 30;
    const aggregation = chartCard.dataset.aggregation || 'day';
    const filtersStr = chartCard.dataset.filters || '{}';
    const showLegend = chartCard.dataset.showLegend === 'true';
    const showGrid = chartCard.dataset.showGrid === 'true';
    const cumulative = chartCard.dataset.cumulative === 'true';
    
    // Получаем фильтры из формы если есть
    const startDate = document.getElementById('filter-start-date')?.value || '';
    const endDate = document.getElementById('filter-end-date')?.value || '';
    
    // Собираем фильтры по справочникам из формы
    const formFilters = {};
    const dictSelects = document.querySelectorAll('select[id^="filter-dict-"]');
    dictSelects.forEach(select => {
        const dictId = select.id.replace('filter-dict-', '');
        const selected = Array.from(select.selectedOptions)
            .map(opt => opt.value)
            .filter(val => val !== 'all');
        if (selected.length > 0) {
            formFilters[dictId] = selected.map(id => parseInt(id));
        }
    });
    
    // Объединяем фильтры из настроек показателя и из формы (форма имеет приоритет)
    const baseFilters = JSON.parse(filtersStr);
    const filters = { ...baseFilters, ...formFilters };
    
    await renderChartWithFilters(canvasElement, chartCard, startDate, endDate, filters);
}

/**
 * Рендерит график с указанными фильтрами
 */
async function renderChartWithFilters(canvasElement, chartCard, startDate, endDate, filters) {
    const indicatorId = chartCard.dataset.indicatorId;
    const chartType = chartCard.dataset.chartType;
    const daysBack = parseInt(chartCard.dataset.daysBack) || 30;
    const aggregation = chartCard.dataset.aggregation || 'day';
    const showLegend = chartCard.dataset.showLegend === 'true';
    const showGrid = chartCard.dataset.showGrid === 'true';
    const cumulative = chartCard.dataset.cumulative === 'true';
    
    // Сохраняем ID canvas перед заменой
    const canvasId = canvasElement.id;
    const chartContainer = canvasElement.parentElement;
    
    // Показываем индикатор загрузки
    chartContainer.innerHTML = '<div style="text-align: center; padding: 40px; color: #666;">Загрузка данных...</div>';
    
    try {
        // Загружаем данные с фильтрами
        const indicatorData = await loadIndicatorData(indicatorId, daysBack, aggregation, filters, startDate, endDate, cumulative);
        
        if (!indicatorData) {
            chartContainer.innerHTML = '<div style="text-align: center; padding: 40px; color: #f44336;">Ошибка загрузки данных</div>';
            return;
        }
        
        // Восстанавливаем canvas с правильным ID
        chartContainer.innerHTML = `<canvas id="${canvasId}" style="max-height: ${chartCard.style.minHeight};"></canvas>`;
        const newCanvas = document.getElementById(canvasId);
        
        if (!newCanvas) {
            chartContainer.innerHTML = '<div style="text-align: center; padding: 40px; color: #f44336;">Ошибка создания canvas</div>';
            return;
        }
        
        // Проверяем наличие данных
        console.log('Проверка данных:', {
            hasData: !!indicatorData.data,
            hasDates: !!(indicatorData.data && indicatorData.data.dates),
            datesLength: indicatorData.data?.dates?.length || 0,
            valuesLength: indicatorData.data?.values?.length || 0
        });
        
        if (!indicatorData.data || !indicatorData.data.dates || indicatorData.data.dates.length === 0) {
            console.warn('Нет данных для отображения');
            chartContainer.innerHTML = '<div style="text-align: center; padding: 40px; color: #999;">Нет данных для отображения</div>';
            return;
        }
        
        // Проверяем, что Chart доступен
        if (typeof Chart === 'undefined') {
            console.error('Chart.js не загружен');
            chartContainer.innerHTML = '<div style="text-align: center; padding: 40px; color: #f44336;">Chart.js не загружен</div>';
            return;
        }
        
        console.log('Создание конфигурации графика, тип:', chartType);
        
        // Создаем конфигурацию графика
        let config;
        try {
            config = createChartConfig(
                chartType,
                indicatorData,
                showLegend,
                showGrid,
                indicatorData.data.statuses
            );
            console.log('Конфигурация создана:', config);
        } catch (configError) {
            console.error('Ошибка создания конфигурации:', configError);
            chartContainer.innerHTML = '<div style="text-align: center; padding: 40px; color: #f44336;">Ошибка создания конфигурации: ' + configError.message + '</div>';
            return;
        }
        
        // Создаем график
        try {
            console.log('Создание графика Chart.js...');
            const chartId = canvasId.replace('chart-', '');
            
            // Удаляем старый график если есть
            if (window.dashboardCharts && window.dashboardCharts[chartId]) {
                window.dashboardCharts[chartId].destroy();
            }
            
            // Создаем новый график
            const chart = new Chart(newCanvas, config);
            
            // Сохраняем ссылку на график
            if (!window.dashboardCharts) {
                window.dashboardCharts = {};
            }
            window.dashboardCharts[chartId] = chart;
            
            console.log('График успешно создан');
        } catch (chartError) {
            console.error('Ошибка создания графика:', chartError);
            console.error('Stack:', chartError.stack);
            chartContainer.innerHTML = '<div style="text-align: center; padding: 40px; color: #f44336;">Ошибка создания графика: ' + chartError.message + '</div>';
        }
        
    } catch (error) {
        console.error('Ошибка при рендеринге графика:', error);
        console.error('Stack trace:', error.stack);
        chartContainer.innerHTML = '<div style="text-align: center; padding: 40px; color: #f44336;">Ошибка отображения графика: ' + (error.message || error.toString()) + '</div>';
    }
}

/**
 * Инициализирует все графики на странице дашборда
 */
function initializeDashboard() {
    console.log('Инициализация дашборда...');
    
    // Проверяем, что Chart.js загружен
    if (typeof Chart === 'undefined') {
        console.error('Chart.js не загружен!');
        document.querySelectorAll('.chart-container').forEach(container => {
            container.innerHTML = '<div style="text-align: center; padding: 40px; color: #f44336;">Ошибка: Chart.js не загружен</div>';
        });
        return;
    }
    
    const chartCards = document.querySelectorAll('.chart-card');
    console.log('Найдено карточек графиков:', chartCards.length);
    
    if (chartCards.length === 0) {
        console.log('Графики не найдены на странице');
        return;
    }
    
    chartCards.forEach((chartCard, index) => {
        console.log(`Обработка графика ${index + 1}...`);
        const canvasId = chartCard.querySelector('canvas')?.id;
        console.log('Canvas ID:', canvasId);
        
        if (canvasId) {
            const canvasElement = document.getElementById(canvasId);
            if (canvasElement) {
                console.log('Найден canvas элемент, начинаем рендеринг...');
                renderChart(canvasElement, chartCard);
            } else {
                console.error('Canvas элемент не найден по ID:', canvasId);
            }
        } else {
            console.error('Canvas ID не найден в карточке графика');
        }
    });
}

// Экспортируем функции для использования в других скриптах
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        initializeDashboard,
        renderChart,
        renderChartWithFilters,
        loadIndicatorData
    };
}

// Делаем функции доступными глобально
window.renderChartWithFilters = renderChartWithFilters;
window.applyFilters = function() {
    // Эта функция будет переопределена в шаблоне
};
