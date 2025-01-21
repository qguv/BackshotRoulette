from collections import OrderedDict
from dataclasses import dataclass, field
from typing import List, Optional, Set

from roulette import Items

# true is live, false is blank
type ShellType = bool

@dataclass
class RoundState:
    total_live_shells: int
    total_blank_shells: int
    past_shells: List[ShellType] = field(default_factory=list)
    is_players_turn: bool = True
    gun_is_sawed: bool = False
    handcuffed_player_names: Set[str] = field(default_factory=set)

    def remaining_live_shells(self) -> int:
        return self.total_live_shells - sum(1 for is_live in self.past_shells if is_live)

    def remaining_blank_shells(self) -> int:
        return self.total_blank_shells - sum(1 for is_live in self.past_shells if not is_live)

    def total_shells(self) -> int:
        return self.total_live_shells + self.total_blank_shells

    def eject_shell(self):
        pass

    def has_shell(self, is_live):
        if is_live:
            return self.remaining_live_shells() > 0
        return self.remaining_blank_shells() > 0


@dataclass
class Player:
    charges: int
    items: List[Items] = field(default_factory=list)

@dataclass
class PhaseState:
    max_charges: int
    players: OrderedDict[str, Player]
    num_completed_rounds: int = 0
    round: Optional[RoundState] = None

@dataclass
class GameState:
    player_names: List[str]
    is_double_or_nothing_mode: bool = False
    phase: Optional[PhaseState] = None
    total_phases: int = 3
    num_completed_phases: int = 0
    winner: Optional[str] = None
    winner_names_by_phase: List[str] = field(default_factory=list) # just for sanity checking logs
    max_items: int = 8

    def shoot(self, target_name, is_live):
        non_target_name = "dealer" if target_name == "player" else "player"
        if is_live:

            # handle sawed gun
            damage = 2 if self.phase.round.gun_is_sawed else 1
            self.phase.round.gun_is_sawed = False

            self.phase.players[target_name].charges -= damage

            # if the target died
            if self.phase.players[target_name].charges <= 0:

                # the non-target wins the phase
                self.winner_names_by_phase.append(non_target_name)
                self.num_completed_phases += 1
                self.phase = None

                # the non-target wins the game if:
                if (
                    # the human player dies in double-or-nothing mode
                    (target_name == "player" and self.is_double_or_nothing_mode)

                    # or the target dies in the last phase
                    or (self.num_completed_phases == self.total_phases)
                ):
                    self.winner = non_target_name

                return

        self.eject_shell(is_live)
        if not self.phase.round:
            return

        # advance turn
        shooter_name = "player" if self.phase.round.is_players_turn else "dealer"
        if shooter_name != target_name or is_live:
            next_player = "dealer" if self.phase.round.is_players_turn else "player"
            try:
                self.phase.round.handcuffed_player_names.remove(next_player)
            except KeyError:
                self.phase.round.is_players_turn = not self.phase.round.is_players_turn

    def eject_shell(self, is_live):
        self.phase.round.past_shells.append(is_live)

        # if no shells left, end round
        if len(self.phase.round.past_shells) == self.phase.round.total_shells():
            self.phase.round = None
            self.phase.num_completed_rounds += 1
