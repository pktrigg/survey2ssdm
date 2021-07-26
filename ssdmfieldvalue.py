import sys
import os

###############################################################################
def main(*opargs, **kwargs):
    '''test rig for ssdmfieldvalue'''
    print(readvalue("SURVEY_ID", "defaultvalue"))
    print(readvalue("invalidrequest", "defaultvalue"))
###############################################################################    
def readvalue(fieldname, default=""):
    dir = os.path.dirname(os.path.abspath(__file__))
    filename = 'ssdmfieldvalue.txt'
    filename = os.path.join(dir, filename)
    if not os.path.isfile(filename):
        return default

    file = open(filename)
    for line in file:
        if line.lower().startswith(fieldname.lower()):
            fields = line.strip().split(',')
            if len(fields) > 0:
                return str(fields[1]).strip()
    
###############################################################################    
if __name__ == "__main__":
	main()
