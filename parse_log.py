from argparse import ArgumentParser, FileType
from copy import deepcopy
from sys import exit

from game_state import GameState
from roulette import Items, ValidMoves

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


def parse_line(old_state: GameState, line):

    # separate lines conjoined by a semicolon
    conjoined_lines = line.split(";")
    if len(conjoined_lines) > 1:
        for conjoined_line in conjoined_lines:
            old_state.parse_line(conjoined_line)

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
        return update_from_setup_line(old_state, words)
    except NoMatch:
        pass

    if old_state.game is None:
        raise SetupError("not in a game phase yet")

    try:
        check_query_line(old_state, words)
        return
    except NoMatch:
        pass

    if (words[0] == "dealer") != old_state.game.is_players_turn:
        return TurnError()

    return old_state.parse_game_line(words)


def update_from_setup_line(old_state, words):
    new_state = deepcopy(old_state)
    match words:

        case ["phase", phase, ",", charges, "charges"]:
            new_state.phase = len(phase)
            new_state.init_charges = int(charges)
            new_state.round = None
            new_state.game = None

        case ["round", phase, ".", round]:
            if len(phase) != new_state.phase:
                return SetupError("round not in that phase")
            new_state.round = int(round)

        case [player, "gets", *separated_item_names]:

            # skip separators (odd-numbered elements)
            item_names = separated_item_names[::2]

            items = set(items_by_name[item_name.strip()] for item_name in item_names)

            match player:
                case "player":
                    if game:
                        new_state.game.player_items.extend(items)
                    else:
                        new_state.player_first_items = items
                case _:
                    if game:
                        new_state.game.dealer_items.extend(items)
                    else:
                        new_state.dealer_first_items = items

        case ["dealer", "loads", num_live_rounds, "live", ",", num_blank_rounds, "blank"]:
            if new_state.phase is None:
                raise SetupError("need to declare the current phase before bullets are loaded")
            if new_state.init_charges is None:
                raise SetupError("need to declare the number of charges for this phase before bullets are loaded")
            if new_state.round is None:
                raise SetupError("need to declare the current round before bullets are loaded")

            new_state.game = BuckshotRouletteMove(
                True,
                4,
                new_state.init_charges,
                new_state.init_charges,
                int(num_live_rounds),
                int(num_blank_rounds),
                new_state.dealer_first_items or [],
                new_state.player_first_items or [],
            )

        case _:
            raise NoMatch()
    return new_state

def check_query_line(state, words):
    match words:

        case ["!check", "player", "charges", "=", value]:
            if state.game.player_health != int(value):
                raise CheckFailed(f"{state.game.player_health} != {value}")

        case ["!check", "dealer", "charges", "=", value]:
            if state.game.dealer_health != int(value):
                raise CheckFailed(f"{state.game.dealer_health} != {value}")

        case ["!check", player, "items", "=", *separated_item_names]:

            # skip separators (odd-numbered elements)
            item_names = separated_item_names[::2]

            items = set(items_by_name[item_name.strip()] for item_name in item_names)
            if set(state.game.dealer_items if player == "dealer" else state.game.player_items) != items:
                raise CheckFailed(f"{sorted(state.game.dealer_items)} != {sorted(items)}")

        case _:
            raise NoMatch()

def update_from_game_line(self, words):
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
    game_state = GameState()
    for i, line in enumerate(f):
        try:
            game_state = parse_line(line)
        except LogParseError as e:
            print("line", i+1)
            print(line.strip())
            print(e)
            return


def parse_args():
    parser = ArgumentParser()
    parser.add_argument("LOGFILE", type=FileType('r'))
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    game = parse_logfile(args.LOGFILE)
    error_when = game is None
    exit(error_when)
