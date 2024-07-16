

"""
 One-click image sorting/labelling script. Copies or moves images from a folder into subfolders. 
 This script launches a GUI which displays one image after the other and lets the user give different labels
 from a list provided as input to the script. In contrast to original version, version 2 allows for 
 relabelling and keeping track of the labels.
 Provides also short-cuts - press "1" to put into "label 1", press "2" to put into "label 2" a.s.o.

 USAGE:
 run 'python sort_folder_vers2.py' or copy the script in a jupyter notebook and run then

 you need also to provide your specific input (source folder, labels and other) in the preamble
 original Author: Christian Baumgartner (c.baumgartner@imperial.ac.uk)
 changes, version 2: Nestor Arsenov (nestorarsenov@gmail.com), Date: 24. Dec 2018
 changes, version 3: J Kwon, Date: 29 Jun 2021

 run in pnet36 env
 
 """


# Define global variables, which are to be changed by user:

##### added in version 2
from pathlib import Path
import pandas as pd
import os
import numpy as np

import argparse
import tkinter as tk
import os
from shutil import copyfile, move
from PIL import ImageTk, Image
# the folder in which the pictures that are to be sorted are stored
# don't forget to end it with the sign '/' !
scriptdir = Path(__file__).parent.resolve()
input_dir = Path('/data/biomedia1/pulse/FL/').resolve()
# input_dir = (scriptdir / '../../03_Data/HC_Anomaly_2019-11-04T1/').resolve()

# the different folders into which you want to sort the images, e.g. ['cars', 'bikes', 'cats', 'horses', 'shoes']
labels = ["1", "0", "0.5"]

# the number key will be bound to the labels. <1> key will be bound to first label, <2> key the 2nd etc.
# i.e. {<1>, labels[0], <2>, labels[1]}
key_bindings = {"1": "1", "2":"0", "3":"0.5"}


# A file-path to a csv-file, that WILL be created by the script. The results of the sorting wil be stored there.
# Don't provide a filepath to an empty file, provide to a non-existing one!
# If you provide a path to file that already exists, than this file will be used for keeping track of the storing.
# This means: 1st time you run this script and such a file doesn't exist the file will be created and populated,
# 2nd time you run the same script, and you use the same df_path, the script will use the file to continue the sorting.
df_path = "/data/biomedia1/pulse/manual_anno___.csv"

# a selection of what file-types to be sorted, anything else will be excluded
file_extension = ".png" # ['.jpg', '.png', '.JPEG', '.whatever']


save_freq = 100  # saves every x annotations complete - if you save every time it's slow

# set resize to True to resize image keeping same aspect ratio
# set resize to False to display original image
resize = True



class ImageGui:
    """
    GUI for iFind1 image sorting. This draws the GUI and handles all the events.
    Useful, for sorting views into sub views or for removing outliers from the data.
    """

    def __init__(self, master, labels, paths, df, df_path, save_freq=100):
        """
        Initialise GUI
        :param master: The parent window
        :param labels: A list of labels that are associated with the images
        :param paths: A list of file paths to images
        :return:
        """

        # So we can quit the window from within the functions
        self.master = master

        # Extract the frame so we can draw stuff on it
        frame = tk.Frame(master)

        # Initialise grid
        frame.grid()

        # Start at the first file name
        self.index = 0
        self.paths = paths
        self.labels = labels
        #### added in version 2
        self.sorting_label = 'unsorted'
        ####

        df = df.replace('', np.nan)
        df = df.replace(r'^\s*$', np.nan, regex=True)
        self.df = df
        self.df_path = df_path


        self.save_freq = save_freq
        # Number of labels and paths
        self.n_labels = len(labels)
        self.n_paths = len(paths)

        # Set empty image container
        self.image_raw = None
        self.image = None
        self.image_panel = tk.Label(frame)

        # set image container to first image
        self.set_image(paths[self.index])

        # Make buttons
        self.buttons = []
        for label in labels:
            self.buttons.append(
                    tk.Button(frame, text=label, width=10, height=2, fg='blue', command=lambda l=label: self.vote(l))
            )
            
        ### added in version 2
        self.buttons.append(tk.Button(frame, text="prev im", width=10, height=1, fg="green", command=lambda l=label: self.move_prev_image()))
        self.buttons.append(tk.Button(frame, text="next im", width=10, height=1, fg='green', command=lambda l=label: self.move_next_image()))
        ###
        
        # Add progress label
        progress_string = "%d/%d" % (self.index+1, self.n_paths)
        self.progress_label = tk.Label(frame, text=progress_string, width=10)
        
        # Place buttons in grid
        for ll, button in enumerate(self.buttons):
            button.grid(row=0, column=ll, sticky='we')
            #frame.grid_columnconfigure(ll, weight=1)

        # Place progress label in grid
        self.progress_label.grid(row=0, column=self.n_labels+2, sticky='we') # +2, since progress_label is placed after
                                                                            # and the additional 2 buttons "next im", "prev im"

        # Add progress label
        completeness_string = "num annos: %d/%d : %.2f%% " % (self.df.lab.count(), len(self.df), (self.df.lab.count()*100)/(len(self.df)))
        self.completeness_label = tk.Label(frame, text=completeness_string, width=10)
        self.completeness_label.grid(row=1, column=self.n_labels, columnspan=3, sticky='we') # +2, since progress_label is placed after
                                                                            # and the additional 2 buttons "next im", "prev im"
        #### added in version 2
        # Add sorting label
        sorting_string = Path(df.im_path[self.index]).resolve().parent.parent.stem +"/"+ Path(df.im_path[self.index]).resolve().stem
        # sorting_string = Path(df.os.path.split(df.sorted_in_folder[self.index])[-2]
        if pd.isnull(df.lab[self.index]):
            sort_label_colour = "red"
        else:
            sort_label_colour = "green"
        self.sorting_label = tk.Label(frame, text=("in folder: %s" % (sorting_string)),
                                      width=15, wraplength=140, bg=sort_label_colour,
                                      font=("Arial", 12, "bold"))
        
        # Place typing input in grid
        tk.Label(frame, text="go to #pic:").grid(row=1, column=0)

        self.return_ = tk.IntVar() # return_-> self.index
        self.return_entry = tk.Entry(frame, width=6, textvariable=self.return_)
        self.return_entry.grid(row=1, column=1, sticky='we')
        master.bind('<Return>', self.num_pic_type)
        ####
        
        master.bind('<Destroy>', self.save_df)


        # Place sorting label in grid
        self.sorting_label.grid(row=2, column=self.n_labels+1,columnspan=2, sticky='we') # +2, since progress_label is placed after
                                                                            # and the additional 2 buttons "next im", "prev im"
        # Place the image in grid
        self.image_panel.grid(row=2, column=0, columnspan=self.n_labels+1, sticky='we')

        # key bindings (so number pad can be used as shortcut)
        # master.bind("y",self.vote_key)

        # make it not work for 'copy', so there is no conflict between typing a picture to go to and choosing a label with a number-key
        for key in range(self.n_labels):
            master.bind(str(key+1), self.vote_key)

        master.bind("<Left>", self.move_prev_key)
        master.bind("<Right>", self.move_next_key)

    def show_next_image(self):
        """
        Displays the next image in the paths list and updates the progress display
        """
        self.index += 1
        progress_string = "%d/%d" % (self.index+1, self.n_paths)
        self.progress_label.configure(text=progress_string)
        
        #### added in version 2
        sorting_string = Path(self.df.im_path[self.index]).resolve().parent.parent.stem +"/"+ Path(self.df.im_path[self.index]).resolve().stem
        # sorting_string = os.path.split(self.df.sorted_in_folder[self.index])[-2] #shows the last folder in the filepath before the file
        if pd.isnull(self.df.lab[self.index]):
            sort_label_colour = "red"
        else:
            sort_label_colour = "green"
        self.sorting_label.configure(text=("in folder: %s" % (sorting_string)), bg=sort_label_colour)
        ####

        if self.index < self.n_paths:
            self.set_image(self.df.im_path[self.index])
        else:
            self.master.quit()
    
    ### added in version 2        
    def move_prev_image(self):
        """
        Displays the prev image in the paths list AFTER BUTTON CLICK,
        doesn't update the progress display
        """
        self.index -= 1
        progress_string = "%d/%d" % (self.index+1, self.n_paths)
        self.progress_label.configure(text=progress_string)
        
        sorting_string = Path(self.df.im_path[self.index]).resolve().parent.parent.stem +"/"+ Path(self.df.im_path[self.index]).resolve().stem
        # sorting_string = os.path.split(self.df.sorted_in_folder[self.index])[-2] #shows the last folder in the filepath before the file
        # self.sorting_label.configure(text=("in folder: %s" % (sorting_string)))
        if pd.isnull(self.df.lab[self.index]):
            sort_label_colour = "red"
        else:
            sort_label_colour = "green"
        self.sorting_label.configure(text=("in folder: %s" % (sorting_string)), bg=sort_label_colour)


        if self.index < self.n_paths:
            self.set_image(self.df.im_path[self.index]) # change path to be out of self.df
        else:
            self.master.quit()
    
    ### added in version 2
    def move_next_image(self):
        """
        Displays the next image in the paths list AFTER BUTTON CLICK,
        doesn't update the progress display
        """
        self.index += 1
        progress_string = "%d/%d" % (self.index+1, self.n_paths)
        self.progress_label.configure(text=progress_string)

        sorting_string = Path(self.df.im_path[self.index]).resolve().parent.parent.stem+"/"+Path(self.df.im_path[self.index]).resolve().stem
        # sorting_string = os.path.split(self.df.sorted_in_folder[self.index])[-2] #shows the last folder in the filepath before the file
        # self.sorting_label.configure(text=("in folder: %s" % (sorting_string)))
        if pd.isnull(self.df.lab[self.index]):
            sort_label_colour = "red"
        else:
            sort_label_colour = "green"
        self.sorting_label.configure(text=("in folder: %s" % (sorting_string)), bg=sort_label_colour)
        
        if self.index < self.n_paths:
            self.set_image(self.df.im_path[self.index])
        else:
            self.master.quit()

    def set_image(self, path):
        """
        Helper function which sets a new image in the image view
        :param path: path to that image
        """
        image = self._load_image(path)
        self.image_raw = image
        self.image = ImageTk.PhotoImage(image)
        self.image_panel.configure(image=self.image)

    def vote(self, label):
        """
        Processes a vote for a label: Initiates the file copying and shows the next image
        :param label: The label that the user voted for
        """

        self.df.lab[self.index] = label

#       TODO: check if already sorted via saved df comparison?
        # if pd.isnull(df.label[self.index]):

        if self.df.lab.count() % self.save_freq == 0:
            self.df.to_csv(self.df_path, index=False)

        completeness_string = "num annos: %d/%d : %.2f%% " % (self.df.lab.count(), len(self.df), (self.df.lab.count()*100)/(len(self.df)))

        self.completeness_label.configure(text=completeness_string)

        self.show_next_image()

    def vote_key(self, event):
        """
        Processes voting via the number key bindings.
        :param event: The event contains information about which key was pressed
        """
        pressed_key = int(event.char)
        label = self.labels[pressed_key-1]
        self.vote(label)

    def move_next_key(self, event):
        """
        Processes voting via the number key bindings.
        :param event: The event contains information about which key was pressed
        """
        self.move_next_image()

    def move_prev_key(self, event):
        self.move_prev_image()

    #### added in version 2
    def num_pic_type(self, event):
        """Function that allows for typing to what picture the user wants to go.
        Works only in mode 'copy'."""
        # -1 in line below, because we want images bo be counted from 1 on, not from 0
        self.index = self.return_.get() - 1
        
        progress_string = "%d/%d" % (self.index+1, self.n_paths)
        self.progress_label.configure(text=progress_string)
        sorting_string = Path(self.df.im_path[self.index]).resolve().parent.parent.stem+"/"+Path(self.df.im_path[self.index]).resolve().stem
        # sorting_string = os.path.split(self.df.sorted_in_folder[self.index])[-2] #shows the last folder in the filepath before the file
        # self.sorting_label.configure(text=("in folder: %s" % (sorting_string)))
        if pd.isnull(self.df.lab[self.index]):
            sort_label_colour = "red"
        else:
            sort_label_colour = "green"
        self.sorting_label.configure(text=("in folder: %s" % (sorting_string)), bg=sort_label_colour)


        self.set_image(self.df.im_path[self.index])

    def save_df(self, event):
        self.df.to_csv(self.df_path, index=False)

    @staticmethod
    def _load_image(path):
        """
        Loads and resizes an image from a given path using the Pillow library
        :param path: Path to image
        :return: Resized or original image 
        """
        image = Image.open(path)
        if(resize):
            max_height = 500
            img = image 
            s = img.size
            ratio = max_height / s[1]
            image = img.resize((int(s[0]*ratio), int(s[1]*ratio)), Image.ANTIALIAS)
        return image



if __name__ == "__main__":
    paths = sorted(list(input_dir.glob(f"**/*{file_extension}")))
    # for file in input_dir.glob(f"**/*{file_extension}"):
    #     path = input_dir / file
    #     paths.append(path)

    ######## added in version 2
    # file_names = [fn for fn in sorted(os.listdir(input_folder))
    #                 if any(fn.endswith(ext) for ext in file_extensions)]
    # paths = [input_folder+file_name for file_name in file_names]

    try:
        df = pd.read_csv(df_path, header=0)
        # Store configuration file values
    except FileNotFoundError:
        df = pd.DataFrame(columns=["im_path", 'lab'])
        df.im_path = paths

    # print(df.head)

    # Start the GUI
    root = tk.Tk()
    app = ImageGui(root, labels, paths, df, df_path, save_freq)
    root.mainloop()

