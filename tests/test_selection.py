from ziptrend.selection import parse_zip_list


def test_bulk_zip_parsing():
    accepted, rejected = parse_zip_list("02108, 80202\n2108;80203-1234 bogus 99999", ["02108", "80202", "80203"])
    assert accepted == ["02108", "80202", "80203"]
    assert rejected == ["bogus", "99999"]
