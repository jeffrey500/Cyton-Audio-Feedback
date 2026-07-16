import time
import numpy as np
import sounddevice as sd
from brainflow import DetrendOperations
from brainflow.board_shim import BoardShim, BrainFlowInputParams, BoardIds
from brainflow.data_filter import DataFilter, WindowOperations, FilterTypes

BLINK_THRESHOLD = 200 #in milivolts
CYTON_PORT = "/dev/cu.usbserial-DP05IVPL"


def play_blink_sound(sampling_freq = 44100, duration = 0.4, freq = 1000):
    #construct the sound wave
    t = np.linspace(0, duration, int(sampling_freq * duration), False)
    tone = np.sin(freq * 2 * np.pi * t)

    sd.play(tone, sampling_freq)

def play_alpha_sound(sampling_freq = 44100, duration = 0.4, freq = 700):
    #construct the sound wave
    t = np.linspace(0, duration, int(sampling_freq * duration), False)
    tone = np.sin(freq * 2 * np.pi * t)

    sd.play(tone, sampling_freq)

#find alpha threshold that is 60% of the difference of the eyes open vs closed states
def calibrate_alpha(board):
    #find baseline
    print("Keep eyes OPEN for 10 seconds starting in 3 seconds")
    for i in range(3, 0, -1):
        print(f"{i}...")
        time.sleep(1)
    print("recording now...")
    time.sleep(10)
    data_open = board.get_board_data(250 * 10)  # 10 seconds of data
    ch_open = data_open[1, :]
    DataFilter.detrend(ch_open, DetrendOperations.LINEAR.value)
    psd_open = DataFilter.get_psd(ch_open, 250, WindowOperations.HANNING.value)
    baseline_power = DataFilter.get_band_power(psd_open, 8.0, 12.0)

    print("Keep eyes CLOSED for 10 seconds starting in 3 seconds")
    for i in range(3, 0, -1):
        print(f"{i}...")
        time.sleep(1)
    print("recording now...")
    time.sleep(10)
    data_open = board.get_board_data(250 * 10)  # 10 seconds of data
    ch_open = data_open[1, :]
    DataFilter.detrend(ch_open, DetrendOperations.LINEAR.value)
    psd_open = DataFilter.get_psd(ch_open, 250, WindowOperations.HANNING.value)
    peak_power = DataFilter.get_band_power(psd_open, 8.0, 12.0)

    print(f"\nCalibration Complete.")
    print(f"Baseline (Open): {baseline_power:.2f}")
    print(f"Peak (Closed): {peak_power:.2f}")

    alpha_thres = baseline_power + (0.6 * (peak_power - baseline_power))
    print(f"The alpha threshold is: {alpha_thres}")
    return alpha_thres

def main():
    #setup cyton board object
    BoardShim.enable_dev_board_logger()
    params = BrainFlowInputParams()
    params.serial_port = CYTON_PORT
    board_id = BoardIds.CYTON_BOARD.value
    board = BoardShim(BoardIds.CYTON_BOARD.value, params)

    eeg_channels = BoardShim.get_eeg_channels(board_id)
    eeg_ch1 = eeg_channels[0]

    #connect to board
    print("Connecting to the Cyton Board")
    board.prepare_session()
    board.start_stream()
    print("Connected to Cyton Board")

    previous_time = time.time()

    try:
        ALPHA_THREASHOLD = calibrate_alpha(board)
        # ALPHA_THREASHOLD = 99999

        #wait until window has at least 250 points of data (one second)
        while board.get_board_data_count() < 256:
            time.sleep(0.2)

        while True:
            time.sleep(0.02)

            #Proccess the most recent 250 samples of data for psd (sliding window)
            data = board.get_current_board_data(250)
            ch1 = data[eeg_ch1][:]

            #PSD and filtering
            DataFilter.detrend(ch1, DetrendOperations.LINEAR.value)
            DataFilter.perform_bandstop(ch1, 250, 58.0, 62.0, 4, FilterTypes.BUTTERWORTH.value, 0)
            DataFilter.perform_bandpass(ch1, 250, 1.0, 50.0, 4, FilterTypes.BUTTERWORTH.value, 0)
            psd_tuple = DataFilter.get_psd(ch1, 250, WindowOperations.HANNING.value)
            alpha_power = DataFilter.get_band_power(psd_tuple, 8.0, 12.0)

            ch1_blink = ch1[-50:]

            #lockout for the blink sound
            max_amplitude = np.max(ch1_blink) - np.min(ch1_blink)
            if max_amplitude > BLINK_THRESHOLD:
                if time.time() - previous_time > 1:
                    play_blink_sound()
                    previous_time = time.time()

            #lockout for the alpha sound
            if alpha_power > ALPHA_THREASHOLD:
                if time.time() - previous_time > 0.5:
                    play_alpha_sound()
                    previous_time = time.time()

            print(f"Alpha Power: {alpha_power} |", f"Amplitude: {max_amplitude} uV")

    except:
        print("Stream Interrupted")

    finally:
        if board.is_prepared():
            board.stop_stream()
            board.release_session()
            print("Stream Terminated")

if __name__ == "__main__":
    for _ in range(3):
        play_blink_sound()
        time.sleep(1)

    main()