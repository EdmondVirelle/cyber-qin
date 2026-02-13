"""Tests for FF14 key mapping 37-key diatonic scheme."""

from __future__ import annotations

from cyber_qin.core.constants import Modifier
from cyber_qin.core.mapping_schemes import get_scheme


def test_ff14_37_structure():
    scheme = get_scheme("ff14_37")
    assert scheme.key_count == 37
    assert scheme.midi_range == (48, 84)  # C3 to C6

    # Check C3 (48) -> '1'
    c3 = scheme.mapping[48]
    assert c3.scan_code == 0x02  # '1' scan code
    assert c3.modifier == Modifier.NONE

    # Check C#3 (49) -> Ctrl + '1'
    cs3 = scheme.mapping[49]
    assert cs3.scan_code == 0x02  # '1'
    assert cs3.modifier == Modifier.CTRL

    # Check E3 (52) -> '3' (Natural)
    e3 = scheme.mapping[52]
    assert e3.scan_code == 0x04  # '3'
    assert e3.modifier == Modifier.NONE

    # Check F3 (53) -> '4' (Natural)
    f3 = scheme.mapping[53]
    assert f3.scan_code == 0x05  # '4'
    assert f3.modifier == Modifier.NONE

    # Check C4 (60) -> 'Q'
    c4 = scheme.mapping[60]
    assert c4.scan_code == 0x10  # 'Q'
    assert c4.modifier == Modifier.NONE

    # Check C5 (72) -> 'A'
    c5 = scheme.mapping[72]
    assert c5.scan_code == 0x1E  # 'A'
    assert c5.modifier == Modifier.NONE

    # Check C6 (84) -> 'K'
    c6 = scheme.mapping[84]
    assert c6.scan_code == 0x25  # 'K' (A=1E, S=1F, D=20, F=21, G=22, H=23, J=24, K=25)
    assert c6.modifier == Modifier.NONE
