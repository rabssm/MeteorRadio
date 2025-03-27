# SMP to wav converter

import argparse
import numpy as np
import scipy.io.wavfile as wav
import datetime


# Main program
if __name__ == "__main__":


    # construct the argument parser and parse the arguments
    ap = argparse.ArgumentParser(description='Convert an SMP*.npz file to an audio wav file')
    ap.add_argument("smp_file", type=str, help="SMP .npz file")

    args = vars(ap.parse_args())

    file_name = smp_file = args['smp_file']

    npz_data = np.load(smp_file)
    samples = npz_data['samples']
    try:
        centre_freq = npz_data['centre_freq']
        sample_rate = npz_data['sample_rate']
        obs_time = datetime.datetime.strptime(str(npz_data['obs_time']), "%Y-%m-%d %H:%M:%S.%f")
    except Exception as e :
        print(e)


    # Save to file as 16-bit signed single-channel audio samples
    # Note that we can throw away the imaginary part of the IQ sample data for USB
    audio_filename = file_name.replace("SMP", "AUD")
    audio_filename = audio_filename.replace("npz", "raw")
    wav_filename = audio_filename.replace("raw", "wav")
    # print("Saving", audio_filename)
    # Scale samples to adjust volume
    # x7 = samples * (10000 / np.max(np.abs(samples)))
    # x7.astype("int16").tofile(audio_filename)

    # Convert to 16-bit PCM format (WAV format requirement)
    audio_real = np.real(samples).astype(np.float32)
    audio_data = (audio_real * 32767).astype(np.int16)

    # Save as WAV file
    wav.write(wav_filename, int(sample_rate), audio_data)

    print("WAV audio file saved successfully: ", wav_filename)
