import argparse
parser = argparse.ArgumentParser()
parser.add_argument("input", help="choice a input file")
parser.add_argument("-o", "--o", help="choice a output file")
parser.add_argument("-type", "--type", choices=["milili"], help="choice a type of ISA", default="milili")
args = parser.parse_args()
