from app.services.combat_service.exceptions import _parse_dice, _roll_dice_expression

def test_parse_dice_positive():
    assert _parse_dice("1d4") == (1, 1, 4, 0)
    assert _parse_dice("2d6+3") == (1, 2, 6, 3)
    assert _parse_dice("1d8-2") == (1, 1, 8, -2)

def test_parse_dice_negative():
    assert _parse_dice("-1d4") == (-1, 1, 4, 0)
    assert _parse_dice("-2d6+2") == (-1, 2, 6, 2)
    assert _parse_dice("- 1d4") == (-1, 1, 4, 0)
    assert _parse_dice("+1d4") == (1, 1, 4, 0)

def test_parse_dice_static():
    assert _parse_dice("5") == (1, 0, 0, 5)
    assert _parse_dice("-3") == (1, 0, 0, -3)
    assert _parse_dice("+2") == (1, 0, 0, 2)

def test_roll_dice_expression(mocker):
    # Mock random.randint to always return 2 for deterministic testing
    mocker.patch("app.services.combat_service.exceptions.random.randint", return_value=2)
    
    # 1d4 => 1 * 2 + 0 = 2
    assert _roll_dice_expression("1d4") == 2
    # -1d4 => -1 * 2 + 0 = -2
    assert _roll_dice_expression("-1d4") == -2
    # 2d6+3 => 1 * (2+2) + 3 = 7
    assert _roll_dice_expression("2d6+3") == 7
    # -2d6+2 => -1 * (2+2) + 2 = -2
    assert _roll_dice_expression("-2d6+2") == -2
    # 5 => 5
    assert _roll_dice_expression("5") == 5
    # -3 => -3
    assert _roll_dice_expression("-3") == -3
