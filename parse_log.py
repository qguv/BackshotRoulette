from argparse import ArgumentParser, FileType
from collections import OrderedDict
from copy import deepcopy
from sys import exit

from game_state import GameState, PhaseState, Player, RoundState
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
        new_state = old_state
        for conjoined_line in conjoined_lines:
            new_state = old_state.parse_line(conjoined_line)
        return new_state

    line = line.strip()

    # ignore comments
    if line.startswith("#"):
        return old_state

    if not line:
        return old_state

    # treat commas, dots, and equals signs as separate words
    for c in ',.=':
        line = line.replace(c, f" {c} ")

    # TODO: handle repeated games in double-or-nothing mode
    if old_state.winner is not None:
        return SetupError("game over")

    words = line.split()
    if old_state.phase is None:
        # TODO: maybe give context that we can only accept phase setup commands?
        return parse_phase_setup_line(old_state, words)

    if old_state.phase.round is None:
        # TODO: maybe give context that we can only accept round setup commands?
        return parse_round_setup_line(old_state, words)

    try:
        check_query_line(old_state, words)
        return old_state
    except NoMatch:
        pass

    if (words[0] == "dealer") == old_state.phase.round.is_players_turn:
        raise TurnError()

    return parse_game_line(old_state, words)


def parse_phase_setup_line(old_state: GameState, words) -> GameState:
    new_state = deepcopy(old_state)
    match words:

        case ["phase", _phase_num, ",", _max_charges, "charges"]:
            # phase in log: one-indexed tally numerals
            # phase_num here: zero-indexed int
            phase_num = len(_phase_num) - 1
            if new_state.num_completed_phases != phase_num:
                return SetupError(f"expected phase {"I" * (new_state.num_completed_phases + 1)}")

            max_charges = int(_max_charges)

            new_state.phase = PhaseState(
                max_charges=max_charges,
                players=OrderedDict(
                    (player_name, Player(charges=max_charges))
                    for player_name in new_state.player_names
                )
            )

        case _:
            raise NoMatch("expecting phase setup line")
    return new_state

def parse_round_setup_line(old_state: GameState, words) -> GameState:
    new_state = deepcopy(old_state)
    match words:

        # just for decoration
        case ["round", _phase_num, ".", _round_num]:
            phase_num = len(_phase_num) - 1
            if phase_num != new_state.num_completed_phases:
                return SetupError(f"expected a round in phase {"I" * (new_state.num_completed_phases + 1)}")
            round_num = int(_round_num) - 1
            if round_num != new_state.phase.num_completed_rounds:
                return SetupError(f"expected round {new_state.phase.num_completed_rounds + 1}")

        case [player, "gets", *separated_item_names]:

            # skip separators (odd-numbered elements)
            item_names = separated_item_names[::2]

            items = set(items_by_name[item_name.strip()] for item_name in item_names)
            new_state.phase.players[player].items.update(items)

        # this line actually starts the round
        case ["dealer", "loads", total_live_shells, "live", ",", total_blank_shells, "blank"]:
            new_state.phase.round = RoundState(
                total_live_shells=total_live_shells,
                total_blank_shells=total_blank_shells,
            )

        case _:
            raise NoMatch("expecting round setup line")
    return new_state

def check_query_line(state: GameState, words) -> None:
    match words:

        case ["!check", player_name, "charges", "=", value]:
            player_charges = state.phase.players[player_name].charges
            if player_charges != int(value):
                raise CheckFailed(f"{player_charges} != {value}")

        case ["!check", player_name, "items", "=", *separated_item_names]:

            # skip separators (odd-numbered elements)
            item_names = separated_item_names[::2]

            items = set(items_by_name[item_name.strip()] for item_name in item_names)
            player_items = state.phase.players[player_name].items
            if player_items != items:
                raise CheckFailed(f"{sorted(player_items)} != {sorted(items)}")

        case _:
            raise NoMatch("expecting query line")

def parse_game_line(old_state: GameState, words) -> GameState:
    new_state = deepcopy(old_state)
    match words:
        case [player_name, "shoots", target_name, ",", _shell_type]:

            # parse line
            if target_name == "self":
                target_name = player_name
            is_live = (_shell_type == "live")

            new_state.shoot(target_name, is_live)

        case _:
            raise NoMatch("expecting game line")

    return new_state


def parse_logfile(f):
    game_state = GameState(player_names=["player", "dealer"])
    for i, line in enumerate(f):
        try:
            game_state = parse_line(game_state, line)
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
