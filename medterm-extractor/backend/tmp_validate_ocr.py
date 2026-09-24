from data.ocr_corrections import apply_ocr_corrections, hardcoded_cleanup

sample = " CoAmoxiclav 625mg tab\nsig: 1 tab 3x 1 day for\n5 days -1 "

cleaned = hardcoded_cleanup(apply_ocr_corrections(sample))
print(cleaned)

assert 'Co Amoxiclav 625mg tab' in cleaned
assert 'sig: 1 tab 3x 1 day for' in cleaned
assert '5 days (1-1-1)' in cleaned

for s in ['1-1-1', '1/1/1', '1-0-1', '1/0/1', '1-0-0', '2x a day', '3x/day']:
    out = hardcoded_cleanup(apply_ocr_corrections(s))
    print(repr(s), '->', repr(out))
    assert '1 tab' in out or 'tab daily' in out or 'x/day' in out

print('ok')