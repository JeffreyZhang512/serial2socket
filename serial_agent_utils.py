# ------------------------------------------------------------------------------
#     Copyright (c) 2023
#     Author: Zhang, Jeffrey <jeffreyzh512@outlook.com>
# ------------------------------------------------------------------------------

from tkinter import *
import os
import sys
import time
import json


def debug_print(debug_string):
    time_stamp = "[" + time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + "] "
    print(time_stamp + debug_string)


def debug_sprint(debug_string):
    time_stamp = "[" + time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + "] "
    return time_stamp + debug_string + "\n"


# Get the folder name of the current py file 
def get_current_folder():
    return os.path.dirname(os.path.realpath(__file__))


class dialog(Toplevel):
	
    def __init__(self, parent, hide_parent = False, always_on_top = True, always_grab_focus = True, title = None):
        print(str(type(self)) + ".__init__ called")
        self.hide_parent = hide_parent
        Toplevel.__init__(self, parent)
        
        if title:
            self.title(title)
 
        self.parent = parent
        self.protocol("WM_DELETE_WINDOW", self.cancel)
        self.geometry("+%d+%d" % (parent.winfo_rootx()+30,
                                  parent.winfo_rooty()+30))

        self.initial_focus = self.body()
 
        if not self.initial_focus:
            self.initial_focus = self
 
        if self.initial_focus:
            self.initial_focus.focus_set()

        if always_on_top:
            self.transient(parent)
        
        if always_grab_focus:
            self.grab_set()
            self.wait_window(self)

    
    # Will be overridden in child class
    def validate(self):
        return True

        
    # Will be overridden in child class
    def apply(self):
        pass


    # standard button semantics
    def ok(self, event = None):
        if not self.validate():
            self.focus_set()
            return
        self.withdraw()
        self.update_idletasks()
        self.apply()
        self.cancel()


    def ok_keep_open(self, event = None):
        if not self.validate():
            self.focus_set()
            return
        self.apply()
        
        
 
    def cancel(self, event = None):
        # put focus back to the parent window
        print(str(type(self)) + ".cancel called")
        # self.parent.focus_set()
        self.destroy()
        if self.hide_parent:
            self.parent.destroy()


    # Will be overridden in child class
    # construction hooks
    def body(self):
        # create dialog body.  return widget that should have
        # initial focus.  this method should be overridden
        return None # initial focus 

	 

def main():
    def test():
        pass
        w = dialog(root, "ABC")
		
    # Main Window
    root = Tk()
    root.title("Fast UTP Testing")
    root.geometry("1200x600")
    
    button_test = Button(root, text = "test", default = ACTIVE, command = test)
    button_test.pack()
    
    
    root.mainloop()
    
    
    return 0

if __name__ == '__main__':
    main()
	
