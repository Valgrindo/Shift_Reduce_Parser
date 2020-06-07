# Shift_Reduce_Parser
An implementation of a Shift-Reduce parser for CS 799.06 Independent Study.


usage: parser.py [-h] [-g GRAMMAR] [-r REDUCTION] [-v] text


positional arguments:
  text                  Text to be parsed.


optional arguments:
  -h, --help            show this help message and exit
  
  -g GRAMMAR, --grammar GRAMMAR
                        JSON file specifying the language grammar.
                        
  -r REDUCTION, --reduction REDUCTION
                        POS Tag-to-grammar reduction map.
                        
  -v, --verbose         Display detailed parser operation output.
  
