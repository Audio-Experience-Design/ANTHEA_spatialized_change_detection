# ANTHEA_stim_generator
 
## Installation
Firstly make sure python is downloaded. The latest version should be fine.
Then create a virtual environment. The easiest way is to use VS Code and then select the python interpreter and create a virtual environment that way and it should make an environment in the root folder of the repository

Install the dependencies by running in the activated virtual environment

`pip install -r requirements.txt`

## Configuration

To generate the stimuli first check/change the config file in the config folder. Feel free to copy and paste and create a new one under any name.
Make sure the directory where your HRTFs are stored is correct.

So that you can just enter the p number when generating the wav files of the HRTF you will want to specify with 'wildcards' how to load the HRTF (as there are different versions of HRTFs)

For example in the case of :
hrtf_dir: 'C:\Users\Kat\Box\2023_HRTF-Kathi\Data\'
hrtf_type: '*\*_Windowed_NoITD_48kHz.sofa'

The HRTF it will load when you enter the P number P0107 is:

C:\Users\Kat\Box\2023_HRTF-Kathi\Data\P0107\P0107_Windowed_NoITD_48kHz.sofa

It will insert the p number where the astericks are. 

## Generating the files
Once you have sorted out the configuration file, to generate the stimuli, make sure the terminal is open in the root directorty of the ANTHEA_stim_generator.
Then type in the command:

`python anthea.py <p_number> <configuration_filename>`

For example:

`python anthea.py P0107 config.yml`

It should then generate a bunch of wavs in the stimuli folder under the designated P number with a csv that will tell you the information for each wav (i.e. whether there was a change, the location of each source etc.)
