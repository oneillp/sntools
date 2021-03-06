from math import pi, sqrt, log
from scipy import integrate

# Note: `es.py` uses `__builtin__._flavor` (which is set in `genevts.py`)

targets_per_molecule = 10 # number of electrons per water molecule
pid = 11
possible_flavors = ["e", "eb", "x", "xb"]


'''
Particle physics section.
* cross section for neutrino-electron scattering
* directionality of scattered electron

Based on the Appendices of Bahcall et al. 1995 (https://doi.org/10.1103/PhysRevD.51.6146).
This calculation includes radiative corrections from QCD & QED effects.

For differences between neutrinos/antineutrinos and a derivation of directionality,
see https://www.kvi.nl/~loehner/saf_seminar/2010/neutrino-electron-interactions.pdf
Note that it uses different conventions (e.g. minus signs) from Bahcall et al.!
'''
sin2theta_w = 0.2317 # weak mixing angle
alpha = 1 / 137.036 # fine structure constant
mE = 0.5109989 # electron mass (MeV)
gF = 1.16637e-11 # Fermi coupling constant
rho_NC = 1.0126 # numerical factor from Bahcall et al.

_cache = {} # save time by avoiding repeat calculations
def spence(n):
    if not _cache.has_key(n):
        _cache[n] = integrate.quad(lambda t: log(abs(1-t))/t, 0, n) [0]
    return _cache[n]


def dSigma_dE(eNu, eE):
    if eE < bounds_eE(eNu)[0] or eE > bounds_eE(eNu)[1]:
        return 0

    # Appendix A: Radiative Corrections
    L = sqrt(eE**2 - mE**2)
    beta = L / eNu
    T = eE - mE # kinetic energy of recoil electron
    z = T / eNu
    x = sqrt(1 + 2*mE/T)
    I = 1./6 * (1./3 + (3 - x**2) * (x/2. * log((x+1)/(x-1)) - 1))

    if _flavor in ("e", "eb"):
        k = 0.9791 + 0.0097 * I
    elif _flavor in ("x", "xb"):
        k = 0.9970 - 0.00037 * I

    g1 = rho_NC * (0.5 - k * sin2theta_w)
    g2 = -rho_NC * k * sin2theta_w

    if _flavor == "e":
        gL = g1 - 1
        gR = g2
    elif _flavor == "eb":
        gL = g2
        gR = g1 - 1
    elif _flavor == "x":
        gL = g1
        gR = g2
    elif _flavor == "xb":
        gL = g2
        gR = g1

    # Appendix B: QED Effects
    f0 = eE/L * log((eE+L)/mE) - 1 # common factor of all three f_*
    log_zmE = log(1-z-mE/(eE+L)) # Warning: imprecise at low E, throws ValueError in extreme cases

    # fMinus(z)
    f1 = f0 * (2 * log_zmE - log(1-z) - log(z)/2. - 5./12) \
           + 0.5 * (spence(z) - spence(beta)) \
           - 0.5 * log(1-z)**2 - (11./12 + z/2.) * log(1-z) \
           + z * (log(z) + 0.5 * log(2*eNu / mE)) \
           - (31./18 + 1./12 * log(z)) * beta \
           - 11./12 * z + z**2 / 24.

    # (1-z)**2 * fPlus(z)
    f2 = f0 * ((1-z)**2 * (2*log_zmE - log(1-z) - log(z)/2. - 2./3) - (z**2 * log(z) + 1 - z)/2.) \
           - (1-z)**2 / 2. * (log(1-z)**2 + beta * (spence(1-z) - log(z)*log(1-z))) \
           + log(1-z) * (z**2 / 2. * log(z) + (1-z)/3. * (2*z - 0.5)) \
           - z**2 / 2. * spence(1-z) - z * (1-2*z)/3 * log(z) - z * (1-z)/6 \
           - beta/12. * (log(z) + (1-z) * (115 - 109 * z)/6.)

    # fPlusMinus(z)
    f3 = f0 * 2 * log_zmE

    result = 2*mE*gF**2 / pi * (gL**2 * (1 + alpha/pi * f1)
                              + gR**2 * ((1-z)**2 + alpha/pi * f2)
                              - gR * gL * mE/eNu * z * (1 + alpha/pi * f3)
                              )
    if result < 0:
        if eNu < 0.8:
            # Approximations in f_* may be imprecise at very low energies.
            # This is below threshold in HK anyway, so we suppress it.
            result = 0
        else:
            raise ValueError("Calculated negative cross section for E_nu=%f, E_e=%f. Aborting..." % (eNu, eE))

    return result


# energy of electron scattered into direction cosT by a neutrino with energy eNu
def get_eE(eNu, cosT):
    return mE + (2 * mE * eNu**2 * cosT**2) / ((mE + eNu)**2 - eNu**2 * cosT**2)

# distribution of scattering angles
def dSigma_dCosT(eNu, cosT):
    if cosT < 0: # backward scattering is kinematically impossible
        return 0

    dE_dCosT = 4 * mE * eNu**2 * (mE+eNu)**2 * cosT / ((mE+eNu)**2 - eNu**2 * cosT**2)**2
    eE = get_eE(eNu, cosT)
    return dE_dCosT * dSigma_dE(eNu, eE)


# Bounds for integration over eE
eE_min = 0.77 # Cherenkov threshold in water (refraction index n=1.34)
def bounds_eE(eNu, *args): # ignore additional arguments handed over by integrate.nquad()
    eE_max = mE + 2*eNu**2 / (2*eNu + mE) # this is get_eE(eNu, cosT=1)
    return [eE_min, eE_max]


# Bounds for integration over eNu
def eNu_min(eE):
    T = eE - mE
    return T/2. * (1 + sqrt(1 + 2*mE/T)) # inversion of eE_max(eNu)
eNu_max = 100
bounds_eNu = [eNu_min(eE_min), eNu_max]

# minimum/maximum neutrino energy that can produce a given positron energy
def _bounds_eNu(eE):
    return [eNu_min(eE), eNu_max]
