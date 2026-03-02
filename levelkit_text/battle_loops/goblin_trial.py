"""Simple battle used on the right-hand path of the template adventure."""

from engine.models import BattleAction, BattleSpec, Enemy

BATTLE = BattleSpec(
    id="goblin_trial",
    title="Goblin Ambush",
    enemy=Enemy(
        id="hallway_goblin",
        name="Goblin Skulker",
        hp=10,
        attack=4,
        defence=1,
        loot=[],
    ),
    actions=[
        BattleAction(
            kind="skill_check",
            label="Hold your ground",
            stat="attack",
            gte=4,
            success_damage=12,
            fail_damage=999,
        ),
    ],
    victory_to="goblin_victory",
    defeat_to="goblin_defeat",
    victory_text="Your blade flashes and the goblin collapses with a startled hiss.",
    defeat_text="Without proper steel, the goblin's spear finds its mark.",
)

