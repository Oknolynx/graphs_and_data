#! /usr/bin/env python3

import numpy as np
from gen_figures_regular import JSON_FOLDER, average_throughput, observed_group_vals, sort_blocksizes
from os import listdir
from os.path import basename, isdir, join


def handle_directory(directory):
    group_vals = observed_group_vals(directory)
    modes = list(sorted(group_vals['mode']))
    blocksizes = sort_blocksizes(list(group_vals['blocksize']))
    numbers = list(sorted(group_vals['number']))
    luks2flt = None
    for d in group_vals['driver']:
        if 'luks2flt-opt' in d:
            luks2flt = d
            break
    ssd = None
    for d in group_vals['disk']:
        if 'ssd' in d:
            ssd = d
            break

    for suffix in group_vals['suffix']:
        for mode in modes:
            luks2flt_data = np.empty(len(blocksizes))
            bitlocker_data = np.empty(len(blocksizes))
            veracrypt_data = np.empty(len(blocksizes))
            for i, bs in enumerate(blocksizes):
                luks2flt_data[i] = average_throughput(directory, mode, bs, luks2flt, ssd, suffix, numbers)
                bitlocker_data[i] = average_throughput(directory, mode, bs, 'bitlocker', ssd, suffix, numbers)
                veracrypt_data[i] = average_throughput(directory, mode, bs, 'veracrypt', ssd, suffix, numbers)
            
            bitlocker_vc_data = bitlocker_data / veracrypt_data
            luks2flt_vc_data = luks2flt_data / veracrypt_data
            luks2flt_bl_data = luks2flt_data / bitlocker_data
            bitlocker_data /= luks2flt_data
            veracrypt_data /= luks2flt_data
            bitlocker_vc_percent = np.round(np.max(bitlocker_vc_data) * 100) - 100
            luks2flt_vc_percent = np.round(np.max(luks2flt_vc_data) * 100) - 100
            luks2flt_bl_percent = np.round(np.max(luks2flt_bl_data) * 100) - 100
            bitlocker_percent = np.round(np.max(bitlocker_data) * 100) - 100
            veracrypt_percent = np.round(np.max(veracrypt_data) * 100) - 100
            bitlocker_vc_bs = 2**(np.argmax(bitlocker_vc_data) + 2)
            luks2flt_vc_bs = 2**(np.argmax(luks2flt_vc_data) + 2)
            luks2flt_bl_bs = 2**(np.argmax(luks2flt_bl_data) + 2)
            bitlocker_bs = 2**(np.argmax(bitlocker_data) + 2)
            veracrypt_bs = 2**(np.argmax(veracrypt_data) + 2)
                
            print(f'{mode}_{ssd}{suffix}')
            print(f'\tHighest BitLocker percentage: {bitlocker_percent}% better than luks2flt (at {bitlocker_bs} KiB), {bitlocker_vc_percent}% better than VeraCrypt (at {bitlocker_vc_bs} KiB)')
            print(f'\tHighest VeraCrypt percentage: {veracrypt_percent}% better than luks2flt (at {veracrypt_bs} KiB)')
            print(f'\tHighest luks2flt percentage: {luks2flt_bl_percent}% better than BitLocker (at {luks2flt_bl_bs} KiB), {luks2flt_vc_percent}% better than VeraCrypt (at {luks2flt_vc_bs} KiB)')
            print(f'\t{luks2flt_vc_data[-4:]=}')
            print(f'\t{luks2flt_bl_data[-4:]=}')


if __name__ == '__main__':
    for maybe_dir in listdir(JSON_FOLDER):
        full_path = join(JSON_FOLDER, maybe_dir)
        if not isdir(full_path):
            continue
        handle_directory(full_path)
