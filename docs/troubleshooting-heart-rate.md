# Heart Rate Troubleshooting Guide

## Issue: Heart Rate Values Don't Match Bike Display

If you notice that the heart rate values recorded in the Rogue Garmin Bridge application are different from what's displayed on your bike, this is a common issue with several possible causes.

### Common Scenarios

#### Scenario 1: App shows lower HR than bike display
- **App shows**: ~70-80 BPM
- **Bike shows**: ~120+ BPM
- **Cause**: The bike is not transmitting heart rate data via FTMS, or is transmitting from a different source

#### Scenario 2: App shows 0 or no HR data
- **App shows**: 0 BPM or no heart rate
- **Bike shows**: Normal heart rate values
- **Cause**: No heart rate sensor connected to FTMS transmission

#### Scenario 3: Intermittent HR spikes
- **App shows**: Mostly low values with occasional correct spikes
- **Bike shows**: Consistent heart rate
- **Cause**: Intermittent heart rate sensor connection

### Root Causes

#### 1. Multiple Heart Rate Sources
Many bikes have multiple ways to detect heart rate:
- **Built-in handlebar sensors**: Contact sensors on the handlebars
- **Wireless chest strap**: ANT+ or Bluetooth chest strap
- **Wrist-based monitors**: Connected fitness watches
- **External HR monitors**: Separate Bluetooth/ANT+ devices

The bike display might show data from one source (e.g., handlebar sensors) while FTMS transmits from another source (e.g., wireless chest strap).

#### 2. Heart Rate Sensor Not Paired for FTMS
The bike might have a heart rate sensor connected for display purposes, but not configured to transmit via FTMS/Bluetooth.

#### 3. FTMS Protocol Limitations
Some bikes don't properly implement heart rate transmission in their FTMS protocol, even if they display heart rate locally.

### Troubleshooting Steps

#### Step 1: Check Heart Rate Sensor Connection
1. **Verify sensor is connected to bike**:
   - Check bike settings/menu for heart rate sensor status
   - Ensure sensor is properly paired with the bike
   - Test that bike display shows correct heart rate

2. **Check sensor battery**:
   - Replace battery in chest strap or HR monitor
   - Ensure good contact with skin (for chest straps)

#### Step 2: Configure Heart Rate for FTMS
1. **Check bike FTMS settings**:
   - Look for "Bluetooth" or "FTMS" settings in bike menu
   - Ensure heart rate is enabled for Bluetooth transmission
   - Some bikes have separate settings for "display HR" vs "transmit HR"

2. **Pair HR sensor directly with bike for FTMS**:
   - Some bikes require HR sensor to be paired specifically for FTMS
   - Check bike manual for FTMS heart rate configuration

#### Step 3: Use External Heart Rate Monitor
If the bike doesn't properly transmit heart rate via FTMS:

1. **Connect HR monitor directly to computer**:
   - Use a Bluetooth chest strap that can connect directly to your computer
   - Pair it with the Rogue Garmin Bridge application
   - This bypasses the bike's FTMS limitations

2. **Recommended HR monitors**:
   - Polar H10 (Bluetooth + ANT+)
   - Wahoo TICKR (Bluetooth + ANT+)
   - Garmin HRM-Pro (Bluetooth + ANT+)

#### Step 4: Verify FTMS Data
1. **Check application logs**:
   - Look for heart rate warnings in the logs
   - The app will warn if heart rate is consistently low
   - Check if heart rate flag is present in FTMS data

2. **Monitor raw FTMS data**:
   - The logs show raw heart rate bytes from FTMS
   - Compare with bike display to identify discrepancies

### Bike-Specific Solutions

#### Rogue Bikes
- Check if bike has heart rate sensor pairing mode
- Some models require holding specific buttons to enable FTMS heart rate
- Consult bike manual for Bluetooth/FTMS configuration

#### General Indoor Bikes
- Look for "App connectivity" or "Third-party app" settings
- Enable all data transmission options
- Some bikes have separate ANT+ and Bluetooth settings

### Workarounds

#### Option 1: Use Bike Display Values
- Manually record heart rate from bike display
- Use bike's built-in workout tracking
- Export data from bike's app if available

#### Option 2: Dual Heart Rate Monitoring
- Use external HR monitor for accurate data in Rogue Garmin Bridge
- Continue using bike display for real-time feedback during workout

#### Option 3: Post-Workout Data Correction
- Record workout with available data
- Manually edit FIT files to add correct heart rate data
- Use third-party tools to merge heart rate data

### Technical Details

#### FTMS Heart Rate Flag
The FTMS protocol includes a heart rate flag (bit 9) that indicates if heart rate data is present. If this flag is not set, no heart rate data will be transmitted.

#### Heart Rate Data Format
Heart rate in FTMS is transmitted as a single byte (0-255 BPM). Values outside the normal range (40-220 BPM) are considered invalid.

#### Data Validation
The application validates heart rate data and will:
- Remove values below 40 BPM or above 220 BPM
- Detect statistical outliers and replace with median values
- Warn about consistently low heart rate values

### Getting Help

If you continue to have heart rate issues:

1. **Check the logs** for heart rate warnings and FTMS data
2. **Test with different heart rate sensors** to isolate the issue
3. **Consult your bike manual** for FTMS/Bluetooth configuration
4. **Contact bike manufacturer** if FTMS heart rate should be supported
5. **Report the issue** with logs and bike model information

### Prevention

- **Regular sensor maintenance**: Clean chest straps, replace batteries
- **Proper sensor placement**: Ensure good skin contact for chest straps
- **Firmware updates**: Keep bike firmware updated for FTMS improvements
- **Test before workouts**: Verify heart rate is working before starting long sessions