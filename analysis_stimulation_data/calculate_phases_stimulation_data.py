import os
import numpy as np
import utils as ut
from definitions import SAVE_PATH_DATA_BAROW, DATA_PATH_BAROW, SAVE_PATH_FIGURES_BAROW
import matplotlib.pyplot as plt
import scipy.signal

"""
read in the selected subject data

look at raw and psd to check for artifacts

band-pass filter in theta

calculate instantaneous phase

save to new dicts
"""

data_folder = os.path.join(SAVE_PATH_DATA_BAROW, 'cleaned')
save_folder = os.path.join(SAVE_PATH_DATA_BAROW, 'phase')
plot_subjects = False

# read all files in the data folder
file_list = [f for f in os.listdir(data_folder) if f.startswith('subject')]

frequ_range = 'beta'
if frequ_range == 'theta':
    band = np.array([4., 12.])
elif frequ_range == 'beta':
    band = np.array([12., 30.])
else:
    band = None

# use only a certain time range of the data
lfp_sample_length = -1
lfp_cutoff = 2  # in sec

n_conditions = 3
condition_order = ['rest', 'stim', 'poststim']
mean_vector_length_matrix = np.zeros((len(file_list), n_conditions))

# for every subject file
for sub, sub_file in enumerate(file_list):
    # load data
    d = ut.load_data_analysis(sub_file, data_folder=data_folder)
    print('analysing subject file {}'.format(sub_file))
    subject_number = d['number']
    conditions = d['conditions']

    # make new dict
    subject_dict = dict(lfp_band={}, conditions=conditions, phase={}, lfp_raw={})

    plt.figure(figsize=(10, 5))

    for cond_idx in range(len(conditions)):
        condition = condition_order[cond_idx]
        lfp_raw = d['lfp'][condition]
        fs = d['fs'][condition]

        # pre processing
        # remove power noise
        nyq = fs / 2
        wn = np.array([48, 52]) / nyq
        # noinspection PyTupleAssignmentBalance
        b, a = scipy.signal.butter(3, wn, btype='bandstop')
        lfp_pre = scipy.signal.lfilter(b, a, lfp_raw)

        # low pass filter at 200hz, FIR, window method, numtaps = 250ms = 250 samples
        cut_off_normalized = 200 / nyq
        coefs = scipy.signal.firwin(numtaps=250, cutoff=cut_off_normalized)
        lfp_pre = scipy.signal.filtfilt(coefs, 1., lfp_pre)
        lfp_pre -= lfp_pre.mean()

        # filter
        wn = np.array(band) / fs * 2
        # noinspection PyTupleAssignmentBalance
        b, a = scipy.signal.butter(3, wn, btype='bandpass')
        lfp_band = scipy.signal.filtfilt(b, a, lfp_raw)
        # lfp_band = ut.band_pass_filter(lfp, fs, band=band, plot_response=False)
        # cut the beginning and the end of the time series to avoid artifacts
        lfp_band -= lfp_band.mean()

        # extract instantaneous phase
        # take only a part of the data to save time
        start = 5 * fs  # 5 sec offset
        stop = start + 240 * fs  # take 4 minutes of recording maximum
        if stop > lfp_band.size:
            stop = -1
        analystic_signal = scipy.signal.hilbert(lfp_band[start:stop])

        # look at the spectogram to select time periods of higher beta
        # t, burst_mask = ut.select_time_periods_of_high_power(data=lfp_pre[start:stop], band=band)
        burst_mask = np.logical_not(np.zeros_like(lfp_pre[start:stop]))
        # plt.plot(t, lfp_pre)
        # plt.fill_between(t, np.min(lfp_pre), np.max(lfp_pre), where=burst_mask, alpha=.4, color='red')
        # plt.show()

        # calculate the phase only on the beta burst periods
        phase = np.unwrap(np.angle(analystic_signal[burst_mask]))

        # calculate circular mean length
        circular_mean_vector = np.mean(np.exp(1j * phase))
        circ_mean_angle = np.angle(circular_mean_vector)
        circular_mean_length = np.abs(circular_mean_vector)
        mean_vector_length_matrix[sub, cond_idx] = circular_mean_length

        # save to dict
        subject_dict['phase'][condition] = phase
        subject_dict['lfp_band'][condition] = lfp_band
        subject_dict['fs'] = fs

        # save raw data
        subject_dict['lfp_raw'][condition] = lfp_raw[start:stop]

        # plot
        phase_data_to_use = phase[start:stop]
        hist, bins = np.histogram(phase_data_to_use, bins=60)
        radii = hist
        theta = 0.5 * (bins[:-1] + bins[1:])
        ax = plt.subplot(1, 3, cond_idx + 1, projection='polar')
        bars = ax.bar(theta, radii)
        ax.set_rticks(np.round(np.linspace(0, np.max(radii), 3), 4))
        plt.title('{}, circ mean={}'.format(condition, np.round(circular_mean_length, 4)))

    # start = 1000
    # stop = start + 5000
    # plt.figure(figsize=(10, 7))
    # plt.subplot(2, 1, 1)
    # plt.plot(lfp[start:stop])
    # plt.plot(lfp_band[start:stop])
    # # plt.plot(lfp_broad[start:stop])
    #
    # # plot phase
    # plt.subplot(2, 1, 2)
    # plt.plot(phase[start:stop])
    # plt.show()

    plt.suptitle('Instantaneous phase distribution')
    filename_figure = '{}_subject_{}_phase_histogra.pdf'.format(frequ_range, subject_number)
    if plot_subjects:
        plt.savefig(os.path.join(SAVE_PATH_FIGURES_BAROW, 'phase', filename_figure))
    # plt.show()
    plt.close()

    # plot the raw data and theta and beta waves
    # plt.figure(figsize=(10, 7))
    # plt.suptitle('{}sec lfp raw data with pure theta and beta waves'.format(lfp_sample_length))
    # # determine theta and beta stuff
    # fs = subject_dict['fs']
    # n_samples = lfp_sample_length * fs
    # n_cycles_theta = lfp_sample_length * 6
    # samples_theta = np.linspace(0, n_cycles_theta * 2 * np.pi, n_samples)
    # n_cycles_beta = lfp_sample_length * 20
    # samples_beta = np.linspace(0, n_cycles_beta * 2 * np.pi, n_samples)
    # samples = np.arange(n_samples)
    #
    # for i, c in enumerate(conditions):
    #     plt.subplot(3, 1, i + 1)
    #     # plot raw data
    #     lfp_raw_sample = subject_dict['lfp_raw'][c]
    #     plt.plot(samples, lfp_raw_sample)
    #     amplitude = 0.2 * abs(np.max(lfp_raw_sample) - np.min(lfp_raw_sample))
    #     # plot pure sinusoidal theta and beta
    #     plt.plot(samples, amplitude * np.sin(samples_theta), label='theta', alpha=.7)
    #     plt.plot(samples, amplitude * np.sin(samples_beta), label='beta', alpha=.7)
    #     plt.title(c)
    #     plt.ylabel('raw lfp [ $\mu V$ ]')
    #     if i < len(conditions) - 1:
    #         plt.xticks([], [])
    #
    # plt.xlabel('time [ms]')
    # filename_figure = '{}_subject_{}_rawLFP_vs_sinusoidal{}s.pdf'.format(frequ_range, subject_number, seconds_str)
    # plt.savefig(os.path.join(SAVE_PATH_FIGURES_BAROW, 'phase', filename_figure))
    # # plt.show()
    # plt.close()

# plot overview over mean phase vector
plt.figure(figsize=(8, 5))
plt.title('Circular mean amplitude of the phases')
plt.plot(mean_vector_length_matrix.mean(axis=0), '-o', linewidth=2)
plt.plot(mean_vector_length_matrix.T, alpha=.4)
plt.legend(np.hstack((['mean'], np.arange(1, 17))), loc=0, prop={'size': 7})
plt.xticks(np.arange(3), condition_order)
plt.ylabel('mean amplitude')
filename_figure = '{}_mean_phase_vector_amplitude_IIR_all.pdf'.format(frequ_range)
plt.savefig(os.path.join(SAVE_PATH_FIGURES_BAROW, 'phase', filename_figure))
plt.show()
plt.close()
