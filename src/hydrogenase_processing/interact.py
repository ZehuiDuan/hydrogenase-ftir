#Setting Up and Importing the Necessary Packages/Libraries
import matplotlib.pyplot as plt
import pathlib
#Local Functions

from hydrogenase_processing.anchor_points import get_peaks, get_start_end_anchorpoints, get_all_anchor_points
from hydrogenase_processing.io import import_run_data
from hydrogenase_processing.anchor_points import get_peaks, get_start_end_anchorpoints, get_all_anchor_points, baseline_spline, get_peaks_absorbance, baseline_correction#, get_peak_baseline_absorbance, plot_baseline_data
from hydrogenase_processing.second_deriv import second_deriv
from hydrogenase_processing.cut_range import cut_range_subtract_multiple_wv

import ipywidgets as widgets
from IPython.display import display
import os

import re

#addition from Eric interactive widgets
def interact(path_to_data_input, path_to_water_vapor_input, threshold_guess, adj_guess):
    '''
    x is the sample second derivative
    example_cut_sub is the sample raw loaded from cut_range_sub_wv_data[] which is the output of cut_range
    '''
    path_to_data = pathlib.Path(path_to_data_input)
    path_to_water_vapor_data = pathlib.Path(path_to_water_vapor_input)

    raw_data = import_run_data(path_to_data)
    wv_data = import_run_data(path_to_water_vapor_data)
    
    cut_range_sub_wv_data = cut_range_subtract_multiple_wv(raw_data, wv_data, range_start = 2150, range_end = 1850)
    
    file_names = os.listdir(path_to_data)

    #sort_key is used to guide the later sorted() function that sorts by alphabet and number
    def sort_key(file_names):
        #2 capture groups: 
        #1. look for letters small and upper case as well as .
        #2. look for r"string in the format of \d match any digit and + indicate /d should appear one or more times
        #eg parts output [('Hyd', '1'), ('pD', '6'), ('ACT.', '0017')]
        parts = re.findall(r'([a-zA-Z.]+)(\d+)', file_names)
        if parts:
            #for letters stored in first position, then numbers in the second position, and for loop for each element in each part
            letters = tuple(element[0].lower()for element in parts)
            numbers = tuple(int(part[1]) for part in parts)
            return letters + numbers #output a combined tuple
        return ((file_names.lower),0 )

    sorted_file_names = sorted(file_names, key=sort_key)
    
    file_widget = widgets.ToggleButtons(
    options = sorted_file_names,
    description='Step 1. File selection:',
    disabled=False
    )

    style = {'description_width': '500px'}
    #Preset threshold widget range and step by us
    threshold_widget = widgets.BoundedFloatText(
        value=threshold_guess,
        min=0,
        max=1,
        step=0.01,
        description='Threshold for peak selection(0 to 1 in 0.01 steps):',
        disabled=False,
        layout=widgets.Layout(width='70%'),
        style = style
    )
    

    
    #Preset adj widget range and step by us
    adj_widget = widgets.BoundedFloatText(
        value=adj_guess,
        min=0,
        max=5,
        step=0.01,
        description='adj for anchor point selection(0 to 5 in 0.01 steps):',
        disabled=False,
        layout=widgets.Layout(width='70%'),
        style=style
    )
    
    ##edits on 6/13/24
    submit = widgets.Button(
    description ='Submit'
    )

    oops = widgets.Button(
    description = 'Oops'
    )

    threshold_save = []
    adj_save = []
    file_save = []

    def button_click(a):
        #global threshold_save
        #global adj_save
        #global file_name_save
        threshold_save.append(threshold_widget.value)
        adj_save.append(adj_widget.value)
        file_save.append(file_widget.value)
        #print(f'Saved file:{file_save}, threshold:{threshold_save}, adj:{adj_save}')
        
        return file_save, threshold_save, adj_save
    
    def do_over(b):
        del file_save[-1]
        del threshold_save[-1]
        del adj_save[-1]
    


    #a version of the get_all_anchor_points function that is easily inserted for the interactive widget function
    #a version of the get_peaks function that is format wise easily inserted for the interactive widget function
    def interact_with_functions(desired_file, threshold, adj):
        
        sample_raw = cut_range_sub_wv_data[desired_file]
        sample_raw[0][0].plot()

        fit_atm_params_func = sample_raw[0][0].fit_atm_params

        #Creating Empty Dict for second derivative of cut and subtracted data
        second_deriv_data = dict()

        #Filling it with second derivatives of all the data
        for i in cut_range_sub_wv_data:
            cut_range_sub_wv_data_i = cut_range_sub_wv_data[i]
            second_deriv_data[f'{i}_second_deriv'] = second_deriv(cut_range_sub_wv_data_i, show_plots=False)

        sample_second_deriv = second_deriv_data[f'{desired_file}_second_deriv']

        output = get_peaks(sample_second_deriv, threshold)
        
        #re-extract values
        peaks_index = output[0]
        deriv_x_peak_val = output[1]
        d2ydx2_peak_val = output[2]

        wv_startIdx, wv_endIdx = get_start_end_anchorpoints(peaks_index[0], sample_second_deriv)
        y_corr_abs = sample_raw[0][0].sub_spectrum
        anchor_points_raw_data = sample_raw[0][0].wavenb

        anchor_point_dict_output, peak_wavenumber, peak_absorbance = get_all_anchor_points(wv_startIdx, wv_endIdx, deriv_x_peak_val, anchor_points_raw_data, y_corr_abs, adj)

        plt.figure(figsize=(18, 6))

        #second derivative plot
        plt.subplot(1,2,1)
        plt.plot(deriv_x_peak_val, d2ydx2_peak_val, "ro",label = "peak finder peaks")
        plt.plot(sample_second_deriv[2], sample_second_deriv[1], label = "spline results")
        plt.title("Second derivative plot peak selection")
        plt.legend()

        plt.subplot(1,2,2)
        plt.plot(anchor_points_raw_data, y_corr_abs)
        plt.plot(peak_wavenumber, peak_absorbance,'ro', label='peaks')
        plt.plot(anchor_point_dict_output['wavenumber'], anchor_point_dict_output['absorbance'], 'bx', label = 'anchor_points')
        
        plt.xlabel("wavenumber")
        plt.ylabel("Absorbance")
        plt.title("Anchor point selection")
        plt.legend()

        plt.tight_layout()

        print('Step 2. Use the threshold and adj widgets to adjust the number of peaks included and the where to put the anchor points, and click submit after desired outcome to save the final parameters')

        submit.on_click(button_click)
        #display(submit)

        oops.on_click(do_over)
        
        return output, anchor_point_dict_output, deriv_x_peak_val, anchor_points_raw_data, y_corr_abs
    
    #use one output because the output has to follow structure of ipywidget output and only interactive and produce non package specific objects
    interactive_results = widgets.interactive(interact_with_functions, desired_file = file_widget, threshold = threshold_widget, adj = adj_widget)
    
    #print(interactive_results)
    file_selection_display = interactive_results.children[0]
    threshold_adj_plot_display = interactive_results.children[1]
    threshold_adj_display = interactive_results.children[2]
    raw_display = interactive_results.children[3]
    

    #break down the results
    output = interactive_results.result[0]
    anchor_point_dict_output = interactive_results.result[1]
    deriv_x_peak_val = interactive_results.result[2]
    anchor_points_raw_data = interactive_results.result[3]
    y_corr_abs = interactive_results.result[4]

    #show the output so that it's interactive
    display(file_selection_display)
    display(raw_display) 
    display(threshold_adj_plot_display)
    display(threshold_adj_display)
    
    display(submit)
    display(oops)
    
    anchor_point_dict = anchor_point_dict_output
   
    
    return anchor_point_dict, deriv_x_peak_val, anchor_points_raw_data, y_corr_abs, file_save, threshold_save, adj_save



