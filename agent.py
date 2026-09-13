"""A working Crane starter agent.

Each unit runs a separate instance of this class. This starter walks forward until it sees an
enemy, then takes one legal step toward the nearest visible enemy and names it. Start at the
``TODO(you)`` comments.
Read ``environment.md`` beside this file for the rules, helpers, and first improvement. Prepare
episode state in ``reset``. The constructor takes no arguments.
"""


from sandbox.crane import action, me, tile, units, visible
from sandbox.observation_types import AxialPosition, SkirmishAction, SkirmishObservation


class Agent:
    """Marches toward the enemy side, then steps toward the nearest visible enemy."""

    FOOTMAN_FORMATION_DISTANCE = 4
    ARCHER_FORMATION_DISTANCE = 4

    def reset(self, seed, observation) -> None:
        # Called once before each match. The opening observation is available here for
        # precomputation outside the decision clock. This starter stores no state.
        pass

    def act(self, observation: SkirmishObservation) -> SkirmishAction:
        # The enemies this unit can see.
        enemies = visible.enemies(observation)
        friends = visible.allies(observation)
        here = me.position(observation)
        is_archer = me.unit_type(observation) == "archer"
        is_cavalry = me.unit_type(observation) == "cavalry"

        nearest = min(enemies, key=lambda enemy: tile.distance(here, enemy["position"])) if enemies else None
        if is_archer and nearest is not None:
            enemy_distance = tile.distance(here, nearest["position"])
            if enemy_distance < units.STATS["archer"].attack_range:
                retreat_path = self._path_away(observation, nearest["position"])
                if retreat_path:
                    return action.move(retreat_path, nearest["unit_id"], observation)
                return action.stay(nearest["unit_id"], observation)

        # Stay close to a visible footman so it can protect this archer.
        footmen = [ally for ally in friends if ally["type"] == "footman"]
        if is_archer and footmen:
            footman = min(footmen, key=lambda ally: tile.distance(here, ally["position"]))
            # The footman should be on the enemy-facing side of the archer. The q coordinate
            # increases toward the enemy for red and decreases toward it for blue.
            front_sign = 1 if me.direction(observation) == 2 else -1
            footman_is_ahead = front_sign * (footman["position"]["q"] - here["q"]) >= 0
            if tile.distance(here, footman["position"]) > self.ARCHER_FORMATION_DISTANCE or not footman_is_ahead:
                follow_step = self._step_toward(observation, footman["position"])
                if follow_step:
                    return action.move(follow_step)

        # Keep a visible archer within a short distance of its footman bodyguard.
        archers = [ally for ally in friends if ally["type"] == "archer"]
        if not is_archer and me.unit_type(observation) == "footman" and archers:
            archer = min(archers, key=lambda ally: tile.distance(here, ally["position"]))
            if tile.distance(here, archer["position"]) > self.FOOTMAN_FORMATION_DISTANCE:
                regroup_step = self._step_toward(observation, archer["position"])
                if regroup_step:
                    return action.move(regroup_step)

        # Replaced: roster entries do not contain positions, and this selected any ally type.
        # nearest_ally = min(friends, key=lambda ally: tile.distance(here, ally["position"]))

        if not enemies:
            # At the beginning of a default skirmish match, units sit apart and see no enemies.
            # An unseen footman cannot provide a position, so the archer falls back toward its
            # own side until the footman enters vision.
            if is_archer and not footmen:
                fallback = 5 if me.direction(observation) == 2 else 2
                if fallback in action.legal_steps(observation):
                    return action.move(fallback)

            # Non-archers continue toward the enemy side.
            forward = me.direction(observation)

            # legal_steps lists the single steps allowed by the mask. Checking membership keeps
            # this order legal when a wall, ally, or enemy blocks the way.
            if forward in action.legal_steps(observation):
                return action.move(forward)

            # TODO(you): this unit stands still when something blocks the way.
            # It may still attack, but can you choose a better response?
            return action.stay()

        # TODO(you): walking toward the nearest enemy is the entire strategy, and it is weak.
        # An archer should shoot and back away, cavalry should swing wide for a flank, and a
        # footman should hold the line beside an ally. What should each of your units do?

        # This unit's current {"q": ..., "r": ...} position.
        #here = me.position(observation)

        # The closest enemy in sight. min returns the enemy dictionary, not the distance.
        nearest = min(enemies, key=lambda enemy: tile.distance(here, enemy["position"]))
        #if friends:
            #nearest_ally = min(friends, key=lambda ally: tile.distance(here, ally["position"]))
        # The step that gets closest to the enemy, or 0 when no step gets closer.

        if is_archer:
            return action.stay(nearest["unit_id"], observation)

        if is_cavalry:
            flank_goal = self._flank_goal(here, nearest["position"])
            flank_path = self._step_toward(observation, flank_goal)
            if flank_path:
                return action.move(flank_path, nearest["unit_id"], observation)
            return action.stay(nearest["unit_id"], observation)

        #if me.unit_type(observation) == "archer" and enemy_distance <= 4:
    
            #ally_step = self._step_toward(observation, nearest_ally["position"])
            #return action.move(ally_step, nearest["unit_id"], observation)
        

        step = self._step_toward(observation, nearest["position"])

        # Naming a target makes the strike prefer that enemy. Any visible enemy can be named,
        # so both orders below are legal.
        if step == 0:
            return action.stay(nearest["unit_id"], observation)
        return action.move(step, nearest["unit_id"], observation)

    def _step_toward(self, observation: SkirmishObservation, goal: AxialPosition) -> int:
        """Return the single step that most closes the gap to goal, or 0 when none does."""
        # TODO(you): only single steps are tried here. A path can contain four steps, and cavalry
        # has four movement points, so most of that speed goes to waste.
        here = me.position(observation)

        # Standing still is path id 0. A step must reduce the distance to be worth taking.
        best_path = 0
        best_distance = tile.distance(here, goal)

        for path_id in action.legal_paths(observation):
            # at_path_end gives the landing tile, so this is the distance after the step.
            land_tile = tile.at_path_end(here, path_id)
            step_distance = tile.distance(land_tile, goal)

            # Remember this step if it is the best one so far.
            if step_distance < best_distance:
                best_path, best_distance = path_id, step_distance

        return best_path

    def _path_away(self, observation: SkirmishObservation, threat: AxialPosition) -> int:
        """Return the legal path that maximizes distance from a nearby threat."""
        here = me.position(observation)
        best_path = 0
        best_distance = tile.distance(here, threat)

        for path_id in action.legal_paths(observation):
            landing = tile.at_path_end(here, path_id)
            landing_distance = tile.distance(landing, threat)
            if landing_distance > best_distance:
                best_path, best_distance = path_id, landing_distance

        return best_path

    def _flank_goal(self, here: AxialPosition, enemy: AxialPosition) -> AxialPosition:
        """Choose the nearer of the two side tiles next to an enemy."""
        enemy_sides = tile.neighbors(enemy)
        side_tiles = (enemy_sides[1], enemy_sides[3])
        return min(side_tiles, key=lambda side: tile.distance(here, side))

    # Optional: a reinforcement-learning hook called after every step with that step's
    # transition. Its time counts against the timing and episode budget. The order argument is
    # what act returned. It is named order so it does not shadow the action helpers.
    #
    # def learn(self, observation, order: SkirmishAction, reward: float, terminated: bool) -> None:
    #     ...

    # Optional: messaging. Season settings enable it from Season 3 onward. When enabled, chat runs
    # after a unit chooses its order and receives messages that arrived since its previous
    # activation. Return each message with a recipient and text. Use None to broadcast to both
    # sides, or a player id such as "player_2", not a unit id, to send directly to one ally. The
    # rosters in the observation map each player to its unit. By default, text is limited to 200
    # characters.
    # A direct message reaches its allied unit at its next activation, after that unit chooses its
    # own order. Every message is recorded and shown in replays, so nothing you send is ever secret.
    # Return nothing to stay silent.
    #
    # def chat(self, inbox: list[dict]) -> list[dict] | None:
    #     ...
