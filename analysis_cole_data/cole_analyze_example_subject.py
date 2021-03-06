import os
import matplotlib.pyplot as plt
import numpy as np
import utils as ut
from definitions import SAVE_PATH_FIGURES_BAROW, SAVE_PATH_DATA_BAROW
import scipy.signal
from scipy import signal

"""
read raw data and filter like in the Cole paper. Then analyze the waveform like in the cole paper. 
Does it make a difference to take the values of the raw data for peak analysis versus to take the filtered values?  
"""

path_to_file = '/Users/Jan/Dropbox/Master/LR_Kuehn/data/example_Cole.mat'
save_folder = os.path.join(SAVE_PATH_DATA_BAROW, 'analysis')

d = scipy.io.loadmat(path_to_file)

# make new entries in the dict
result_dict = dict(sharpness={}, steepness={}, phase={})
frequ_range = 'beta'
result_dict['frequ_range'] = frequ_range


# define the list of conditions
conditions = ['subj11_before_DBS', 'subj11_during_DBS', 'subj11_after_DBS']
# get the sampling rate
fs = d['fsample'][0][0]

# look at the psd
#  f, psd = ut.calculate_psd(y=d['subj11_before_DBS'].squeeze(), fs=fsample, window_length=1024)
# plt.plot(f, psd)
# plt.show()

plt.figure(figsize=(10, 7))
raw_sample_length = 2  # in sec

for i, condition in enumerate(conditions):
    print('Condition {}'.format(condition))
    result_dict['sharpness'][condition] = {}
    result_dict['steepness'][condition] = {}
    result_dict['phase'][condition] = {}

    # remove line noise
    lfp_raw = d[condition].squeeze()

    # pre processing
    # remove power noise
    nyq = fs / 2
    wn = np.array([58, 62]) / nyq
    # noinspection PyTupleAssignmentBalance
    b, a = scipy.signal.butter(3, wn, btype='bandstop')
    lfp_pre = scipy.signal.lfilter(b, a, lfp_raw)

    # low pass filter at 200hz, FIR, window method, numtaps = 250ms = 250 samples
    cut_off_normalized = 200 / nyq
    coefs = scipy.signal.firwin(numtaps=250, cutoff=cut_off_normalized)
    lfp_pre = scipy.signal.filtfilt(coefs, 1., lfp_pre)
    lfp_pre -= lfp_pre.mean()

    # filter in beta range
    wn = np.array([13, 30]) / fs * 2
    # noinspection PyTupleAssignmentBalance
    b, a = scipy.signal.butter(2, wn, btype='bandpass')
    lfp_band= scipy.signal.filtfilt(b, a, lfp_pre)
    # lfp_band2 = ut.band_pass_filter(y=lfp_raw, fs=fs, band=[13, 30], plot_response=False)
    lfp_band = lfp_band[250:-250]
    lfp_band -= lfp_band.mean()

    # identify time points of rising and falling zero-crossings:
    zeros_rising, zeros_falling, zeros = ut.find_rising_and_falling_zeros(lfp_band)

    # find the peaks in between the zeros, USING THE RAW DATA!
    analysis_lfp = lfp_pre
    peaks, troughs, extrema = ut.find_peaks_and_troughs_cole(analysis_lfp,
                                                             zeros=zeros,
                                                             rising_zeros=zeros_rising,
                                                             falling_zeros=zeros_falling)

    # debug plot
    # upto = 10
    # zero_idx = zeros[upto]
    # plt.close()
    # plt.figure(figsize=(15, 5))
    # plt.plot(lfp_pre[:zero_idx])
    # plt.plot(lfp_band[:zero_idx], 'o')
    # plt.plot(zeros[:upto], lfp_band[zeros][:upto], 'go')
    # plt.axhline(0)
    # plt.plot(peaks[:int(upto/2)], lfp_pre[peaks][:int(upto/2)], 'ro')
    # plt.plot(troughs[:int(upto/2)], lfp_pre[troughs][:int(upto/2)], 'bo')
    # plt.show()

    # calculate peak sharpness:
    peak_sharpness = ut.calculate_peak_sharpness(analysis_lfp, peaks, fs=fs)
    trough_sharpness = ut.calculate_peak_sharpness(analysis_lfp, troughs, fs=fs)
    mean_peak_sharpness = np.mean(peak_sharpness)
    mean_trough_sharpness = np.mean(trough_sharpness)
    # extrema sharpness ratio, from the paper
    esr = np.max([mean_peak_sharpness / mean_trough_sharpness, mean_trough_sharpness / mean_peak_sharpness])

    # calculate the steepness
    rise_steepness, fall_steepness = ut.calculate_rise_and_fall_steepness(analysis_lfp, extrema)
    mean_rise_steepness = np.mean(rise_steepness)
    mean_fall_steepness = np.mean(fall_steepness)
    # rise decay steepness ratio
    rdsr = np.max([mean_rise_steepness / mean_fall_steepness, mean_fall_steepness / mean_rise_steepness])

    # calculate the circular mean of the phases of the bandpass filtered signal
    analystic_signal = scipy.signal.hilbert(lfp_band)

    phase = np.unwrap(np.angle(analystic_signal))
    circular_mean_vector = np.mean(np.exp(1j * phase))
    circ_mean_angle = np.angle(circular_mean_vector)
    circ_mean_length = np.abs(circular_mean_vector)

    # filter in theta and beta to compare to pure sinusoidal shapes
    start = 5 * fs  # 5 sec offset
    stop = start + raw_sample_length * fs  # take 5 seconds only
    lfp_raw_sample = lfp_pre[start:stop]

    result_dict['phase'][condition]['lfp_raw_sample'] = lfp_raw_sample

    # save to dict
    result_dict['sharpness'][condition]['trough_sharpness'] = trough_sharpness
    result_dict['sharpness'][condition]['peak_sharpness'] = peak_sharpness
    result_dict['sharpness'][condition]['trough_average'] = mean_trough_sharpness
    result_dict['sharpness'][condition]['peak_average'] = mean_peak_sharpness
    result_dict['sharpness'][condition]['esr'] = esr

    result_dict['steepness'][condition]['rise'] = rise_steepness
    result_dict['steepness'][condition]['fall'] = fall_steepness
    result_dict['steepness'][condition]['rise_average'] = mean_rise_steepness
    result_dict['steepness'][condition]['fall_average'] = mean_fall_steepness
    result_dict['steepness'][condition]['rdsr'] = rdsr

    result_dict['phase'][condition]['circular_mean_length'] = circ_mean_length
    result_dict['phase'][condition]['circular_mean_angle'] = circ_mean_angle



    # plot figure 1BC from the paper: histograms of the peak and trough values
    plt.subplot(1, 3, i + 1)
    plt.title(condition)
    troughs = result_dict['sharpness'][condition]['trough_sharpness']
    hist_troughs, bins = np.histogram(np.log(troughs), bins=30)
    plt.hist(np.log(troughs), label='trough', alpha=.5, bins=bins)
    plt.hist(np.log(result_dict['sharpness'][condition]['peak_sharpness']), label='peak', alpha=.5, bins=bins)
    plt.xlabel('log sharpness')

plt.legend()
plt.savefig(os.path.join(SAVE_PATH_FIGURES_BAROW, 'sharpness', 'cole_example_f1BC.pdf'))

# plot figure 1D: esr over conditions
plt.figure(figsize=(8, 5))
plt.subplot(2, 1, 1)
plt.title('Extrema sharpness ratio (ESR) over conditions')
plt.plot([result_dict['sharpness'][c]['esr'] for c in conditions], '-o', label='esr')
plt.ylabel('ESR and circular mean')
plt.xticks([], [])
plt.subplot(2, 1, 2)
plt.title('circurlar mean of phases over conditions')
plt.plot([result_dict['phase'][c]['circular_mean_length'] for c in conditions], '-o', label='circular mean')
plt.ylabel('ESR and circular mean')
plt.xticks(range(3), conditions)
plt.savefig(os.path.join(SAVE_PATH_FIGURES_BAROW, 'cole_example_f1D.pdf'))

# plot the raw data and theta and beta waves
plt.figure(figsize=(10, 7))
plt.suptitle('{}sec lfp raw data with pure theta and beta waves'.format(raw_sample_length))
# determine theta and beta stuff
n_samples = raw_sample_length * fs
n_cycles_theta = raw_sample_length * 6
samples_theta = np.linspace(0, n_cycles_theta * 2 * np.pi, n_samples)
n_cycles_beta = raw_sample_length * 20
samples_beta = np.linspace(0, n_cycles_beta * 2 * np.pi, n_samples)
samples = np.arange(n_samples)

for i, c in enumerate(conditions):
    plt.subplot(3, 1, i + 1)
    # plot raw data
    lfp_raw_sample = result_dict['phase'][c]['lfp_raw_sample']
    plt.plot(samples, lfp_raw_sample)
    amplitude = 0.2 * abs(np.max(lfp_raw_sample) - np.min(lfp_raw_sample))
    # plot pure sinusoidal theta and beta
    plt.plot(samples, amplitude * np.sin(samples_theta), label='theta', alpha=.7)
    plt.plot(samples, amplitude * np.sin(samples_beta), label='beta', alpha=.7)
    plt.title(c)
    plt.ylabel('raw lfp [ $\mu V$ ]')
    if i < len(conditions) - 1:
        plt.xticks([], [])

plt.xlabel('time [ms]')
plt.savefig(os.path.join(SAVE_PATH_FIGURES_BAROW, 'cole_example_rawLFP_vs_sinusoidal.pdf'))
plt.show()

# save data
# ut.save_data(data_dict=result_dict,
#              filename='cole_example_subject_sharpness_steepness_{}.p'.format(frequ_range),
#              folder=save_folder)

