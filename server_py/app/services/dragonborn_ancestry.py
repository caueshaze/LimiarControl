DRAGONBORN_ANCESTRIES = {
    "black": {
        "label": "Black",
        "damageType": "acid",
        "resistanceType": "acid",
        "area": {"shape": "line", "size": "1.5m x 9m"},
        "saveAbility": "DEX",
    },
    "blue": {
        "label": "Blue",
        "damageType": "lightning",
        "resistanceType": "lightning",
        "area": {"shape": "line", "size": "1.5m x 9m"},
        "saveAbility": "DEX",
    },
    "brass": {
        "label": "Brass",
        "damageType": "fire",
        "resistanceType": "fire",
        "area": {"shape": "line", "size": "1.5m x 9m"},
        "saveAbility": "DEX",
    },
    "bronze": {
        "label": "Bronze",
        "damageType": "lightning",
        "resistanceType": "lightning",
        "area": {"shape": "line", "size": "1.5m x 9m"},
        "saveAbility": "DEX",
    },
    "copper": {
        "label": "Copper",
        "damageType": "acid",
        "resistanceType": "acid",
        "area": {"shape": "line", "size": "1.5m x 9m"},
        "saveAbility": "DEX",
    },
    "gold": {
        "label": "Gold",
        "damageType": "fire",
        "resistanceType": "fire",
        "area": {"shape": "cone", "size": "4.5m"},
        "saveAbility": "DEX",
    },
    "green": {
        "label": "Green",
        "damageType": "poison",
        "resistanceType": "poison",
        "area": {"shape": "cone", "size": "4.5m"},
        "saveAbility": "CON",
    },
    "red": {
        "label": "Red",
        "damageType": "fire",
        "resistanceType": "fire",
        "area": {"shape": "cone", "size": "4.5m"},
        "saveAbility": "DEX",
    },
    "silver": {
        "label": "Silver",
        "damageType": "cold",
        "resistanceType": "cold",
        "area": {"shape": "cone", "size": "4.5m"},
        "saveAbility": "CON",
    },
    "white": {
        "label": "White",
        "damageType": "cold",
        "resistanceType": "cold",
        "area": {"shape": "cone", "size": "4.5m"},
        "saveAbility": "CON",
    },
}


def is_valid_dragonborn_ancestry(value: object) -> bool:
    return isinstance(value, str) and value in DRAGONBORN_ANCESTRIES
