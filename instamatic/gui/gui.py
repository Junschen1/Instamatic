from tkinter import *
from tkinter.ttk import *

import os, sys
import traceback
from instamatic.formats import *

import time
import logging

import threading
import queue

import datetime

from instamatic.camera.videostream import VideoStream
from .modules import MODULES

job_dict = {}


class DataCollectionController(object):
    """docstring for DataCollectionController"""
    def __init__(self, tem_ctrl=None, stream=None, beam_ctrl=None, log=None):
        super(DataCollectionController, self).__init__()
        self.ctrl = tem_ctrl
        self.stream = stream
        self.beam_ctrl = beam_ctrl

        self.log = log

        self.q = queue.LifoQueue(maxsize=1)
        self.triggerEvent = threading.Event()
        
        self.module_io = self.stream.get_module("io")
<<<<<<< HEAD
        self.module_sed = self.stream.get_module("sed")
        self.module_cred = self.stream.get_module("cred")
        self.module_red = self.stream.get_module("red")
        self.module_autocred = self.stream.get_module("autocred")
        self.module_ctrl = self.stream.get_module("ctrl")
        self.module_debug = self.stream.get_module("debug")

        self.module_sed.set_trigger(trigger=self.triggerEvent, q=self.q)
        self.module_cred.set_trigger(trigger=self.triggerEvent, q=self.q)
        self.module_red.set_trigger(trigger=self.triggerEvent, q=self.q)
        self.module_autocred.set_trigger(trigger=self.triggerEvent, q=self.q)
        self.module_ctrl.set_trigger(trigger=self.triggerEvent, q=self.q)
        self.module_debug.set_trigger(trigger=self.triggerEvent, q=self.q)
=======
>>>>>>> 3192a876cdb6d93d4cc47a89d4b9e82ac8864a3d

        for name, module in self.stream.modules.items():
            try:
                module.set_trigger(trigger=self.triggerEvent, q=self.q)
            except AttributeError:
                pass  # module does not need/accept a trigger
        
        self.exitEvent = threading.Event()
        self.stream._atexit_funcs.append(self.exitEvent.set)
        self.stream._atexit_funcs.append(self.triggerEvent.set)

        self.wait_for_event()

    def wait_for_event(self):
        while True:
            self.triggerEvent.wait()
            self.triggerEvent.clear()

            if self.exitEvent.is_set():
                self.close()
                sys.exit()

            job, kwargs = self.q.get()

            try:
<<<<<<< HEAD
                if job == "cred":
                    self.acquire_data_cRED(**kwargs)
                    
                if job == "autocred":
                    self.acquire_data_autocRED(**kwargs)
    
                elif job == "sed":
                    self.acquire_data_SED(**kwargs)
    
                elif job == "red":
                    self.acquire_data_RED(**kwargs)
    
                elif job == "ctrl":
                    self.move_stage(**kwargs)
    
                elif job == "debug":
                    self.debug(**kwargs)
    
                elif job == "toggle_difffocus":
                    self.toggle_difffocus(**kwargs)
=======
                func = job_dict[job]
            except KeyError:
                print("Unknown job: {}".format(job))
                print("Kwargs:\n{}".format(kwargs))
                continue
>>>>>>> 3192a876cdb6d93d4cc47a89d4b9e82ac8864a3d

            try:
                func(self, **kwargs)
            except Exception as e:
                traceback.print_exc()
                self.log.debug("Error caught -> {} while running '{}' with {}".format(repr(e), job, kwargs))
                self.log.exception(e)

<<<<<<< HEAD

    def acquire_data_cRED(self, **kwargs):
        self.log.info("Start cRED experiment")
        from instamatic.experiments import cRED
        
        expdir = self.module_io.get_new_experiment_directory()

        if not os.path.exists(expdir):
            os.makedirs(expdir)
        
        exposure_time = kwargs["exposure_time"]
        unblank_beam = kwargs["unblank_beam"]
        stop_event = kwargs["stop_event"]
        enable_image_interval = kwargs["enable_image_interval"]
        enable_autotrack = kwargs["enable_autotrack"]
        image_interval = kwargs["image_interval"]
        diff_defocus = self.ctrl.difffocus.value + kwargs["diff_defocus"]

        cexp = cRED.Experiment(ctrl=self.ctrl, path=expdir, expt=exposure_time, unblank_beam=unblank_beam, 
                               log=self.log, stopEvent=stop_event,
                               flatfield=self.module_io.get_flatfield())

        if enable_image_interval:
            cexp.enable_image_interval(interval=image_interval, defocus=diff_defocus)
            
                
        cexp.report_status()
        cexp.start_collection()
        
        stop_event.clear()
        self.log.info("Finish cRED experiment")
    
    def acquire_data_autocRED(self, **kwargs):
        self.log.info("Starting automatic cRED experiment")
        from instamatic.experiments import autocred
        
        if not os.path.exists(expdir):
            os.makedirs(expdir)
        
        exposure_time = kwargs["exposure_time"]
        unblank_beam = kwargs["unblank_beam"]
        stop_event = kwargs["stop_event"]
        enable_image_interval = kwargs["enable_image_interval"]
        enable_autotrack = kwargs["enable_autotrack"]
        image_interval = kwargs["image_interval"]
        diff_defocus = self.ctrl.difffocus.value + kwargs["diff_defocus"]

        cexp = autocRED.Experiment(ctrl=self.ctrl, path=expdir, expt=exposure_time, unblank_beam=unblank_beam, 
                               log=self.log, stopEvent=stop_event,
                               flatfield=self.module_io.get_flatfield())
        
        cexp.enable_autotrack(interval=image_interval, defocus=diff_defocus)
        
        cexp.report_status()
        cexp.start_collection()
        
        stop_event.clear()
        self.log.info("Finish autocRED experiment")
        
        
    def acquire_data_SED(self, **kwargs):
        self.log.info("Start serialED experiment")
        from instamatic.experiments import serialED

        workdir = self.module_io.get_working_directory()
        expdir = self.module_io.get_new_experiment_directory()

        if not os.path.exists(expdir):
            os.makedirs(expdir)

        params = os.path.join(workdir, "params.json")
        try:
            params = json.load(open(params,"r"))
        except IOError:
            params = PARAMS
        
        params.update(kwargs)
        params["flatfield"] = self.module_io.get_flatfield()

        scan_radius = kwargs["scan_radius"]

        self.module_sed.calib_path = os.path.join(expdir, "calib")

        exp = serialED.Experiment(self.ctrl, params, expdir=expdir, log=self.log, 
            scan_radius=scan_radius, begin_here=True)
        exp.report_status()
        exp.run()

        self.log.info("Finish serialED experiment")

    def acquire_data_RED(self, **kwargs):
        self.log.info("Start RED experiment")
        from instamatic.experiments import RED

        task = kwargs["task"]

        exposure_time = kwargs["exposure_time"]
        tilt_range = kwargs["tilt_range"]
        stepsize = kwargs["stepsize"]

        if task == "start":
            flatfield = self.module_io.get_flatfield()

            expdir = self.module_io.get_new_experiment_directory()

            if not os.path.exists(expdir):
                os.makedirs(expdir)
        
            self.red_exp = RED.Experiment(ctrl=self.ctrl, path=expdir, log=self.log,
                               flatfield=flatfield)
            self.red_exp.start_collection(expt=exposure_time, tilt_range=tilt_range, stepsize=stepsize)
        elif task == "continue":
            self.red_exp.start_collection(expt=exposure_time, tilt_range=tilt_range, stepsize=stepsize)
        elif task == "stop":
            self.red_exp.finalize()
            del self.red_exp

    def move_stage(self, **kwargs):
        task = kwargs.pop("task")

        f = getattr(self.ctrl, task)
        f.set(**kwargs)

        print f

    def debug(self, **kwargs):
        task = kwargs.pop("task")
        if task == "open_ipython":
            from IPython import embed
            embed(banner1="\nAssuming direct control.\n")
        elif task == "report_status":
            print self.ctrl
        elif task == "close_down":
            self.ctrl.stageposition.neutral()
            self.ctrl.mode = "mag1"
            self.ctrl.brightness.max()
            self.ctrl.magnification.value = 500000
            self.ctrl.spotsize = 1

            print "All done!"

    def toggle_difffocus(self, **kwargs):
        toggle = kwargs["toggle"]

        if toggle:
            print "Proper:", self.ctrl.difffocus
            self._difffocus_proper = self.ctrl.difffocus.value
            value = self._difffocus_proper + kwargs["value"]
        else:
            value = self._difffocus_proper

        self.ctrl.difffocus.set(value=value)
        print self.ctrl.difffocus
=======
    def close(self):
        for item in (self.ctrl, self.stream, self.beam_ctrl):
            try:
                item.close()
            except AttributeError:
                pass
>>>>>>> 3192a876cdb6d93d4cc47a89d4b9e82ac8864a3d


class DataCollectionGUI(VideoStream):
    """docstring for DataCollectionGUI"""
    def __init__(self, modules=(), cam=None):
        super(DataCollectionGUI, self).__init__(cam=cam)
        self._modules = modules
        self._modules_have_loaded = False
        self.modules = {}

    def load_modules(self, master):
        frame = Frame(master)
        frame.pack(side="right", fill="both", expand="yes")

        make_notebook = any(module.tabbed for module in self._modules)
        if make_notebook:
            self.nb = Notebook(frame, padding=10)

        for module in self._modules:
            if module.tabbed:
                page = Frame(self.nb)
                module_frame = module.tk_frame(page)
                module_frame.pack(side="top", fill="both", expand="yes", padx=10, pady=10)
                self.modules[module.name] = module_frame
                self.nb.add(page, text=module.display_name)
            else:
                module_frame = module.tk_frame(frame)
                module_frame.pack(side="top", fill="both", expand="yes", padx=10, pady=10)
                self.modules[module.name] = module_frame
            job_dict.update(module.commands)

        if make_notebook:
            self.nb.pack(fill="both", expand="yes")

        self._modules_have_loaded = True

    def get_module(self, module):
        return self.modules[module]

    def saveImage(self):
        module_io = self.get_module("io")

        drc = module_io.get_experiment_directory()
        drc.mkdir(exist_ok=True, parents=True)

        outfile = datetime.datetime.now().strftime("%Y%m%d-%H%M%S.%f") + ".tiff"
        outfile = drc / outfile

        try:
            from instamatic.processing.flatfield import apply_flatfield_correction
            flatfield, h = read_tiff(module_io.get_flatfield())
            frame = apply_flatfield_correction(self.frame, flatfield)
        except:
            frame = self.frame
        write_tiff(outfile, frame)
        print(" >> Wrote file:", outfile)


def main():
    from instamatic.utils import high_precision_timers
    high_precision_timers.enable()  # sleep timers with 1 ms resolution
    
    # enable faster switching between threads
    sys.setswitchinterval(0.001)  # seconds

    from instamatic import version
    version.register_thank_you_message()

    from instamatic import config

    date = datetime.datetime.now().strftime("%Y-%m-%d")
    logfile = config.logs_drc / f"instamatic_{date}.log"

    logging.basicConfig(format="%(asctime)s | %(module)s:%(lineno)s | %(levelname)s | %(message)s", 
                        filename=logfile, 
                        level=logging.DEBUG)

    logging.captureWarnings(True)
    log = logging.getLogger(__name__)
    log.info("Instamatic.gui started")

    from instamatic import TEMController

    # Work-around for race condition (errors) that occurs when 
    # DataCollectionController tries to access them

    tem_ctrl = TEMController.initialize(camera=DataCollectionGUI, modules=MODULES)
    
    while not tem_ctrl.cam._modules_have_loaded:
        time.sleep(0.1)

    experiment_ctrl = DataCollectionController(tem_ctrl=tem_ctrl, stream=tem_ctrl.cam, beam_ctrl=None, log=log)

    tem_ctrl.close()


if __name__ == '__main__':
    main()