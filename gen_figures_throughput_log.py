#! /usr/bin/env python3

import csv
import matplotlib.pyplot as plt
import numpy as np
import re
from gen_figures_regular import FIGURE_SIZE, FIGURES_FOLDER, FONT_OPTIONS, nice_driver_name, nice_mode_name, nice_suffix, sort_blocksizes
from os import listdir
from os.path import basename, join


JSON_FOLDER = 'json_throughput_log'
REGEX_GROUPS = ['mode', 'blocksize', 'driver', 'disk', 'suffix']
LINEWIDTH = 0.5
LEGEND_LINEWIDTH = 1


def observed_group_vals(directory):
    '''
    parses the filenames of all log files in the given directory and returns all observed regex group values
    
    ### parameters
    - directory: the directory in which to search for log files

    ### return value
    a dictionary where the key is one of REGEX_GROUPS and the value is a set of all observed values of this group.
    calling `filename_from_group_vals()` with all combinations of observed group values should give all filenames
    in `directory`.
    
    an example return value could look like this:
    ```
    {
        'mode': { 'seqread', 'randread', ... },
        'blocksize': { '8k', '16k', ... },
        ...
    }
    ```
    '''

    filename_regex = re.compile(
        '(?P<mode>[^_]+)_(?P<blocksize>[^_]+)_(?P<driver>[^_]+)_(?P<disk>[^_]+)(?P<suffix>.*)_bw.1.log'
    )
    filter_lambda = lambda filename: filename.endswith('.log')
    filenames = list(filter(filter_lambda, listdir(directory)))
    group_vals = dict(map(lambda g: (g, set()), REGEX_GROUPS))

    for filename in filenames:
        match = filename_regex.match(filename)
        for group in REGEX_GROUPS:
            group_vals[group].add(match.group(group))

    return group_vals


def filename_from_group_vals(mode, blocksize, driver, disk, suffix):
    '''
    reconstructs a filename from its regex group values
    '''
    return f'{mode}_{blocksize}_{driver}_{disk}{suffix}_bw.1.log'


def get_throughput_data(filename):
    '''
    reads timestamps and throughput values from a bw.log file.
    
    returns a tuple of the timestamps and the throughput values.
    '''
    with open(filename, 'r', newline='') as csvfile:
        reader = csv.reader(csvfile)
        map_func = lambda line: [int(line[0]), int(line[1])]
        mapped_vals = map(map_func, reader)
        take_every_nth = 1
        arr = np.array(list(mapped_vals))[::take_every_nth]
        timestamps, throughput = arr[:, 0] / 1000, arr[:, 1] / 1024
        return timestamps, throughput


def throughput_statistics(throughput_data):
    mean = np.mean(throughput_data)
    median = np.median(throughput_data)
    stddev = np.std(throughput_data)
    min = np.min(throughput_data)
    max = np.max(throughput_data)
    print(f'\t{mean=}')
    print(f'\t{median=}')
    print(f'\t{stddev=}')
    print(f'\t{min=}')
    print(f'\t{max=}')


def generate_throughput_graphs(timestamps, throughput_data, drivers, blocksize, mode, disk, suffix, ax):
    '''
    TODO
    '''
    blocksize = blocksize[:-1]
    for ts, driver, data in zip(timestamps, drivers, throughput_data):
        ax.plot(ts, data, label=nice_driver_name(driver), linewidth=LINEWIDTH)
    legend = ax.legend(loc='upper right', frameon=False)
    plt.setp(legend.get_lines(), linewidth=LEGEND_LINEWIDTH)
    suffix = nice_suffix(suffix)
    title = f'{nice_mode_name(mode)} over time ({blocksize} KiB blocks'
    title += f', {suffix})' if suffix != '' else ')'
    ax.set_title(title)
    ax.set_xlabel('Time [s]')
    ax.set_ylabel('Read rate [MiB/s]')


def generate_boxplots(throughput_data, drivers, blocksize, mode, disk, suffix, ax):
    blocksize = blocksize[:-1]
    drivers = list(map(nice_driver_name, drivers))
    flierprops = dict(marker='.', markerfacecolor='black', linestyle='none', markersize=3)
    ax.boxplot(throughput_data, labels=drivers, flierprops=flierprops)
    suffix = nice_suffix(suffix)
    title = f'Distribution of {nice_mode_name(mode).lower()} ({blocksize} KiB blocks'
    title += f', {suffix})' if suffix != '' else ')'
    ax.set_title(title)
    ax.set_ylabel('Read rate [MiB/s]')


def handle_directory(directory):
    '''
    generates figures for all json files in a directory.
    a separate figure is generated for all combinations of suffixes and modes.
    '''
    group_vals = observed_group_vals(directory)
    modes = list(sorted(group_vals['mode']))
    disks = list(sorted(group_vals['disk']))
    try:
        group_vals['driver'].remove('unenc')
    except:
        pass
    drivers = list(sorted(group_vals['driver']))
    blocksizes = sort_blocksizes(list(group_vals['blocksize']))

    for suffix in group_vals['suffix']:
        if ('logmsec32' not in suffix) or ('iodepth16' in suffix):
            continue
        for mode in modes:
            for bs in blocksizes:
                if bs != '32k':
                    continue
                figure_path = join(FIGURES_FOLDER, f'{basename(directory)}_{mode}_{bs}{suffix}')
                figure_path_boxplot = f'{figure_path}_boxplot.pdf'
                figure_path += '.pdf'
                fig = plt.figure(figsize=FIGURE_SIZE)
                axes = fig.subplots(len(disks), 1)
                fig_boxplot = plt.figure(figsize=FIGURE_SIZE)
                axes_boxplot = fig_boxplot.subplots(len(disks), 1)
                print(f'generating figure \'{figure_path}\'')

                for i, disk in enumerate(disks):
                    throughput_data = [None for _ in range(len(drivers))]
                    timestamps = [None for _ in range(len(drivers))]
                    for ii, driver in enumerate(drivers):
                        log_filename = filename_from_group_vals(mode, bs, driver, disk, suffix)
                        log_path = join(directory, log_filename)
                        timestamps[ii], throughput_data[ii] = get_throughput_data(log_path)

                    ax = axes[i] if len(disks) > 1 else axes
                    ax_boxplot = axes_boxplot[i] if len(disks) > 1 else axes_boxplot
                    generate_throughput_graphs(timestamps, throughput_data, drivers, bs, mode, disk, suffix, ax)
                    generate_boxplots(throughput_data, drivers, bs, mode, disk, suffix, ax_boxplot)
                    ax.set_ylim(bottom=0)
                    ax_boxplot.set_ylim(bottom=0)

                fig.tight_layout()
                fig_boxplot.tight_layout()
                fig.savefig(figure_path, bbox_inches='tight')
                fig_boxplot.savefig(figure_path_boxplot, bbox_inches='tight')
                plt.close(fig)
                plt.close(fig_boxplot)


if __name__ == '__main__':
    plt.rc('font', **FONT_OPTIONS)
    handle_directory(JSON_FOLDER)
