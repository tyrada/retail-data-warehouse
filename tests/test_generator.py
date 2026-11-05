from retail_warehouse.generator import generate_retail_data


def test_generator_is_deterministic(tmp_path):
    first = tmp_path / "first.csv"
    second = tmp_path / "second.csv"
    generate_retail_data(first, rows=100, seed=7)
    generate_retail_data(second, rows=100, seed=7)
    assert first.read_bytes() == second.read_bytes()
    assert len(first.read_text(encoding="utf-8").splitlines()) == 101

