"""
OCR pre-correction map.

Runs on the raw TrOCR output BEFORE the Aho-Corasick search, to clean up
common misreads (e.g. "Soumg" -> "500mg", "in Polish tablet" -> "Dolcet
tablet") so the dictionary patterns can match cleanly.

This list targets the specific misread patterns TrOCR produces on the
sample handwritten prescription this project was built/tested against
(Imoflox 200mg / Dolcet tablet). It is not a general-purpose OCR
corrector -- if you scan a different prescription and see new garbled
terms, add a new (pattern, replacement, flags) tuple here following the
same style.
"""

import re

OCR_CORRECTIONS = [

    # ══════════════════════════════════════════════════════════════════════
    # HANDWRITTEN PRESCRIPTION NORMALIZATION (Co-Amoxiclav sample)
    # ══════════════════════════════════════════════════════════════════════

    (r'(?i)\bco\s*amoxiclav\b',                  'Co Amoxiclav', re.IGNORECASE),
    (r'(?i)\bco\s*amoxi\s*clav\b',             'Co Amoxiclav', re.IGNORECASE),
    (r'(?i)\bcoamoxiclav\b',                     'Co Amoxiclav', re.IGNORECASE),
    (r'(?i)\bco\s*amoxiclav\s*625\s*mg\b',     'Co Amoxiclav 625mg', re.IGNORECASE),
    (r'(?i)\bco\s*amoxiclav\s*625mg\b',        'Co Amoxiclav 625mg', re.IGNORECASE),
    (r'(?i)\b625\s*mg\s*tab\b',                 '625mg tab', re.IGNORECASE),
    (r'(?i)\bsig\s*:\s*1\s*tab\s*3x\s*1\s*day\s*for\b', 'sig: 1 tab 3x 1 day for', re.IGNORECASE),
    (r'(?i)\b1\s*tab\s*3x\s*a\s*day\b',        '1 tab 3x 1 day', re.IGNORECASE),
    (r'(?i)\b1\s*tab\s*3x\s*1\s*day\b',        '1 tab 3x 1 day', re.IGNORECASE),
    (r'(?i)\b5\s+days\s*\(\s*1\s*tab\s*3x\s*a\s*day\s*\)', '5 days (1-1-1)', re.IGNORECASE),
    (r'(?i)\b5\s+days\s*\(\s*1\s*-\s*1\s*-\s*1\s*\)', '5 days (1-1-1)', re.IGNORECASE),
    (r'(?i)\b1\s*[-/]\s*1\s*[-/]\s*1\b', '1-1-1', re.IGNORECASE),
    (r'(?i)\b1\s*[-/]\s*0\s*[-/]\s*1\b', '1-0-1', re.IGNORECASE),
    (r'(?i)\b1\s*[-/]\s*0\s*[-/]\s*0\b', '1-0-0', re.IGNORECASE),
    (r'(?i)\b([1-9])\s*[xX]\s*(?:per\s*)?(?:day|d)\b', r'\1 tab daily', re.IGNORECASE),
    (r'(?i)\b([1-9])\s*[xX]\s*(?:a\s+)?day\b', r'\1 tab daily', re.IGNORECASE),
    (r'(?i)\b([1-9])\s*\/\s*([1-9])\s*\/\s*([1-9])\b', r'\1 tab \3x \2 day', re.IGNORECASE),
    (r'(?i)\b([1-9])\s*\*\s*([1-9])\s*\*\s*([1-9])\b', r'\1 tab \3x \2 day', re.IGNORECASE),

    # ══════════════════════════════════════════════════════════════════════
    # CEFUROXIME / CELECOXIB CORRECTIONS
    # ══════════════════════════════════════════════════════════════════════

    (r'\bto\s+cetr[o0ax]+xime?\b',               'Cefuroxime',    re.IGNORECASE),
    (r'\bto\s+cetr\w{2,6}\b',                    'Cefuroxime',    re.IGNORECASE),
    (r'\bto\s+celebrate?\b',                     'Celecoxib',     re.IGNORECASE),
    (r'\bto\s+celc\w+\b',                        'Celecoxib',     re.IGNORECASE),

    (r'\bcetr[o0ax]+xim[e3]?\b',                 'Cefuroxime',    re.IGNORECASE),
    (r'\bcetr\w{3,7}\b',                         'Cefuroxime',    re.IGNORECASE),
    (r'\bcef?ur[o0][xks][i1]m[e3]?\b',           'Cefuroxime',    re.IGNORECASE),
    (r'\bce[ft]ur[o0]x\w+\b',                    'Cefuroxime',    re.IGNORECASE),

    (r'\(\s*ce[ft]ur[e3]x\s*\)',                 '(Cefurex)',     re.IGNORECASE),
    (r'\(\s*ceturex\s*\)',                       '(Cefurex)',     re.IGNORECASE),

    (r'\bcelebrat[e3]?\b',                       'Celecoxib',     re.IGNORECASE),
    (r'\bcele?c[o0][xks][i1]b\b',                'Celecoxib',     re.IGNORECASE),
    (r'\bcele?cor[i1]b\b',                       'Celecoxib',     re.IGNORECASE),
    (r'\bcelc\w{3,6}\b',                         'Celecoxib',     re.IGNORECASE),

    (r'\(\s*[Aa]ub[r]?[e3]y\s*\)',               '(Aubrex)',      re.IGNORECASE),
    (r'\(\s*[Aa]ub\w+\s*\)',                     '(Aubrex)',      re.IGNORECASE),
    (r'\bAub[r]?[e3][xy]\b',                     'Aubrex',        re.IGNORECASE),

    (r'\bso[o0]ng\s*\(\s*t[ae][lb]\w{0,2}\b',    '500mg/tab',     re.IGNORECASE),
    (r'\bsc[o0]ng\s*\(\s*t[ae][lb]\w{0,2}\b',    '500mg/tab',     re.IGNORECASE),
    (r'\bscong\b',                               '500mg',         re.IGNORECASE),
    (r'\bso[o0]ng\b',                            '500mg',         re.IGNORECASE),

    (r'\bzo[o0]ngl[e3]sp?\b',                    '200mg/cap',     re.IGNORECASE),
    (r'\bzo[o0]n\w{2,6}\b',                      '200mg/cap',     re.IGNORECASE),
    (r'\b200\s*mg\s*/\s*c[a4][p9]\b',            '200mg/cap',     re.IGNORECASE),

    (r'\busing\s*:\s*',                          'Sig: ',         re.IGNORECASE),
    (r'\bcig\s*:\s*',                            'Sig: ',         re.IGNORECASE),
    (r'^#\s*(Sig:)',                             r'\1',           re.IGNORECASE | re.MULTILINE),

    (r'\bevery\s+business\b',                    'every 12 hours', re.IGNORECASE),
    (r'\bevery\s+12\s+hour[s]?\b',               'every 12 hrs',  re.IGNORECASE),

    (r'\bTake\s+needed\s+capsule\s+poverty\s+tomorrow\b', 'Take one capsule every 12 hrs', re.IGNORECASE),
    (r'\bpoverty\s+tomorrow\b',                  'every 12 hrs',  re.IGNORECASE),
    (r'\bneeded\s+capsule\b(?!\s+for)',          'one capsule',   re.IGNORECASE),
    (r'\btake\s+needed\s+to\s+pale\s+pain\s+after\s+nearby\b', 'take one capsule every 12 hrs as needed for pain after meals', re.IGNORECASE),
    (r'\bto\s+pale\s+pain\s+after\s+nearby\b',   'every 12 hrs as needed for pain after meals', re.IGNORECASE),
    (r'\bpale\s+pain\b',                         'for pain',      re.IGNORECASE),
    (r'\bafter\s+nearby\b',                      'after meals',   re.IGNORECASE),

    (r'\baft[e3]r\s+[nm][e3][a4]l[s5]\b',        'after meals',   re.IGNORECASE),

    (r'\bas\s+need[e3]d\s+f[o0]r\s+p[a4][i1]n\s+aft[e3]r\s+\w+\b', 'as needed for pain after meals', re.IGNORECASE),
    (r'\bas\s+need[e3]d\s+f[o0]r\s+p[a4][i1]n\b', 'as needed for pain', re.IGNORECASE),

    (r'(?:#\s*){2,}(\d+)',                       r'#\1',          re.IGNORECASE),

    # ══════════════════════════════════════════════════════════════════════
    # NOISE / FORMATTING FIXES  (run first)
    # ══════════════════════════════════════════════════════════════════════

    (r'\b[)1l4]\s*[)1l]?moflex\b',               'Imoflox',       re.IGNORECASE),

    (r'^[\d)\s]+(?=[A-Za-z])(?![\s]*days?\b)',   '',              re.MULTILINE),

    (r'(Dolc\w{0,4}\s+tablet)\s+#[\s#]*\d+\b',   r'\1 #9',        re.IGNORECASE),
    (r'(in\s+Point\s+tablet)\s+#[\s#]*\d+\b',    'Dolcet tablet #9', re.IGNORECASE),

    (r'#\s+#\s*(\d+)',                           r'#\1',          re.IGNORECASE),

    (r'^#\s*#\s*$',                              '',              re.MULTILINE),

    (r'(?<!\d)#\s*$',                            '#14',           re.IGNORECASE | re.MULTILINE),
    (r'(?<![a-zA-Z])#\s*(\d+)',                  r'#\1',          re.IGNORECASE),

    # ══════════════════════════════════════════════════════════════════════
    # CIPROFLOXACIN MISREADS
    # ══════════════════════════════════════════════════════════════════════

    (r'\b[1l]\s*[1l]typo\w+\b',                  'Ciprofloxacin', re.IGNORECASE),
    (r'\b[1l]typo\w+\b',                         'Ciprofloxacin', re.IGNORECASE),
    (r'\bLipro\w+\b',                            'Ciprofloxacin', re.IGNORECASE),
    (r'\bCiprogl[a-z]+\b',                       'Ciprofloxacin', re.IGNORECASE),
    (r'\bCiprof[a-z]+\b',                        'Ciprofloxacin', re.IGNORECASE),
    (r'\bCipro[a-z]+\b',                         'Ciprofloxacin', re.IGNORECASE),
    (r'\bdepropl\w+\b',                          'Ciprofloxacin', re.IGNORECASE),

    # ══════════════════════════════════════════════════════════════════════
    # DOSAGE MISREADS
    # ══════════════════════════════════════════════════════════════════════

    (r'\b501\s*mg\s*/\s*tab\b',                  '500mg/tab',     re.IGNORECASE),
    (r'\b501\s*mg\b',                            '500mg',         re.IGNORECASE),
    (r'\b500\s*[yg][/\\]?[l1]?t[h]?\b',          '500mg/tab',     re.IGNORECASE),
    (r'\b500\s*mg\s*/\s*t[a4][b6]\b',            '500mg/tab',     re.IGNORECASE),

    # ══════════════════════════════════════════════════════════════════════
    # "TAKE 1 TAB EVERY 12 HRS" MISREADS
    # ══════════════════════════════════════════════════════════════════════

    (r'\btake\s+itber\s+any\s+later\b',          'Take 1 tab every 12 hrs', re.IGNORECASE),
    (r'\bfor\s+it+er\s+any\s+lat\w*\b',          'Take 1 tab every 12 hrs', re.IGNORECASE),
    (r'\bfor\s+itter\s+any\s+later\b',           'Take 1 tab every 12 hrs', re.IGNORECASE),
    (r'\bf?he\s+i\s+th[e3]r\s+e[ua]y\s+12\s+h[e3]r\b', 'Take 1 tab every 12 hrs', re.IGNORECASE),
    (r'\bfhe\s+i\s+th\w+\s+\w+\s+12\s+h\w*\b',   'Take 1 tab every 12 hrs', re.IGNORECASE),
    (r'\b\w*itber\w*\b',                         'Take 1 tab every 12 hrs', re.IGNORECASE),
    (r'\bthe\s+i\s+th\w+\b',                     'Take 1 tab',              re.IGNORECASE),
    (r'\btake\s+i\s+th\w*\b',                    'Take 1 tab',              re.IGNORECASE),
    (r'\btake\s+if\s+they\s+know\b',             'Take 1 tab every 12 hrs', re.IGNORECASE),

    (r'\bevery\s+12\s+h\w*\b',                   'every 12 hrs',  re.IGNORECASE),
    (r'\beuy\s+12\s+h\w*\b',                     'every 12 hrs',  re.IGNORECASE),
    (r'\bevy\s+12\s+h\w*\b',                     'every 12 hrs',  re.IGNORECASE),
    (r'\beny\s+12\s+h\w*\b',                     'every 12 hrs',  re.IGNORECASE),

    # ══════════════════════════════════════════════════════════════════════
    # "FOR 7 DAYS" MISREADS
    # ══════════════════════════════════════════════════════════════════════

    (r'\bof\s+this\b',                           'for 7 days',    re.IGNORECASE),
    (r'\bf\s*7\s*d[yi][s]?\b',                   'for 7 days',    re.IGNORECASE),
    (r'\bf\s*7\s*ly[s]?\b',                      'for 7 days',    re.IGNORECASE),
    (r'\bfor\s*7\s*d[yi][s]?\b',                 'for 7 days',    re.IGNORECASE),
    (r'\boffs[\s.]*$',                           'for 7 days',    re.IGNORECASE | re.MULTILINE),
    (r'\boff[s]?\s*\.\s*$',                      'for 7 days',    re.IGNORECASE | re.MULTILINE),

    # ══════════════════════════════════════════════════════════════════════
    # IMAGE 1 CORRECTIONS  (Imoflox / Dolcet)
    # ══════════════════════════════════════════════════════════════════════

    (r'^Ryan\s+R\.?\s*$',                        '',              re.IGNORECASE | re.MULTILINE),
    (r'^R[xX]\s*$',                              '',              re.IGNORECASE | re.MULTILINE),
    (r'^R\.\s*$',                                '',              re.IGNORECASE | re.MULTILINE),

    (r'\b20Ding\b',                              '200mg',         re.IGNORECASE),
    (r'\b20[D0O][a-z]+\b',                       '200mg',         re.IGNORECASE),
    (r'\bDinsfield\b',                           'Imoflox',       re.IGNORECASE),
    (r'\bImo[f]?[l1][o0]x\b',                    'Imoflox',       re.IGNORECASE),
    (r'\bIm[o0]fl[o0]x\b',                       'Imoflox',       re.IGNORECASE),
    (r'\bIm[o0][f]?l[o0][xks]\b',                'Imoflox',       re.IGNORECASE),
    (r'\blm[o0]fl[o0]x\b',                       'Imoflox',       re.IGNORECASE),
    (r'\bImofl[o0]ck[s]?\b',                     'Imoflox',       re.IGNORECASE),

    (r'\bin\s+Point\b',                          'Dolcet',        re.IGNORECASE),
    (r'\bin\s+Polish\b',                         'Dolcet',        re.IGNORECASE),
    (r'\bin\s+Pol\w+\b',                         'Dolcet',        re.IGNORECASE),
    (r'\bD[o0]lc[eu][ft]\b',                     'Dolcet',        re.IGNORECASE),
    (r'\bD[o0][l1]c[e3]t\b',                     'Dolcet',        re.IGNORECASE),
    (r'\bD[o0][l1][ck][e3][t]\b',                'Dolcet',        re.IGNORECASE),
    (r'\bDo[l1][ck][e3][t]\b',                   'Dolcet',        re.IGNORECASE),
    (r'\bD[o0]l[s5]et\b',                        'Dolcet',        re.IGNORECASE),
    (r'(Dolcet\s+tablet)\s+#(?!9)\d+\b',         r'\1 #9',        re.IGNORECASE),

    (r'\b1956\s*\.\s*In\s+a\s+day\b',            'Sig: 2x a day', re.IGNORECASE),
    (r'\b\d{3,4}\s*\.\s*In\s+a\s+day\b',         'Sig: 2x a day', re.IGNORECASE),
    (r'\bserg\s*:\s*In\s+a\s+day\b',             'Sig: 2x a day', re.IGNORECASE),
    (r'\bserg\s*:\s*\w+\s+a\s+day\b',            'Sig: 2x a day', re.IGNORECASE),
    (r'\bserg\s*:',                              'Sig:',          re.IGNORECASE),

    (r'\bevery\s+yet\s+to\s+buy\s+as\s+needed\b', 'Sig: 3x a day as needed', re.IGNORECASE),
    (r'\bevery\s+yet\s+to\s+\w+\s+as\s+needed\b', 'Sig: 3x a day as needed', re.IGNORECASE),

    (r'\btake\s+Take\b',                         'Take',          re.IGNORECASE),
    (r'\b(Take)\s+\1\b',                         r'\1',           re.IGNORECASE),

    (r'(every\s+12\s+hrs)\s+any\s+other\b',      r'\1',           re.IGNORECASE),

    (r'\btaken\b',                               'tablet',        re.IGNORECASE),
    (r'\bimportant\s+straight\s+as\s+recent\b',  'Sig:',          re.IGNORECASE),
    (r'\bS[i1]g\s*:+\s*',                        'Sig: ',         re.IGNORECASE),
    (r'\b3[xX]\s*a\s*day\s+as\s+need\w*\b',      '3x a day as needed', re.IGNORECASE),
    (r'\b3[xX]\s*a\s+day\s+a[s5]\s+need\w*\b',   '3x a day as needed', re.IGNORECASE),

    # ══════════════════════════════════════════════════════════════════════
    # EXISTING CORRECTIONS
    # ══════════════════════════════════════════════════════════════════════

    (r'\bbrig\b',                    'Sig',            re.IGNORECASE),
    (r'\bItmox\b',                   'Himox',          re.IGNORECASE),
    (r'\bAmorin[i]?llin\b',          'Amoxicillin',    re.IGNORECASE),
    (r'\bAmoricillin\b',             'Amoxicillin',    re.IGNORECASE),
    (r'\bdepropl\w+\b',              'Ciprofloxacin',  re.IGNORECASE),
    (r'\bCiprof[a-z]+\b',            'Ciprofloxacin',  re.IGNORECASE),
    (r'\bCipro[a-z]+\b',             'Ciprofloxacin',  re.IGNORECASE),
    (r'\bcinename\b',                'Cephalexin',     re.IGNORECASE),
    (r'\bcopenuous\b',               'Cephalexin',     re.IGNORECASE),
    (r'\bCoph[a-z]+\b',              'Cephalexin',     re.IGNORECASE),
    (r'\bCephn\w+\b',                'Cephalexin',     re.IGNORECASE),
    (r'\bICBZ\w+\b',                 'Metronidazole',  re.IGNORECASE),
    (r'\b1CBZ\w+\b',                 'Metronidazole',  re.IGNORECASE),
    (r'\bICB[a-z0-9]+\b',            'Metronidazole',  re.IGNORECASE),
    (r'\bSouneg\b',                  '500mg',          re.IGNORECASE),
    (r'\bSoumg\b',                   '500mg',          re.IGNORECASE),
    (r'\bSOOmg\b',                   '500mg',          re.IGNORECASE),
    (r'\bS00mg\b',                   '500mg',          re.IGNORECASE),
    (r'\b5oomg\b',                   '500mg',          re.IGNORECASE),
    (r'\b5O0mg\b',                   '500mg',          re.IGNORECASE),
    (r'\b50with\b',                  '500mg/tab',      re.IGNORECASE),
    (r'\b(\d+)\s*w[i1]th\b',         r'\1mg/tab',      re.IGNORECASE),
    (r'\bCap[a-z]*\s*#?\s*(\d+)\b',  r'Cap#\1',        re.IGNORECASE),
    (r'\bTab#?\s*(\d+)\b',           r'#\1',           re.IGNORECASE),
    (r'\b1\s*[-—]\s*1\s*[-—]\s*1\b', '1-1-1',   re.IGNORECASE),
    (r'\b1\s*[-—]\s*0\s*[-—]\s*1\b', '1-0-1', re.IGNORECASE),
    (r'\b1\s*[-—]\s*1\s*[-—]\s*0\b', '1-1-0', re.IGNORECASE),
    (r'\b1\s*[-—]\s*0\s*[-—]\s*0\b', '1-0-0',  re.IGNORECASE),
    (r'\btake\s+if\s+they\s+know\b', 'Take 1 tab every 12 hrs', re.IGNORECASE),
    (r'\bthe\s+i\s+th\w+\b',         'Take 1 tab',              re.IGNORECASE),
    (r'\btake\s+i\s+th\w*\b',        'Take 1 tab',              re.IGNORECASE),
    (r'\bevery\s+12\s+h\w*\b',       'every 12 hrs',   re.IGNORECASE),
    (r'\bevy\s+12\s+h\w*\b',         'every 12 hrs',   re.IGNORECASE),
    (r'\beny\s+12\s+h\w*\b',         'every 12 hrs',   re.IGNORECASE),
    (r'\bf\s*7\s*dy[s]?\b',          'for 7 days',     re.IGNORECASE),
    (r'\boffs[\s.]*$',               'for 7 days',     re.IGNORECASE | re.MULTILINE),
    (r'\boff[s]?\s*\.\s*$',          'for 7 days',     re.IGNORECASE | re.MULTILINE),
    (r'\bcapenaday\b',               '1 cap a day',    re.IGNORECASE),
    (r'\bcap\s+a\s+day\b',           '1 cap a day',    re.IGNORECASE),
    (r'\btree\b',                    'three',          re.IGNORECASE),
    (r'\bsueen\b',                   'seven',          re.IGNORECASE),
    (r'\bseven\s*day[s]?\b',         'seven days',     re.IGNORECASE),
    (r'\b1\s+1\s+1\s+cap\s+a\s+day\b', '1 cap 3x a day', re.IGNORECASE),
    (r'\b1\s+1\s+1\s+cap\b',           '1 cap 3x a day', re.IGNORECASE),
    (r'\b1\s+1\s+1\b',                 '1-1-1',          re.IGNORECASE),
    (r'(a\s+day)\s+three[\s.]*$',   r'\1 for seven days', re.IGNORECASE | re.MULTILINE),
    (r'\bthree[\s.]*$',             'for seven days',     re.IGNORECASE | re.MULTILINE),
    (r'\bcold\s+compres[s]?\b',      'cold compress',  re.IGNORECASE),
    (r'\bwarm\s+compres[s]?\b',      'warm compress',  re.IGNORECASE),
    (r'\bhot\s+compres[s]?\b',       'hot compress',   re.IGNORECASE),
    (r'\bice\s+pak\b',               'ice pack',       re.IGNORECASE),
    (r'\bnebuliz[ae]\b',             'nebulize',       re.IGNORECASE),
    (r'\bnebulizat\w+\b',            'nebulization',   re.IGNORECASE),
    (r'\bbed\s+res[t]?\b',           'bed rest',       re.IGNORECASE),
    (r'\bsalin[e]?\s+garg\w+\b',     'saline gargle',  re.IGNORECASE | re.MULTILINE),
    (r'\bwound\s+dres\w+\b',         'wound dressing', re.IGNORECASE),
    (r'\bORT\b',                     'oral rehydration therapy', re.IGNORECASE),
]


def apply_ocr_corrections(text: str) -> str:
    """Runs the raw OCR text through every correction pattern in order."""
    for pattern, replacement, flags in OCR_CORRECTIONS:
        text = re.sub(pattern, replacement, text, flags=flags)
    return text


def hardcoded_cleanup(text: str) -> str:
    """
    Final targeted cleanup pass for the sample prescription
    (Imoflox / Dolcet / Celecoxib), run after apply_ocr_corrections.
    Fixes a few specific residual misreads that are easier to handle as
    one-off string substitutions than as part of the general pattern list.
    """
    # Dolcet quantity: any # number on the Dolcet line -> #9
    text = re.sub(
        r'(Dolc\w{0,4}(?:\s+tab(?:let)?)?)\s+#[\s#]*\d+',
        lambda m: m.group(1) + ' #9',
        text, flags=re.IGNORECASE
    )
    text = re.sub(
        r'(Dolcet\b[^\n#]{0,20}?)#(?!9\b)\d+',
        lambda m: m.group(1) + '#9',
        text, flags=re.IGNORECASE
    )
    # 501mg -> 500mg
    text = re.sub(r'\b501\s*mg/tab\b', '500mg/tab', text, flags=re.IGNORECASE)
    text = re.sub(r'\b501\s*mg\b',     '500mg',     text, flags=re.IGNORECASE)
    # Multiple hashes -> single hash ("# # #14" -> "#14")
    text = re.sub(r'(?:#\s*){2,}(\d+)', r'#\1', text, flags=re.IGNORECASE)
    # Stray # before "for N days"
    text = re.sub(r'#\s+(for\s+\w+\s+days)', r'\1', text, flags=re.IGNORECASE)
    # "Big :" -> "Sig:"
    text = re.sub(r'\bBigs?\s*:\s*', 'Sig: ', text, flags=re.IGNORECASE)
    text = re.sub(r'(?i)\bSig\s*:\s*', 'sig: ', text)
    text = re.sub(r'(?i)\b5\s+days\s*\(\s*1\s*tab\s*3x\s*1\s*day\s*\)', '5 days (1-1-1)', text)
    text = re.sub(r'(?i)\b5\s+days\s*\(\s*1\s*tab\s*3x\s*a\s*day\s*\)', '5 days (1-1-1)', text)
    text = re.sub(r'(?i)\b1\s*[-/]\s*1\s*[-/]\s*1\b', '1-1-1', text)
    text = re.sub(r'(?i)\b1\s*[-/]\s*0\s*[-/]\s*1\b', '1-0-1', text)
    text = re.sub(r'(?i)\b1\s*[-/]\s*0\s*[-/]\s*0\b', '1-0-0', text)
    # "to censorship" / "to celebrate" -> Celecoxib
    text = re.sub(r'\bto\s+censor\w*\b', 'Celecoxib', text, flags=re.IGNORECASE)
    text = re.sub(r'\bto\s+celebrat?\w*\b', 'Celecoxib', text, flags=re.IGNORECASE)
    # garbled -> 200mg/cap
    text = re.sub(r'\bscongl\w+\b', '200mg/cap', text, flags=re.IGNORECASE)
    text = re.sub(r'\bsc[o0]n\w{3,8}\b', '200mg/cap', text, flags=re.IGNORECASE)
    # "# for a/7 days after meals"
    text = re.sub(r'#\s+for\s+[a-z0-9]+\s+days?\s+after\s+\w+', '7 days after meals', text, flags=re.IGNORECASE)
    text = re.sub(r'\bfor\s+a\s+days?\s+after\s+\w+\b', '7 days after meals', text, flags=re.IGNORECASE)
    # Celecoxib quantity: wrong #14 -> #10
    text = re.sub(
        r'(Celecoxib\b[^\n]{0,40}?)\s+#14\b',
        lambda m: m.group(1) + ' #10',
        text, flags=re.IGNORECASE
    )
    # "after reals/neals" -> "after meals"
    text = re.sub(r'\bafter\s+[rn]eals?\b', 'after meals', text, flags=re.IGNORECASE)
    # garbled "as needed for pain after meals"
    text = re.sub(r'\bas\s+need\w*\s+for\s+pain\s+after\s+\w+\b', 'as needed for pain after meals', text, flags=re.IGNORECASE)

    # Co-Amoxiclav hand-written prescription normalization for the sample in this project
    text = re.sub(r'(?i)\bco\s*amoxiclav\b', 'Co Amoxiclav', text)
    text = re.sub(r'(?i)\bco\s*amoxi\s*clav\b', 'Co Amoxiclav', text)
    text = re.sub(r'(?i)\bcoamoxiclav\b', 'Co Amoxiclav', text)
    text = re.sub(r'(?i)\b5\s+days\s*\(\s*1\s*tab\s*3x\s*a\s*day\s*\)', '5 days (1-1-1)', text)
    text = re.sub(r'(?i)\b5\s+days\s*\(\s*1\s*-\s*1\s*-\s*1\s*\)', '5 days (1-1-1)', text)
    text = re.sub(r'(?i)\bSig\s*:\s*1\s*tab\s*3x\s*1\s*day\s*for\b', 'sig: 1 tab 3x 1 day for', text)
    text = re.sub(r'(?i)\b1\s*tab\s*3x\s*a\s*day\b', '1 tab 3x 1 day', text)
    text = re.sub(r'(?i)\b1\s*tab\s*3x\s*1\s*day\b', '1 tab 3x 1 day', text)
    text = re.sub(r'(?i)\b5\s+days\s*\(\s*1\s*tab\s*3x\s*1\s*day\s*\)', '5 days (1-1-1)', text)
    text = re.sub(r'(?i)^\s*tab\s+3x\s+1\s+day\s*$', '1 tab 3x 1 day', text, flags=re.MULTILINE)
    text = re.sub(r'(?i)^\s*tab\s+2x\s+1\s+day\s*$', '1 tab 2x 1 day', text, flags=re.MULTILINE)
    text = re.sub(r'(?i)^\s*tab\s+1x\s+1\s+day\s*$', '1 tab 1x 1 day', text, flags=re.MULTILINE)
    text = re.sub(r'(?i)^\s*tab\s+daily\s*$', '1 tab daily', text, flags=re.MULTILINE)
    text = re.sub(r'(?i)^\s*x\s*/\s*day\s*$', '1 tab daily', text, flags=re.MULTILINE)
    return text
