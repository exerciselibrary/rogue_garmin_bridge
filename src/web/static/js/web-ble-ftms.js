/**
 * Lightweight Web Bluetooth FTMS client for browser-only BLE (Bluefy/mobile).
 * Handles device discovery, FTMS data subscription, parsing, and streaming
 * to the backend ingestion endpoints.
 */

class WebBLEFTMSClient {
    constructor({ onData, onStatus, sendIntervalMs = 500 } = {}) {
        this.FTMS_SERVICE_UUID = '00001826-0000-1000-8000-00805f9b34fb';
        this.INDOOR_BIKE_DATA_UUID = '00002ad2-0000-1000-8000-00805f9b34fb';
        this.ROWER_DATA_UUID = '00002ad1-0000-1000-8000-00805f9b34fb';
        this.CONTROL_POINT_UUID = '00002ad9-0000-1000-8000-00805f9b34fb';
        this.HEART_RATE_SERVICE = '0000180d-0000-1000-8000-00805f9b34fb';
        this.HEART_RATE_MEASUREMENT = '00002a37-0000-1000-8000-00805f9b34fb';

        this.device = null;
        this.server = null;
        this.dataCharacteristic = null;
        this.heartRateCharacteristic = null;
        this.deviceType = 'bike';
        this.workoutId = null;
        this.sendIntervalMs = sendIntervalMs;
        this.sendTimer = null;
        this.latestPayload = null;
        this.isConnected = false;

        this.onData = onData || (() => {});
        this.onStatus = onStatus || (() => {});
    }

    isSupported() {
        return typeof navigator !== 'undefined' && 'bluetooth' in navigator;
    }

    async connect(deviceType = 'bike') {
        if (!this.isSupported()) {
            throw new Error('Web Bluetooth not supported in this browser');
        }

        this.deviceType = deviceType;

        // Request device with FTMS service; fall back to acceptAllDevices if needed.
        try {
            this.device = await navigator.bluetooth.requestDevice({
                filters: [{ services: [this.FTMS_SERVICE_UUID] }],
                optionalServices: [this.FTMS_SERVICE_UUID, this.HEART_RATE_SERVICE]
            });
        } catch (primaryError) {
            // Bluefy/Chrome on iOS sometimes requires acceptAllDevices.
            this.device = await navigator.bluetooth.requestDevice({
                acceptAllDevices: true,
                optionalServices: [this.FTMS_SERVICE_UUID, this.HEART_RATE_SERVICE]
            });
        }

        this.device.addEventListener('gattserverdisconnected', () => {
            this.isConnected = false;
            this.onStatus({ type: 'disconnected', device: this.device });
            this._stopSendTimer();
        });

        this.server = await this.device.gatt.connect();
        const ftmsService = await this.server.getPrimaryService(this.FTMS_SERVICE_UUID);

        // Pick the right data characteristic (bike first, then rower).
        this.dataCharacteristic = await this._getCharacteristic(
            ftmsService,
            this.INDOOR_BIKE_DATA_UUID,
            this.ROWER_DATA_UUID
        );
        if (!this.dataCharacteristic) {
            throw new Error('FTMS data characteristic not found');
        }

        // Infer device type based on characteristic.
        if (this.dataCharacteristic.uuid === this.ROWER_DATA_UUID) {
            this.deviceType = 'rower';
        } else if (this.dataCharacteristic.uuid === this.INDOOR_BIKE_DATA_UUID) {
            this.deviceType = deviceType || 'bike';
        }

        await this.dataCharacteristic.startNotifications();
        this._ftmsListener = (event) => this._handleFtmsData(event);
        this.dataCharacteristic.addEventListener('characteristicvaluechanged', this._ftmsListener);

        // Optional heart rate characteristic
        try {
            const hrService = await this.server.getPrimaryService(this.HEART_RATE_SERVICE);
            this.heartRateCharacteristic = await hrService.getCharacteristic(this.HEART_RATE_MEASUREMENT);
            await this.heartRateCharacteristic.startNotifications();
            this._hrListener = (event) => this._handleHeartRate(event);
            this.heartRateCharacteristic.addEventListener('characteristicvaluechanged', this._hrListener);
        } catch (err) {
            // Heart rate is optional; ignore if not present.
            console.debug('Heart rate characteristic not available', err);
        }

        // Start workout on backend
        await this._startBackendSession();

        this.isConnected = true;
        this.onStatus({
            type: 'connected',
            device: this.device,
            deviceType: this.deviceType,
            workoutId: this.workoutId
        });
    }

    async disconnect() {
        try {
            await fetch('/api/webble/end', { method: 'POST' });
        } catch (err) {
            console.warn('Error ending Web BLE session on server', err);
        }

        this._stopSendTimer();

        try {
            if (this.dataCharacteristic && this._ftmsListener) {
                this.dataCharacteristic.removeEventListener('characteristicvaluechanged', this._ftmsListener);
            }
            if (this.heartRateCharacteristic && this._hrListener) {
                this.heartRateCharacteristic.removeEventListener('characteristicvaluechanged', this._hrListener);
            }
            if (this.device && this.device.gatt && this.device.gatt.connected) {
                this.device.gatt.disconnect();
            }
        } catch (err) {
            console.warn('Error during Web BLE disconnect', err);
        } finally {
            this.isConnected = false;
            this.onStatus({ type: 'disconnected' });
        }
    }

    async _getCharacteristic(service, primaryUuid, secondaryUuid) {
        try {
            return await service.getCharacteristic(primaryUuid);
        } catch (e1) {
            if (!secondaryUuid) return null;
            try {
                return await service.getCharacteristic(secondaryUuid);
            } catch (e2) {
                return null;
            }
        }
    }

    _handleFtmsData(event) {
        const view = event.target.value;
        let parsed = {};

        if (this.dataCharacteristic.uuid === this.INDOOR_BIKE_DATA_UUID) {
            parsed = this._parseIndoorBikeData(view);
        } else {
            parsed = this._parseRowerData(view);
        }

        parsed.device_type = this.deviceType;
        parsed.source = 'web_ble';
        parsed.timestamp = new Date().toISOString();

        this.onData(parsed);
        this._scheduleSend(parsed);
    }

    _handleHeartRate(event) {
        const view = event.target.value;
        if (!view || view.byteLength < 2) return;

        const flags = view.getUint8(0);
        const hr16 = (flags & 0x01) === 1;
        const hr = hr16 ? view.getUint16(1, true) : view.getUint8(1);

        const payload = {
            heart_rate: hr,
            source: 'web_ble',
            device_type: this.deviceType,
            timestamp: new Date().toISOString()
        };
        this.onData(payload);
        this._scheduleSend(payload);
    }

    _scheduleSend(payload) {
        this.latestPayload = payload;
        if (this.sendTimer) return;

        this.sendTimer = setTimeout(() => this._flushLatest(), this.sendIntervalMs);
    }

    _stopSendTimer() {
        if (this.sendTimer) {
            clearTimeout(this.sendTimer);
            this.sendTimer = null;
        }
    }

    async _flushLatest() {
        this.sendTimer = null;
        if (!this.latestPayload) return;

        try {
            await fetch('/api/webble/ingest', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(this.latestPayload)
            });
        } catch (err) {
            console.warn('Failed to stream Web BLE data to backend', err);
        }
    }

    async _startBackendSession() {
        const deviceInfo = {
            name: this.device?.name || 'Web Bluetooth Device',
            address: this.device?.id || this.device?.name
        };
        const response = await fetch('/api/webble/start', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ device: deviceInfo, workout_type: this.deviceType })
        });
        const result = await response.json();
        if (!result.success) {
            throw new Error(result.error || 'Unable to start workout');
        }
        this.workoutId = result.workout_id;
    }

    _parseIndoorBikeData(view) {
        const flags = view.getUint16(0, true);
        let index = 2;
        const data = { raw_hex: bufferToHex(view.buffer) };

        if (flags & 0x0001) {
            const speedMps = view.getUint16(index, true) / 100;
            data.speed = parseFloat((speedMps * 3.6).toFixed(2));
            data.speed_mps = speedMps;
            index += 2;
        }
        if (flags & 0x0002) {
            data.average_speed = view.getUint16(index, true) / 100;
            index += 2;
        }
        if (flags & 0x0004) {
            data.instant_cadence = view.getUint16(index, true) / 2;
            index += 2;
        }
        if (flags & 0x0008) {
            data.average_cadence = view.getUint16(index, true) / 2;
            index += 2;
        }
        if (flags & 0x0010) {
            data.total_distance = readUInt24LE(view, index);
            index += 3;
        }
        if (flags & 0x0020) {
            data.resistance_level = view.getInt16(index, true);
            index += 2;
        }
        if (flags & 0x0040) {
            data.instant_power = view.getInt16(index, true);
            index += 2;
        }
        if (flags & 0x0080) {
            data.average_power = view.getInt16(index, true);
            index += 2;
        }
        if (flags & 0x0100) {
            data.total_energy = view.getUint16(index, true);
            index += 2;
        }
        if (flags & 0x0200) {
            data.energy_per_hour = view.getUint16(index, true);
            index += 2;
        }
        if (flags & 0x0400) {
            data.energy_per_minute = view.getUint8(index);
            index += 1;
        }
        if (flags & 0x0800) {
            data.heart_rate = view.getUint8(index);
            index += 1;
        }
        if (flags & 0x1000) {
            data.met = view.getUint16(index, true) / 10;
            index += 2;
        }
        if (flags & 0x2000) {
            data.elapsed_time = view.getUint16(index, true);
            index += 2;
        }
        if (flags & 0x4000) {
            data.remaining_time = view.getUint16(index, true);
            index += 2;
        }

        return data;
    }

    _parseRowerData(view) {
        const flags = view.getUint16(0, true);
        let index = 2;
        const data = { raw_hex: bufferToHex(view.buffer) };

        if (flags & 0x0001) {
            data.stroke_rate = view.getUint16(index, true) / 10;
            data.stroke_count = view.getUint16(index + 2, true);
            index += 4;
        }
        if (flags & 0x0002) {
            data.average_stroke_rate = view.getUint16(index, true) / 10;
            index += 2;
        }
        if (flags & 0x0004) {
            data.total_strokes = view.getUint16(index, true);
            index += 2;
        }
        if (flags & 0x0008) {
            data.instant_pace = view.getUint16(index, true) / 10;
            index += 2;
        }
        if (flags & 0x0010) {
            data.average_pace = view.getUint16(index, true) / 10;
            index += 2;
        }
        if (flags & 0x0020) {
            data.instant_power = view.getInt16(index, true);
            index += 2;
        }
        if (flags & 0x0040) {
            data.average_power = view.getInt16(index, true);
            index += 2;
        }
        if (flags & 0x0080) {
            data.resistance_level = view.getInt16(index, true);
            index += 2;
        }
        if (flags & 0x0100) {
            data.total_energy = view.getUint16(index, true);
            index += 2;
        }
        if (flags & 0x0200) {
            data.energy_per_hour = view.getUint16(index, true);
            index += 2;
        }
        if (flags & 0x0400) {
            data.energy_per_minute = view.getUint8(index);
            index += 1;
        }
        if (flags & 0x0800) {
            data.heart_rate = view.getUint8(index);
            index += 1;
        }
        if (flags & 0x1000) {
            data.met = view.getUint8(index) / 10;
            index += 1;
        }
        if (flags & 0x2000) {
            data.elapsed_time = view.getUint16(index, true);
            index += 2;
        }
        if (flags & 0x4000) {
            data.remaining_time = view.getUint16(index, true);
            index += 2;
        }

        return data;
    }
}

// Helpers
function readUInt24LE(view, offset) {
    return (view.getUint8(offset)) |
        (view.getUint8(offset + 1) << 8) |
        (view.getUint8(offset + 2) << 16);
}

function bufferToHex(buffer) {
    return Array.from(new Uint8Array(buffer))
        .map((b) => b.toString(16).padStart(2, '0'))
        .join('');
}

// Expose globally for page scripts
window.WebBLEFTMSClient = WebBLEFTMSClient;
