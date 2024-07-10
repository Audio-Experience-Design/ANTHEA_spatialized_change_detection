import os
import sys
import pandas as pd
import random
import yaml
import numpy as np
import py3dti
import datetime
import scipy
from miniaudio import decode_file, SampleFormat
import matplotlib.pyplot as plt
from spatialaudiometrics import angular_metrics as am

def generate_trials(config):
    '''
    Generates a table that contains the stimulus information for each trial
    '''
    print('Generating stimuli...')
    full_trial_set      = pd.DataFrame()
    speaker_df          = pd.read_csv('./tables/speakerSetup.csv')

    # Shuffle blocks if mono
    random.shuffle(config['mono'])
    for m, mon in enumerate(config['mono']):
        curr_trial_set = pd.DataFrame()
        for s, source in enumerate(config['sources']):
            speakers        = speaker_df.loc[(speaker_df.Total_sources == source)]
            target_speakers = speakers[speakers.TargetSource.isin(config['target_speakers'])].reset_index(drop = True)
            if int(config['any_target_file']) == 0:
                # Selecting top performers for target (from previous pilots)
                stim_masker_files = [11,4,3,16,8,1,6,2,5,12]
                stim_target_files = [9,15,10,14,7]
            else: # If still collecting info on top performers
                stim_target_files = [1,2,3,4,5,6,7,8,9,10,11,12,14,15,16]
            # Now generate what is the target and masker for each trial
            for t, target_row in target_speakers.iterrows():
                for c in range(int(config['change_appear'])+1): # Check if there is a change appearing
                    curr_stim_target_files = list(stim_target_files)
                    random.shuffle(curr_stim_target_files)
                    # Generate list of target files so its pseudorandomised
                    while len(curr_stim_target_files)<int(config['repeats']):
                        temp = list(stim_target_files)
                        random.shuffle(temp)
                        curr_stim_target_files = curr_stim_target_files + temp
                    for n in range(int(config['repeats'])):
                        if int(config['any_target_file']) == 0:
                            curr_stim_masker_files = list(stim_masker_files)
                        else:
                            curr_stim_masker_files = list(curr_stim_target_files)
                            curr_stim_masker_files.pop(n)
                        random.shuffle(curr_stim_masker_files)

                        # Generate the onset of the target and allocate target
                        target_onset = np.round(random.uniform(float(config['target_onset_min_s']),float(config['target_onset_max_s'])),3)
                        sF1 = curr_stim_target_files[n]
                        sL1 = target_row.Speaker
                        sA1 = target_row.Az
                        sE1 = target_row.El

                        # Allocate maskers
                        masker_locs     = speakers.groupby("Quadrant").sample(n=target_row.SourcesPerQuadrant).reset_index(drop = True)
                        removed_speaker = masker_locs.loc[(masker_locs.Quadrant == target_row.Quadrant)].reset_index(drop=True).Speaker[0]
                        masker_locs     = masker_locs.loc[(masker_locs.Speaker != removed_speaker)].reset_index()
                        leftover_speakers = speakers.Speaker.unique()
                        leftover_speakers = leftover_speakers[leftover_speakers != sL1]
                        for i in range(len(masker_locs)):
                            leftover_speakers = leftover_speakers[leftover_speakers != masker_locs.Speaker[i]]
                        mask = {}
                        for i in range(7): 
                            # Make the other locations and files empty so they don't play anything (quick hack to work with the max patch easiest)
                            if i > len(masker_locs)-1:
                                silent_speaker = leftover_speakers[i-len(masker_locs)]
                                mask["sL" + str(i+2)] = silent_speaker
                                mask["sF" + str(i+2)] = int(config['silent_filenumber'])
                                mask["sA" + str(i+2)] = speakers.loc[(speakers.Speaker == silent_speaker)].Az.values[0]
                                mask["sE" + str(i+2)] = speakers.loc[(speakers.Speaker == silent_speaker)].El.values[0]
                            else:
                                mask["sL" + str(i+2)] = masker_locs.Speaker[i]
                                mask["sF" + str(i+2)] = curr_stim_masker_files[i+1]
                                mask["sA" + str(i+2)] = speakers.loc[(speakers.Speaker == masker_locs.Speaker[i])].Az.values[0]
                                mask["sE" + str(i+2)] = speakers.loc[(speakers.Speaker == masker_locs.Speaker[i])].El.values[0]

                        temp = pd.DataFrame([[0,c,target_onset,source,mon,sL1,sF1,sA1,sE1,
                                                mask['sL2'],mask['sF2'],mask['sA2'],mask['sE2'],
                                                mask['sL3'],mask['sF3'],mask['sA3'],mask['sE3'],
                                                mask['sL4'],mask['sF4'],mask['sA4'],mask['sE4'],
                                                mask['sL5'],mask['sF5'],mask['sA5'],mask['sE5'],
                                                mask['sL6'],mask['sF6'],mask['sA6'],mask['sE6'],
                                                mask['sL7'],mask['sF7'],mask['sA7'],mask['sE7'],
                                                mask['sL8'],mask['sF8'],mask['sA8'],mask['sE8']]],
                                columns = ['wav_number','Change','TargetOnset','Sources','Mono',
                                        'sL1','sF1','sA1','sE1',
                                        'sL2','sF2','sA2','sE2',
                                        'sL3','sF3','sA3','sE3',
                                        'sL4','sF4','sA4','sE4',
                                        'sL5','sF5','sA5','sE5',
                                        'sL6','sF6','sA6','sE6',
                                        'sL7','sF7','sA7','sE7',
                                        'sL8','sF8','sA8','sE8'])
                        curr_trial_set = pd.concat([curr_trial_set,temp])
        # Randomly permute the stimulus set
        curr_stim_set = curr_trial_set.sample(frac=1)
        full_trial_set = pd.concat([full_trial_set,curr_stim_set])
    #Then add in the trial index 
    full_trial_set['wav_number'] = np.arange(1,len(full_trial_set)+1,1)
    full_trial_set = full_trial_set.reset_index(drop = True)

    return full_trial_set

def load_config_file(config_file):
    '''
    Loads in the parameters from the chosen .yml file
    
    :param config_file: path to the .yml file you want to load for the test chosen
    '''
    with open(config_file, 'r') as f:
        config = yaml.load(f, Loader=yaml.SafeLoader)
    return config

def ramp_stimuli(stim,fs):
    '''
    Ramps with a 10ms ramp. Since they are wavs they have different max values so just ramp to the max value
    '''
    ts = np.arange(0,np.shape(stim)[0]/fs,1/fs)
    ramp_dur_samps = int(np.ceil(fs * 0.01))
    ramp = np.sin(np.linspace(0,np.pi/2,ramp_dur_samps))
    ramp_mid = np.ones([1,len(ts)-(ramp_dur_samps*2)]) * np.max(np.abs(stim))
    ramp_full = np.append(ramp,ramp_mid)
    ramp_full = np.append(ramp_full,np.flip(ramp))
    # Do both channels because binaural
    stim[:,0] = stim[:,0]*ramp_full
    stim[:,1] = stim[:,1]*ramp_full

    return stim

def generate_wavs(config,df):
    '''
    Generates the necessary wavs from the table
    '''
    # Load in the hrtf
    print('Loading HRTF...')
    renderer = py3dti.BinauralRenderer(rate=config['sample_rate'], buffer_size=512, resampled_angular_resolution=5)
    listener = renderer.add_listener(position=None, orientation=None)
    hrtf_name = config['hrtf_dir'] + config['hrtf_type'].replace("*", config['subject'])
    listener.load_hrtf_from_sofa(hrtf_name)

    for i,row in df.iterrows():
        print('Generating trial ' + str(i+1))
        sources = dict()
        for s in range(row.Sources):
            filename = row['sF'+ str(s+1)]
            if filename <= 9:
                filename = './chimeras/0' + str(filename) + '.wav'
            else:
                filename = './chimeras/' + str(filename) + '.wav'
            decoded_file    = decode_file(filename=filename, output_format=SampleFormat.FLOAT32,
                            nchannels=1, sample_rate=config['sample_rate'])
            
            stim         = np.asarray(decoded_file.samples)
            # If its source one and this has a change then add zeros and then have the wav come in, otherwise keep it silent.
            if (s == 0) & (row.Change == 1):
                x,y,z = am.polar2cartesian(row['sA' + str(s+1)],row['sE' + str(s+1)],1.5) # HRTFS were measured at 1.5m
                source = renderer.add_source(position=(x, y, z))
                # Add in the zeros 
                padding = np.zeros(int(np.ceil(config['sample_rate']*row.TargetOnset)))
                stim = np.concatenate([padding,stim])
                sources[source] = stim

            elif s > 0:
                x,y,z = am.polar2cartesian(row['sA' + str(s+1)],row['sE' + str(s+1)],1.5) # HRTFS were measured at 1.5m
                source = renderer.add_source(position=(x, y, z))
                sources[source] = stim
        # Render the binaural audio
        binaural_stim = renderer.render_offline(sources)

        # Cut audio so that its only the target length + target onset 
        binaural_stim = binaural_stim[0:int(np.ceil(config['sample_rate']*(row.TargetOnset + config['target_length_s']))),:]
        # Ramp it to avoid any popping
        binaural_stim = ramp_stimuli(binaural_stim,config['sample_rate'])
        scipy.io.wavfile.write('./stimuli/' + config['subject'] + '/' + config['subject'] + '_' + str(row.wav_number) + '.wav',config['sample_rate'],binaural_stim)

def main(p_number,config_file):
    '''
    Load in HRTF and generate wavs
    '''
    try:
        os.mkdir('./stimuli/' + p_number)
    except FileExistsError:
        ans = input('Folder already exists. Do you want to overwrite the folder? (y/n)')
        if ans == 'y':
            print('Overwriting folder...')
        else:
            sys.exit('Stopped generating files')

    # Load in the config
    config = load_config_file('./config/' + config_file)
    config['subject'] = p_number
    # Generate table that contains all the information
    full_trial_set = generate_trials(config)
    
    # Add in some more information
    full_trial_set['subject'] = p_number
    full_trial_set['test_type'] = config['test_type']
    full_trial_set['datestr'] = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    # Save the table in the folder with the stimuli
    full_trial_set.to_csv('./stimuli/' + p_number + '/' + p_number + '_trial_info.csv', index = False)

    # Generate all the wavs
    generate_wavs(config,full_trial_set)
    
    print('Finished generating wavs')

if __name__ == '__main__':
    p_number    = str(sys.argv[1])
    config      = str(sys.argv[2])
    main(p_number,config)
