"""
An implementation of a basic Shift-Reduce Parse (SRP).
CS 799.06 Graduate Independent Study in NLP/NLU.

:author: Sergey Goldobin
:date: 06/02/2020 15:51
"""
import argparse

from grammar import Grammar, Reduction
from shift_reduce_parser import SRParser, ParseSuccess


DEFAULT_GRAMMAR = '.\\grammars\\grammar.json'


def main():
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("text", help="Text to be parsed.")
    arg_parser.add_argument("-g", "--grammar", help="JSON file specifying the language grammar.")
    arg_parser.add_argument("-r", "--reduction", help="POS Tag-to-grammar reduction map.")
    args = arg_parser.parse_args()

    grammar = DEFAULT_GRAMMAR if args.grammar is None else args.grammar
    reduction = None if args.reduction is None else args.reduction
    try:
        grammar = Grammar(grammar)
        reduction = Reduction(reduction)
    except Exception as e:
        print(e)  # TODO Upgrade error handling.

    # Perform the parse of the sentence structure according to the grammar,
    parser = SRParser(grammar=grammar, reduction=reduction)
    pt = parser.parse(args.text)

    print(args.text + ':')
    if isinstance(pt, ParseSuccess):
        pt.pretty_print()
    else:
        pt.dump()


if __name__ == '__main__':
    main()
