# The test suite runs in <20 seconds so is worth running here to
# make sure there are no issues with the C/Cython extensions
import astropy_healpix
astropy_healpix.test()
