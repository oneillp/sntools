"""Parse Nakazato fluxes.

For simulations by Nakazato et al., Astrophys. J. Supp. 205 (2013) 2, arXiv:1210.6841
and Nakazato et al., Astrophys. J. 804 (2015) 75, arXiv:1503.01236.
Flux files are available at http://asphwww.ph.noda.tus.ac.jp/snn/index.html
"""

from math import ceil, floor
from scipy.interpolate import InterpolatedUnivariateSpline as IUSpline


def parse_input(input, inflv, starttime, endtime):
    """Read simulations data from input file.

    Arguments:
    input -- prefix of file containing neutrino fluxes
    inflv -- neutrino flavor to consider
    starttime -- start time set by user via command line option (or None)
    endtime -- end time set by user via command line option (or None)
    """
    global times, dNLdE
    times = []
    dNLdE = {}

    with open(input) as infile:
        indata = [map(float, line.split()) for line in infile]

    # 21 lines (+1 empty line) per time bin, 391 bins
    chunks = [indata[22*i:22*(i+1)-1] for i in range(391)]

    # input files contain information for e, eb & x in neighbouring columns,
    # so depending on the flavor, we might need an offset
    offset = {"e": 0, "eb": 1, "x": 2, "xb": 2}[inflv]

    # for each time bin, save data to dictionaries to look up later
    for chunk in chunks:
        # first line contains time
        time = chunk[0][0] * 1000 # convert to ms
        times.append(time)

        diff_number_flux, diff_luminosity, energy_mesh = [0], [0], [0] # flux, lum = 0 at 0 MeV
        for bin_data in chunk[1:-1]: # exclude first line (time) and last line (empty)
            number_flux = bin_data[2+offset] / 1000. # convert 1/s to 1/ms
            luminosity = bin_data[5+offset] * 624.151 # convert erg/s to MeV/ms
            diff_number_flux.append(number_flux)
            diff_luminosity.append(luminosity)
            energy_mesh.append(luminosity / number_flux)

        dNLdE[time] = IUSpline(energy_mesh, diff_number_flux)

    # Compare start/end time entered by user with first/last line of input file
    _starttime = times[0]
    _endtime = times[-1]

    if not starttime:
        starttime = ceil(_starttime)
    elif starttime < _starttime:
        print("Error: Start time must be greater than earliest time in input files. Aborting ...")
        exit()

    if not endtime:
        endtime = floor(_endtime)
    elif endtime > _endtime:
        print("Error: End time must be less than latest time in input files. Aborting ...")
        exit()

    # if user entered a custom start/end time, find indices of relevant time bins
    i_min, i_max = 0, len(times) - 1
    for (i, time) in enumerate(times):
        if time < starttime:
            i_min = i
        elif time > endtime:
            i_max = i
            break

    return (starttime, endtime, times[i_min:i_max+1])


def prepare_evt_gen(binned_t):
    """Pre-compute values necessary for event generation.

    Scipy/numpy are optimized for parallel operation on large arrays, making
    it orders of magnitude faster to pre-compute all values at one time
    instead of computing them lazily when needed.

    Argument:
    binned_t -- list of time bins for generating events
    """
    # unnecessary here; linear interpolation is fast enough to do it on demand
    return None

def nu_emission(eNu, time):
    """Number of neutrinos emitted, as a function of energy.

    This is not yet the flux! The geometry factor 1/(4 pi r**2) is added later.
    Arguments:
    eNu -- neutrino energy
    time -- time ;)
    """
    # find previous/next time bin and perform linear interpolation
    for t_prev, t_next in zip(times[:-1], times[1:]):
        if time < t_next:
            break

    dNLdE_prev = dNLdE[t_prev](eNu)
    dNLdE_next = dNLdE[t_next](eNu)
    dNL = dNLdE_prev + (dNLdE_next - dNLdE_prev) * (time - t_prev) / (t_next - t_prev)

    return dNL
