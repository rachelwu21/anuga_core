#--------------------------------
# import modules
#--------------------------------
from fabricate import *
from validation_tests.utilities import run_validation_script


# Setup the python scripts which produce the output for this
# validation test
def build():
    run_validation_script('runup.py')
    run_validation_script('plot_runup.py')

def clean():
    autoclean()

main()