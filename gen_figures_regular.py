#! /usr/bin/env python3

import json
import matplotlib.pyplot as plt
import numpy as np
import os.path
import re
from os import listdir
from os.path import basename, isdir, join


JSON_FOLDER = 'json'
FIGURES_FOLDER = 'figures'
REGEX_GROUPS = ['mode', 'blocksize', 'driver', 'disk', 'suffix', 'number']


def observed_group_vals(directory):
    '''
    parses the filenames of all json files in the given directory and returns all observed regex group values
    
    ### parameters
    - directory: the directory in which to search for json files

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

    # the suffix group uses the .*? notation to make it non-greedy, else the number group is always None
    # because the suffix greedily takes its content
    filename_regex = re.compile(
        '(?P<mode>[^_]+)_(?P<blocksize>[^_]+)_(?P<driver>[^_]+)_(?P<disk>[^_]+)(?P<suffix>.*?)(_(?P<number>\\d+))?.json'
    )
    filter_lambda = lambda filename: filename.endswith('.json')
    filenames = list(filter(filter_lambda, listdir(directory)))
    group_vals = dict(map(lambda g: (g, set()), REGEX_GROUPS))

    for filename in filenames:
        match = filename_regex.match(filename)
        for group in REGEX_GROUPS:
            group_vals[group].add(match.group(group))

    return group_vals


def filename_from_group_vals(mode, blocksize, driver, disk, suffix, number=''):
    '''
    reconstructs a filename from its regex group values
    '''
    filename = f"{mode}_{blocksize}_{driver}_{disk}{suffix}"
    if number != '':
        filename += '_' + number
    return filename + '.json'


def nice_mode_name(mode):
    if mode == 'seqread':
        return 'Sequential reading'
    elif mode == 'randread':
        return 'Random-access reading'


def nice_disk_name(disk):
    if disk == 'ssd':
        return 'SSD'
    elif disk == 'hdd':
        return 'HDD'


def nice_driver_name(driver):
    if driver == 'bitlocker':
        return 'BitLocker'
    elif driver == 'veracrypt':
        return 'VeraCrypt'
    elif driver == 'luks2flt-optimizedv2':
        return 'luks2flt (optimized)'
    elif driver == 'luks2flt-beforemoreopts':
        return 'luks2flt'
    elif driver == 'nullcrypto-disabled':
        return 'Regular'
    elif driver == 'nullcrypto-enabled':
        return 'Nullcrypto'


def generate_bandwidth_graphs(bandwidth_data, driver_names, block_sizes, mode, disk, ax):
    '''
    parameters:
        - bandwidth_data: list that contains the bandwidths of the different drivers
        (these are lists themselves)
        - driver_names: list of the driver names in the same order as the data in
        `bandwidth_data`
        - block_sizes: list of the block sizes that the bandwidths correspond to
        in the same order as the data in `bandwidth_data`
        - disk: name of the disk (e.g. 'hdd' or 'ssd')
        - mode: mode of the data (e.g. 'seqread' or 'randread')
        - ax: matplotlib axis used for plotting
    '''
    strip_k_suffix = lambda bs: bs[:-1]
    block_sizes = list(map(strip_k_suffix, block_sizes))
    for driver, data in zip(driver_names, bandwidth_data):
        ax.plot(block_sizes, data, label=nice_driver_name(driver))
    if mode == 'seqread':
        ax.legend(loc='lower left')
    elif mode == 'randread':
        ax.legend(loc='upper left')
    ax.set_title(nice_mode_name(mode) + f' ({nice_disk_name(disk)})')
    ax.set_xlabel('Block size [KiB]')
    ax.set_ylabel('Throughput [MiB/s]')


def get_bandwidth_data(json_path):
    '''
    reads the bandwidth from a given json path
    parameters:
        - json_path: path to the JSON file to read the data from
    '''
    with open(json_path, 'r') as json_file:
        jobs = json.load(json_file)['jobs']
        njobs = 0
        bw_sum = 0
        for job in jobs:
            bw_sum += job['read']['bw_bytes']
            njobs += 1
        return bw_sum / njobs


def sort_blocksizes(blocksizes):
    '''
    sorts a list of blocksizes, e.g. ['64k', '8k', '32k', '16k'] -> ['8k', '16k', '32k', '64k']
    '''
    map_func = lambda bs: int(bs[:-1])
    blocksizes = sorted(map(map_func, blocksizes))
    map_func = lambda bs: f'{bs}k'
    return list(map(map_func, blocksizes))


def average_bandwidth(directory, mode, bs, driver, disk, suffix, numbers):
    '''
    gets the average bandwidth from json files with all the same regex group values except for different numbers
    '''
    bw_sum = 0
    for number in numbers:
        json_file = filename_from_group_vals(mode, bs, driver, disk, suffix, number)
        json_path = os.path.join(directory, json_file)
        bw_sum += get_bandwidth_data(json_path)
    return bw_sum / len(numbers)


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
    numbers = list(sorted(group_vals['number']))

    for suffix in group_vals['suffix']:
        for mode in modes:
            final_data = {disk: np.empty((len(drivers), len(blocksizes))) for disk in disks}
            figure_path = join(FIGURES_FOLDER, f'{basename(directory)}_{mode}{suffix}.pdf')
            fig = plt.figure(figsize=(10, 8))
            axes = fig.subplots(len(disks), 1)
            print(f'generating figure \'{figure_path}\'')

            for i, disk in enumerate(disks):
                for ii, driver in enumerate(drivers):
                    data = np.empty(len(blocksizes))
                    for iii, bs in enumerate(blocksizes):
                        data[iii] = average_bandwidth(directory, mode, bs, driver, disk, suffix, numbers)
                        
                    final_data[disk][ii] = data / 1024 / 1024

                axis_index = i
                generate_bandwidth_graphs(final_data[disk], drivers, blocksizes, mode, disk, axes[axis_index])
                # plt.setp(axes[axis_index].get_xticklabels(), ha="right", rotation=45)
                axes[axis_index].set_ylim(bottom=0)

            fig.tight_layout()
            fig.savefig(figure_path, bbox_inches='tight')

if __name__ == '__main__':
    for maybe_dir in listdir(JSON_FOLDER):
        full_path = join(JSON_FOLDER, maybe_dir)
        if not isdir(full_path):
            continue
        handle_directory(full_path)
