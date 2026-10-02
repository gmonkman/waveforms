import ctypes
import sys
import time
import matplotlib.pyplot as plt




# ==========================================
# LIBRARY LOADING
# ==========================================
if sys.platform.startswith("win"):
    dwf = ctypes.cdll.dwf
elif sys.platform.startswith("darwin"):
    dwf = ctypes.cdll.LoadLibrary("/Library/Frameworks/dwf.framework/dwf")
else:
    dwf = ctypes.cdll.LoadLibrary("libdwf.so")

# ==========================================
# CONFIGURATION PARAMETERS
# ==========================================
R_LOAD = 10.0  # Discharge load resistance in Ohms
V_CUTOFF = 10.5  # Cutoff threshold voltage (V1)
PEUKERT_K = 1.20  # Peukert exponent for SLA/AGM battery
RATED_C20_AH = 7.0  # Nominal battery C20 rating in Ah
SAMPLE_INTERVAL = 1.0  # Sampling interval in seconds
DIO_PIN = 0  # Digital I/O pin controlling MOSFET Gate (DIO 0)
BUZZER_PIN = 1  # Digital I/O pin controlling optional Buzzer (DIO 1)

# ==========================================
# DWF API INITIALIZATION
# ==========================================
hdwf = ctypes.c_int()
version = (ctypes.c_char * 32)()
dwf.FDwfGetVersion(version)
print(f"WaveForms SDK Version: {version.value.decode('utf-8')}")

print("Opening Analog Discovery 2...")
# -1 opens the first available Digilent device
if dwf.FDwfDeviceOpen(ctypes.c_int(-1), ctypes.byref(hdwf)) == 0:
    print("Failed to open Analog Discovery 2.")
    sys.exit(1)

# Enable Digital I/O outputs for DIO 0 (MOSFET) and DIO 1 (Buzzer)
io_enable_mask = (1 << DIO_PIN) | (1 << BUZZER_PIN)
dwf.FDwfDigitalIOOutputEnableSet(hdwf, ctypes.c_int(io_enable_mask))


def set_outputs(mosfet_on: bool, buzzer_on: bool):
    """Sets digital output states for MOSFET and Buzzer."""
    mask = 0
    if mosfet_on:
        mask |= 1 << DIO_PIN
    if buzzer_on:
        mask |= 1 << BUZZER_PIN
    dwf.FDwfDigitalIOOutputSet(hdwf, ctypes.c_int(mask))


# Set initial states to OFF
set_outputs(mosfet_on=False, buzzer_on=False)

# Configure Analog In: Scope Channel 1 (Battery +) & Scope Channel 2 (Drain)
for ch in [0, 1]:  # 0 = Channel 1, 1 = Channel 2
    dwf.FDwfAnalogInChannelEnableSet(hdwf, ctypes.c_int(ch), ctypes.c_bool(True))
    dwf.FDwfAnalogInChannelRangeSet(
        hdwf, ctypes.c_int(ch), ctypes.c_double(50.0)
    )  # 50V Range

# Configure instrument without starting acquisition immediately
dwf.FDwfAnalogInConfigure(hdwf, ctypes.c_bool(False), ctypes.c_bool(True))
time.sleep(1.0)


def read_scope_voltages() -> tuple[float, float]:
    """Reads instantaneous voltages from Scope Ch 1 (V_bat) and Ch 2 (V_drain)."""
    # 0 forces immediate status update
    dwf.FDwfAnalogInStatus(hdwf, ctypes.c_bool(True), ctypes.c_int(0))

    v1 = ctypes.c_double()
    v2 = ctypes.c_double()

    dwf.FDwfAnalogInStatusSample(hdwf, ctypes.c_int(0), ctypes.byref(v1))
    dwf.FDwfAnalogInStatusSample(hdwf, ctypes.c_int(1), ctypes.byref(v2))

    return v1.value, v2.value


# ==========================================
# MATPLOTLIB LIVE GRAPH SETUP
# ==========================================
plt.ion()
fig, ax1 = plt.subplots(figsize=(10, 6))

times_min = []
voltages = []
capacities_ah = []

ax2 = ax1.twinx()

(line_v,) = ax1.plot([], [], "b-", linewidth=2, label="Battery Voltage (V1)")
(line_ah,) = ax2.plot([], [], "g--", linewidth=1.5, label="Capacity (Ah)")

ax1.set_xlabel("Elapsed Time (Minutes)")
ax1.set_ylabel("Battery Voltage (V)", color="b")
ax2.set_ylabel("Delivered Capacity (Ah)", color="g")
ax1.set_title("12V Lead-Acid Battery Discharge Curve (Dual Scope Channel)")
ax1.grid(True)
ax1.axhline(
    y=V_CUTOFF,
    color="r",
    linestyle=":",
    linewidth=1.5,
    label=f"Cutoff ({V_CUTOFF}V)",
)

lines = [line_v, line_ah]
labels = [l.get_label() for l in lines]  # noqa
ax1.legend(lines, labels, loc="upper right") # noqa

# ==========================================
# DISCHARGE TEST LOGIC
# ==========================================
print("\n--- Battery Discharge Test Configuration ---")
print(f"Load Resistor:      {R_LOAD} Ohms")
print(f"Cutoff Voltage:     {V_CUTOFF} V")
print(f"Peukert Exponent:   {PEUKERT_K}")
print("--------------------------------------------\n")

v1_init, v2_init = read_scope_voltages()
print(f"Initial Battery Voltage (Ch 1): {v1_init:.2f} V")
print(f"Initial Drain Voltage (Ch 2):   {v2_init:.2f} V")

if v1_init < V_CUTOFF:
    print("Error: Battery voltage is already below cutoff threshold.")
    dwf.FDwfDeviceClose(hdwf)
    sys.exit(1)

input("Press ENTER to start discharge test...")

# Enable load (Drive MOSFET Gate HIGH)
set_outputs(mosfet_on=True, buzzer_on=False)
start_time = time.time()

# Initial state for trapezoidal integration
t_prev = start_time
v1_prev, v2_prev = read_scope_voltages()
i_prev = (v1_prev - v2_prev) / R_LOAD

total_amp_seconds = 0.0

print(
    "\nTime (s) | V_bat (Ch1) | V_drain (Ch2) | V_load (V) | Current (A) | Capacity (Ah)"
)
print("-" * 80)

try:
    while True:
        time.sleep(SAMPLE_INTERVAL)

        t_curr = time.time()
        dt = t_curr - t_prev

        v1_curr, v2_curr = read_scope_voltages()

        # Check cutoff on total battery voltage (Scope 1)
        if v1_curr <= V_CUTOFF:
            set_outputs(mosfet_on=False, buzzer_on=False)
            print(f"\nCutoff reached! Final Battery Voltage: {v1_curr:.2f} V")

            # Audible alert (3 short beeps on DIO 1)
            for _ in range(3):
                set_outputs(mosfet_on=False, buzzer_on=True)
                time.sleep(0.3)
                set_outputs(mosfet_on=False, buzzer_on=False)
                time.sleep(0.2)

            break

        # Calculate current at present sample
        v_load_curr = v1_curr - v2_curr
        i_curr = v_load_curr / R_LOAD

        # Trapezoidal Integration Segment: ((I_prev + I_curr) / 2) * dt
        i_avg_segment = (i_prev + i_curr) / 2.0
        total_amp_seconds += i_avg_segment * dt

        raw_ah = total_amp_seconds / 3600.0
        elapsed = t_curr - start_time
        elapsed_min = elapsed / 60.0

        # Console Logging
        print(
            f"{elapsed:8.1f} | {v1_curr:11.2f} | {v2_curr:13.3f} | {v_load_curr:10.2f} | {i_curr:11.3f} | {raw_ah:13.4f}"
        )

        # Plot Data Arrays
        times_min.append(elapsed_min)
        voltages.append(v1_curr)
        capacities_ah.append(raw_ah)

        # Update Live Plot
        line_v.set_xdata(times_min)
        line_v.set_ydata(voltages)
        line_ah.set_xdata(times_min)
        line_ah.set_ydata(capacities_ah)

        ax1.relim()
        ax1.autoscale_view()
        ax2.relim()
        ax2.autoscale_view()

        fig.canvas.flush_events()
        plt.pause(0.01)

        # Shift state for next iteration
        t_prev = t_curr
        i_prev = i_curr

except KeyboardInterrupt:
    set_outputs(mosfet_on=False, buzzer_on=False)
    print("\nTest manually interrupted by user.")

# Safe shutdown
set_outputs(mosfet_on=False, buzzer_on=False)
dwf.FDwfDeviceClose(hdwf)

plt.ioff()

# ==========================================
# POST-TEST CALCULATIONS & SUMMARY
# ==========================================
total_test_seconds = time.time() - start_time
total_test_hours = total_test_seconds / 3600.0
raw_capacity_ah = total_amp_seconds / 3600.0

if total_test_hours > 0 and raw_capacity_ah > 0:
    i_avg_overall = raw_capacity_ah / total_test_hours

    # Peukert adjustment factor: (20 / t_test)^((k-1)/k)
    peukert_factor = (20.0 / total_test_hours) ** ((PEUKERT_K - 1.0) / PEUKERT_K)
    adjusted_c20_ah = raw_capacity_ah * peukert_factor
    state_of_health = (adjusted_c20_ah / RATED_C20_AH) * 100.0

    print("\n==========================================")
    print("          TEST RESULTS SUMMARY            ")
    print("==========================================")
    print(
        f"Total Duration:            {int(total_test_hours)}h {int((total_test_hours % 1) * 60)}m {int(total_test_seconds % 60)}s"
    )
    print(f"Average Discharge Current: {i_avg_overall:.3f} A")
    print(f"Raw Measured Capacity:     {raw_capacity_ah:.3f} Ah")
    print(f"Peukert Scaling Factor:    {peukert_factor:.3f}x")
    print(f"Estimated C20 Capacity:    {adjusted_c20_ah:.3f} Ah")
    print(f"State of Health (SoH):     {state_of_health:.1f}%")
    print("==========================================")

    plt.show()
else:
    print("\nInsufficient test duration for processing.")
