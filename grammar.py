"""
An abstraction for easy CFG grammar interface.
CS 799.06 Graduate Independent Study in NLP/NLU.

:author: Sergey Goldobin
:date: 06/02/2020 16:18
"""

import json
from typing import *


class Symbol:
    """
    Represents a symbol of a grammar.
    """

    def __init__(self, name: str):
        self._name = name
        self.value = None
        self.components = []

    def __str__(self):
        return self._name

    def __copy__(self):
        cpy = Symbol(self._name)
        cpy.value = self.value
        cpy.components = [x for x in self.components]
        return cpy

    def __repr__(self):
        return self.__str__()

    def __hash__(self):
        return hash(self._name)

    def __eq__(self, other):
        if not isinstance(other, Symbol):
            return False
        return self._name == other._name


class Grammar:
    """
    An abstraction representing a CFG grammar.
    """

    RULE_END = Symbol('EOF')
    ROOT_SYM = Symbol('ROOT')

    def __init__(self, source_file, start_symbol="S"):
        with open(source_file, 'r') as grammar_fp:
            self.__data = json.load(grammar_fp)
        self.start_symbol = Symbol(start_symbol)

        self._rules = {Grammar.ROOT_SYM: [[self.start_symbol]]}  # Needed for parsing

        # Create a sophisticated representation of the grammar.
        for k, v in self.__data.items():
            key = Symbol(k)
            self._rules[key] = []
            for rule in v:
                self._rules[key].append([Symbol(x) for x in rule])

    def __getitem__(self, item: Symbol):
        """
        Get the production generated by a given symbol.
        :param item: The Symbol to look up.
        :return: The reduction matching the symbol or an empty list.
        """
        if item not in self._rules.keys():
            return []

        return self._rules[item]

    def match_pattern(self, pattern: List[Symbol]) -> Union[Symbol, NoReturn]:
        """
        Reduce a symbol pattern to a singular symbol.
        :param pattern:
        :return:
        """
        for from_s, rules in self._rules.items():
            for rule in rules:
                if rule == pattern:
                    return from_s.__copy__()  # Important to create a copy to prevent words 'bleeding' into each other

        return None

    def __str__(self):
        # TODO: If I have time make this fancy.
        return "Grammar"


class Reduction:
    """
    A mapping of Symbol -> Symbol reductions to adapt sophisticated POS Taggers to simple grammars.
    """

    def __init__(self, reduction_file: str):
        with open(reduction_file, 'r') as fp:
            self.__raw_data = json.load(fp)

        # In order to be useful, we transform the dictionary
        self.data = {}
        for k, vs in self.__raw_data.items():
            for v in vs:
                if v not in self.data:
                    self.data[Symbol(v)] = Symbol(k)

    def __getitem__(self, item: Symbol):
        """
        Given a Symbol, find a symbol to which it reduces.
        :param item: The symbol to reduce.
        :return:
        """
        return self.data[item].__copy__()


