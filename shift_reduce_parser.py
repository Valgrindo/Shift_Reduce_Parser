"""
Parser class itself.
CS 799.06 Graduate Independent Study in NLP/NLU.

:author: Sergey Goldobin
:date: 06/02/2020 16:08
"""

from typing import *
from grammar import Grammar, Symbol
import nltk


class ParseNode:
    """
    A very simple tree node with N branches.
    """

    def __init__(self, name: str, node: Symbol = None):
        self.name = name
        self.node = node
        self.partial = []

    def pretty_print(self):
        """
        Graphically display the parse tree structure.
        :return:
        """
        depth = 0
        if self.partial:
            for pp in self.partial:
                self._pretty_print_help(pp, depth)
        else:
            self._pretty_print_help(self.node, depth)

    def _pretty_print_help(self, sym: Symbol, depth):
        pad = '|\t' * depth
        val = f' ({sym.value})' if sym.value is not None else ''
        print(pad + str(sym) + val)
        for s in sym.components:
            self._pretty_print_help(s, depth + 1)


class StateFrame:

    def __init__(self, data: Tuple[Symbol, int, int]):
        self.from_sym = data[0]
        self.rule = data[1]
        self.constituent = data[2]

    def __hash__(self):
        return hash((self.from_sym, self.rule, self.constituent))

    def __repr__(self):
        return f'({self.from_sym} -> {self.rule} {self.constituent})'

    def comp_by_rule(self, other):
        """
        Perform a fuzzy comparison of two StateFrames.
        StateFrames are equal if the refer to the same rule, but not necessarily the same constituent.
        :param other: An object to compare against.
        :return:
        """
        if not isinstance(other, StateFrame):
            return False

        return self.from_sym == other.from_sym and self.rule == other.rule

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
                if not any(frame.comp_by_rule(s) for s in self.__state):
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
        if state_frame.constituent >= len(self._grammar[state_frame.from_sym][state_frame.rule]):
            return Grammar.RULE_END
        return self._grammar[state_frame.from_sym][state_frame.rule][state_frame.constituent]

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
        self.__input_stack.append(reduction)

        # Upon reduction, remove all progress from rules yielded by the start symbol.
        # For example, if we were simultaneously building a VP using
        # VP -> V NP
        # VP -> V INF
        # And the first one resolved successfully, there is no need for the second one.
        self.__state = list(filter(lambda x: x.from_sym != frame.from_sym, self.__state))

    def _get_partial_parse(self) -> ParseNode:
        """
        Something did not succeed. Return the current state of the parser,
        :return:
        """
        partial = ParseNode(name="PartialParse")
        partial.partial = [x for x in self.__parse_stack]
        return partial

    def parse(self, text: str) -> ParseNode:
        """
        Obtain a grammatical parse tree for a given sentence.
        :param text: The sentence to parse.
        :return: A nested structure representing the parse tree.
        """
        #word_mapping = dict(nltk.pos_tag(nltk.word_tokenize(text)))
        word_mapping = {'the': 'ART', 'man': 'N', 'ate': 'V', 'carrot': 'N', 'The': 'ART'}

        self.__input_stack = nltk.word_tokenize(text)
        self.__input_stack.reverse()  # Sentence should appear in order

        while len(self.__input_stack) > 1 or self.__parse_stack:  # While there is sentence left.
            # Parser state contains the set of symbols expected for a valid structure.
            # Read in a token and determine if it is expected.
            word = None
            if self.__input_stack:
                word = self.__input_stack.pop()
            if isinstance(word, str):
                token = Symbol(word_mapping[word])  # TODO: Handle missing value
                token.value = word
            else:
                token = word

            # First, we must check if a shift or a reduction if possible.
            # If a shift AND a reduction are possible, favor a shift
            # If only one operation is possible, perform it.
            # If none are possible, then the parser is in an error state.
            can_reduce = any(len(self._grammar[f.from_sym][f.rule]) == f.constituent for f in self.__state)
            can_shift = any(self._look_for(f) == token for f in self.__state)

            if can_shift:
                # A shift action consumes a token form the input stack and advances all matching rule pointers.
                expected = set([self._look_for(f) for f in self.__state])

                # Unexpected token. Parse impossible.
                if token not in expected:
                    return self._get_partial_parse()

                # The token matches a step in one of the followed rules.
                self.__parse_stack.append(token)

                # Examine the current state frames. If we find one that expects a token that we found,
                # perform a shift action.
                state_snapshot = [x for x in self.__state]
                for frame in state_snapshot:
                    # If the input matches the expectations of this state, advance the constituent pointer
                    if self._look_for(frame) == token:
                        frame.constituent += 1

                # If we performed any shifts, there may be new frames we need to add to the state.
                state_snapshot = [x for x in self.__state]
                for s in state_snapshot:
                    frame_target = self._look_for(s)
                    if frame_target != Grammar.RULE_END:
                        self._set_looking_for(frame_target)

            elif can_reduce:
                # Since no shift was performed, the token is not consumed.
                if word is not None:
                    self.__input_stack.append(word)

                # No shifts were performed. See if any reductions can be done.
                # Reductions higher on the state stack take priority unless the higher-level reduction
                # requires more constituents.
                to_reduce = None
                for frame in self.__state:
                    if len(self._grammar[frame.from_sym][frame.rule]) == frame.constituent:
                        # Found a frame that could be reduced. Check if it has a higher reduction priority.
                        # Left-to right stack ordering works well because frames examned first are lower on the stack.
                        if not to_reduce or frame.constituent >= to_reduce.constituent:
                            to_reduce = frame

                self._reduce(to_reduce)
            else:
                return self._get_partial_parse()

        # The last thing remaining on the parse stack is the parse tree root.
        return ParseNode(name="Root", node=self.__input_stack.pop())

