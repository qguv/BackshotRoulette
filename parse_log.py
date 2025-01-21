from argparse import ArgumentParser, FileType
from dataclasses import dataclass
from typing import List, Optional
from sys import exit

from roulette import BuckshotRouletteMove, Items, ValidMoves

items_by_name = {
    "cuffs": Items.HANDCUFFS,
    "cigs": Items.CIGARETTES,
    "knife": Items.HAND_SAW,
    "beer": Items.BEER,
    "glass": Items.MAGNIFYING_GLASS,
}


class LogParseError(Exception):
    '''exited without validating the entire log'''
    pass


class NoMatch(LogParseError):
    '''line didn't match any known pattern'''
    pass


class SetupError(LogParseError):
    '''couldn't start the game because setup was incomplete'''
    pass


class CheckFailed(LogParseError):
    '''!check line failed'''
    pass


class GameError(LogParseError):
    '''log line doesn't follow logic of game'''
    pass


class TurnError(GameError):
    '''out-of-turn move'''
    def __str__(self):
        return "not your turn"


@dataclass
class LogState:
    phase: Optional[int] = None
    round: Optional[int] = None
    init_charges: Optional[int] = None
    dealer_first_items: Optional[List[Items]] = None
    player_first_items: Optional[List[Items]] = None
    game: Optional[BuckshotRouletteMove] = None

    def parse_line(self, line):

        # separate lines conjoined by a semicolon
        conjoined_lines = line.split(";")
        if len(conjoined_lines) > 1:
            for conjoined_line in conjoined_lines:
                self.parse_line(conjoined_line)

        line = line.strip()

        # ignore comments
        if line.startswith("#"):
            return

        if not line:
            return

        # treat commas, dots, and equals signs as separate words
        for c in ',.=':
            line = line.replace(c, f" {c} ")

        words = line.split()
        try:
            return self.parse_setup_line(words)
        except NoMatch:
            pass

        if self.game is None:
            raise SetupError("not in a game phase yet")

        try:
            return self.parse_query_line(words)
        except NoMatch:
            pass

        if (words[0] == "dealer") != self.game.is_players_turn:
            return TurnError()

        return self.parse_game_line(words)

    def parse_setup_line(self, words):
        match words:

            case ["phase", phase, ",", charges, "charges"]:
                self.phase = len(phase)
                self.init_charges = int(charges)
                self.round = None
                self.game = None

            case ["round", phase, ".", round]:
                if len(phase) != self.phase:
                    return SetupError("round not in that phase")
                self.round = int(round)

            case [player, "gets", *separated_item_names]:

                # skip separators (odd-numbered elements)
                item_names = separated_item_names[::2]

                items = set(items_by_name[item_name.strip()] for item_name in item_names)

                match player:
                    case "player":
                        if game:
                            self.game.player_items.extend(items)
                        else:
                            self.player_first_items = items
                    case _:
                        if game:
                            self.game.dealer_items.extend(items)
                        else:
                            self.dealer_first_items = items

            case ["dealer", "loads", num_live_rounds, "live", ",", num_blank_rounds, "blank"]:
                if self.phase is None:
                    raise SetupError("need to declare the current phase before bullets are loaded")
                if self.init_charges is None:
                    raise SetupError("need to declare the number of charges for this phase before bullets are loaded")
                if self.round is None:
                    raise SetupError("need to declare the current round before bullets are loaded")

                self.game = BuckshotRouletteMove(
                    True,
                    4,
                    self.init_charges,
                    self.init_charges,
                    int(num_live_rounds),
                    int(num_blank_rounds),
                    self.dealer_first_items or [],
                    self.player_first_items or [],
                )

            case _:
                raise NoMatch()

    def parse_query_line(self, words):
        match words:

            case ["!check", "player", "charges", "=", value]:
                if self.game.player_health != int(value):
                    raise CheckFailed(f"{self.game.player_health} != {value}")

            case ["!check", "dealer", "charges", "=", value]:
                if self.game.dealer_health != int(value):
                    raise CheckFailed(f"{self.game.dealer_health} != {value}")

            case ["!check", player, "items", "=", *separated_item_names]:

                # skip separators (odd-numbered elements)
                item_names = separated_item_names[::2]

                items = set(items_by_name[item_name.strip()] for item_name in item_names)
                if set(self.game.dealer_items if player == "dealer" else self.game.player_items) != items:
                    raise CheckFailed(f"{sorted(self.game.dealer_items)} != {sorted(items)}")

            case _:
                raise NoMatch()

    def parse_game_line(self, words):
        match words:
            case ["player", "shoots", "self", ",", round_type] | ["dealer", "shoots", "player", ",", round_type]:
                self.game.current_shell = round_type
                self.game.move(ValidMoves.SHOOT_PLAYER)

            case ["player", "shoots", "dealer", ",", round_type] | ["dealer", "shoots", "self", ",", round_type]:
                self.game.current_shell = round_type
                self.game.move(ValidMoves.SHOOT_DEALER)

            case _:
                raise NoMatch()


def parse_logfile(f):
    logstate = LogState()
    for i, line in enumerate(f):
        try:
            logstate.parse_line(line)
        except LogParseError as e:
            print("line", i+1)
            print(line.strip())
            print(e)
            return
    return logstate


def parse_args():
    parser = ArgumentParser()
    parser.add_argument("LOGFILE", type=FileType('r'))
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    game = parse_logfile(args.LOGFILE)
    error_when = game is None
    exit(error_when)
