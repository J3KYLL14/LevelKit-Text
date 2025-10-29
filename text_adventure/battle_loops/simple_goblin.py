from engine.models import BattleSpec, BattleAction, Enemy

BATTLE = BattleSpec(
    id="simple_goblin",
    title="Goblin Skirmish",
    enemy=Enemy(id="goblin", name="Goblin Scout", hp=10, attack=3, defence=1, loot=["potion_small"]),
    actions=[
        BattleAction(kind="attack", label="Quick strike", bonus=0, variance=2),
        BattleAction(
            kind="skill_check",
            label="Brace and shove",
            stat="stamina",
            gte=6,
            success_damage=3,
            fail_damage=0,
        ),
        BattleAction(kind="cast", label="Focus burst", mana_cost=3, bonus=2, variance=1),
    ],
    victory_to=None,
    defeat_to=None,
    victory_text="The goblin drops its dagger and flees.",
    defeat_text="You crumple to the floor; cold stone greets you.",
)
