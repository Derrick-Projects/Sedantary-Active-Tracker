/**
 * Sedentary Activity Tracker - Frontend Dashboard
 * Uses D3.js for data visualization
 */

// ===== Configuration =====
const API_BASE_URL = 'http://localhost:8000';
const UPDATE_INTERVAL = 1000; // Update every 1 second
const MOVEMENT_THRESHOLD = 0.5; // m/s² threshold line

// ===== State =====
let timelineData = [];
let accelData = [];
let isConnected = false;

// ===== DOM Elements =====
const elements = {
    connectionStatus: document.getElementById('connectionStatus'),
    connectionText: document.getElementById('connectionText'),
    statusIndicator: document.getElementById('statusIndicator'),
    statusIcon: document.getElementById('statusIcon'),
    activityStateText: document.getElementById('activityStateText'),
    timerValue: document.getElementById('timerValue'),
    confidenceValue: document.getElementById('confidenceValue'),
    totalReadings: document.getElementById('totalReadings'),
    activePercentage: document.getElementById('activePercentage'),
    longestInactive: document.getElementById('longestInactive'),
    alertCount: document.getElementById('alertCount'),
    alertList: document.getElementById('alertList')
};

// ===== API Functions =====

async function fetchAPI(endpoint) {
    try {
        const response = await fetch(`${API_BASE_URL}${endpoint}`);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        return await response.json();
    } catch (error) {
        console.error(`API Error (${endpoint}):`, error);
        return null;
    }
}

async function fetchCurrentStatus() {
    return await fetchAPI('/api/status');
}

async function fetchStats() {
    return await fetchAPI('/api/stats');
}

async function fetchRecentReadings(limit = 60) {
    return await fetchAPI(`/api/readings/recent?limit=${limit}`);
}

async function fetchAlerts(limit = 10) {
    return await fetchAPI(`/api/alerts?limit=${limit}`);
}

async function fetchSerialStatus() {
    return await fetchAPI('/api/serial/status');
}

// ===== Update Functions =====

function updateConnectionStatus(connected) {
    isConnected = connected;
    const dot = elements.connectionStatus.querySelector('.status-dot');
    
    if (connected) {
        dot.classList.remove('disconnected');
        dot.classList.add('connected');
        elements.connectionText.textContent = 'Connected to Arduino';
    } else {
        dot.classList.remove('connected');
        dot.classList.add('disconnected');
        elements.connectionText.textContent = 'Disconnected';
    }
}

function updateActivityStatus(status) {
    if (!status) return;

    const { activity_state, inactive_seconds, is_alerted, confidence } = status;

    // Update indicator
    elements.statusIndicator.className = 'status-indicator ' + activity_state;

    // Update icon and text
    const stateConfig = {
        active: { icon: '🏃', text: 'Active' },
        inactive: { icon: '🪑', text: 'Sedentary' },
        transition: { icon: '🚶', text: 'Transition' }
    };

    const config = stateConfig[activity_state] || stateConfig.inactive;
    elements.statusIcon.textContent = config.icon;
    elements.activityStateText.textContent = config.text;

    // Update timer
    const minutes = Math.floor(inactive_seconds / 60);
    const seconds = inactive_seconds % 60;
    elements.timerValue.textContent = 
        `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;

    // Flash timer if alerted
    if (is_alerted) {
        elements.timerValue.style.color = '#ef4444';
    } else {
        elements.timerValue.style.color = '#3b82f6';
    }

    // Update confidence
    elements.confidenceValue.textContent = Math.round(confidence * 100);
}

function updateStats(stats) {
    if (!stats) return;

    elements.totalReadings.textContent = stats.total_readings.toLocaleString();
    elements.activePercentage.textContent = `${stats.active_percentage}%`;
    elements.longestInactive.textContent = `${stats.longest_inactive_period_seconds}s`;
    elements.alertCount.textContent = stats.alert_count;
}

function updateAlertList(alerts) {
    if (!alerts || alerts.length === 0) {
        elements.alertList.innerHTML = '<p class="no-alerts">No alerts yet</p>';
        return;
    }

    elements.alertList.innerHTML = alerts.map(alert => {
        const time = new Date(alert.timestamp).toLocaleTimeString();
        return `
            <div class="alert-item">
                <span class="alert-time">🔔 ${time}</span>
                <span class="alert-duration">Inactive: ${alert.duration_seconds}s</span>
            </div>
        `;
    }).join('');
}

// ===== D3.js Charts =====

// Chart dimensions
const margin = { top: 20, right: 30, bottom: 40, left: 50 };

// Timeline Activity Chart
function createTimelineChart(data) {
    const container = d3.select('#timelineChart');
    container.selectAll('*').remove();

    if (!data || data.length === 0) {
        container.append('p')
            .style('color', '#94a3b8')
            .style('text-align', 'center')
            .style('padding', '40px')
            .text('Waiting for data...');
        return;
    }

    const containerWidth = container.node().getBoundingClientRect().width;
    const width = containerWidth - margin.left - margin.right;
    const height = 150;

    const svg = container.append('svg')
        .attr('width', containerWidth)
        .attr('height', height + margin.top + margin.bottom)
        .append('g')
        .attr('transform', `translate(${margin.left},${margin.top})`);

    // Scales
    const x = d3.scaleTime()
        .domain(d3.extent(data, d => new Date(d.timestamp)))
        .range([0, width]);

    const stateToY = {
        'active': 2,
        'transition': 1,
        'inactive': 0
    };

    const y = d3.scaleLinear()
        .domain([0, 2])
        .range([height, 0]);

    const colorScale = d3.scaleOrdinal()
        .domain(['active', 'transition', 'inactive'])
        .range(['#22c55e', '#eab308', '#ef4444']);

    // X Axis
    svg.append('g')
        .attr('transform', `translate(0,${height})`)
        .call(d3.axisBottom(x).ticks(6).tickFormat(d3.timeFormat('%H:%M:%S')))
        .attr('class', 'axis-label');

    // Y Axis labels
    svg.append('text')
        .attr('x', -10)
        .attr('y', y(2))
        .attr('dy', '0.35em')
        .attr('text-anchor', 'end')
        .attr('class', 'axis-label')
        .text('Active');

    svg.append('text')
        .attr('x', -10)
        .attr('y', y(1))
        .attr('dy', '0.35em')
        .attr('text-anchor', 'end')
        .attr('class', 'axis-label')
        .text('Trans');

    svg.append('text')
        .attr('x', -10)
        .attr('y', y(0))
        .attr('dy', '0.35em')
        .attr('text-anchor', 'end')
        .attr('class', 'axis-label')
        .text('Inactive');

    // Grid lines
    svg.append('g')
        .attr('class', 'grid')
        .selectAll('line')
        .data([0, 1, 2])
        .enter()
        .append('line')
        .attr('x1', 0)
        .attr('x2', width)
        .attr('y1', d => y(d))
        .attr('y2', d => y(d));

    // Data points
    svg.selectAll('circle')
        .data(data)
        .enter()
        .append('circle')
        .attr('cx', d => x(new Date(d.timestamp)))
        .attr('cy', d => y(stateToY[d.activity_state] || 0))
        .attr('r', 5)
        .attr('fill', d => colorScale(d.activity_state))
        .attr('opacity', 0.8);

    // Connect with line
    const line = d3.line()
        .x(d => x(new Date(d.timestamp)))
        .y(d => y(stateToY[d.activity_state] || 0))
        .curve(d3.curveStepAfter);

    svg.append('path')
        .datum(data)
        .attr('fill', 'none')
        .attr('stroke', '#64748b')
        .attr('stroke-width', 1.5)
        .attr('d', line);
}

// Acceleration Magnitude Chart
function createAccelChart(data) {
    const container = d3.select('#accelChart');
    container.selectAll('*').remove();

    if (!data || data.length === 0) {
        container.append('p')
            .style('color', '#94a3b8')
            .style('text-align', 'center')
            .style('padding', '40px')
            .text('Waiting for data...');
        return;
    }

    const containerWidth = container.node().getBoundingClientRect().width;
    const width = containerWidth - margin.left - margin.right;
    const height = 180;

    const svg = container.append('svg')
        .attr('width', containerWidth)
        .attr('height', height + margin.top + margin.bottom)
        .append('g')
        .attr('transform', `translate(${margin.left},${margin.top})`);

    // Scales
    const x = d3.scaleTime()
        .domain(d3.extent(data, d => new Date(d.timestamp)))
        .range([0, width]);

    const maxDelta = Math.max(d3.max(data, d => d.delta_mag) || 1, 1);
    const y = d3.scaleLinear()
        .domain([0, maxDelta * 1.2])
        .range([height, 0]);

    // Axes
    svg.append('g')
        .attr('transform', `translate(0,${height})`)
        .call(d3.axisBottom(x).ticks(6).tickFormat(d3.timeFormat('%H:%M:%S')))
        .attr('class', 'axis-label');

    svg.append('g')
        .call(d3.axisLeft(y).ticks(5))
        .attr('class', 'axis-label');

    // Y axis label
    svg.append('text')
        .attr('transform', 'rotate(-90)')
        .attr('y', -40)
        .attr('x', -height / 2)
        .attr('text-anchor', 'middle')
        .attr('class', 'axis-label')
        .text('Delta Magnitude (m/s²)');

    // Threshold line
    svg.append('line')
        .attr('class', 'threshold-line')
        .attr('x1', 0)
        .attr('x2', width)
        .attr('y1', y(MOVEMENT_THRESHOLD))
        .attr('y2', y(MOVEMENT_THRESHOLD));

    svg.append('text')
        .attr('x', width - 5)
        .attr('y', y(MOVEMENT_THRESHOLD) - 5)
        .attr('text-anchor', 'end')
        .attr('fill', '#eab308')
        .attr('font-size', '10px')
        .text('Threshold');

    // Area under line
    const area = d3.area()
        .x(d => x(new Date(d.timestamp)))
        .y0(height)
        .y1(d => y(d.delta_mag))
        .curve(d3.curveMonotoneX);

    svg.append('path')
        .datum(data)
        .attr('fill', 'url(#accelGradient)')
        .attr('d', area);

    // Gradient
    const defs = svg.append('defs');
    const gradient = defs.append('linearGradient')
        .attr('id', 'accelGradient')
        .attr('x1', '0%')
        .attr('y1', '0%')
        .attr('x2', '0%')
        .attr('y2', '100%');

    gradient.append('stop')
        .attr('offset', '0%')
        .attr('stop-color', '#3b82f6')
        .attr('stop-opacity', 0.6);

    gradient.append('stop')
        .attr('offset', '100%')
        .attr('stop-color', '#3b82f6')
        .attr('stop-opacity', 0.1);

    // Line
    const line = d3.line()
        .x(d => x(new Date(d.timestamp)))
        .y(d => y(d.delta_mag))
        .curve(d3.curveMonotoneX);

    svg.append('path')
        .datum(data)
        .attr('fill', 'none')
        .attr('stroke', '#3b82f6')
        .attr('stroke-width', 2)
        .attr('d', line);

    // Data points colored by state
    const colorScale = d3.scaleOrdinal()
        .domain(['active', 'transition', 'inactive'])
        .range(['#22c55e', '#eab308', '#ef4444']);

    svg.selectAll('circle')
        .data(data)
        .enter()
        .append('circle')
        .attr('cx', d => x(new Date(d.timestamp)))
        .attr('cy', d => y(d.delta_mag))
        .attr('r', 3)
        .attr('fill', d => colorScale(d.activity_state));
}

// Session Summary Bar Chart
function createSummaryChart(stats) {
    const container = d3.select('#summaryChart');
    container.selectAll('*').remove();

    if (!stats || stats.total_readings === 0) {
        container.append('p')
            .style('color', '#94a3b8')
            .style('text-align', 'center')
            .style('padding', '40px')
            .text('Waiting for data...');
        return;
    }

    const data = [
        { label: 'Active', value: stats.total_active_time_seconds, color: '#22c55e' },
        { label: 'Inactive', value: stats.total_inactive_time_seconds, color: '#ef4444' }
    ];

    const containerWidth = container.node().getBoundingClientRect().width;
    const width = containerWidth - margin.left - margin.right;
    const height = 180;

    const svg = container.append('svg')
        .attr('width', containerWidth)
        .attr('height', height + margin.top + margin.bottom)
        .append('g')
        .attr('transform', `translate(${margin.left},${margin.top})`);

    // Scales
    const x = d3.scaleBand()
        .domain(data.map(d => d.label))
        .range([0, width])
        .padding(0.4);

    const y = d3.scaleLinear()
        .domain([0, d3.max(data, d => d.value) * 1.2 || 10])
        .range([height, 0]);

    // Axes
    svg.append('g')
        .attr('transform', `translate(0,${height})`)
        .call(d3.axisBottom(x))
        .attr('class', 'axis-label');

    svg.append('g')
        .call(d3.axisLeft(y).ticks(5))
        .attr('class', 'axis-label');

    // Y axis label
    svg.append('text')
        .attr('transform', 'rotate(-90)')
        .attr('y', -40)
        .attr('x', -height / 2)
        .attr('text-anchor', 'middle')
        .attr('class', 'axis-label')
        .text('Seconds');

    // Bars
    svg.selectAll('rect')
        .data(data)
        .enter()
        .append('rect')
        .attr('x', d => x(d.label))
        .attr('y', d => y(d.value))
        .attr('width', x.bandwidth())
        .attr('height', d => height - y(d.value))
        .attr('fill', d => d.color)
        .attr('rx', 4);

    // Value labels
    svg.selectAll('.value-label')
        .data(data)
        .enter()
        .append('text')
        .attr('x', d => x(d.label) + x.bandwidth() / 2)
        .attr('y', d => y(d.value) - 5)
        .attr('text-anchor', 'middle')
        .attr('fill', '#f8fafc')
        .attr('font-size', '12px')
        .attr('font-weight', 'bold')
        .text(d => `${d.value}s`);
}

// ===== Main Update Loop =====

async function updateDashboard() {
    try {
        // Fetch all data in parallel
        const [status, stats, readings, alerts, serialStatus] = await Promise.all([
            fetchCurrentStatus(),
            fetchStats(),
            fetchRecentReadings(60),
            fetchAlerts(10),
            fetchSerialStatus()
        ]);

        // Update connection status
        updateConnectionStatus(serialStatus?.connected ?? false);

        // Update status display
        updateActivityStatus(status);

        // Update stats
        updateStats(stats);

        // Update alerts
        updateAlertList(alerts);

        // Update charts
        if (readings && readings.length > 0) {
            createTimelineChart(readings);
            createAccelChart(readings);
        }

        if (stats) {
            createSummaryChart(stats);
        }

    } catch (error) {
        console.error('Dashboard update error:', error);
        updateConnectionStatus(false);
    }
}

// ===== Window Resize Handler =====
let resizeTimeout;
window.addEventListener('resize', () => {
    clearTimeout(resizeTimeout);
    resizeTimeout = setTimeout(updateDashboard, 250);
});

// ===== Initialize =====
async function init() {
    console.log('Sedentary Activity Tracker Dashboard - Initializing...');
    
    // Initial update
    await updateDashboard();
    
    // Start update loop
    setInterval(updateDashboard, UPDATE_INTERVAL);
    
    console.log('Dashboard initialized. Updating every', UPDATE_INTERVAL, 'ms');
}

// Start when DOM is ready
document.addEventListener('DOMContentLoaded', init);
