"""
Parser class itself.
CS 799.06 Graduate Independent Study in NLP/NLU.

:author: Sergey Goldobin
:date: 06/02/2020 16:08
"""

from typing import *
from grammar import Grammar, Symbol
import nltk


class ParseTree:
    """
    A very simple tree with N branches.
    """

    def __init__(self, node: Symbol):
        self.node = node
        self.children = []


class StateFrame:

    def __init__(self, data: Tuple[Symbol, int, int]):
        self.from_sym = data[0]
        self.rule = data[1]
        self.constituent = data[2]

    def __hash__(self):
        return hash((self.from_sym, self.rule, self.constituent))

    def __eq__(self, other):
        if not isinstance(other, StateFrame):
            return False

        return self.from_sym == other.from_sym and self.rule == other.rule and self.constituent == other.constituent


class SRParser:

    def __init__(self, grammar: Grammar):
        self._grammar = grammar
        self.__parse_stack = []
        self.__input_stack = []

        # nltk.download('punkt')

        # The state of the parser is a collection of pointers to the next terminal symbol through all currently
        # accessible branches of the grammar.
        # Each state record is a tuple (FromSymbol, rule, constituent)
        # (NP, 1, 2) ==>
        # NP -> <some rule #0>
        # NP -> ART N *PP
        self.__state = []
        self._set_looking_for(self._grammar.start_symbol)

    def _set_looking_for(self, start: Symbol):
        """
        Navigate all rules reachable from a given state of the grammar.
        :param start: The symbol to start from.
        :return: None
        """
        rules = self._grammar[start]  # Get all the rules visible from the current start.

        for rule in range(len(rules)):
            for sym in range(len(rules[rule])):
                # If it is possible to navigate to another rule from here, record the position and recurse
                # Otherwise, record the position and abort.
                frame = StateFrame((start, rule, sym))
                if frame not in self.__state:
                    self.__state.append(frame)

                # If this symbol translates to any other rules:
                symbol = rules[rule][sym]
                if self._grammar[symbol]:
                    self._set_looking_for(symbol)
                break  # The rule did not recurse further, move to next

    def _look_for(self, state_frame: StateFrame) -> Symbol:
        """
        Fetch a constituent that a state frame refers to.
        :param state_frame: An entry from parser's state representation.
        :return: A referenced symbol.
        """
        from_s, rule, sym = state_frame
        return self._grammar[from_s][rule][sym]

    def _reduce(self, frame: StateFrame):
        """
        Given a state frame, consolidate the parse stack.
        :param frame:
        :return:
        """
        to_take = len(self._grammar[frame.from_sym][frame.rule])

        pattern = [self.__parse_stack.pop() for _ in range(to_take)]
        pattern.reverse()

        reduction = self._grammar.match_pattern(pattern)
        if reduction is None:
            raise ValueError(f'Could not reduce pattern {pattern}')

        reduction.components = pattern
        self.__parse_stack.append(reduction)
        self.__state.remove(frame)

    def parse(self, text: str) -> Symbol:
        """
        Obtain a grammatical parse tree for a given sentence.
        :param text: The sentence to parse.
        :return: A nested structure representing the parse tree.
        """
        #word_mapping = dict(nltk.pos_tag(nltk.word_tokenize(text)))
        word_mapping = {'The': 'ART', 'man': 'N', 'ate': 'V', 'carrot': 'N'}

        self.__input_stack = nltk.word_tokenize(text)
        self.__input_stack.reverse()  # Sentence should appear in order

        while self.__input_stack:  # While there is sentence left.
            # Parser state contains the set of symbols expected for a valid structure.
            # Read in a token and determine if it is expected.
            word = self.__input_stack.pop()
            token = word_mapping[word]  # TODO: Handle missing value
            expected = [self._look_for(x) for x in self.__state]

            # Unexpected token. Parse impossible.
            if token not in expected:
                return Symbol("None")

            # The token matches a step in one of the followed rules.
            self.__parse_stack.append(token)

            # Update the state by moving the index in the rule that matched.
            for frame in self.__state:
                if self._look_for(frame) == token:
                    frame.constituent += 1

                # TODO Handle ambiguity of proper prefixes here.

                # Detect if the advance triggered a reduction action
                if len(self._grammar[frame.from_sym][frame.rule]) == frame.constituent:
                    # A rule has been followed to completion.
                    # Remove the frame from the state and reduce the constituents on the parse stack
                    self._reduce(frame)

        # The last thing remaining on the parse stack is the parse tree root.
        return self.__parse_stack.pop()

