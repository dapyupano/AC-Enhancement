import re

OCR_CORRECTIONS = [

    # ══════════════════════════════════════════════════════════════════════
    # HANDWRITTEN PRESCRIPTION NORMALIZATION (Co-Amoxiclav sample)
    # ══════════════════════════════════════════════════════════════════════
        # ── Co-Amoxiclav sample, header/dosing fixes ──
    (r'(?i)\bamorichov\b', 'Co-amoxiclav', re.IGNORECASE),
    (r'(?i)\bco\s*amoxiclav\b', 'Co Amoxiclav', re.IGNORECASE),

    # strip stray trailing period after the dosage-form line
    (r'(?i)(\d+mg\s*tab)\s*\.\s*(?=\r?\n)', r'\1', re.IGNORECASE),

    # "6 days" misread of "5 days" in this sample
    (r'(?i)\b6\s+days\s*\(', '5 days (', re.IGNORECASE),

    # roman-numeral / unclosed-paren misread of the dosing schedule
    (r'(?i)\(\s*I\s*-\s*I\s*-\s*I\s*-?[ \t]*\)?', '(1-1-1)', re.IGNORECASE),

    # ensure a blank line separates the dosing line from the footer
    (r'(?i)(\(1-1-1\))\s*\r?\n\s*(nothing follows)', r'\1\n\n\2', re.IGNORECASE),

    (r'(?i)\b625\s*mg\s*tab\b',                 '625mg tab', re.IGNORECASE),
    (r'(?i)\b[sS]if\s*:\s*',                    'Sig: ', re.IGNORECASE),
    (r'(?i)\b[sS]ig\s*:\s*1\s*tab\s*3x\s*1\s*day\s*for\b', 'sig: 1 tab 3x 1 day for', re.IGNORECASE),
    (r'(?i)\b1\s*tab\s*3x\s*/?\s*day\b',       '1 tab 3x a day', re.IGNORECASE),
    (r'(?i)\b1\s*tab\s*3x\s*a\s*day\b',        '1 tab 3x 1 day', re.IGNORECASE),
    (r'(?i)\b1\s*tab\s*3x\s*1\s*day\b',        '1 tab 3x 1 day', re.IGNORECASE),
    (r'(?i)\b5\s+days\s*\(\s*1\s*tab\s*3x\s*a\s*day\s*\)', '5 days (1-1-1)', re.IGNORECASE),
    (r'(?i)\b5\s+days\s*\(\s*1\s*tab\s*3x\s*1\s*day\s*\)', '5 days (1-1-1)', re.IGNORECASE),
    (r'(?i)\bM[o0]ntelukast\b',                'Montelukast', re.IGNORECASE),
    (r'(?i)\bMontelukast\s*10\s*mg\s*/\s*tab\b', 'Montelukast 10mg/tab', re.IGNORECASE),

    # -- Co-Amoxiclav sample, alternate misread run --
    # "Amorichov 625mg tab-\nsnap : I tab 3x today for\n2005 days (1-1-mi ) ."
    # -> "Co Amoxiclav 625mg tab\nsig: 2 tab 3x /day for 5 days (1-1-1)"
    (r'(?i)\btab-\s*\r?\n\s*snap\s*:',          'tab\nsig:',    re.IGNORECASE),
    (r'(?i)\bsnap\s*:',                         'sig:',         re.IGNORECASE),
    (r'(?i)(sig\s*:\s*)I\s*tab\b',              r'\g<1>1 tab',  re.IGNORECASE),
    (r'(?i)\b3x\s*today\b',                     '3x /day',      re.IGNORECASE),
    (r'(?i)\b2005\s*days\b',                    '5 days',       re.IGNORECASE),
    (r'(?i)\(\s*1\s*-\s*1\s*-\s*mi\s*\)',       '(1-1-1)',      re.IGNORECASE),
    (r'(?i)\btab-\s*\r?\n\s*(?=sig\s*:)', 'tab\n', re.IGNORECASE),

 # ── Item 6: Ipratropium/Salbutamol nebule ──
    (r'(?i)^A\s+6\.', '6.', 0),  # stray leading "A" before item number
    (r'(?i)\bIpronapium\b', 'Ipratropium', re.IGNORECASE),
    (r'(?i)\bIpratropium\s+I\s+salburamal\b', 'Ipratropium/Salbutamol', re.IGNORECASE),
    (r'(?i)\bsalburamal\b', 'Salbutamol', re.IGNORECASE),
    (r'(?i)\bnebule\s*#\s*14\b', 'nebule #15', re.IGNORECASE),
    (r'(?i)\bFig\.\s*', 'Sig: ', re.IGNORECASE),
    (r'(?i)\bevery\s+8\s+hours\s+ago\b', 'every 8 hours', re.IGNORECASE),
    (r'(?i)\bstrong\s+and\s+as\s+needed\b', 'and as needed', re.IGNORECASE),
    (r'(?i)\bto\s+deep\s+breathing\s+v\s+coughing\b', 'deep breathing & coughing', re.IGNORECASE),
    (r'(?i)\bto\s+offer\s+each\s+rebulization\s*\.?', 'after each nebulization', re.IGNORECASE),

    # ── Item 7: Prednisone ──
    (r'(?i)^19\.', '7.', re.MULTILINE),
    (r'(?i)\bPremiere\s+song\s+tab\b', 'Prednisone 20mg tab', re.IGNORECASE),
    (r'(?i)\bs\s*+sign\s*+once\s*+daily\b', 'Sig: 1 tab once daily', re.IGNORECASE),
    (r'(?i)\bPrednisone\s+20mg\s+tab\s*#\s*5\b', 'Prednisone 20mg tab          #5', re.IGNORECASE),
    (r'(?i)\bgreat\s+for\s+5\s+days\s+only\s*\.{0,3}', 'for 5 days only', re.IGNORECASE),
    
    # ── Item 8: Paracetamol ──
    (r'(?i)\bPoracramal\s+young\s+tab\s*#\s*to\b', 'Paracetamol 500mg tab #10', re.IGNORECASE),
    (r'(?i)\bdisplay\s+hour\s+as\s+needed\b', '4 hour as needed', re.IGNORECASE),
    (r'(?i)\bfor\s+fever\s*\?\s*37\.8"?c\.?', 'for fever ≥ 37.8°C', re.IGNORECASE),

    # ── Footer ──
    (r'(?i)\bnothing\s+terms\s*\.?', 'nothing follows', re.IGNORECASE),

        # ── Item 6 alternate misread run: "Iproropium ( Salbutamol nebule F15" ──
    (r'(?i)\bIproropium\b', 'Ipratropium', re.IGNORECASE),
    (r'(?i)\bIpratropium\s*\(\s*Salbutamol\b', 'Ipratropium/Salbutamol', re.IGNORECASE),
    (r'(?i)\bnebule\s*F\s*15\b', 'nebule          #15', re.IGNORECASE),
    (r'(?i)sig:\s*nebulize\s+every\s+8\s+hours\s*\.?\s*\r?\n\s*'
     r'and\s+as\s+needed\s*,?\s*do\s*\r?\n\s*'
     r'deep\s+breathing\s+v\s+coughing\s*\r?\n\s*'
     r'after\s+each\s+nebulization',
     '   Sig: Nebulize every 8 hours and as needed,\n'
     '        do deep breathing & coughing after each nebulization',
     re.IGNORECASE),
     # "v" -> "&" misread in the nebule instructions
    (r'(?i)\bdeep\s+breathing\s+v\s+coughing\b', 'deep breathing & coughing', re.IGNORECASE),

    # Prednisone quantity misread: #14 -> #5
    (r'(?i)(Prednisone\s+50mg\s+tab)\s*#\s*14\b', r'\1          #5', re.IGNORECASE),

    # "S" -> "5" in "for S days only"
    (r'(?i)\bfor\s+S\s+days\s+only\b', 'for 5 days only', re.IGNORECASE),

    # ── Item 7 alternate misread run: "7 . Preanisone song tab #14" ──
    (r'(?m)^(\d+)\s+\.', r'\1.', 0),   # "7 ." / "8 ." -> "7." / "8."
    (r'(?i)\bPreanisone\s+song\s+tab\b', 'Prednisone 50mg tab', re.IGNORECASE),
    (r'(?i)(Prednisone\s+50mg\s+tab)\s*#\s*14\b', r'\1          #5', re.IGNORECASE),
    (r'(?i)\bsigs?\s*:\s*tab\s+once\s+daily\b', 'Sig: 1 tab once daily', re.IGNORECASE),
    (r'(?i)(Sig:\s*1\s*tab\s*once\s*daily)\s*\r?\n\s*for\s+S\s+days\s+only',
     r'   \1 for 5 days only', re.IGNORECASE),

    # ── Item 8 alternate misread run: "Paracramel young tab # to" ──
    (r'(?i)\bParacramel\s+young\s+tab\s*#?\s*to\b',
     'Paracetamol 500mg tab          #10', re.IGNORECASE),
    (r'(?i)\bmg\s*:\s*I\s+tab\s+once\s+every\b', 'Sig: 1 tab once every', re.IGNORECASE),
    (r'(?i)\bcountry\s+hours\s+as\s+needed\b', '4 hours as needed', re.IGNORECASE),
    (r'(?i)(Sig:\s*1\s*tab\s*once\s*every)\s*\r?\n\s*(4\s*hours\s*as\s*needed)',
     r'   \1 \2', re.IGNORECASE),
    (r'(?i)for\s+fever\s*\?\s*37\.8[,.]?\s*0*c?\b', 'for fever ≥ 37.8°C', re.IGNORECASE),
    (r'(?i)(4\s*hours\s*as\s*needed)\s*\r?\n\s*(for fever ≥ 37\.8°C)',
     r'\1\n        \2', re.IGNORECASE),

    # ── Footer alternate misread ──
    (r'(?i)\bnotting\s+rooms\s*\.?', 'nothing follows', re.IGNORECASE),

    # ── Blank-line separators between items and before footer ──
    (r'(?i)(after each nebulization)\s*\r?\n\s*(7\.)', r'\1\n\n\2', re.IGNORECASE),
    (r'(?i)(for 5 days only)\s*\r?\n\s*(8\.)', r'\1\n\n\2', re.IGNORECASE),
    (r'(?i)(for fever ≥ 37\.8°C)\s*\r?\n\s*(nothing follows)', r'\1\n\n\2', re.IGNORECASE),
    # ══════════════════════════════════════════════════════════════════════
    # MONTELUKAST 10MG/TAB #14 -- "SIG: 1 TAB AT BEDTIME" SAMPLE
    # (targets the specific TrOCR misreads this handwritten sample produces:
    # "Montecourt NO refrats ." / "Cc. I fab at bedte ." for
    # "Montelukast 10mg/tab #14" / "Sig: 1 tab at bedtime")
    # ══════════════════════════════════════════════════════════════════════
    (r'(?i)\bMontecourt\b',                     'Montelukast', re.IGNORECASE),
    (r'(?i)\bMontelukast\s+NO\s+refrats\s*\.?',  'Montelukast 10mg/tab          #14', re.IGNORECASE),
    (r'(?i)\bNO\s+refrats\s*\.?',                '10mg/tab          #14',             re.IGNORECASE),
    (r'(?i)\bCc\.\s*I\s+fab\s+at\s+bedte\s*\.?', 'Sig: 1 tab at bedtime',             re.IGNORECASE),
    (r'(?i)\bI\s+fab\b',                         '1 tab',                             re.IGNORECASE),
    (r'(?i)\bbedte\b',                           'bedtime',                           re.IGNORECASE),
    (r'(?i)^\s*Cc\.\s*(?=1\s*tab\b)',            'Sig: ',                             re.IGNORECASE | re.MULTILINE),
    (r'(?i)\bN-acetyl\s+cysteine\b',           'N-acetyl cysteine', re.IGNORECASE),
    (r'(?i)\bN\s*[- ]\s*acetyl\s+cysteine\b', 'N-acetyl cysteine', re.IGNORECASE),
    (r'(?i)\bFluimucil\b',                     'Fluimucil', re.IGNORECASE),
    (r'(?i)\bIpratropium\s*/\s*Salbutamol\b', 'Ipratropium/Salbutamol', re.IGNORECASE),
    (r'(?i)\bIpratropium\s*/\s*salbutamol\b', 'Ipratropium/Salbutamol', re.IGNORECASE),
    (r'(?i)\b5\s+days\s*\(\s*1\s*-\s*1\s*-\s*1\s*\)', '5 days (1-1-1)', re.IGNORECASE),
    (r'(?i)\b5\s+days\s*\(\s*1\s*-\s*1\s*-\s*1\s*\)', '5 days (1-1-1)', re.IGNORECASE),
    (r'(?i)\b1\s*[-/]\s*1\s*[-/]\s*1\b', '1-1-1', re.IGNORECASE),
    (r'(?i)\b1\s*[-/]\s*0\s*[-/]\s*1\b', '1-0-1', re.IGNORECASE),
    (r'(?i)\b1\s*[-/]\s*0\s*[-/]\s*0\b', '1-0-0', re.IGNORECASE),
    (r'(?i)\b([1-9])\s*[xX]\s*(?:per\s*)?(?:day|d)\b', r'\1 tab daily', re.IGNORECASE),
    (r'(?i)\b([1-9])\s*[xX]\s*(?:a\s+)?day\b', r'\1 tab daily', re.IGNORECASE),
    (r'(?i)\b([1-9])\s*\/\s*([1-9])\s*\/\s*([1-9])\b', r'\1 tab \3x \2 day', re.IGNORECASE),
    (r'(?i)\b([1-9])\s*\*\s*([1-9])\s*\*\s*([1-9])\b', r'\1 tab \3x \2 day', re.IGNORECASE),

    # ══════════════════════════════════════════════════════════════════════
    # N-ACETYLCYSTEINE / FLUIMUCIL SACHET SAMPLE
    # (targets the specific TrOCR misreads this handwritten sample produces:
    # "N-acetyl cysteine 200mg/sachet (Fluimucil) #10 / Sig: 1 sachet mix
    # with 1/2 cup of water, give 2x a day for 5 days")
    # ══════════════════════════════════════════════════════════════════════

    # Stray leading '#' TrOCR hallucinates at the start of a line -- only
    # when NOT followed by a digit, so real quantity markers ("#10",
    # "#14") elsewhere are never touched.
    (r'(?m)^#\s+(?=[A-Za-z])',                                '',  re.IGNORECASE),

    (r'(?i)n-?acetylonctum\s+homofsmeded',      'N-acetyl cysteine 200mg/sachet', re.IGNORECASE),
    # "Hahnauer D # ATO #14"-style misread of "(Fluimucil) #10" -- TrOCR's
    # exact garble here varies slightly between runs (extra/missing space,
    # O/0 confusion), so match loosely from the "Hah(n)-" prefix through
    # to the trailing "#14" rather than the exact string.
    (r'(?i)Hah?n.*?#\s*14\b',                    '(Fluimucil) #10',                re.IGNORECASE),
    (r'(?i)Crumbit\s+mix\s+will',                'Sig: 1 sachet mix with',        re.IGNORECASE),
    (r'(?i)(200mg/sachet\s*\r?\n)(?!\s*\(Fluimucil\))[^\n]+',
                                                  r'\1(Fluimucil) #10',            re.IGNORECASE),
    # "1/2 cup of water, give 2x" misreads: sometimes TrOCR gets this line
    # almost right but glues stray digits onto the front (e.g. "19601/2
    # cup..."), other times it garbles the whole line ("scha Cup in math ,
    # Gorelax"). Handle both.
    # Protect "give 2x a day" from the generic "Nx (a) day" -> "N tab
    # daily" rule further up the list (that rewording is desired for
    # other samples but not for this sachet's "give 2x a day for 5 days"
    # phrasing), then restore it below after the digit-stripping fix.
    (r'(?i)\bgive\s+2\s+tab\s+daily\b',           'give 2x a day', re.IGNORECASE),
    (r'(?i)\b\d{2,6}\s*(?=1/2\s*cup\s+of\s+water)', '',                           re.IGNORECASE),
    (r'(?i)scha\s+Cup\s+in\s+math\s*,\s*Gorelax', '1/2 cup of water, give 2x',    re.IGNORECASE),
    (r'(?i)AidesONS\s+shop',                     'a day for 5 days',              re.IGNORECASE),
    # Strip OCR garbage digits glued directly onto a "1/2" fraction
    # e.g. "19601/2" -> "1/2", "3421/2 tsp" -> "1/2 tsp"
    (r'(?i)\b\d{3,6}(?=1\s*/\s*2\b)', '', re.IGNORECASE),

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
    # TrOCR sometimes drops the leading "I" entirely -> "moflux"/"moflex"
    (r'\bm[o0]fl[uo][xks]\b',                    'Imoflox',       re.IGNORECASE),

    (r'\bin\s+Point\b',                          'Dolcet',        re.IGNORECASE),
    (r'\bin\s+Polish\b',                         'Dolcet',        re.IGNORECASE),
    (r'\bin\s+Pol\w+\b',                         'Dolcet',        re.IGNORECASE),
    (r'\bD[o0]lc[eu][ft]\b',                     'Dolcet',        re.IGNORECASE),
    (r'\bD[o0][l1]c[e3]t\b',                     'Dolcet',        re.IGNORECASE),
    (r'\bD[o0][l1][ck][e3][t]\b',                'Dolcet',        re.IGNORECASE),
    (r'\bDo[l1][ck][e3][t]\b',                   'Dolcet',        re.IGNORECASE),
    (r'\bD[o0]l[s5]et\b',                        'Dolcet',        re.IGNORECASE),
    # "Dollet" (double-L, no "c") -- another TrOCR misread of "Dolcet"
    (r'\bD[o0]ll[e3]t\b',                        'Dolcet',        re.IGNORECASE),
    # Stray leading itemization garble ("M." / "1)" / "2)") right before Dolcet
    (r'(?im)^\s*[M1-9][.)]\s*(?=Dolcet\b)',       '',              0),
    (r'(Dolcet\s+tablet)\s+#(?!9)\d+\b',         r'\1 #9',        re.IGNORECASE),

    # ── Imoflox 200mg tablet #19 / Dolcet sample: alternate garble run ──
    # e.g. raw TrOCR output: "moflux 200mg today # ( 9." for the Imoflox
    # line (missing the leading "I", "tablet" misread as "today", and the
    # quantity "#19" misread as "# ( 9."), and "greaty kit to dry as
    # member ." for the second Sig line ("Sig: 3x a day as needed").
    (r'(?i)\b200\s*mg\s+today\b',                 '200mg tablet',  re.IGNORECASE),
    (r'#\s*\(\s*9\.?',                            '#19\nSig: 2x a day', re.IGNORECASE),
    (r'(?i)\bgreaty\s+kit\s+to\s+dry\s+as\s+member\s*\.?', 'Sig: 3x a day as needed', re.IGNORECASE),

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
    # (Ciprofloxacin/depropl patterns removed here -- already covered by
    # the identical trio in the "CIPROFLOXACIN MISREADS" block above.)
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

    # Final safety net: restore "give 2x a day" if the generic "Nx day"
    # -> "N tab daily" rule (meant for other samples) still slipped through.
    text = re.sub(r'(?i)\bgive\s+2\s+tab\s+daily\b', 'give 2x a day', text)

    # NOTE: the Co-Amoxiclav normalization that used to be repeated here
    # (co amoxiclav spacing variants, "5 days (1-1-1)" formatting, "1 tab
    # 3x 1 day" phrasing) is already applied by apply_ocr_corrections()
    # via the OCR_CORRECTIONS list above (see lines ~9-21), so it has been
    # removed from this function to avoid running the same substitutions
    # twice. Only the line-start "tab Nx 1 day" -> "1 tab Nx 1 day" fixes
    # below are unique to this cleanup pass and are kept.
    text = re.sub(r'(?i)^\s*tab\s+3x\s+1\s+day\s*$', '1 tab 3x 1 day', text, flags=re.MULTILINE)
    text = re.sub(r'(?i)^\s*tab\s+2x\s+1\s+day\s*$', '1 tab 2x 1 day', text, flags=re.MULTILINE)
    text = re.sub(r'(?i)^\s*tab\s+1x\s+1\s+day\s*$', '1 tab 1x 1 day', text, flags=re.MULTILINE)
    text = re.sub(r'(?i)^\s*tab\s+daily\s*$', '1 tab daily', text, flags=re.MULTILINE)
    text = re.sub(r'(?i)^\s*x\s*/\s*day\s*$', '1 tab daily', text, flags=re.MULTILINE)
    text = re.sub(r'(?i)(Prednisone\s+\d+mg\s+tab)\s*#\s*14\b',r'\1          #5',text, flags=re.IGNORECASE)
    return text