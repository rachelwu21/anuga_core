#--------------------------------
# import modules
#--------------------------------
from fabricate import *
from validation_tests.utilities import run_validation_script

# Setup the python scripts which produce the output for this
# validation test
def build():
    #run_validation_script('run_problem.py')
    #run_validation_script('plot_problem.py')
    pass

def clean():
    autoclean()

main()



