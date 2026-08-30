"""
Test untuk pembobotan bahan yang menggerakkan semantic encoding.

Mengunci keputusan tier yang gampang berubah tak sengaja tapi mahal ditemukan
ulang; tiap keputusan berasal dari hasil evaluasi, bukan intuisi.
"""

from app.services.weighted_encoder import INGREDIENT_WEIGHTS, _get_weight


def test_santan_is_weighted_as_an_aromatic_not_a_base_seasoning():
    """Santan menentukan identitas hidangan jadi harus di atas bumbu dasar.

    "daging + santan" itu rendang/gulai; "daging + kecap + saos" itu teriyaki.
    Pada bobot bumbu dasar 0.5, santan tenggelam oleh protein dan query
    "daging, santan, garam, kecap, saos" mengembalikan Beef Teriyaki (P@5 0.00).
    Menaikkannya ke tier aromatik memperbaiki 4 dari 20 query evaluasi (rata-rata
    P@5 0.87 -> 0.96) tanpa menurunkan satu pun.
    """
    assert INGREDIENT_WEIGHTS["santan"] >= 1.5
    assert INGREDIENT_WEIGHTS["santan"] > INGREDIENT_WEIGHTS["garam"]
    assert INGREDIENT_WEIGHTS["santan"] > INGREDIENT_WEIGHTS["kecap"]


def test_base_seasonings_stay_below_every_real_ingredient():
    """Garam, gula, minyak, tepung menggambarkan cara membumbui, bukan hidangan."""
    base = ["garam", "gula", "minyak", "tepung", "kecap", "penyedap"]
    staples = ["ayam", "ikan", "daging", "nasi", "telur", "tahu", "tempe"]
    for b in base:
        for s in staples:
            assert INGREDIENT_WEIGHTS[b] < INGREDIENT_WEIGHTS[s], (
                f"'{b}' harus berbobot lebih kecil dari bahan pokok '{s}'"
            )


def test_longest_match_wins_over_substring():
    """"bawang putih" aromatik spesifik; "bawang" saja tidak boleh menutupinya."""
    assert _get_weight("bawang putih") == INGREDIENT_WEIGHTS["bawang putih"]
    assert _get_weight("santan kental") == INGREDIENT_WEIGHTS["santan"]


def test_unlisted_ingredient_falls_back_to_neutral_weight():
    assert _get_weight("bahan yang tidak terdaftar sama sekali") == 1.0
