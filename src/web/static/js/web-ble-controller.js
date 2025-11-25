/**
 * Page-level wiring for Web Bluetooth FTMS client on the Devices page.
 * Keeps UI elements in sync and relays user actions to WebBLEFTMSClient.
 */
(function () {
    const connectBtn = document.getElementById('webble-connect');
    const disconnectBtn = document.getElementById('webble-disconnect');
    const statusBadge = document.getElementById('webble-status');
    const supportNotice = document.getElementById('webble-support');
    const lastDataBox = document.getElementById('webble-last-data');
    const deviceLabel = document.getElementById('webble-device');
    const workoutLabel = document.getElementById('webble-workout-id');
    const errorBox = document.getElementById('webble-error');

    if (!connectBtn || !statusBadge || !supportNotice) {
        return; // Section not on this page
    }

    const client = new WebBLEFTMSClient({
        sendIntervalMs: 700,
        onData: handleData,
        onStatus: handleStatus
    });

    if (!client.isSupported()) {
        supportNotice.innerHTML = '<div class="alert alert-danger mb-2">Web Bluetooth not available in this browser. Use Bluefy on iOS or Chrome on Android/desktop over HTTPS.</div>';
        connectBtn.disabled = true;
        return;
    }

    supportNotice.innerHTML = '<div class="alert alert-success mb-2">Web Bluetooth available. Use the button below to connect directly from the browser.</div>';

    connectBtn.addEventListener('click', async () => {
        clearError();
        const deviceType = (document.querySelector('input[name="webble-device-type"]:checked') || {}).value || 'bike';
        setBusy(true, 'Connecting...');
        try {
            await client.connect(deviceType);
        } catch (err) {
            showError(err.message || 'Unable to connect');
            setBusy(false);
        }
    });

    disconnectBtn?.addEventListener('click', async () => {
        clearError();
        setBusy(true, 'Disconnecting...');
        try {
            await client.disconnect();
        } finally {
            setBusy(false);
        }
    });

    function handleStatus(status) {
        if (status.type === 'connected') {
            statusBadge.className = 'badge bg-success';
            statusBadge.textContent = 'Connected (Web Bluetooth)';
            connectBtn.classList.add('d-none');
            disconnectBtn.classList.remove('d-none');
            deviceLabel.textContent = status.device?.name || 'Web Bluetooth Device';
            workoutLabel.textContent = status.workoutId || '—';
        } else if (status.type === 'disconnected') {
            statusBadge.className = 'badge bg-secondary';
            statusBadge.textContent = 'Disconnected';
            connectBtn.classList.remove('d-none');
            disconnectBtn.classList.add('d-none');
            deviceLabel.textContent = 'None';
            workoutLabel.textContent = '—';
        }
        setBusy(false);
    }

    function handleData(data) {
        // Keep UI lightweight; backend receives full payload.
        const lines = [];
        if (data.instant_power !== undefined) lines.push(`Power: ${data.instant_power} W`);
        if (data.instant_cadence !== undefined) lines.push(`Cadence: ${data.instant_cadence} rpm`);
        if (data.speed !== undefined) lines.push(`Speed: ${data.speed.toFixed ? data.speed.toFixed(1) : data.speed} km/h`);
        if (data.stroke_rate !== undefined) lines.push(`Stroke Rate: ${data.stroke_rate} spm`);
        if (data.heart_rate !== undefined) lines.push(`Heart Rate: ${data.heart_rate} bpm`);
        if (data.total_distance !== undefined) lines.push(`Distance: ${data.total_distance} m`);
        if (data.timestamp) lines.push(`Updated: ${new Date(data.timestamp).toLocaleTimeString()}`);

        if (lines.length === 0) lines.push('Receiving data...');
        lastDataBox.innerHTML = lines.join('<br>');
    }

    function setBusy(isBusy, message = '') {
        if (isBusy) {
            connectBtn.disabled = true;
            disconnectBtn.disabled = true;
            statusBadge.textContent = message || 'Working...';
        } else {
            connectBtn.disabled = false;
            disconnectBtn.disabled = false;
        }
    }

    function showError(msg) {
        if (errorBox) {
            errorBox.innerHTML = `<div class="alert alert-danger">${msg}</div>`;
        } else {
            alert(msg);
        }
    }

    function clearError() {
        if (errorBox) {
            errorBox.innerHTML = '';
        }
    }
})();
