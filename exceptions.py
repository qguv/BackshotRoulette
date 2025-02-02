class GameError(Exception):
    '''log line doesn't follow logic of game'''
    pass


class TurnError(GameError):
    '''out-of-turn move'''
    def __str__(self):
        return "not your turn"

