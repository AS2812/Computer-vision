"""Reviewed bilingual treatment knowledge base for Egyptian crop diseases.

For each disease we list control products ordered by effectiveness. Every entry
carries the active ingredient, FRAC resistance group, a typical label dose range,
the application scheme (how / when / rotation), the pre-harvest interval (PHI),
the hazard / side-effects, and an *approximate* price range.

Honesty rules baked into this file:
- Doses and PHIs are typical label references for guidance — the farmer must read
  the actual product label, because rates differ by formulation and crop.
- Prices are approximate and change constantly, so every price says to confirm
  with the local dealer (محل مبيدات / الجمعية الزراعية). We never state an exact price.
- Where a disease has no chemical cure (Fusarium wilt, viruses), we say so plainly
  and list cultural control instead of inventing a "cure".

The assistant and the dashboard read from this module; they must not invent any
product, dose, or price that is not written here.
"""

from __future__ import annotations

from .schemas import Treatment


# --- Reusable product builders ------------------------------------------------
# Each builder holds the standard, well-established facts for one active and lets
# the caller set the effectiveness rank and a disease-specific note.

def _mancozeb(rank: int, note_en: str, note_ar: str, phi_en: str = "7–14 days (check the crop label)", phi_ar: str = "7–14 يوم (راجع لافتة المحصول)") -> Treatment:
    return Treatment(
        rank=rank,
        name_en="Mancozeb 80% WP (e.g. Dithane M-45, Penncozeb)",
        name_ar="مانكوزيب 80% (زي ديثان إم-45 أو بنكوزيب)",
        frac="M03 — multi-site contact (very low resistance risk)",
        dose_en="250–300 g per 100 L water (about 2.5–3 kg/feddan)",
        dose_ar="250–300 جم لكل 100 لتر مية (حوالي 2.5–3 كجم للفدان)",
        application_en="Protectant — spray before/early in the disease, cover the underside of the leaves, repeat every 7–10 days. Good tank-mix partner to protect single-site fungicides.",
        application_ar="وقائي — رشّه قبل أو في بداية المرض، وغطّي ضهر الورق، وكرّر كل 7–10 أيام. كويس تخلطه مع مبيد جهازي عشان يحميه.",
        phi_en=phi_en,
        phi_ar=phi_ar,
        hazard_en="Low acute toxicity (WHO 'U'); still wear gloves + mask, it irritates skin/eyes and chronic exposure has thyroid/reproductive concerns. Toxic to fish.",
        hazard_ar="سُمّيّته قليلة، بس البس جوانتي وكمامة لأنه بيهيّج الجلد والعين، والتعرّض المزمن له تحذيرات على الغدة والإنجاب. سام للأسماك.",
        price_en="Cheap — roughly 40–90 EGP/kg. Confirm the current price at your local dealer.",
        price_ar="رخيص — حوالي 40–90 جنيه للكيلو. أكّد السعر الحالي من محل المبيدات.",
        note_en=note_en,
        note_ar=note_ar,
    )


def _chlorothalonil(rank: int, note_en: str, note_ar: str) -> Treatment:
    return Treatment(
        rank=rank,
        name_en="Chlorothalonil 72% SC / 75% WP (e.g. Bravo, Daconil)",
        name_ar="كلوروثالونيل 72% (زي برافو أو داكونيل)",
        frac="M05 — multi-site contact (very low resistance risk)",
        dose_en="200–250 ml/g per 100 L water",
        dose_ar="200–250 مل/جم لكل 100 لتر مية",
        application_en="Strong protectant for leaf spots and blights. Spray every 7 days in disease weather, full coverage. Use in rotation with mancozeb to protect systemic products.",
        application_ar="وقائي قوي للتبقّع واللفحة. رشّ كل 7 أيام في جو المرض مع تغطية كاملة، وبدّله مع المانكوزيب عشان يحمي المبيدات الجهازية.",
        phi_en="About 7 days",
        phi_ar="حوالي 7 أيام",
        hazard_en="Irritating to eyes, skin and lungs — wear goggles + mask. Very toxic to fish; restricted in the EU. Do not spray near water.",
        hazard_ar="بيهيّج العين والجلد والصدر — البس نضّارة وكمامة. سام جدًا للأسماك وممنوع في أوروبا. ما ترشّش جنب المية.",
        price_en="Moderate — roughly 120–220 EGP/L. Confirm locally.",
        price_ar="متوسط — حوالي 120–220 جنيه للتر. أكّد السعر محليًا.",
        note_en=note_en,
        note_ar=note_ar,
    )


def _copper(rank: int, note_en: str, note_ar: str) -> Treatment:
    return Treatment(
        rank=rank,
        name_en="Copper hydroxide / oxychloride (e.g. Kocide, Champion, Cupravit)",
        name_ar="مركبات النحاس — هيدروكسيد/أوكسي كلورايد (زي كوسيد أو شامبيون أو كوبرافيت)",
        frac="M01 — multi-site (very low resistance risk); allowed in organic farming",
        dose_en="250–350 g per 100 L water",
        dose_ar="250–350 جم لكل 100 لتر مية",
        application_en="Protectant and mildly bactericidal. Spray every 7–10 days. Avoid spraying in cold, wet weather or on young leaves — copper can burn the foliage.",
        application_ar="وقائي وبيقلّل البكتيريا كمان. رشّ كل 7–10 أيام. ما ترشّوش في جو بارد ومبلّل ولا على ورق صغيّر عشان النحاس ممكن يحرق الورق.",
        phi_en="About 3–7 days",
        phi_ar="حوالي 3–7 أيام",
        hazard_en="Low toxicity to people; irritates eyes. Builds up in the soil over years and is toxic to fish. Can scorch leaves (phytotoxic).",
        hazard_ar="سُمّيّته قليلة للإنسان وبيهيّج العين. بيتراكم في الأرض مع السنين وسام للأسماك، وممكن يحرق الورق.",
        price_en="Cheap–moderate — roughly 60–150 EGP/kg. Confirm locally.",
        price_ar="رخيص لمتوسط — حوالي 60–150 جنيه للكيلو. أكّد السعر محليًا.",
        note_en=note_en,
        note_ar=note_ar,
    )


def _azoxy_difeno(rank: int, note_en: str, note_ar: str) -> Treatment:
    return Treatment(
        rank=rank,
        name_en="Azoxystrobin + Difenoconazole (e.g. Ortiva Top, Amistar Top)",
        name_ar="أزوكسيستروبين + ديفينوكونازول (زي أورتيفا توب أو أميستار توب)",
        frac="11 + 3 — systemic (rotate; do not over-use group 11)",
        dose_en="75–100 ml per 100 L water (follow the label)",
        dose_ar="75–100 مل لكل 100 لتر مية (اتبع اللافتة)",
        application_en="Strong systemic with curative + protectant action — best when symptoms are just starting. Use at most 2–3 times a season and rotate with multi-site products (mancozeb/chlorothalonil) to avoid resistance.",
        application_ar="جهازي قوي بيعالج ويحمي — أحسن استخدام في أول ظهور للمرض. استخدمه 2–3 مرات بالكتير في الموسم وبدّله مع مبيدات وقائية (مانكوزيب/كلوروثالونيل) عشان ما يحصلش مقاومة.",
        phi_en="About 3–7 days",
        phi_ar="حوالي 3–7 أيام",
        hazard_en="Low toxicity to people; very toxic to aquatic life — keep away from water and bees during spraying.",
        hazard_ar="سُمّيّته قليلة للإنسان، بس سام جدًا للكائنات المائية — بعّده عن المية والنحل وقت الرش.",
        price_en="Higher — roughly 250–500 EGP per small bottle. Confirm locally.",
        price_ar="أغلى شوية — حوالي 250–500 جنيه للعبوة الصغيرة. أكّد السعر محليًا.",
        note_en=note_en,
        note_ar=note_ar,
    )


def _difenoconazole(rank: int, note_en: str, note_ar: str) -> Treatment:
    return Treatment(
        rank=rank,
        name_en="Difenoconazole 25% EC (e.g. Score)",
        name_ar="ديفينوكونازول 25% (زي سكور)",
        frac="3 — DMI systemic (rotate)",
        dose_en="30–50 ml per 100 L water",
        dose_ar="30–50 مل لكل 100 لتر مية",
        application_en="Systemic, good on leaf spots and early blight. Spray at first symptoms and repeat after 10–14 days; rotate with a different group.",
        application_ar="جهازي، كويس للتبقّع واللفحة المبكرة. رشّ أول ما تظهر الأعراض وكرّر بعد 10–14 يوم، وبدّله مع مجموعة تانية.",
        phi_en="About 7–14 days",
        phi_ar="حوالي 7–14 يوم",
        hazard_en="Moderate — avoid breathing the spray, wear PPE. Toxic to fish.",
        hazard_ar="متوسط — ما تتنفّسش الرذاذ والبس وقاية. سام للأسماك.",
        price_en="Moderate–high. Confirm locally.",
        price_ar="متوسط لأعلى. أكّد السعر محليًا.",
        note_en=note_en,
        note_ar=note_ar,
    )


def _metalaxyl_mz(rank: int, note_en: str, note_ar: str) -> Treatment:
    return Treatment(
        rank=rank,
        name_en="Metalaxyl-M + Mancozeb (e.g. Ridomil Gold MZ 68 WG)",
        name_ar="ميتالاكسيل-إم + مانكوزيب (زي ريدوميل جولد إم زد)",
        frac="4 + M03 — systemic for downy/late blight (group 4 has high resistance risk)",
        dose_en="250 g per 100 L water",
        dose_ar="250 جم لكل 100 لتر مية",
        application_en="Systemic, moves inside the plant against late/downy mildew. Because resistance builds fast, use at most 2–3 times a season, always in this ready-mix, and rotate with a non-group-4 product.",
        application_ar="جهازي بيدخل جوّه النبات ضد اللفحة المتأخرة والبياض الزغبي. المقاومة بتظهر بسرعة، فاستخدمه 2–3 مرات بالكتير في الموسم وهو متخلوط كده وبدّله مع مبيد من مجموعة تانية.",
        phi_en="About 7–14 days",
        phi_ar="حوالي 7–14 يوم",
        hazard_en="Low–moderate toxicity; wear gloves + mask (contains mancozeb). Toxic to fish.",
        hazard_ar="سُمّيّته قليلة لمتوسطة، البس جوانتي وكمامة (فيه مانكوزيب). سام للأسماك.",
        price_en="Higher — roughly 150–300 EGP per pack. Confirm locally.",
        price_ar="أغلى — حوالي 150–300 جنيه للعبوة. أكّد السعر محليًا.",
        note_en=note_en,
        note_ar=note_ar,
    )


def _cymoxanil_mz(rank: int, note_en: str, note_ar: str) -> Treatment:
    return Treatment(
        rank=rank,
        name_en="Cymoxanil + Mancozeb (e.g. Curzate M)",
        name_ar="سيموكسانيل + مانكوزيب (زي كيرزيت إم)",
        frac="27 + M03 — short curative kick-back + protectant",
        dose_en="200–250 g per 100 L water",
        dose_ar="200–250 جم لكل 100 لتر مية",
        application_en="Has a 1–2 day 'kick-back' on early late/downy blight infections but short persistence, so spray every 5–7 days during high pressure and tank-mix/rotate with a protectant.",
        application_ar="بيلحق إصابة اللفحة في أول يوم أو يومين بس تأثيره قصير، فارشّ كل 5–7 أيام في وقت الضغط العالي واخلطه/بدّله مع مبيد وقائي.",
        phi_en="About 3–7 days",
        phi_ar="حوالي 3–7 أيام",
        hazard_en="Low–moderate; wear gloves + mask. Toxic to fish.",
        hazard_ar="قليلة لمتوسطة، البس جوانتي وكمامة. سام للأسماك.",
        price_en="Moderate. Confirm locally.",
        price_ar="متوسط. أكّد السعر محليًا.",
        note_en=note_en,
        note_ar=note_ar,
    )


def _mandipropamid(rank: int, note_en: str, note_ar: str) -> Treatment:
    return Treatment(
        rank=rank,
        name_en="Mandipropamid (e.g. Revus)",
        name_ar="مانديبروباميد (زي ريفوس)",
        frac="40 — CAA, translaminar (rotate)",
        dose_en="50–60 ml per 100 L water",
        dose_ar="50–60 مل لكل 100 لتر مية",
        application_en="Excellent rainfast protectant that moves into the leaf — strong on late blight and downy mildew. Spray every 7–10 days, rotate with a different group.",
        application_ar="وقائي ممتاز بيثبت على الورق وما تغسلوش المطرة وبيدخل في الورقة — قوي على اللفحة المتأخرة والبياض الزغبي. رشّ كل 7–10 أيام وبدّله مع مجموعة تانية.",
        phi_en="About 1–3 days",
        phi_ar="حوالي 1–3 أيام",
        hazard_en="Low toxicity to people; still keep off water bodies.",
        hazard_ar="سُمّيّته قليلة للإنسان، بس بعّده عن المية.",
        price_en="Higher. Confirm locally.",
        price_ar="أغلى. أكّد السعر محليًا.",
        note_en=note_en,
        note_ar=note_ar,
    )


def _revus_top(rank: int, note_en: str, note_ar: str) -> Treatment:
    return Treatment(
        rank=rank,
        name_en="Mandipropamid + Difenoconazole (e.g. Revus Top 500 SC)",
        name_ar="مانديبروباميد + ديفينوكونازول (زي ريفوس توب 500 إس سي)",
        frac="40 + 3 — translaminar + DMI systemic (rotate)",
        dose_en="50 ml per 100 L water is a common label-style reference; verify the Egyptian label before use",
        dose_ar="50 مل لكل 100 لتر مية كمرجع شائع؛ أكّد اللافتة المصرية قبل الاستخدام",
        application_en="Useful when the farmer needs one spray covering late blight pressure plus Alternaria/early-blight pressure. Do not use as a routine repeated spray; rotate with multi-site protectants.",
        application_ar="مفيد لما يكون ضغط اللفحة المتأخرة موجود ومعاه ضغط ألترناريا/لفحة مبكرة. ما يتكررش كروتين؛ بدّله مع مبيدات وقائية متعددة المواقع.",
        phi_en="Check the local tomato label; do not guess near harvest",
        phi_ar="راجع لافتة الطماطم المحلية؛ ما تخمّنش قرب الحصاد",
        hazard_en="Moderate caution: wear PPE; avoid spray drift and water bodies.",
        hazard_ar="احتياطات متوسطة: البس وقاية؛ ابعد الرذاذ عن المجاري المائية.",
        price_en="Online retail source may show price/stock; confirm locally before buying.",
        price_ar="مصدر أونلاين قد يعرض السعر/التوفر؛ أكّد محليًا قبل الشراء.",
        note_en=note_en,
        note_ar=note_ar,
    )


def _sulfur(rank: int, note_en: str, note_ar: str) -> Treatment:
    return Treatment(
        rank=rank,
        name_en="Wettable sulfur 80% (e.g. Thiovit, Kumulus)",
        name_ar="كبريت قابل للبلل 80% (زي ثيوفيت أو كوميولوس)",
        frac="M02 — multi-site (very low resistance risk); organic-approved",
        dose_en="250–300 g per 100 L water",
        dose_ar="250–300 جم لكل 100 لتر مية",
        application_en="Cheap, reliable protectant for powdery mildew (also helps with mites). Spray every 7–10 days. Do NOT spray when it is hotter than ~32°C or mix with oils — it will burn the leaves.",
        application_ar="رخيص وممتاز للبياض الدقيقي (وبيساعد ضد العنكبوت كمان). رشّ كل 7–10 أيام. ما ترشّوش لما الحر يعدّي 32 درجة ولا تخلطه بزيوت عشان ما يحرقش الورق.",
        phi_en="About 0–3 days",
        phi_ar="حوالي 0–3 أيام",
        hazard_en="Very low toxicity; can irritate skin/eyes. Phytotoxic in high heat.",
        hazard_ar="سُمّيّته قليلة جدًا، بس ممكن يهيّج الجلد والعين، وبيحرق الورق في الحر العالي.",
        price_en="Very cheap. Confirm locally.",
        price_ar="رخيص جدًا. أكّد السعر محليًا.",
        note_en=note_en,
        note_ar=note_ar,
    )


def _triazole_pm(rank: int, note_en: str, note_ar: str) -> Treatment:
    return Treatment(
        rank=rank,
        name_en="Penconazole / Myclobutanil / Tebuconazole (DMI, e.g. Topas, Systhane)",
        name_ar="بنكونازول / ميكلوبيوتانيل / تيبوكونازول (زي توباس أو سيستان)",
        frac="3 — DMI systemic (rotate)",
        dose_en="Follow the label (rates differ by product and crop)",
        dose_ar="اتبع اللافتة (الجرعة بتختلف حسب المنتج والمحصول)",
        application_en="Systemic, both protective and curative on powdery mildew and rusts. Spray at first symptoms; rotate with sulfur or a group-11 product to slow resistance.",
        application_ar="جهازي بيحمي ويعالج البياض الدقيقي والأصداء. رشّ أول ظهور للمرض وبدّله مع الكبريت أو مبيد من مجموعة 11 عشان تأخّر المقاومة.",
        phi_en="About 7–14 days",
        phi_ar="حوالي 7–14 يوم",
        hazard_en="Moderate — wear PPE, avoid inhaling the spray. Toxic to fish.",
        hazard_ar="متوسط — البس وقاية وما تتنفّسش الرذاذ. سام للأسماك.",
        price_en="Moderate. Confirm locally.",
        price_ar="متوسط. أكّد السعر محليًا.",
        note_en=note_en,
        note_ar=note_ar,
    )


def _azoxystrobin(rank: int, note_en: str, note_ar: str) -> Treatment:
    return Treatment(
        rank=rank,
        name_en="Azoxystrobin 25% SC (e.g. Ortiva, Quadris)",
        name_ar="أزوكسيستروبين 25% (زي أورتيفا أو كوادريس)",
        frac="11 — QoI systemic (HIGH resistance risk — rotate, max 2–3/season)",
        dose_en="50–80 ml per 100 L water",
        dose_ar="50–80 مل لكل 100 لتر مية",
        application_en="Systemic, protective + early-curative on many leaf spots and mildews. Group 11 loses power fast if over-used, so never spray it twice in a row — alternate with mancozeb/chlorothalonil or a triazole.",
        application_ar="جهازي بيحمي وبيعالج بدري كتير من التبقّع والبياض. مجموعة 11 بتفقد قوتها بسرعة لو زوّدت عليها، فما ترشّهاش مرتين ورا بعض — بدّل مع مانكوزيب/كلوروثالونيل أو ترايازول.",
        phi_en="About 3–7 days",
        phi_ar="حوالي 3–7 أيام",
        hazard_en="Low to people; very toxic to aquatic life and bees during spraying.",
        hazard_ar="قليلة للإنسان، بس سام جدًا للكائنات المائية والنحل وقت الرش.",
        price_en="Higher. Confirm locally.",
        price_ar="أغلى. أكّد السعر محليًا.",
        note_en=note_en,
        note_ar=note_ar,
    )


def _propiconazole(rank: int, note_en: str, note_ar: str) -> Treatment:
    return Treatment(
        rank=rank,
        name_en="Propiconazole 25% EC (e.g. Tilt)",
        name_ar="بروبيكونازول 25% (زي تيلت)",
        frac="3 — DMI systemic (rotate)",
        dose_en="50 ml per 100 L water (follow the label)",
        dose_ar="50 مل لكل 100 لتر مية (اتبع اللافتة)",
        application_en="Systemic, a backbone product against Sigatoka leaf spot and rusts. Often sprayed with mineral oil on banana; rotate with a strobilurin or multi-site.",
        application_ar="جهازي وأساسي ضد تبقّع سيجاتوكا والأصداء. بيترش كتير مع زيت معدني على الموز، وبدّله مع ستروبيلورين أو مبيد متعدد المواقع.",
        phi_en="About 14–30 days (check the crop)",
        phi_ar="حوالي 14–30 يوم (راجع المحصول)",
        hazard_en="Moderate — wear PPE. Toxic to fish.",
        hazard_ar="متوسط — البس وقاية. سام للأسماك.",
        price_en="Moderate. Confirm locally.",
        price_ar="متوسط. أكّد السعر محليًا.",
        note_en=note_en,
        note_ar=note_ar,
    )


# --- Disease -> ranked treatment program -------------------------------------

_TREATMENTS: dict[str, list[Treatment]] = {
    # Tomato Septoria leaf spot (the photo the user tested) — same family of
    # foliar fungicides used for early blight.
    "septoria_leaf_spot_tomato": [
        _azoxy_difeno(1, "Best single choice when spots are spreading — stops the fungus and protects new growth.", "أحسن اختيار لما البقع تبدأ تنتشر — بيوقف الفطر ويحمي النموّ الجديد."),
        _difenoconazole(2, "Strong, cheaper systemic for early Septoria; rotate it with the mix above.", "جهازي قوي وأرخص للسبتوريا المبكرة، وبدّله مع الخلطة اللي فوق."),
        _chlorothalonil(3, "Reliable protective backbone — spray it between the systemic sprays.", "وقائي أساسي ومضمون — رشّه بين رشّات المبيد الجهازي."),
        _mancozeb(4, "Cheap protectant for routine cover sprays and to protect the systemics from resistance.", "وقائي رخيص للرشّ الدوري وعشان يحمي المبيدات الجهازية من المقاومة."),
        _copper(5, "Budget / organic option and helps against bacterial spots too; weaker alone in heavy disease.", "اختيار اقتصادي/عضوي وبيساعد ضد التبقّع البكتيري كمان، بس ضعيف لوحده في الإصابة الشديدة."),
    ],
    # Tomato / potato EARLY blight (Alternaria)
    "tomato_early_blight": [
        _azoxy_difeno(1, "Top choice — strong on Alternaria's target-spot lesions and protects the plant.", "الاختيار الأول — قوي على بقع الألترناريا وبيحمي النبات."),
        _difenoconazole(2, "Effective systemic; rotate with the strobilurin mix.", "جهازي فعّال، وبدّله مع خلطة الستروبيلورين."),
        _chlorothalonil(3, "Excellent protectant cover spray every 7 days in disease weather.", "وقائي ممتاز كل 7 أيام في جو المرض."),
        _mancozeb(4, "Cheap routine protectant and resistance partner.", "وقائي رخيص للروتين وشريك ضد المقاومة."),
        _copper(5, "Low-cost protectant, weaker on heavy early blight.", "وقائي رخيص، أضعف في الإصابة الشديدة."),
    ],
    # Tomato / potato LATE blight (Phytophthora infestans) — oomycete, fast & destructive
    "tomato_late_blight": [
        _mandipropamid(1, "Best protectant for late blight — rainfast and moves into the leaf. Start before/at first signs.", "أحسن وقائي للّفحة المتأخرة — ما تغسلوش المطرة وبيدخل الورقة. ابدأ قبل/مع أول علامة."),
        _revus_top(2, "Premium broad option when late blight and early-blight/Alternaria pressure overlap; rotate strictly.", "اختيار قوي لما ضغط اللفحة المتأخرة واللفحة المبكرة/الألترناريا يكونوا مع بعض؛ بدّله بصرامة."),
        _cymoxanil_mz(3, "Use when blight has already started — it catches very early infections, then keep covering.", "استخدمه لما اللفحة تكون بدأت — بيلحق الإصابة في أولها، وبعدين كمّل تغطية."),
        _metalaxyl_mz(4, "Powerful systemic but resistance-prone — only 2–3 times a season, always rotated.", "جهازي قوي بس المقاومة بتطلع عليه بسرعة — 2–3 مرات بس في الموسم ودايمًا بالتبديل."),
        _chlorothalonil(5, "Solid multi-site protectant for the cover sprays between systemics.", "وقائي متعدد المواقع كويس للرشّات بين المبيدات الجهازية."),
        _mancozeb(6, "Cheap protectant base; spray every 7 days in cool, wet, foggy weather.", "أساس وقائي رخيص، رشّ كل 7 أيام في الجو البارد المبلّل المضبّب."),
    ],
    # Powdery mildew (tomato, pepper, cucurbits, grape, ...)
    "powdery_mildew": [
        _sulfur(1, "First choice — cheap, very effective on powdery mildew, and safe close to harvest (just not in high heat).", "الاختيار الأول — رخيص وفعّال جدًا على البياض الدقيقي وآمن قرب الحصاد (بس مش في الحر العالي)."),
        _triazole_pm(2, "Systemic that also cures established mildew; rotate with sulfur.", "جهازي بيعالج البياض المستقر كمان، وبدّله مع الكبريت."),
        _azoxystrobin(3, "Protective + early-curative; never two sprays in a row (group 11).", "بيحمي ويعالج بدري، بس ما ترشّوش مرتين ورا بعض (مجموعة 11)."),
        _difenoconazole(4, "Another DMI option to rotate into the program.", "اختيار ترايازول تاني تبدّله في البرنامج."),
        _copper(5, "Weak on powdery mildew specifically — use only as a last/cheap option.", "ضعيف على البياض الدقيقي بالذات — استخدمه كآخر اختيار رخيص بس."),
    ],
    # Downy mildew (cucurbits, grape, onion, ...) — oomycete like late blight
    "downy_mildew": [
        _mandipropamid(1, "Best rainfast protectant for downy mildew; start early and keep a 7–10 day rhythm.", "أحسن وقائي ثابت ضد البياض الزغبي، ابدأ بدري وحافظ على رشّة كل 7–10 أيام."),
        _metalaxyl_mz(2, "Strong systemic — limited uses per season, always rotated.", "جهازي قوي — مرات محدودة في الموسم ودايمًا بالتبديل."),
        _cymoxanil_mz(3, "Good kick-back when downy mildew has just appeared.", "كويس لما البياض الزغبي يكون لسه ظاهر."),
        _copper(4, "Cheap protectant, useful on grape and onion downy mildew.", "وقائي رخيص ومفيد على البياض الزغبي في العنب والبصل."),
        _mancozeb(5, "Routine protectant base in the rotation.", "أساس وقائي للروتين في التبديل."),
    ],
    # Banana Sigatoka leaf spot (the model's class) — fungicide-responsive
    "sigatoka_leaf_spot": [
        _propiconazole(1, "Backbone systemic for Sigatoka, usually sprayed with light mineral oil; rotate groups.", "الأساس الجهازي ضد سيجاتوكا، بيترش عادة مع زيت معدني خفيف، وبدّل المجموعات."),
        _azoxystrobin(2, "Strong systemic — alternate with the triazole, never back-to-back.", "جهازي قوي — بدّله مع الترايازول، وما ترشّهاش ورا بعض."),
        _chlorothalonil(3, "Protectant cover spray to slow resistance to the systemics.", "وقائي بيبطّأ المقاومة للمبيدات الجهازية."),
        _mancozeb(4, "Cheap protectant base, repeated every 10–14 days.", "أساس وقائي رخيص كل 10–14 يوم."),
        _copper(5, "Low-cost protectant; weaker alone under heavy Sigatoka pressure.", "وقائي رخيص، أضعف لوحده تحت ضغط سيجاتوكا الشديد."),
    ],
    # Banana Cordana leaf spot — usually minor; mostly cultural + protectant
    "cordana_leaf_spot": [
        _mancozeb(1, "Usually enough for this minor disease — a protectant spray plus removing spotted leaves.", "غالبًا بيكفي للمرض البسيط ده — رشّة وقائية مع شيل الورق المبقّع."),
        _copper(2, "Alternative cheap protectant; also helps keep leaves clean.", "بديل وقائي رخيص وبيساعد يخلّي الورق نضيف."),
        _chlorothalonil(3, "Use only if spots spread widely in warm, humid, poorly drained blocks.", "استخدمه بس لو البقع انتشرت كتير في جو دافي رطب وصرف ضعيف."),
    ],
}


def _abamectin(rank: int, note_en: str, note_ar: str) -> Treatment:
    return Treatment(
        rank=rank,
        name_en="Abamectin 1.8% EC (e.g. Vertimec)",
        name_ar="أباميكتين 1.8% (زي فيرتيمك)",
        frac="Miticide/insecticide (IRAC 6) — NOT a fungicide",
        dose_en="40–50 ml per 100 L water (follow the label)",
        dose_ar="40–50 مل لكل 100 لتر مية (اتبع اللافتة)",
        application_en="Spider mites are a PEST, not a fungus. Spray covering the leaf underside where mites live; repeat after 7–10 days. Add a wetting agent and rotate with a different miticide group.",
        application_ar="العنكبوت الأحمر آفة مش فطر. رشّ وغطّي ضهر الورقة اللي العنكبوت عايش فيه، وكرّر بعد 7–10 أيام. حِط مادة ناشرة وبدّل مع مجموعة أكاروسيد تانية.",
        phi_en="About 7–14 days",
        phi_ar="حوالي 7–14 يوم",
        hazard_en="Toxic — wear full PPE. Very toxic to bees and fish; never spray on flowers during bee activity.",
        hazard_ar="سام — البس وقاية كاملة. سام جدًا للنحل والأسماك؛ ما ترشّش على الزهور وقت نشاط النحل.",
        note_en=note_en,
        note_ar=note_ar,
    )


def _acetamiprid(rank: int, note_en: str, note_ar: str) -> Treatment:
    return Treatment(
        rank=rank,
        name_en="Acetamiprid 20% SP (e.g. Mospilan)",
        name_ar="أسيتامبريد 20% (زي موسبيلان)",
        frac="Insecticide (IRAC 4A neonicotinoid)",
        dose_en="25 g per 100 L water (about 250 g/feddan)",
        dose_ar="25 جم لكل 100 لتر مية (حوالي 250 جم للفدان)",
        application_en="Systemic vector control — targets whiteflies. Spray thoroughly, especially leaf undersides where adults gather. Rotate with different IRAC groups to prevent rapid resistance.",
        application_ar="مكافحة جهازية للناقل — بيستهدف الذبابة البيضا. رشّ كويس خصوصًا ضهر الورق مكان تجمع الذبابة. بدّل مع مجموعات تانية عشان تمنع المقاومة.",
        phi_en="About 3–7 days",
        phi_ar="حوالي 3–7 أيام",
        hazard_en="Moderate toxicity to humans (wear PPE: gloves + mask). Highly toxic to bees; do not spray during active bloom or bee foraging.",
        hazard_ar="سمية متوسطة للإنسان (البس وقاية: جوانتي وكمامة). سام جداً للنحل؛ ما ترشّش وقت التزهير أو نشاط النحل.",
        price_en="Moderate — roughly 80–150 EGP per pack. Confirm locally.",
        price_ar="متوسط — حوالي 80–150 جنيه للعبوة. أكّد السعر محليًا.",
        note_en=note_en,
        note_ar=note_ar,
    )


def _mineral_oil_vector(rank: int, note_en: str, note_ar: str) -> Treatment:
    return Treatment(
        rank=rank,
        name_en="Summer Mineral Oil / Potassium Soap",
        name_ar="الزيت المعدني الصيفي / صابون البوتاسيوم",
        frac="Contact physical control (smothers eggs/nymphs)",
        dose_en="1–1.5 L per 100 L water",
        dose_ar="1–1.5 لتر لكل 100 لتر مية",
        application_en="Contact physical action — smothers whitefly eggs and young nymphs. Ensure complete leaf coverage. Do not apply in direct hot sunlight (above 32°C) to prevent foliage burn.",
        application_ar="تأثير بالملامسة — بيخنق بيض ويرقات الذبابة البيضا. لازم تغطية كاملة للورق. ما ترشّوش في الشمس الحامية (أعلى من 32 درجة مئوية) عشان ما يحرقش الورق.",
        phi_en="0 days (safe close to harvest)",
        phi_ar="0 يوم (آمن قرب الحصاد)",
        hazard_en="Low toxicity to humans. Can cause leaf scorch (phytotoxicity) under heat stress. Safe for beneficial insects once dry.",
        hazard_ar="سمية منخفضة للإنسان. ممكن يحرق الورق تحت الإجهاد الحراري. آمن للحشرات النافعة بعد ما يجف.",
        price_en="Cheap — roughly 50–90 EGP/L. Confirm locally.",
        price_ar="رخيص — حوالي 50–90 جنيه للتر. أكّد السعر محليًا.",
        note_en=note_en,
        note_ar=note_ar,
    )


def _yellow_sticky_traps(rank: int, note_en: str, note_ar: str) -> Treatment:
    return Treatment(
        rank=rank,
        name_en="Yellow Sticky Traps (Physical Monitoring/Control)",
        name_ar="المصايد اللاصقة الصفراء (رصد ومكافحة فيزيائية)",
        frac="Physical control barrier — NOT a chemical spray",
        dose_en="10–20 traps per feddan, hung just above crop canopy",
        dose_ar="10–20 مصيدة للفدان، تتعلق فوق قمة النباتات مباشرة",
        application_en="Hang traps near crop heads and entry points. Attracts and traps flying adult whiteflies, reducing population and monitoring pressure. Replace when covered with dust or insects.",
        application_ar="علّق المصايد قرب قمم النباتات ومداخل الصوبة. بتجذب وتصطاد الذبابة البيضا البالغة، وبتقلل تعدادها وبتساعد في الرصد. غيرها لما تتملى تراب أو حشرات.",
        phi_en="0 days (non-chemical, residue-free)",
        phi_ar="0 يوم (غير كيميائي، بدون متبقيات)",
        hazard_en="Non-toxic. Safe for consumers, environment, and water. Very sticky; avoid touching clothing or foliage.",
        hazard_ar="غير سام. آمن للمستهلك والبيئة والمية. لاصق جداً؛ تجنب ملامسته للملابس أو أوراق الشجر.",
        price_en="Cheap — roughly 10–20 EGP per trap. Confirm locally.",
        price_ar="رخيص — حوالي 10–20 جنيه للمصيدة. أكّد السعر محليًا.",
        note_en=note_en,
        note_ar=note_ar,
    )


def _chlorine_disinfectant(rank: int, note_en: str, note_ar: str) -> Treatment:
    return Treatment(
        rank=rank,
        name_en="10% Household Bleach / Chlorine solution",
        name_ar="محلول كلور تجاري 10% لتطهير الأدوات",
        frac="Sanitizer / Virucide (disinfectant)",
        dose_en="1 part household bleach (5.25% sodium hypochlorite) to 9 parts water",
        dose_ar="جزء كلور تجاري إلى 9 أجزاء مية",
        application_en="Dip pruning shears, tools, and hands between plants/rows to prevent mechanical transmission of the virus. Keep tools wet for at least 1 minute for full sanitization.",
        application_ar="اغمس مقصات التقليم والأدوات والإيدين بين النباتات/الخطوط لمنع الانتقال الميكانيكي للفيروس. سيب الأدوات مبللة دقيقة على الأقل للتطهير الكامل.",
        phi_en="0 days (applied to tools, not directly to plants)",
        phi_ar="0 يوم (بيترش/بيتحط على الأدوات مش النبات نفسه)",
        hazard_en="Corrosive to metals (rinse tools with clean water after use and oil them). Irritates skin/eyes; wear protective gloves.",
        hazard_ar="مسبب للتآكل للمعادن (اشطف الأدوات بمية نضيفة بعد الاستخدام وزيتها). بيهيج الجلد والعين؛ البس جوانتي.",
        price_en="Very cheap — standard household bleach. Confirm locally.",
        price_ar="رخيص جداً — كلور غسيل منزلي عادي. أكّد السعر محليًا.",
        note_en=note_en,
        note_ar=note_ar,
    )


def _skimmed_milk_dip(rank: int, note_en: str, note_ar: str) -> Treatment:
    return Treatment(
        rank=rank,
        name_en="Skimmed Milk powder solution (20%)",
        name_ar="محلول لبن فرز بودرة 20% لتطهير الأيدي والأدوات",
        frac="Physical virus inactivator (organic option)",
        dose_en="200 g skimmed milk powder per 1 L water",
        dose_ar="200 جم لبن بودرة فرز لكل 1 لتر مية",
        application_en="Dip hands and tools frequently while handling plants. The milk proteins coat and physically inactivate virus particles, preventing them from entering leaf wounds.",
        application_ar="اغمس الإيدين والأدوات باستمرار أثناء التعامل مع الزرع. بروتينات اللبن بتغلف جزيئات الفيروس وبتعطلها فيزيائياً، وتمنعها تدخل جروح الورق.",
        phi_en="0 days (safe, natural, non-chemical)",
        phi_ar="0 يوم (آمن، طبيعي، غير كيميائي)",
        hazard_en="Completely safe for humans, plants, and environment. Wash tools afterward to prevent sour odor.",
        hazard_ar="آمن تماماً للإنسان والنبات والبيئة. اغسل الأدوات بعد الشغل عشان ما تعملش ريحة وحشة.",
        price_en="Cheap. Confirm locally.",
        price_ar="رخيص. أكّد السعر محليًا.",
        note_en=note_en,
        note_ar=note_ar,
    )


# Additional disease programs for the multi-crop (PlantVillage) classes.
_TREATMENTS.update({
    # Tomato yellow leaf curl virus (TYLCV) — control the whitefly vector
    "tomato_yellow_leaf_curl_virus": [
        _yellow_sticky_traps(1, "Install yellow sticky traps early to capture flying whitefly adults and monitor population density.", "علّق مصايد صفراء لاصقة بدري لاصطياد الذباب الأبيض البالغ ومراقبة كثافته."),
        _acetamiprid(2, "Systemic insecticide to target whiteflies. Spray undersides of leaves where vectors gather; rotate groups.", "مبيد حشري جهازي لاستهداف الذباب الأبيض. رش ظهر الأوراق حيث تتجمع الحشرات، وبدل المجموعات."),
        _mineral_oil_vector(3, "Summer mineral oil or potassium soap kills whitefly eggs and nymphs by smothering. Do not spray in extreme heat.", "الزيت المعدني الصيفي أو الصابون البوتاسي بيخنق بيض ويرقات الذبابة. تجنب الرش في الحر الشديد."),
    ],
    # Tomato mosaic virus (ToMV) — focus on sanitation and contact transmission prevention
    "tomato_mosaic_virus": [
        _chlorine_disinfectant(1, "Dip pruning tools and shears in 10% bleach solution between plants to prevent touch spread.", "اغمس أدوات ومقصات التقليم في محلول كلور 10% بين النباتات لمنع انتقال العدوى باللمس."),
        _skimmed_milk_dip(2, "Dip hands and tools in 20% skimmed milk powder solution to physically coat and inactivate virus particles.", "اغمس الأيدي والأدوات في محلول لبن بودرة فرز 20% لتعطيل جزيئات الفيروس فيزيائياً."),
    ],
    # Bacterial spot (tomato & pepper) — bacteria, so fungicides do NOT cure it; copper is the backbone.
    "bacterial_spot": [
        _copper(1, "Copper is the main tool against bacterial spot — start early, spray every 5–7 days in wet weather; it limits spread but does not 'cure' bacteria.", "النحاس هو السلاح الأساسي ضد التبقّع البكتيري — ابدأ بدري ورشّ كل 5–7 أيام في الجو المبلّل؛ بيحدّ من الانتشار بس مش بيـ«شفي» البكتيريا."),
        _mancozeb(2, "Tank-mix mancozeb with the copper — the combination works better than copper alone on bacterial spot.", "اخلط المانكوزيب مع النحاس — الخلطة بتشتغل أحسن من النحاس لوحده على التبقّع البكتيري."),
    ],
    # Tomato leaf mold (greenhouse) — humidity-driven fungus
    "tomato_leaf_mold": [
        _chlorothalonil(1, "Protectant backbone for leaf mold; first lower the greenhouse humidity and improve venting.", "الوقائي الأساسي للعفن الورقي؛ الأول قلّل رطوبة الصوبة وحسّن التهوية."),
        _difenoconazole(2, "Systemic that also cures established leaf mold; rotate with the protectant.", "جهازي بيعالج العفن المستقر كمان، وبدّله مع الوقائي."),
        _mancozeb(3, "Cheap protectant cover spray in the rotation.", "وقائي رخيص في التبديل."),
        _copper(4, "Budget protectant option; weaker alone in a humid house.", "اختيار وقائي اقتصادي، أضعف لوحده في الصوبة الرطبة."),
    ],
    # Tomato target spot (Corynespora) — treat like early blight
    "tomato_target_spot": [
        _azoxy_difeno(1, "Strong on target spot's ringed lesions and protects new growth.", "قوي على بقع الـtarget spot الحلقية وبيحمي النموّ الجديد."),
        _difenoconazole(2, "Effective systemic; rotate with the strobilurin mix.", "جهازي فعّال، وبدّله مع خلطة الستروبيلورين."),
        _chlorothalonil(3, "Protectant cover spray every 7 days.", "وقائي كل 7 أيام."),
        _mancozeb(4, "Cheap routine protectant.", "وقائي رخيص للروتين."),
    ],
    # Tomato spider mites — a PEST, needs a miticide not a fungicide
    "tomato_spider_mites": [
        _abamectin(1, "First choice for spider mites — they are a pest, not a disease, so a miticide (not a fungicide) is what works.", "الاختيار الأول للعنكبوت — دي آفة مش مرض، فالأكاروسيد (مش المبيد الفطري) هو اللي بيشتغل."),
        _sulfur(2, "Wettable sulfur also knocks back mites and is cheap; not in high heat.", "الكبريت القابل للبلل بيقلّل العنكبوت كمان وهو رخيص؛ بس مش في الحر العالي."),
    ],
    # Corn (maize) foliar fungal diseases: common rust, Northern leaf blight, gray leaf spot
    "corn_foliar": [
        _azoxystrobin(1, "Strobilurin is the standard at early tasseling for rust/blight on corn; one well-timed spray often pays.", "الستروبيلورين هو الأساس عند بداية طرد النورة للصدأ/اللفحة في الذرة؛ رشّة واحدة في توقيتها بتفرق."),
        _propiconazole(2, "Triazole, good curative on rust; mix or rotate with the strobilurin.", "ترايازول كويس علاجيًا للصدأ؛ اخلطه أو بدّله مع الستروبيلورين."),
        _mancozeb(3, "Cheap protectant base if pressure is high.", "أساس وقائي رخيص لو الضغط عالي."),
    ],
    # Grape black rot / Isariopsis leaf blight (fungal)
    "grape_black_rot": [
        _mancozeb(1, "Protectant backbone from early shoots through fruit set for black rot and leaf blight.", "الوقائي الأساسي من بداية الأفرع لحد عقد الثمار للعفن الأسود وتبقّع الأوراق."),
        _triazole_pm(2, "Systemic (myclobutanil/tebuconazole) with curative action; rotate with the protectant.", "جهازي (ميكلوبيوتانيل/تيبوكونازول) بيعالج، وبدّله مع الوقائي."),
        _copper(3, "Cheap protectant option, also helps on leaf blight.", "اختيار وقائي رخيص وبيساعد على تبقّع الأوراق."),
    ],
})


# Diseases with NO chemical cure — we say so honestly and give cultural control.
# Bacteria and viruses are not cured by fungicides; some (Esca, HLB) have no cure.
_NO_CHEMICAL_CURE = {
    "panama_disease",
    "bunchy_top",
    "tomato_yellow_leaf_curl_virus",
    "tomato_mosaic_virus",
    "citrus_greening",
    "grape_esca",
}


def treatments_for(key: str) -> list[Treatment]:
    """Return the ranked treatment program for a disease key (empty if none)."""
    return _TREATMENTS.get(key, [])


def has_chemical_cure(key: str) -> bool:
    return key not in _NO_CHEMICAL_CURE and bool(_TREATMENTS.get(key))
