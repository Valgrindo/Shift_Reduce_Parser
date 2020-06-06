"""
Parser class itself.
CS 799.06 Graduate Independent Study in NLP/NLU.

:author: Sergey Goldobin
:date: 06/02/2020 16:08
"""

from typing import *
from grammar import Grammar, Symbol, Reduction
import nltk
from string import punctuation


class ParseSuccess:
    """
    A very simple tree node with N branches.
    """

    def __init__(self, name: str, node: Symbol = None):
        self.name = name
        self.root = node

    def pretty_print(self):
        """
        Graphically display the parse tree structure.
        :return:
        """
        self._pretty_print_help(self.root, 0)

    def _pretty_print_help(self, sym: Symbol, depth):
        pad = '|\t' * depth
        val = f' ({sym.value})' if sym.value is not None else ''
        print(pad + str(sym) + val)
        for s in sym.components:
            self._pretty_print_help(s, depth + 1)


class ParseFail:
    """
    A class capturing parse failure with some debug information.
    """

    def __init__(self, parse_stack, input_stack, state):
        self.parse_stack = parse_stack
        self.input_stack = input_stack
        self.state = state

    def dump(self):
        print(f"""
Parse Failed!
    Parse stack:
        {self.parse_stack}
    Input stack:
        {self.input_stack}
    State:
        {self.state}
        """)


class StateFrame:

    def __init__(self, data: Tuple[Symbol, int, int]):
        self.from_sym = data[0]
        self.to_sym = []
        self.rule = data[1]
        self.constituent = data[2]
        self.children = []
        self.parent = None
        self.to_delete = False

    def __hash__(self):
        return hash((self.from_sym, self.rule, self.constituent, self.to_sym))

    def __repr__(self):
        return f'({self.from_sym} -> {self.to_sym} | {self.constituent})'

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

    def __init__(self, grammar: Grammar, reduction: Reduction = None):
        self._grammar = grammar
        self.__parse_stack = []
        self.__input_stack = []
        self._reduction = reduction
        self._needs_prune = False

        # nltk.download('punkt')

        # The state of the parser is a collection of pointers to the next terminal symbol through all currently
        # accessible branches of the grammar.
        # Each state record is a tuple (FromSymbol, rule, constituent)
        # (NP, 1, 2) ==>
        # NP -> <some rule #0>
        # NP -> ART N *PP
        root_frame = StateFrame((Grammar.ROOT_SYM, 0, 0))
        root_frame.to_sym = [grammar.start_symbol]
        self.__state = root_frame
        self._set_looking_for(root_frame, create_all=True)

    def dump_state(self):
        return self._dump_state_help(0, self.__state)

    def _dump_state_help(self, depth: int, frame: StateFrame):
        pad = '|\t' * depth
        result = pad + ' ' + str(frame) + '\n'
        for f in frame.children:
            result += self._dump_state_help(depth + 1, f)
        return result

    def _set_looking_for(self, start: StateFrame, create_all=False):
        """
        Navigate all rules reachable from a given state of the grammar.
        :param start: The symbol to start from.
        :param create_all: If true, will only do work on leaf nodes.
        :return: None
        """
        # Only perform this if constituent is not out of range
        if start.constituent < len(start.to_sym):
            if create_all or not start.children:
                rules = self._grammar[start.to_sym[start.constituent]]  # Get all the rules visible from the start.
                for rule in range(len(rules)):
                    if not any(f.rule == rule for f in start.children):
                        # Create a "fresh" frame for this rule
                        frame = StateFrame((start.to_sym[start.constituent], rule, 0))
                        frame.to_sym = [x for x in rules[rule]]
                        frame.parent = start
                        start.children.append(frame)  # Indicate that this frame is a descendant of start

            # Now, go through existing children and expand their rules based on their cursors
            for c in start.children:
                self._set_looking_for(c)

    def _look_for(self, state_frame: StateFrame) -> Symbol:
        """
        Fetch a constituent that a state frame refers to.
        :param state_frame: An entry from parser's state representation.
        :return: A referenced symbol.
        """
        if state_frame.constituent >= len(self._grammar[state_frame.from_sym][state_frame.rule]):
            return Grammar.RULE_END
        return self._grammar[state_frame.from_sym][state_frame.rule][state_frame.constituent]

    def _traverse_state(self, root: StateFrame) -> List[StateFrame]:
        """
        Perform a BFS of the state tree.
        :return:
        """
        result = []

        if not root.children:
            return []

        result.extend(root.children)  # Gather all nodes on the current level.

        for f in root.children:
            sublist = self._traverse_state(f)
            result.extend(sublist)

        return result

    def _reduce(self, frames: List[StateFrame]):
        """
        Given a state frame, consolidate the parse stack.
        :param frames:
        :return:
        """
        # Investigate the state tree. If any frame's children can be reduced,
        # create an appropriate entry on the input stack and eliminate all children.

        # It is possible for there to be multiple rules of equal length anf equal depth in the tree all ready for
        # reduction. In such case, eliminate all the affected children sets.
        to_reduce = []
        for frame in frames:
            if len(self._grammar[frame.from_sym][frame.rule]) == frame.constituent:
                # Found a frame that could be reduced. Check if it has a higher reduction priority.
                # BFS traversal works well because frames examined first are higher on the tree.
                if not to_reduce:
                    to_reduce.append(frame)
                elif frame == to_reduce[0]:
                    to_reduce.append(frame)
                elif frame.constituent >= to_reduce[0].constituent:
                    to_reduce = [frame]

        # Compute which symbol the frame reduces to.
        to_take = len(self._grammar[to_reduce[0].from_sym][to_reduce[0].rule])

        pattern = [self.__parse_stack.pop() for _ in range(to_take)]
        pattern.reverse()

        reduction = self._grammar.match_pattern(pattern)
        if reduction is None:
            raise ValueError(f'Could not reduce pattern {pattern}')

        print(f'\nReduce {reduction} <== {pattern}')

        # Push the reduction back onto the input stack
        reduction.components = pattern
        self.__input_stack.append(reduction)

        # Finally, blow away the reduced state and ALL ITS SIBLINGS
        for f in to_reduce:
            f.parent.children.clear()

    def _can_reduce(self, frame: StateFrame):
        if not frame.children:
            return frame.constituent == len(self._grammar[frame.from_sym][frame.rule])

        return any([self._can_reduce(f) for f in frame.children])

    def _shift(self, token: Symbol, frames: List[StateFrame]):
        for f in frames:
            # If the frame has no children, it is a leaf.
            if not f.children:
                # If it is a leaf that matches the token, advance it.
                if self._look_for(f) == token:
                    f.constituent += 1  # Advance the frame pointer by 1 symbol
                else:
                    # A leaf that did not get advanced can never happen.
                    # Mark for deletion
                    f.to_delete = True
                    self._needs_prune = True

            # If not a leaf, recurse.
            self._shift(token, f.children)

    def _prune_state(self, frame: StateFrame):
        if not frame.children:
            return False
        # We are at a second-from-the-bottom node if all its children are leaves
        frame.children = list(filter(lambda c: c.children or not c.to_delete, frame.children))

        # If the frame got rid of all its children, then it needs to go as well.
        if not frame.children:
            frame.to_delete = True
            self._needs_prune = True

        for c in frame.children:
            self._prune_state(c)

    def _can_shift(self, token: Symbol, frame: StateFrame):
        """
        Test if a shift can be performed somewhere in the state tree.
        :param token: The received token.
        :param frame: Frame to start checking at.
        :return:
        """
        # Once down to a leaf, check if it expects this token.
        if not frame.children:
            return self._look_for(frame) == token

        # For frames with children, collect the result on every child.
        return self._look_for(frame) == token or any([self._can_shift(token, f) for f in frame.children])

    def _parse_fail(self) -> ParseFail:
        """
        Something did not succeed. Return the current state of the parser.
        :return:
        """
        return ParseFail(self.__parse_stack, self.__input_stack, self.__state)

    def parse(self, text: str) -> Union[ParseSuccess, ParseFail]:
        """
        Obtain a grammatical parse tree for a given sentence.
        :param text: The sentence to parse.
        :return: A nested structure representing the parse tree.
        """
        # Clean the input text.
        text = ''.join(filter(lambda c: c not in punctuation, text))

        # Tokenize and tag the text.
        word_mapping = dict(nltk.pos_tag(nltk.word_tokenize(text)))
        print(f'POS Tags:\n {word_mapping}')

        self.__input_stack = nltk.word_tokenize(text)
        self.__input_stack.reverse()  # Sentence should appear in order

        while len(self.__input_stack) > 1 or self.__parse_stack:  # While there is sentence left.
            # Parser state contains the set of symbols expected for a valid structure.
            # Read in a token and determine if it is expected.
            print(self.dump_state())
            word = None
            if self.__input_stack:
                word = self.__input_stack.pop()
            if isinstance(word, str):
                token = Symbol(word_mapping[word])  # TODO: Handle missing value?

                if self._reduction is not None:
                    token = self._reduction[token]
                token.value = word
            else:
                token = word

            # First, we must check if a shift or a reduction if possible.
            # If a shift AND a reduction are possible, favor a shift
            # If only one operation is possible, perform it.
            # If none are possible, then the parser is in an error state.
            can_reduce = self._can_reduce(self.__state)
            can_shift = self._can_shift(token, self.__state)

            if can_shift:
                print(f'\nShift {word} ==> {token}')
                # A shift action consumes a token form the input stack and advances all matching rule pointers.
                self.__parse_stack.append(token)

                # Examine the current state frames. If we find one that expects a token that we found,
                # perform a shift action.
                self._shift(token, self.__state.children)

                while self._needs_prune:
                    # Shift marked some impossible rules for deletion. Execute.
                    self._needs_prune = False
                    self._prune_state(self.__state)

                # Find new paths that could have been generated by the shift
                self._set_looking_for(self.__state.children[0])  # The top-level Sentence
            elif can_reduce:
                # Since no shift was performed, the token is not consumed.
                if word is not None:
                    self.__input_stack.append(word)

                self._reduce(self._traverse_state(self.__state))
            else:
                return self._parse_fail()

        # The last thing remaining on the parse stack is the parse tree root.
        return ParseSuccess(name="Root", node=self.__input_stack.pop())

