import os, sys, glob

import argparse
import pandas as pd

import time

from indexer import *


__version__ = "2017-03-09"
__author__ = "Stef Smeets"
__email__ = "stef.smeets@mmk.su.se"


TEMPLATE = """title: indexing
experiment:
  azimuth: -6.61
  pixelsize: 0.003957
  stretch: 2.43
projections:
  dmax: 10.0
  dmin: 1.0
  thickness: 100
cell:
  name: LTA
  params:
  - 24.61
  - 24.61
  - 24.61
  - 90
  - 90
  - 90
  spgr: Fm-3c
data:
  csv_out: results.csv
  drc_out: indexing
  glob: data/*.tiff
"""


def printer(data):
    """Print things to stdout on one line dynamically"""
    sys.stdout.write("\r\x1b[K"+data.__str__())
    sys.stdout.flush()


def merge_csv(csvs, csv_out):
    """Read amd combine csv files `csvs` into file csv_out

    Returns: pd.DataFrame with combined items"""
    combined = pd.concat((read_csv(csv) for csv in csvs))
    
    if len(combined) > 0:
        write_csv(csv_out, combined)
        print "Writing results to {}".format(csv_out)

    for csv in csvs:
        os.unlink(csv)

    return combined


class ProgressBar(object):
    """docstring for ProgressBar"""
    def __init__(self):
        
        self.reverse = False
        self.a = ' '
        self.b = '='
        self.width = 10
        self.delay = 1.0

    def loop(self):
        for i in range(self.width):
            if self.reverse:
                i = self.width-i
            time.sleep(self.delay)
            printer('['+self.b*(i)+self.a*(self.width-i)+']')
        self.reverse = not self.reverse
        for i in range(self.width):
            if self.reverse:
                i = self.width-i
            time.sleep(self.delay)
            printer('['+self.a*(self.width-i)+self.b*i+']')
        self.a,self.b = self.b,self.a
        
    def clear(self):
        printer('')


def multi_run(arg, procs=1, dry_run=False):
    import subprocess as sp
    from multiprocessing import cpu_count

    d = yaml_ordered_load(sys.argv[1])

    file_pat  = d["data"]["glob"]
    csv_out   = d["data"]["csv_out"]

    fns = glob.glob(file_pat)

    nfiles = len(fns)
    print "Found {} files".format(nfiles)

    csv_outs = []
    for i in xrange(procs):
        print " Chunk #{}: {} files".format(i, len(fns[i::procs]))
        root, ext = os.path.splitext(csv_out)
        csv_outs.append("{}_{}{}".format(root, i, ext))
    print

    cores = cpu_count()

    assert procs >= 0, 'Expected a positive number of processors'
    if procs > cores:
        print '{} cores detected, are you sure you want to run {} processes? [y/n]'.format(cores, procs)
        if not raw_input(' >> [y] ').lower() == 'y':
            sys.exit()

    processes = []

    t1 = time.time()

    print 'Starting processes...'
    for i in xrange(procs):
        cmd = "instamatic.index.exe {} -c {} {}".format(arg, i, procs)

        print "     >>", cmd,

        if not dry_run:
            # CREATE_NEW_CONSOLE is windows only
            p = sp.Popen(cmd, creationflags=sp.CREATE_NEW_CONSOLE)
            processes.append(p)
            print ';; started (PID={})'.format(p.pid)
        else:
            print ';; not started'
            
   
    pb = ProgressBar()
    while any(p.poll() == None for p in processes):
        pb.loop()
    pb.clear()

    t2 = time.time()

    all_results = merge_csv(csv_outs, csv_out)
    print "Time taken: {:.0f} s / {:.1f} s per image".format(t2-t1, (t2-t1)/nfiles)
    print
    print " >> Done << "


def run(arg, chunk=None, dry_run=False):
    if len(sys.argv) == 1:
        print "Usage: instamatic.index indexing.inp"
        print
        print "Example input file:"
        print 
        print TEMPLATE
        exit()

    d = yaml_ordered_load(arg)

    azimuth   = d["experiment"]["azimuth"]
    stretch   = d["experiment"]["stretch"]
    pixelsize = d["experiment"]["pixelsize"]
    
    dmin      = d["projections"]["dmin"]
    dmax      = d["projections"]["dmax"]
    thickness = d["projections"]["thickness"]
    
    params    = d["cell"]["params"]
    name      = d["cell"]["name"]
    spgr      = d["cell"]["spgr"]
    
    file_pat  = d["data"]["glob"]
    csv_out   = d["data"]["csv_out"]
    drc_out   = d["data"]["drc_out"]

    azimuth = np.radians(stretch)
    stretch = stretch / (2*100)
    tr_mat = affine_transform_ellipse_to_circle(azimuth, stretch)

    method = "powell"

    projector = Projector.from_parameters(params, spgr=spgr, name=name, dmin=dmin, dmax=dmax, thickness=thickness, verbose=True)
    indexer = Indexer.from_projector(projector, pixelsize=pixelsize)

    fns = glob.glob(file_pat)

    if chunk:
        offset, cpu_count = chunk
        root, ext = os.path.splitext(csv_out)
        csv_out = "{}_{}{}".format(root, offset, ext)
        fns = fns[offset::cpu_count]

    nfiles = len(fns)
    print "Found {} files".format(nfiles)

    if not os.path.exists(drc_out):
        os.mkdir(drc_out)
    
    all_results = {}
    
    t1 = time.time()

    for i, fn in enumerate(fns):
        print "{}/{}: {}".format(i, nfiles, fn)
          
        img, h = read_tiff(fn)
        
        img = apply_transform_to_image(img, tr_mat)
        
        cx, cy = find_beam_center(img, sigma=10)
        center = cy, cx
        
        img = remove_background_gauss(img, 2, 30, threshold=10)
        results = indexer.index(img, center, nsolutions=25)
        
        refined = indexer.refine_all(img, results, sort=True, method=method)
        all_results[fn] = refined[0]
            
        hklie = get_intensities(img, refined[0], projector)
        hklie[:,0:3] = standardize_indices(hklie[:,0:3], projector.cell)

        root, ext = os.path.splitext(os.path.basename(fn))
        out = os.path.join("indexed", root+".hkl")

        np.savetxt(out, hklie, fmt="%4d%4d%4d %7.1f %7.1f")

    t2 = time.time()

    if len(all_results) > 0:
        write_csv(csv_out, all_results)
        print "Writing results to {}".format(csv_out)
    
    print "Time taken: {:.0f} s / {:.1f} s per image".format(t2-t1, (t2-t1)/nfiles)
    print
    print " >> DONE <<"



def main():
    usage = """instamatic.index indexing.inp"""

    description = """
Program for indexing electron diffraction images.

""" 
    
    epilog = 'Updated: {}'.format(__version__)
    
    parser = argparse.ArgumentParser(#usage=usage,
                                    description=description,
                                    epilog=epilog, 
                                    formatter_class=argparse.RawDescriptionHelpFormatter,
                                    version=__version__)
    
    parser.add_argument("args", 
                        type=str, metavar="FILE",
                        help="Path to input file.")

    parser.add_argument("-j", "--procs", metavar='N',
                        action="store", type=int, dest="procs",
                        help="Number of processes to use (default = 1)")

    parser.add_argument("-c", "--chunk", metavar='N', nargs=2,
                        action="store", type=int, dest="chunk",
                        help="Used internally to specify the chunk number to process.")

    parser.add_argument("-d", "--dry",
                        action="store_true", dest="dry_run",
                        help="Runs the program, but doesn't start any processes.")

    
    parser.set_defaults(procs=1,
                        chunk=None,
                        dry_run=False,
                        resize=False,
                        )
    
    options = parser.parse_args()
    arg = options.args

    if not arg:
        parser.print_help()
        sys.exit()

    if options.procs > 1:
        multi_run(arg, procs=options.procs, dry_run=options.dry_run)
    else:
        run(arg, options.chunk)