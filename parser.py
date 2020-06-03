"""
An implementation of a basic Shift-Reduce Parse (SRP).
CS 799.06 Graduate Independent Study in NLP/NLU.

:author: Sergey Goldobin
:date: 06/02/2020 15:51
"""

from sys import argv
import json

from grammar import Grammar, Symbol
from shift_reduce_parser import SRParser


DEFAULT_GRAMMAR = '.\\grammars\\grammar.json'


def main():
    if len(argv) != 2 and len(argv) != 3:
        print('Usage: python parser.py "text to parse" [<grammar>]')
        print('\t<grammar> is a JSON file specifying the language grammar.\n')
        exit(1)

    grammar_source = DEFAULT_GRAMMAR if len(argv) == 2 else argv[2]
    grammar = None
    try:
        grammar = Grammar(grammar_source)  # TODO Maybe make a more sophisticated representation of the grammar?
    except Exception as e:
        print(e)  # TODO Upgrade error handling.

    # Perform the parse of the sentence structure according to the grammar,
    parser = SRParser(grammar=grammar)
    pt = parser.parse(argv[1])

    print(f'{argv[1]}:')
    pt.pretty_print()


if __name__ == '__main__':
    main()
