/**
 * Real-time Workout Monitoring with Enhanced Features
 * Implements optimized data polling, client-side caching, responsive charts,
 * and workout phase indicators for improved user experience.
 */

class WorkoutMonitor {
    constructor() {
        this.isActive = false;
        this.pollInterval = null;
        this.pollRate = 1000; // 1 second default
        this.adaptivePollRate = true;
        
        // Data caching
        this.dataCache = {
            status: null,
            lastUpdate: 0,
            workoutData: [],
            maxCacheSize: 300 // 5 minutes at 1Hz
        };
        
        // Chart management
        this.charts = {};
        this.chartUpdateQueue = [];
        this.isUpdatingCharts = false;
        
        // Workout phase tracking
        this.workoutPhases = {
            current: 'inactive',
            startTime: null,
            phases: []
        };
        
        // Performance monitoring
        this.performance = {
            updateTimes: [],
            droppedUpdates: 0,
            lastUpdateTime: 0
        };
        
        // Connection quality monitoring
        this.connectionQuality = {
            consecutiveFailures: 0,
            lastSuccessTime: Date.now(),
            quality: 'good' // good, fair, poor, disconnected
        };
        
        this.init();
    }
    
    init() {
        this.setupEventListeners();
        this.initializeCharts();
        this.loadUserPreferences();
        console.log('WorkoutMonitor initialized');
    }
    
    setupEventListeners() {
        // Window visibility change for adaptive polling
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                this.reducePollRate();
            } else {
                this.restorePollRate();
            }
        });
        
        // Network status monitoring
        window.addEventListener('online', () => {
            console.log('Network connection restored');
            this.connectionQuality.quality = 'good';
            this.updateConnectionIndicator();
        });
        
        window.addEventListener('offline', () => {
            console.log('Network connection lost');
            this.connectionQuality.quality = 'disconnected';
            this.updateConnectionIndicator();
        });
        
        // Resize handler for responsive charts
        window.addEventListener('resize', this.debounce(() => {
            this.resizeCharts();
        }, 250));
    }
    
    async loadUserPreferences() {
        try {
            const response = await fetch('/api/settings');
            const data = await response.json();
            
            if (data.success && data.settings) {
                this.pollRate = data.settings.poll_rate || 1000;
                this.adaptivePollRate = data.settings.adaptive_polling !== false;
                
                // Update chart preferences
                if (data.settings.chart_preferences) {
                    this.updateChartPreferences(data.settings.chart_preferences);
                }
            }
        } catch (error) {
            console.warn('Could not load user preferences:', error);
        }
    }
    
    start() {
        if (this.isActive) return;
        
        this.isActive = true;
        this.workoutPhases.startTime = Date.now();
        this.workoutPhases.current = 'warmup';
        
        console.log('Starting workout monitoring');
        this.startPolling();
        this.updateWorkoutPhaseIndicator();
    }
    
    stop() {
        if (!this.isActive) return;
        
        this.isActive = false;
        this.workoutPhases.current = 'inactive';
        
        console.log('Stopping workout monitoring');
        this.stopPolling();
        this.updateWorkoutPhaseIndicator();
    }
    
    startPolling() {
        this.stopPolling(); // Clear any existing interval
        
        this.pollInterval = setInterval(() => {
            this.fetchWorkoutData();
        }, this.pollRate);
        
        // Initial fetch
        this.fetchWorkoutData();
    }
    
    stopPolling() {
        if (this.pollInterval) {
            clearInterval(this.pollInterval);
            this.pollInterval = null;
        }
    }
    
    async fetchWorkoutData() {
        const startTime = performance.now();
        
        try {
            const response = await fetch('/api/status');
            const data = await response.json();
            
            // Update connection quality
            this.connectionQuality.consecutiveFailures = 0;
            this.connectionQuality.lastSuccessTime = Date.now();
            this.updateConnectionQuality('good');
            
            // Cache the data
            this.cacheData(data);
            
            // Process the data
            this.processWorkoutData(data);
            
            // Track performance
            const updateTime = performance.now() - startTime;
            this.trackPerformance(updateTime);
            
            // Adaptive polling based on data changes
            if (this.adaptivePollRate) {
                this.adjustPollRate(data);
            }
            
        } catch (error) {
            console.error('Error fetching workout data:', error);
            this.handleFetchError(error);
        }
    }
    
    cacheData(data) {
        const now = Date.now();
        
        // Update status cache
        this.dataCache.status = data;
        this.dataCache.lastUpdate = now;
        
        // Cache workout data points
        if (data.latest_data && this.isActive) {
            this.dataCache.workoutData.push({
                timestamp: now,
                data: { ...data.latest_data }
            });
            
            // Maintain cache size
            if (this.dataCache.workoutData.length > this.dataCache.maxCacheSize) {
                this.dataCache.workoutData.shift();
            }
        }
    }
    
    processWorkoutData(data) {
        if (!data) return;
        
        // Update UI elements
        this.updateStatusDisplay(data);
        this.updateMetricsDisplay(data);
        
        // Update charts if workout is active
        if (this.isActive && data.latest_data) {
            this.queueChartUpdate(data.latest_data);
        }
        
        // Update workout phase
        this.updateWorkoutPhase(data);
        
        // Update workout summary
        if (data.latest_data && data.latest_data.workout_summary) {
            this.updateWorkoutSummary(data.latest_data.workout_summary);
        }
    }
    
    updateStatusDisplay(data) {
        const elements = {
            statusText: document.getElementById('status-text'),
            deviceName: document.getElementById('device-name'),
            workoutStatus: document.getElementById('workout-status'),
            workoutDuration: document.getElementById('workout-duration')
        };
        
        // Update connection status
        if (elements.statusText) {
            if (data.device_status === 'connected') {
                elements.statusText.textContent = 'Connected';
                elements.statusText.className = 'badge bg-success';
            } else {
                elements.statusText.textContent = 'Disconnected';
                elements.statusText.className = 'badge bg-secondary';
            }
        }
        
        // Update device name
        if (elements.deviceName) {
            const deviceName = data.device_name || 
                             (data.connected_device && data.connected_device.name) || 
                             'None';
            elements.deviceName.textContent = deviceName;
        }
        
        // Update workout status
        if (elements.workoutStatus) {
            if (data.workout_active) {
                elements.workoutStatus.textContent = 'Active';
                elements.workoutStatus.className = 'badge bg-success';
            } else {
                elements.workoutStatus.textContent = 'Inactive';
                elements.workoutStatus.className = 'badge bg-secondary';
            }
        }
        
        // Update workout duration
        if (elements.workoutDuration && data.latest_data && data.latest_data.elapsed_time) {
            elements.workoutDuration.textContent = this.formatDuration(data.latest_data.elapsed_time);
        }
    }
    
    updateMetricsDisplay(data) {
        if (!data.latest_data) return;
        
        const metrics = data.latest_data;
        const elements = {
            power: document.getElementById('power-value'),
            heartRate: document.getElementById('heart-rate-value'),
            cadence: document.getElementById('cadence-value'),
            speed: document.getElementById('speed-value'),
            distance: document.getElementById('distance-value'),
            calories: document.getElementById('calories-value')
        };
        
        // Update power
        if (elements.power && (metrics.instant_power !== undefined || metrics.power !== undefined)) {
            const power = metrics.instant_power || metrics.power || 0;
            elements.power.textContent = Math.round(power);
            this.addMetricAnimation(elements.power, power);
        }
        
        // Update heart rate
        if (elements.heartRate && metrics.heart_rate !== undefined) {
            elements.heartRate.textContent = Math.round(metrics.heart_rate);
            this.addMetricAnimation(elements.heartRate, metrics.heart_rate);
        }
        
        // Update cadence/stroke rate
        if (elements.cadence) {
            const workoutType = metrics.type || metrics.device_type || 'bike';
            let cadenceValue = 0;
            
            if (workoutType === 'bike') {
                cadenceValue = metrics.instant_cadence || metrics.instantaneous_cadence || metrics.cadence || 0;
            } else if (workoutType === 'rower') {
                cadenceValue = metrics.stroke_rate || 0;
            }
            
            elements.cadence.textContent = Math.round(cadenceValue);
            this.addMetricAnimation(elements.cadence, cadenceValue);
        }
        
        // Update speed
        if (elements.speed && (metrics.instant_speed !== undefined || metrics.speed !== undefined)) {
            const speed = metrics.instant_speed || metrics.speed || 0;
            elements.speed.textContent = speed.toFixed(1);
            this.addMetricAnimation(elements.speed, speed);
        }
        
        // Update distance
        if (elements.distance && (metrics.total_distance !== undefined || metrics.distance !== undefined)) {
            const distance = metrics.total_distance || metrics.distance || 0;
            const distanceKm = distance / 1000;
            elements.distance.textContent = distanceKm.toFixed(2);
        }
        
        // Update calories
        if (elements.calories && (metrics.total_energy !== undefined || metrics.calories !== undefined)) {
            const calories = metrics.total_energy || metrics.calories || 0;
            elements.calories.textContent = Math.round(calories);
        }
    }
    
    addMetricAnimation(element, value) {
        // Add subtle animation for metric changes
        element.style.transform = 'scale(1.05)';
        element.style.transition = 'transform 0.1s ease-out';
        
        setTimeout(() => {
            element.style.transform = 'scale(1)';
        }, 100);
        
        // Add color coding for power zones
        if (element.id === 'power-value') {
            this.updatePowerZoneColor(element, value);
        }
    }
    
    updatePowerZoneColor(element, power) {
        // Remove existing zone classes
        element.classList.remove('power-zone-1', 'power-zone-2', 'power-zone-3', 'power-zone-4', 'power-zone-5');
        
        // Add appropriate zone class based on power
        if (power > 250) {
            element.classList.add('power-zone-5'); // Neuromuscular Power
        } else if (power > 200) {
            element.classList.add('power-zone-4'); // Lactate Threshold
        } else if (power > 150) {
            element.classList.add('power-zone-3'); // Tempo
        } else if (power > 100) {
            element.classList.add('power-zone-2'); // Endurance
        } else if (power > 50) {
            element.classList.add('power-zone-1'); // Active Recovery
        }
    }
    
    queueChartUpdate(data) {
        this.chartUpdateQueue.push(data);
        
        if (!this.isUpdatingCharts) {
            this.processChartUpdateQueue();
        }
    }
    
    async processChartUpdateQueue() {
        if (this.chartUpdateQueue.length === 0) return;
        
        this.isUpdatingCharts = true;
        
        // Process all queued updates
        while (this.chartUpdateQueue.length > 0) {
            const data = this.chartUpdateQueue.shift();
            await this.updateCharts(data);
        }
        
        this.isUpdatingCharts = false;
    }
    
    async updateCharts(data) {
        const maxDataPoints = 60; // 1 minute of data
        
        // Update power chart
        if (this.charts.power && (data.instant_power !== undefined || data.power !== undefined)) {
            const power = data.instant_power || data.power || 0;
            this.updateChartData(this.charts.power, power, maxDataPoints);
        }
        
        // Update heart rate chart
        if (this.charts.heartRate && data.heart_rate !== undefined) {
            this.updateChartData(this.charts.heartRate, data.heart_rate, maxDataPoints);
        }
        
        // Update cadence chart
        if (this.charts.cadence) {
            const workoutType = data.type || data.device_type || 'bike';
            let cadenceValue = 0;
            
            if (workoutType === 'bike') {
                cadenceValue = data.instant_cadence || data.instantaneous_cadence || data.cadence || 0;
            } else if (workoutType === 'rower') {
                cadenceValue = data.stroke_rate || 0;
            }
            
            this.updateChartData(this.charts.cadence, cadenceValue, maxDataPoints);
        }
        
        // Batch update all charts
        this.batchUpdateCharts();
    }
    
    updateChartData(chart, value, maxDataPoints) {
        if (!chart || !chart.data || !chart.data.datasets[0]) return;
        
        const dataset = chart.data.datasets[0];
        dataset.data.push(value);
        
        // Maintain max data points
        if (dataset.data.length > maxDataPoints) {
            dataset.data.shift();
        }
        
        // Mark chart as needing update
        chart._needsUpdate = true;
    }
    
    batchUpdateCharts() {
        // Use requestAnimationFrame for smooth updates
        requestAnimationFrame(() => {
            Object.values(this.charts).forEach(chart => {
                if (chart._needsUpdate) {
                    chart.update('none'); // No animation for real-time updates
                    chart._needsUpdate = false;
                }
            });
        });
    }
    
    updateWorkoutPhase(data) {
        if (!this.isActive || !data.latest_data) return;
        
        const elapsed = data.latest_data.elapsed_time || 0;
        const power = data.latest_data.instant_power || data.latest_data.power || 0;
        
        let newPhase = this.determineWorkoutPhase(elapsed, power);
        
        if (newPhase !== this.workoutPhases.current) {
            this.workoutPhases.current = newPhase;
            this.workoutPhases.phases.push({
                phase: newPhase,
                startTime: elapsed,
                timestamp: Date.now()
            });
            
            this.updateWorkoutPhaseIndicator();
            this.showPhaseTransitionNotification(newPhase);
        }
    }
    
    determineWorkoutPhase(elapsed, power) {
        // Simple phase detection based on time and power
        if (elapsed < 300) { // First 5 minutes
            return 'warmup';
        } else if (elapsed < 600) { // 5-10 minutes
            return power > 150 ? 'main' : 'warmup';
        } else if (elapsed > 1800) { // After 30 minutes
            return power < 100 ? 'cooldown' : 'main';
        } else {
            return 'main';
        }
    }
    
    updateWorkoutPhaseIndicator() {
        const indicator = document.getElementById('workout-phase-indicator');
        if (!indicator) return;
        
        const phaseConfig = {
            inactive: { text: 'Inactive', class: 'bg-secondary', icon: '⏸️' },
            warmup: { text: 'Warm-up', class: 'bg-info', icon: '🔥' },
            main: { text: 'Main Workout', class: 'bg-success', icon: '💪' },
            intervals: { text: 'Intervals', class: 'bg-warning', icon: '⚡' },
            cooldown: { text: 'Cool-down', class: 'bg-primary', icon: '❄️' }
        };
        
        const config = phaseConfig[this.workoutPhases.current] || phaseConfig.inactive;
        
        indicator.innerHTML = `
            <span class="badge ${config.class}">
                ${config.icon} ${config.text}
            </span>
        `;
    }
    
    showPhaseTransitionNotification(newPhase) {
        const messages = {
            warmup: 'Starting warm-up phase',
            main: 'Entering main workout',
            intervals: 'Beginning interval training',
            cooldown: 'Starting cool-down'
        };
        
        const message = messages[newPhase];
        if (message && typeof showNotification === 'function') {
            showNotification(message, 'info');
        }
    }
    
    updateWorkoutSummary(summary) {
        const summaryElement = document.getElementById('workout-summary');
        if (!summaryElement || !summary) return;
        
        // Create enhanced summary with progress indicators
        let html = '<div class="workout-summary-enhanced">';
        
        // Progress bars for key metrics
        if (summary.avg_power !== undefined) {
            const powerPercent = Math.min((summary.avg_power / 300) * 100, 100);
            html += this.createProgressMetric('Average Power', summary.avg_power, 'W', powerPercent, 'bg-danger');
        }
        
        if (summary.avg_heart_rate !== undefined) {
            const hrPercent = Math.min((summary.avg_heart_rate / 200) * 100, 100);
            html += this.createProgressMetric('Average HR', summary.avg_heart_rate, 'bpm', hrPercent, 'bg-info');
        }
        
        if (summary.total_distance !== undefined) {
            const distanceKm = summary.total_distance / 1000;
            html += this.createProgressMetric('Distance', distanceKm.toFixed(2), 'km', null, 'bg-success');
        }
        
        if (summary.total_calories !== undefined) {
            html += this.createProgressMetric('Calories', Math.round(summary.total_calories), 'kcal', null, 'bg-warning');
        }
        
        html += '</div>';
        summaryElement.innerHTML = html;
    }
    
    createProgressMetric(label, value, unit, percent, colorClass) {
        let progressBar = '';
        if (percent !== null) {
            progressBar = `
                <div class="progress mt-1" style="height: 4px;">
                    <div class="progress-bar ${colorClass}" role="progressbar" 
                         style="width: ${percent}%" aria-valuenow="${percent}" 
                         aria-valuemin="0" aria-valuemax="100"></div>
                </div>
            `;
        }
        
        return `
            <div class="metric-summary mb-2">
                <div class="d-flex justify-content-between">
                    <span class="metric-label">${label}:</span>
                    <span class="metric-value">${value} ${unit}</span>
                </div>
                ${progressBar}
            </div>
        `;
    }
    
    adjustPollRate(data) {
        // Adaptive polling based on workout activity and data changes
        if (!data.workout_active) {
            // Slower polling when not in workout
            this.setPollRate(2000);
        } else if (data.latest_data) {
            // Faster polling during active workout
            this.setPollRate(1000);
            
            // Even faster during high-intensity phases
            const power = data.latest_data.instant_power || data.latest_data.power || 0;
            if (power > 200) {
                this.setPollRate(500);
            }
        }
    }
    
    setPollRate(newRate) {
        if (this.pollRate === newRate) return;
        
        this.pollRate = newRate;
        
        if (this.isActive) {
            this.startPolling(); // Restart with new rate
        }
    }
    
    reducePollRate() {
        // Reduce polling when tab is not visible
        this.setPollRate(this.pollRate * 2);
    }
    
    restorePollRate() {
        // Restore normal polling when tab becomes visible
        this.setPollRate(Math.max(this.pollRate / 2, 1000));
    }
    
    handleFetchError(error) {
        this.connectionQuality.consecutiveFailures++;
        
        // Update connection quality based on failures
        if (this.connectionQuality.consecutiveFailures >= 5) {
            this.updateConnectionQuality('poor');
        } else if (this.connectionQuality.consecutiveFailures >= 3) {
            this.updateConnectionQuality('fair');
        }
        
        // Exponential backoff for failed requests
        const backoffRate = Math.min(this.pollRate * Math.pow(1.5, this.connectionQuality.consecutiveFailures), 10000);
        this.setPollRate(backoffRate);
        
        this.trackPerformance(null, true);
    }
    
    updateConnectionQuality(quality) {
        if (this.connectionQuality.quality === quality) return;
        
        this.connectionQuality.quality = quality;
        this.updateConnectionIndicator();
    }
    
    updateConnectionIndicator() {
        const indicator = document.getElementById('connection-quality-indicator');
        if (!indicator) return;
        
        const qualityConfig = {
            good: { text: 'Excellent', class: 'bg-success', icon: '📶' },
            fair: { text: 'Fair', class: 'bg-warning', icon: '📶' },
            poor: { text: 'Poor', class: 'bg-danger', icon: '📶' },
            disconnected: { text: 'Disconnected', class: 'bg-secondary', icon: '📵' }
        };
        
        const config = qualityConfig[this.connectionQuality.quality] || qualityConfig.disconnected;
        
        indicator.innerHTML = `
            <small class="badge ${config.class}">
                ${config.icon} ${config.text}
            </small>
        `;
    }
    
    trackPerformance(updateTime, isError = false) {
        if (isError) {
            this.performance.droppedUpdates++;
            return;
        }
        
        this.performance.updateTimes.push(updateTime);
        this.performance.lastUpdateTime = Date.now();
        
        // Keep only last 100 measurements
        if (this.performance.updateTimes.length > 100) {
            this.performance.updateTimes.shift();
        }
        
        // Log performance warnings
        if (updateTime > 1000) {
            console.warn(`Slow update detected: ${updateTime.toFixed(2)}ms`);
        }
    }
    
    getPerformanceStats() {
        const times = this.performance.updateTimes;
        if (times.length === 0) return null;
        
        const avg = times.reduce((a, b) => a + b, 0) / times.length;
        const max = Math.max(...times);
        const min = Math.min(...times);
        
        return {
            averageUpdateTime: avg.toFixed(2),
            maxUpdateTime: max.toFixed(2),
            minUpdateTime: min.toFixed(2),
            droppedUpdates: this.performance.droppedUpdates,
            totalUpdates: times.length
        };
    }
    
    initializeCharts() {
        // Initialize charts with responsive configuration
        const chartOptions = {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: { display: false },
                y: { beginAtZero: true }
            },
            animation: { duration: 0 },
            elements: {
                point: { radius: 0 },
                line: { tension: 0.4 }
            },
            plugins: {
                legend: { display: false }
            }
        };
        
        // Power chart
        const powerCtx = document.getElementById('power-chart');
        if (powerCtx) {
            this.charts.power = new Chart(powerCtx, {
                type: 'line',
                data: {
                    labels: Array(60).fill(''),
                    datasets: [{
                        data: Array(60).fill(null),
                        borderColor: 'rgba(255, 99, 132, 1)',
                        backgroundColor: 'rgba(255, 99, 132, 0.2)',
                        fill: true
                    }]
                },
                options: chartOptions
            });
        }
        
        // Heart rate chart
        const heartRateCtx = document.getElementById('heart-rate-chart');
        if (heartRateCtx) {
            this.charts.heartRate = new Chart(heartRateCtx, {
                type: 'line',
                data: {
                    labels: Array(60).fill(''),
                    datasets: [{
                        data: Array(60).fill(null),
                        borderColor: 'rgba(54, 162, 235, 1)',
                        backgroundColor: 'rgba(54, 162, 235, 0.2)',
                        fill: true
                    }]
                },
                options: chartOptions
            });
        }
        
        // Cadence chart
        const cadenceCtx = document.getElementById('cadence-chart');
        if (cadenceCtx) {
            this.charts.cadence = new Chart(cadenceCtx, {
                type: 'line',
                data: {
                    labels: Array(60).fill(''),
                    datasets: [{
                        data: Array(60).fill(null),
                        borderColor: 'rgba(75, 192, 192, 1)',
                        backgroundColor: 'rgba(75, 192, 192, 0.2)',
                        fill: true
                    }]
                },
                options: chartOptions
            });
        }
    }
    
    resizeCharts() {
        Object.values(this.charts).forEach(chart => {
            if (chart && chart.resize) {
                chart.resize();
            }
        });
    }
    
    updateChartPreferences(preferences) {
        // Update chart colors, styles, etc. based on user preferences
        Object.keys(this.charts).forEach(chartKey => {
            const chart = this.charts[chartKey];
            if (chart && preferences[chartKey]) {
                const pref = preferences[chartKey];
                
                if (pref.color) {
                    chart.data.datasets[0].borderColor = pref.color;
                    chart.data.datasets[0].backgroundColor = pref.color + '33'; // Add transparency
                }
                
                if (pref.fill !== undefined) {
                    chart.data.datasets[0].fill = pref.fill;
                }
                
                chart.update();
            }
        });
    }
    
    // Utility functions
    formatDuration(seconds) {
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        const secs = seconds % 60;
        
        return [
            hours.toString().padStart(2, '0'),
            minutes.toString().padStart(2, '0'),
            secs.toString().padStart(2, '0')
        ].join(':');
    }
    
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }
    
    // Public API
    getStatus() {
        return {
            isActive: this.isActive,
            pollRate: this.pollRate,
            connectionQuality: this.connectionQuality.quality,
            currentPhase: this.workoutPhases.current,
            performance: this.getPerformanceStats(),
            cacheSize: this.dataCache.workoutData.length
        };
    }
    
    exportData() {
        return {
            workoutData: this.dataCache.workoutData,
            phases: this.workoutPhases.phases,
            performance: this.performance
        };
    }
}

// Global instance
window.workoutMonitor = new WorkoutMonitor();