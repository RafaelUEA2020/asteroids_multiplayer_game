"""Team score and per-player match statistics."""

from dataclasses import dataclass

PlayerId = int


@dataclass
class PlayerStats:
    """Statistics tracked for one player during a match."""

    asteroids_destroyed: int = 0
    points_contributed: int = 0
    deaths: int = 0
    revives: int = 0
    time_alive: float = 0.0


class StatsManager:
    """Tracks shared team score and individual player contributions."""

    def __init__(self) -> None:
        self.team_score = 0
        self.players: dict[PlayerId, PlayerStats] = {}

    def ensure_player(self, player_id: PlayerId) -> None:
        if player_id not in self.players:
            self.players[player_id] = PlayerStats()

    def add_score(self, player_id: PlayerId, points: int) -> None:
        self.ensure_player(player_id)
        self.team_score += points
        self.players[player_id].points_contributed += points

    def spend_team_score(self, points: int) -> None:
        self.team_score = max(0, self.team_score - points)

    def record_asteroids_destroyed(
        self,
        player_id: PlayerId,
        count: int = 1,
    ) -> None:
        self.ensure_player(player_id)
        self.players[player_id].asteroids_destroyed += count

    def record_death(self, player_id: PlayerId) -> None:
        self.ensure_player(player_id)
        self.players[player_id].deaths += 1

    def record_revive(self, player_id: PlayerId) -> None:
        self.ensure_player(player_id)
        self.players[player_id].revives += 1

    def add_alive_time(self, player_id: PlayerId, dt: float) -> None:
        self.ensure_player(player_id)
        self.players[player_id].time_alive += dt

    def points_by_player(self) -> dict[PlayerId, int]:
        return {
            player_id: stats.points_contributed
            for player_id, stats in self.players.items()
        }
