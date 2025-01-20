from argparse import ArgumentParser, FileType
from copy import deepcopy
from dataclasses import dataclass
from typing import List, Optional

from roulette import BuckshotRouletteMove, Items

items_by_name = {
    "cuffs": Items.HANDCUFFS,
    "cigs": Items.CIGARETTES,
    "knife": Items.HAND_SAW,
    "beer": Items.BEER,
    "glass": Items.MAGNIFYING_GLASS,
}


@dataclass
class LogState:
    phase: Optional[int] = None
    round: Optional[int] = None
    init_charges: Optional[int] = None
    dealer_items: Optional[List[Items]] = None
    player_items: Optional[List[Items]] = None
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
        match words:

            case ["phase", phase, ",", charges, "charges"]:
                self.phase = len(phase)
                self.init_charges = int(charges)
                self.round = None
                return

            case ["round", phase, ".", round]:
                assert len(phase) == self.phase
                self.round = int(round)
                return

            case [player, "gets", *separated_item_names]:

                # skip separators (odd-numbered elements)
                item_names = separated_item_names[::2]

                items = [items_by_name[item_name.strip()] for item_name in item_names]
                if player == "dealer":
                    self.dealer_items = items
                else:
                    self.player_items = items
                return

            case ["dealer", "loads", num_live_rounds, "live", ",", num_blank_rounds, "blank"]:
                assert self.phase is not None
                assert self.round is not None
                assert self.init_charges is not None
                self.game = BuckshotRouletteMove(
                    True,
                    4,
                    self.init_charges,
                    self.init_charges,
                    int(num_live_rounds),
                    int(num_blank_rounds),
                    self.dealer_items or [],
                    self.player_items or [],
                )
                return

        assert self.game is not None
        match words:

            case ["!check", "player", "charges", "=", value]:
                assert self.game.player_health == int(value)
                return

            case ["!check", "dealer", "charges", "=", value]:
                assert self.game.dealer_health == int(value)
                return

            case ["!check", player, "items", "=", *separated_item_names]:

                # skip separators (odd-numbered elements)
                item_names = separated_item_names[::2]

                items = set(items_by_name[item_name.strip()] for item_name in item_names)
                assert set(self.game.dealer_items if player == "dealer" else self.game.player_items) == items
                return

        assert (words[0] == "player") == self.game.is_players_turn
        #match words:


def parse_logfile(f):
    logstate = LogState()
    for i, line in enumerate(f):
        try:
            logstate.parse_line(line)
        except Exception as e:
            print("line", i+1, ":", line)
            raise e


def parse_args():
    parser = ArgumentParser()
    parser.add_argument("LOGFILE", type=FileType('r'))
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    game = parse_logfile(args.LOGFILE)
