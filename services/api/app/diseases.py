"""Bilingual (English/Arabic) knowledge base for the banana-disease classifier.

The disease classifier (``banana_cordana_vgg19_int8.onnx``) predicts one of four
banana foliage conditions. The deterministic fallback instead reports
``healthy`` / ``possible_leaf_disease``. This module attaches reviewed, human
readable explanations to whatever label the runtime returns so the dashboard and
the assistant can explain each disease in both languages.

The agronomic text is intentionally educational, not prescriptive: it never gives
chemical dosages and always defers final treatment decisions to a local agronomist.
"""

from __future__ import annotations

from .schemas import DiseaseInfo
from .treatments import treatments_for


# Keyed by the raw label returned by ``DiseaseRuntime.predict``.
_DISEASES: dict[str, DiseaseInfo] = {
    "cordana_leaf_spot": DiseaseInfo(
        key="cordana_leaf_spot",
        name_en="Cordana leaf spot",
        name_ar="تبقّع كوردانا في الموز",
        summary_en=(
            "A fungal leaf disease of banana caused by Cordana musae. It is usually a "
            "minor, cosmetic disease but spreads faster in warm, humid, poorly drained fields."
        ),
        summary_ar=(
            "مرض فطري يصيب أوراق الموز ويسببه فطر Cordana musae. غالبًا ما يكون خفيفًا "
            "وذا أثر مظهري محدود، لكنه ينتشر أسرع في الأجواء الدافئة الرطبة وضعيفة الصرف."
        ),
        symptoms_en=[
            "Oval, eye-shaped spots with pale grey centres and dark brown margins.",
            "A yellow halo often surrounds each lesion, frequently starting at the leaf edge.",
            "Spots may merge and dry the leaf tip on older, lower leaves first.",
        ],
        symptoms_ar=[
            "بقع بيضاوية تشبه العين بمركز رمادي باهت وحواف بنية داكنة.",
            "هالة صفراء تحيط بالبقعة غالبًا وتبدأ كثيرًا من حافة الورقة.",
            "قد تتجمع البقع وتُجفّف طرف الورقة، وتظهر أولًا على الأوراق السفلية الأكبر سنًا.",
        ],
        management_en=[
            "Remove and destroy heavily spotted older leaves to reduce spore load.",
            "Improve drainage, spacing, and airflow to keep foliage dry.",
            "Apply a protectant fungicide only if spread is severe, after agronomist advice.",
        ],
        management_ar=[
            "أزل الأوراق السفلية شديدة الإصابة وأتلفها لتقليل مصدر الجراثيم الفطرية.",
            "حسّن الصرف والتباعد والتهوية للحفاظ على جفاف الأوراق.",
            "استخدم مبيدًا فطريًا وقائيًا عند اشتداد الانتشار فقط وبعد استشارة مختص.",
        ],
    ),
    "sigatoka_leaf_spot": DiseaseInfo(
        key="sigatoka_leaf_spot",
        name_en="Sigatoka leaf spot",
        name_ar="مرض سيجاتوكا (تبقّع أوراق الموز)",
        summary_en=(
            "A serious fungal complex (yellow/black Sigatoka, Mycosphaerella spp.) that "
            "destroys leaf area, reduces photosynthesis, and can cut banana yield sharply."
        ),
        summary_ar=(
            "مجموعة فطرية خطيرة (سيجاتوكا الصفراء/السوداء من جنس Mycosphaerella) تدمّر "
            "مساحة الورقة وتقلّل التمثيل الضوئي وقد تخفض إنتاج الموز بشدة."
        ),
        symptoms_en=[
            "Thin yellow-green streaks parallel to the veins that enlarge into spots.",
            "Mature spots have grey dead centres with yellow halos.",
            "Heavy infection turns large parts of the canopy brown and necrotic.",
        ],
        symptoms_ar=[
            "خطوط رفيعة صفراء-خضراء موازية للعروق تتسع لتصبح بقعًا.",
            "البقع الناضجة لها مركز رمادي ميت تحيط به هالة صفراء.",
            "الإصابة الشديدة تحوّل أجزاء كبيرة من المجموع الورقي إلى لون بني متنخّر.",
        ],
        management_en=[
            "Deleaf and destroy infected leaves regularly to break the disease cycle.",
            "Improve plant spacing and drainage to lower canopy humidity.",
            "Follow a planned, rotated fungicide programme and prefer resistant cultivars.",
        ],
        management_ar=[
            "أزل الأوراق المصابة وأتلفها بانتظام لكسر دورة المرض.",
            "حسّن تباعد النباتات والصرف لخفض الرطوبة داخل المجموع الورقي.",
            "اتبع برنامج مكافحة فطرية مدروسًا ومتناوبًا، وفضّل الأصناف المقاومة.",
        ],
    ),
    "panama_disease": DiseaseInfo(
        key="panama_disease",
        name_en="Panama disease (Fusarium wilt)",
        name_ar="مرض بنما (ذبول الفيوزاريوم)",
        summary_en=(
            "A devastating soil-borne fungal wilt caused by Fusarium oxysporum f.sp. cubense. "
            "It blocks the plant's water vessels, has no chemical cure, and survives in soil for years."
        ),
        summary_ar=(
            "ذبول فطري خطير ينتقل عبر التربة ويسببه فطر Fusarium oxysporum f.sp. cubense. "
            "يسدّ الأوعية الناقلة للماء في النبات، ولا يوجد له علاج كيميائي، ويبقى في التربة سنوات."
        ),
        symptoms_en=[
            "Older, lower leaves yellow first, then wilt and collapse around the pseudostem.",
            "Lengthwise splitting at the base of the pseudostem.",
            "Reddish-brown streaks in the inner vascular tissue when the stem is cut.",
        ],
        symptoms_ar=[
            "اصفرار الأوراق السفلية الأكبر سنًا أولًا، ثم ذبولها وتدلّيها حول الساق الكاذبة.",
            "تشقّق طولي في قاعدة الساق الكاذبة.",
            "خطوط بنية محمرّة في الأنسجة الوعائية الداخلية عند قطع الساق.",
        ],
        management_en=[
            "There is no cure: isolate and remove infected mats; do not move infested soil.",
            "Disinfect tools and footwear and use certified disease-free planting material.",
            "Plant resistant varieties and practise strict field quarantine.",
        ],
        management_ar=[
            "لا يوجد علاج: اعزل النباتات المصابة وأزلها، ولا تنقل التربة الملوّثة.",
            "طهّر الأدوات والأحذية واستخدم فسائل/شتلات معتمدة وخالية من المرض.",
            "ازرع أصنافًا مقاومة والتزم بحجر زراعي صارم في الحقل.",
        ],
    ),
    "bunchy_top": DiseaseInfo(
        key="bunchy_top",
        name_en="Banana bunchy top virus (BBTV)",
        name_ar="فيروس القمة المجعّدة في الموز (BBTV)",
        summary_en=(
            "A viral disease spread by the banana aphid. Infected plants become severely "
            "stunted and rarely produce fruit; there is no cure once a plant is infected."
        ),
        summary_ar=(
            "مرض فيروسي ينقله مَنّ الموز. تصاب النباتات بتقزّم شديد ونادرًا ما تثمر، "
            "ولا يوجد علاج بعد إصابة النبات."
        ),
        symptoms_en=[
            "Dark green dot-and-dash streaks along leaf veins and the petiole.",
            "New leaves emerge narrow, upright, and bunched in a rosette at the top.",
            "Marked stunting; the plant produces little or no marketable fruit.",
        ],
        symptoms_ar=[
            "خطوط خضراء داكنة على شكل نقاط وشرطات على عروق الأوراق وعنق الورقة.",
            "خروج الأوراق الجديدة ضيقة ومنتصبة ومتجمّعة كالوردة في قمة النبات.",
            "تقزّم واضح وإنتاج ضعيف أو معدوم من الثمار القابلة للتسويق.",
        ],
        management_en=[
            "Rogue (uproot and destroy) infected plants and the whole mat promptly.",
            "Control the banana aphid vector and avoid suckers from infected fields.",
            "Plant only virus-free, certified material in a cleaned area.",
        ],
        management_ar=[
            "اقتلع النباتات المصابة والجورة بأكملها وأتلفها فورًا.",
            "كافح حشرة المنّ الناقلة وتجنّب أخذ الفسائل من حقول مصابة.",
            "ازرع فقط مادة معتمدة خالية من الفيروس في منطقة منظّفة.",
        ],
    ),
    "possible_leaf_disease": DiseaseInfo(
        key="possible_leaf_disease",
        name_en="Possible leaf disorder (unconfirmed)",
        name_ar="اضطراب محتمل في الورقة (غير مؤكد)",
        summary_en=(
            "The demo color heuristic detected discoloration that may indicate disease, "
            "nutrient stress, or simple leaf aging. This is a screening signal, not a diagnosis."
        ),
        summary_ar=(
            "رصدت الأداة التجريبية تغيّرًا لونيًا قد يدل على مرض أو نقص عناصر أو مجرد "
            "شيخوخة طبيعية للورقة. هذه إشارة فرز أولي وليست تشخيصًا."
        ),
        symptoms_en=[
            "Brown or yellow patches on the leaf surface above the demo threshold.",
        ],
        symptoms_ar=[
            "بقع بنية أو صفراء على سطح الورقة تتجاوز عتبة الأداة التجريبية.",
        ],
        management_en=[
            "Retake clear photos from several angles in good light.",
            "Inspect the plant in person and compare with irrigation and weather records.",
            "Show the leaf to an agronomist before treating.",
        ],
        management_ar=[
            "أعد التقاط صور واضحة من عدة زوايا في إضاءة جيدة.",
            "افحص النبات ميدانيًا وقارن مع سجلات الري والطقس.",
            "اعرض الورقة على مهندس زراعي قبل أي علاج.",
        ],
    ),
    "healthy": DiseaseInfo(
        key="healthy",
        name_en="No disease signs detected",
        name_ar="لا توجد علامات مرض",
        summary_en=(
            "The analyzed foliage shows no clear disease pattern. Keep monitoring, as early "
            "symptoms can be missed by image screening alone."
        ),
        summary_ar=(
            "لا تُظهر الأوراق المحللة نمطًا مرضيًا واضحًا. تابع المراقبة، فقد تفوت الأعراض "
            "المبكرة على الفحص الصوري وحده."
        ),
        symptoms_en=["No characteristic lesions, streaks, or wilting were detected."],
        symptoms_ar=["لم تُرصد بقع أو خطوط أو ذبول مميزة للمرض."],
        management_en=[
            "Continue routine scouting, balanced irrigation, and field sanitation.",
            "Re-scan if you notice spots, yellowing, or stunting between visits.",
        ],
        management_ar=[
            "تابع الكشف الدوري والري المتوازن ونظافة الحقل.",
            "أعد الفحص إذا لاحظت بقعًا أو اصفرارًا أو تقزّمًا بين الزيارات.",
        ],
    ),
}


# --- Egyptian field/vegetable crops -----------------------------------------
# The image model cannot output these yet (it is banana-only). They power the
# assistant: when the farmer names the crop and symptoms, it grounds the disease
# explanation and the treatment program on these reviewed entries. Written in
# simple Egyptian Arabic.
_DISEASES.update({
    "septoria_leaf_spot_tomato": DiseaseInfo(
        key="septoria_leaf_spot_tomato",
        name_en="Septoria leaf spot (tomato)",
        name_ar="تبقّع السبتوريا في الطماطم",
        crop_en="Tomato",
        crop_ar="طماطم",
        summary_en=(
            "A very common fungal leaf disease of tomato (Septoria lycopersici). It does not "
            "rot the fruit directly, but it strips the leaves, so the plant weakens and the "
            "fruit gets sun-scald and stays small. It loves warm, wet, humid weather."
        ),
        summary_ar=(
            "مرض فطري منتشر جدًا في ورق الطماطم (سبتوريا). ما بيعفّنش الثمرة على طول، بس "
            "بيوقّع الورق فالنبات بيضعف والثمرة بتتحرق من الشمس وتفضل صغيرة. بيحب الجو الدافي "
            "المبلّل والرطوبة العالية."
        ),
        symptoms_en=[
            "Many small round spots with grey/tan centres and a dark brown edge — starts on the lowest, oldest leaves.",
            "Tiny black dots (the fungus bodies) in the centre of the spots.",
            "Heavily spotted leaves turn yellow, dry, and drop, working upward.",
        ],
        symptoms_ar=[
            "بقع صغيرة كتير دايرية، وسطها رمادي/بيج وحواليها حافة بنية غامقة — بتبدأ في الورق السفلي الكبير.",
            "نقط سودا صغيّرة جوّه البقع (دي أجسام الفطر).",
            "الورق المليان بقع بيصفرّ ويجف ويقع، ويطلع لفوق بالتدريج.",
        ],
        management_en=[
            "Remove and bin the lowest spotted leaves early — don't leave them on the soil.",
            "Water at the base (drip), keep leaves dry, and give the plants room for airflow.",
            "Mulch the soil and rotate away from tomato/potato for 2–3 seasons.",
            "Start a fungicide program at first spots (see the products below).",
        ],
        management_ar=[
            "شيل الورق السفلي المبقّع بدري وارميه بعيد — ما تسيبهوش على الأرض.",
            "اروي من تحت (بالتنقيط)، وخلّي الورق ناشف، وسيب مسافة بين النباتات للتهوية.",
            "غطّي الأرض بالتبن ولا تزرع طماطم/بطاطس في نفس الأرض 2–3 مواسم.",
            "ابدأ برنامج رش من أول البقع (شوف المنتجات تحت).",
        ],
    ),
    "tomato_early_blight": DiseaseInfo(
        key="tomato_early_blight",
        name_en="Early blight (tomato & potato)",
        name_ar="اللفحة المبكرة (الطماطم والبطاطس)",
        crop_en="Tomato / Potato",
        crop_ar="طماطم / بطاطس",
        summary_en=(
            "A fungal disease (Alternaria) that hits tomato and potato leaves, stems, and fruit. "
            "It shows up in warm weather and on stressed or older plants, and can defoliate the crop."
        ),
        summary_ar=(
            "مرض فطري (ألترناريا) بيضرب ورق وسيقان وثمار الطماطم والبطاطس. بيظهر في الجو الدافي "
            "وعلى النبات المتعب أو الكبير، وممكن يوقّع كل الورق."
        ),
        symptoms_en=[
            "Brown spots with clear rings inside, like a target / tree-rings, on lower leaves first.",
            "A yellow zone around the spots; badly hit leaves dry and fall.",
            "Dark sunken rings on the fruit near the stem end.",
        ],
        symptoms_ar=[
            "بقع بنية جوّاها دواير واضحة زي الهدف/قلب الشجرة، في الورق السفلي الأول.",
            "منطقة صفرا حوالين البقع، والورق المصاب بشدة بيجف ويقع.",
            "دواير غامقة غايرة على الثمرة عند ناحية العنق.",
        ],
        management_en=[
            "Remove the lowest infected leaves and keep the field clean of old debris.",
            "Avoid overhead watering; keep the canopy dry and well spaced.",
            "Rotate crops and feed balanced nutrition (weak plants get hit harder).",
            "Spray on a 7–10 day program in disease weather (see the products below).",
        ],
        management_ar=[
            "شيل الورق السفلي المصاب ونضّف الأرض من المخلّفات القديمة.",
            "ابعد عن الري بالرش من فوق، وخلّي الورق ناشف ومتباعد.",
            "دوّر المحصول وسمّد متوازن (النبات الضعيف بيتصاب أكتر).",
            "رشّ كل 7–10 أيام في جو المرض (شوف المنتجات تحت).",
        ],
    ),
    "tomato_late_blight": DiseaseInfo(
        key="tomato_late_blight",
        name_en="Late blight (tomato & potato)",
        name_ar="اللفحة المتأخرة (الطماطم والبطاطس)",
        crop_en="Tomato / Potato",
        crop_ar="طماطم / بطاطس",
        summary_en=(
            "A fast, very destructive water-mould disease (Phytophthora infestans) — the one that "
            "caused the Irish potato famine. In cool, wet, foggy weather it can destroy a whole "
            "field in days, so act early and preventively."
        ),
        summary_ar=(
            "مرض سريع ومدمّر جدًا من العفن المائي (فيتوفثورا) — هو اللي سبّب مجاعة البطاطس زمان. "
            "في الجو البارد المبلّل والضباب ممكن يخرّب الغيط كله في أيام، فاتحرّك بدري ووقائي."
        ),
        symptoms_en=[
            "Large greasy grey-green to brown blotches, often at the leaf tips/edges.",
            "A white fuzzy mould on the underside of the spot in humid mornings.",
            "Brown firm rot on green fruit; the whole plant can collapse fast.",
        ],
        symptoms_ar=[
            "بقع كبيرة لونها رمادي-أخضر لبني زي الدهن، غالبًا في أطراف وحواف الورق.",
            "زغب أبيض تحت البقعة الصبح في الجو الرطب.",
            "عفن بني صلب على الثمرة الخضرا، والنبات كله ممكن يقع بسرعة.",
        ],
        management_en=[
            "Act preventively — once you see it, you are already late. Watch the weather for cool wet spells.",
            "Destroy infected plants and never leave cull piles or volunteer potatoes.",
            "Keep leaves as dry as possible and improve drainage.",
            "Start a protectant + systemic spray program before/at first signs (see the products below).",
        ],
        management_ar=[
            "اشتغل وقائي — أول ما تشوفه تكون اتأخّرت. راقب الجو البارد المبلّل.",
            "اعدم النباتات المصابة وما تسيبش كوم مخلّفات ولا بطاطس نابتة لوحدها.",
            "خلّي الورق ناشف قد ما تقدر وحسّن الصرف.",
            "ابدأ برنامج رش وقائي + جهازي قبل/مع أول علامة (شوف المنتجات تحت).",
        ],
    ),
    "powdery_mildew": DiseaseInfo(
        key="powdery_mildew",
        name_en="Powdery mildew",
        name_ar="البياض الدقيقي",
        crop_en="Many crops (tomato, pepper, cucurbits, grape…)",
        crop_ar="محاصيل كتير (طماطم، فلفل، قرعيات، عنب…)",
        summary_en=(
            "A fungal disease that looks like white flour dusted on the leaves. Unlike most "
            "fungi it likes warm, dry days with humid nights, and it weakens the plant and "
            "lowers yield and fruit quality."
        ),
        summary_ar=(
            "مرض فطري شكله زي الدقيق الأبيض المرشوش على الورق. على عكس أغلب الفطريات بيحب "
            "النهار الدافي الناشف والليل الرطب، وبيضعّف النبات ويقلّل المحصول وجودة الثمار."
        ),
        symptoms_en=[
            "White-grey powdery patches on the upper side of the leaves, spreading to cover them.",
            "Leaves yellow, curl, and dry under the powder.",
            "Less and smaller fruit; sunburn on exposed fruit.",
        ],
        symptoms_ar=[
            "بقع بودرة بيضا-رمادي على وش الورق وبتنتشر لحد ما تغطّيه.",
            "الورق بيصفرّ ويتلوّي ويجف تحت البودرة.",
            "ثمار أقل وأصغر، وحروق شمس على الثمار المكشوفة.",
        ],
        management_en=[
            "Improve airflow (spacing, pruning) and avoid too much nitrogen.",
            "Start at the very first white spots — it is much easier to stop early.",
            "Sulfur is cheap and strong here; rotate with a systemic (see the products below).",
        ],
        management_ar=[
            "حسّن التهوية (مسافات وتقليم) وما تزوّدش الآزوت (النيتروجين).",
            "ابدأ من أول نقطة بيضا — وقفه بدري أسهل بكتير.",
            "الكبريت رخيص وقوي هنا، وبدّله مع مبيد جهازي (شوف المنتجات تحت).",
        ],
    ),
    "downy_mildew": DiseaseInfo(
        key="downy_mildew",
        name_en="Downy mildew",
        name_ar="البياض الزغبي",
        crop_en="Cucurbits, grape, onion, lettuce…",
        crop_ar="قرعيات، عنب، بصل، خس…",
        summary_en=(
            "A water-mould disease (like late blight) that thrives in cool, wet, humid weather. "
            "It is aggressive on cucurbits, grape, and onion and spreads fast after rain or heavy dew."
        ),
        summary_ar=(
            "مرض من العفن المائي (زي اللفحة المتأخرة) بيحب الجو البارد المبلّل والرطوبة العالية. "
            "شرس على القرعيات والعنب والبصل وبينتشر بسرعة بعد المطر أو الندى الكتير."
        ),
        symptoms_en=[
            "Yellow angular patches on the top of the leaf, boxed in by the veins.",
            "A grey-purple fuzzy growth on the underside right under those patches.",
            "Patches turn brown and the leaves die; fruit stays small.",
        ],
        symptoms_ar=[
            "بقع صفرا مزوّاية على وش الورقة محصورة بين العروق.",
            "نموّ زغبي رمادي-بنفسجي تحت الورقة تحت البقع دي بالظبط.",
            "البقع بتبقى بنية والورق بيموت، والثمرة بتفضل صغيرة.",
        ],
        management_en=[
            "Lower leaf wetness: drip irrigation, wider spacing, morning (not evening) watering.",
            "Remove infected leaves and improve drainage.",
            "Use rainfast protectant + a systemic for oomycetes (see the products below).",
        ],
        management_ar=[
            "قلّل بلل الورق: ري بالتنقيط، مسافات أوسع، ري الصبح مش بالليل.",
            "شيل الورق المصاب وحسّن الصرف.",
            "استخدم وقائي ثابت + مبيد جهازي للعفن المائي (شوف المنتجات تحت).",
        ],
    ),
})


# --- Extra classes the multi-crop (PlantVillage) image model can output --------
_DISEASES.update({
    "tomato_bacterial_spot": DiseaseInfo(
        key="tomato_bacterial_spot", name_en="Bacterial spot (tomato)", name_ar="التبقّع البكتيري (طماطم)",
        crop_en="Tomato", crop_ar="طماطم",
        summary_en="A bacterial disease (Xanthomonas) that spots leaves and fruit. Bacteria are NOT cured by fungicides — copper sprays + clean practices are the control.",
        summary_ar="مرض بكتيري (زانثوموناس) بيعمل بقع على الورق والثمار. البكتيريا ما بتتعالجش بالمبيدات الفطرية — النحاس والنظافة هم المكافحة.",
        symptoms_en=["Small dark, greasy, water-soaked spots on leaves with a yellow halo.", "Raised scabby spots on the fruit.", "Bad in warm, wet, splashing-rain weather."],
        symptoms_ar=["بقع صغيرة غامقة مبلّلة على الورق وحواليها هالة صفرا.", "بقع بارزة خشنة على الثمرة.", "بتزيد في الجو الدافي المبلّل والمطر الرشّاش."],
        management_en=["Use clean, certified seed/seedlings and rotate away from tomato/pepper.", "Avoid working plants when wet; water at the base.", "Start copper sprays early (see products below)."],
        management_ar=["استخدم بذرة/شتلة نضيفة معتمدة ودوّر بعيد عن الطماطم/الفلفل.", "ما تشتغلش في الزرع وهو مبلّل، واروي من تحت.", "ابدأ رش النحاس بدري (شوف المنتجات تحت)."],
    ),
    "pepper_bacterial_spot": DiseaseInfo(
        key="pepper_bacterial_spot", name_en="Bacterial spot (pepper)", name_ar="التبقّع البكتيري (فلفل)",
        crop_en="Pepper", crop_ar="فلفل",
        summary_en="The same Xanthomonas bacterial spot on pepper. Copper-based protection plus sanitation; fungicides do not cure bacteria.",
        summary_ar="نفس التبقّع البكتيري على الفلفل. الحماية بالنحاس مع النظافة؛ المبيدات الفطرية ما بتشفيش البكتيريا.",
        symptoms_en=["Dark water-soaked leaf spots that dry and tear, giving a 'shot-hole' look.", "Scabby raised spots on the fruit.", "Defoliation in wet seasons."],
        symptoms_ar=["بقع مبلّلة غامقة على الورق بتجف وتتقطّع وتدّي شكل «تقب».", "بقع بارزة خشنة على الثمرة.", "تساقط الورق في المواسم المبلّلة."],
        management_en=["Clean seed/seedlings and 2–3 year rotation.", "Keep foliage dry; don't handle wet plants.", "Copper program from early growth (see products below)."],
        management_ar=["بذرة/شتلة نضيفة ودورة 2–3 سنين.", "خلّي الورق ناشف وما تلمسش الزرع وهو مبلّل.", "برنامج نحاس من بدري (شوف المنتجات تحت)."],
    ),
    "tomato_leaf_mold": DiseaseInfo(
        key="tomato_leaf_mold", name_en="Leaf mold (tomato)", name_ar="العفن الورقي (طماطم)",
        crop_en="Tomato (greenhouse)", crop_ar="طماطم (صوبة)",
        summary_en="A fungus (Passalora fulva) that thrives in humid greenhouses. Lowering humidity is half the battle.",
        summary_ar="فطر بيحب الصوب الرطبة. تقليل الرطوبة نص الحل.",
        symptoms_en=["Pale green to yellow blotches on the UPPER leaf surface.", "Olive-green to brown velvety mold on the UNDERSIDE under those blotches.", "Leaves yellow, curl, and drop."],
        symptoms_ar=["بقع صفرا-خضرا على وش الورقة.", "عفن مخملي أخضر زيتوني لبني تحت الورقة تحت البقع.", "الورق بيصفرّ ويتلوّي ويقع."],
        management_en=["Vent and heat the greenhouse to cut humidity; widen spacing.", "Remove infected leaves; water early in the day.", "Spray a fungicide program (see products below)."],
        management_ar=["هوّي وسخّن الصوبة عشان تقلّل الرطوبة ووسّع المسافات.", "شيل الورق المصاب واروي الصبح بدري.", "رشّ برنامج مبيد فطري (شوف المنتجات تحت)."],
    ),
    "tomato_target_spot": DiseaseInfo(
        key="tomato_target_spot", name_en="Target spot (tomato)", name_ar="التبقّع الهدفي (طماطم)",
        crop_en="Tomato", crop_ar="طماطم",
        summary_en="A fungus (Corynespora) giving ringed 'target' lesions on leaves, stems and fruit; can defoliate quickly in humid weather.",
        summary_ar="فطر بيدّي بقع حلقية «زي الهدف» على الورق والساق والثمار؛ بيوقّع الورق بسرعة في الجو الرطب.",
        symptoms_en=["Brown spots with faint concentric rings (a target look).", "Spots also on stems and sunken spots on fruit.", "Heavy leaf drop in wet seasons."],
        symptoms_ar=["بقع بنية بدواير خفيفة جوّاها (شكل الهدف).", "بقع على الساق وبقع غايرة على الثمرة.", "تساقط ورق كتير في المواسم المبلّلة."],
        management_en=["Improve airflow, avoid overhead watering, remove crop debris.", "Rotate crops.", "Fungicide program at first spots (see products below)."],
        management_ar=["حسّن التهوية، وابعد عن الري من فوق، وشيل بقايا المحصول.", "دوّر المحصول.", "برنامج مبيد من أول البقع (شوف المنتجات تحت)."],
    ),
    "tomato_spider_mites": DiseaseInfo(
        key="tomato_spider_mites", name_en="Spider mites (tomato)", name_ar="العنكبوت الأحمر (طماطم)",
        crop_en="Tomato", crop_ar="طماطم",
        summary_en="NOT a disease — a tiny PEST (two-spotted spider mite) that sucks the leaves. It explodes in hot, dry, dusty weather. It needs a miticide, not a fungicide.",
        summary_ar="مش مرض — دي آفة صغيّرة (العنكبوت الأحمر) بتمصّ الورق. بتزيد في الجو الحار الناشف المتربّن. محتاجة أكاروسيد مش مبيد فطري.",
        symptoms_en=["Fine pale speckling/stippling on the leaves.", "Tiny webbing on the underside and around the tips.", "Leaves bronze, dry, and drop."],
        symptoms_ar=["نقط باهتة دقيقة على الورق.", "خيوط عنكبوت رفيعة تحت الورقة وعند الأطراف.", "الورق بيبرنز ويجف ويقع."],
        management_en=["Wash off dust, keep plants watered (stress makes it worse).", "Encourage natural predators; avoid broad insecticides that kill them.", "Use a miticide if it spreads (see products below)."],
        management_ar=["اغسل التراب وحافظ على ري الزرع (الإجهاد بيزوّدها).", "شجّع الأعداء الطبيعية وابعد عن المبيدات الواسعة اللي بتقتلها.", "استخدم أكاروسيد لو انتشر (شوف المنتجات تحت)."],
    ),
    "tomato_yellow_leaf_curl_virus": DiseaseInfo(
        key="tomato_yellow_leaf_curl_virus", name_en="Tomato yellow leaf curl virus (TYLCV)", name_ar="فيروس تجعّد واصفرار أوراق الطماطم (TYLCV)",
        crop_en="Tomato", crop_ar="طماطم",
        summary_en="A virus spread by the whitefly. There is NO chemical cure for the virus — you control the whitefly and remove infected plants.",
        summary_ar="فيروس بتنقله الذبابة البيضا. مفيش علاج كيميائي للفيروس — بتكافح الذبابة البيضا وتشيل الزرع المصاب.",
        symptoms_en=["New leaves small, curled up, and yellow at the edges.", "Plant stunted and bushy; flowers drop, little fruit.", "Whiteflies present under the leaves."],
        symptoms_ar=["الورق الجديد صغيّر ومتجعّد ومصفرّ من الحواف.", "النبات متقزّم وكثيف؛ الزهر بيقع والثمار قليلة.", "ذبابة بيضا تحت الورق."],
        management_en=["Use resistant varieties and clean seedlings; rogue infected plants early.", "Control whitefly (yellow sticky traps, insecticide rotation), use nets in the nursery.", "There is no spray that cures the virus itself."],
        management_ar=["استخدم أصناف مقاومة وشتلات نضيفة، وشيل الزرع المصاب بدري.", "كافح الذبابة البيضا (مصايد صفرا لاصقة، تبديل مبيدات) واستخدم شبك في المشتل.", "مفيش رشّة بتشفي الفيروس نفسه."],
    ),
    "tomato_mosaic_virus": DiseaseInfo(
        key="tomato_mosaic_virus", name_en="Tomato mosaic virus (ToMV)", name_ar="فيروس موزاييك الطماطم",
        crop_en="Tomato", crop_ar="طماطم",
        summary_en="A very contagious virus spread by touch/tools/hands. No chemical cure — strict hygiene and resistant seed are the control.",
        summary_ar="فيروس معدي جدًا بينتقل باللمس والأدوات والإيدين. مفيش علاج كيميائي — النظافة الصارمة والبذرة المقاومة هما المكافحة.",
        symptoms_en=["Light/dark green mosaic mottling on the leaves.", "Leaves narrow, wrinkled, fern-like; plant stunted.", "Uneven ripening / brown marks in the fruit."],
        symptoms_ar=["تبرقّش أخضر فاتح/غامق على الورق (موزاييك).", "ورق ضيّق ومكرمش زي السرخس؛ نبات متقزّم.", "نضج غير منتظم/علامات بنية في الثمرة."],
        management_en=["Use resistant/certified seed; wash hands and disinfect tools (milk or bleach solution).", "Don't smoke near plants (tobacco can carry it); remove infected plants.", "No spray cures the virus."],
        management_ar=["استخدم بذرة مقاومة/معتمدة؛ اغسل إيدك وطهّر الأدوات (لبن أو محلول كلور).", "ما تدخّنش جنب الزرع (الدخان ممكن ينقله)؛ شيل الزرع المصاب.", "مفيش رشّة بتشفي الفيروس."],
    ),
    "corn_gray_leaf_spot": DiseaseInfo(
        key="corn_gray_leaf_spot", name_en="Gray leaf spot (maize)", name_ar="التبقّع الرمادي (ذرة)",
        crop_en="Maize", crop_ar="ذرة",
        summary_en="A fungus that makes long grey rectangular lesions on corn leaves, robbing the plant of green area before grain fill.",
        summary_ar="فطر بيعمل بقع رمادية مستطيلة طويلة على ورق الذرة وبياخد من مساحة الورق قبل امتلاء الحبوب.",
        symptoms_en=["Long, narrow, grey-tan rectangular lesions running between the veins.", "Lesions merge and blight whole leaves.", "Worse in warm, humid, no-till fields."],
        symptoms_ar=["بقع مستطيلة طويلة رفيعة رمادية بين العروق.", "البقع بتتجمع وتلفح الورقة كلها.", "بتزيد في الحقول الدافية الرطبة قليلة الحرث."],
        management_en=["Rotate, plough in residue, and pick tolerant hybrids.", "Spray a fungicide around tasseling if pressure is high (see products below)."],
        management_ar=["دوّر المحصول، واقلب بقايا النبات، واختار هجن متحمّلة.", "رشّ مبيد حوالي طرد النورة لو الضغط عالي (شوف المنتجات تحت)."],
    ),
    "corn_common_rust": DiseaseInfo(
        key="corn_common_rust", name_en="Common rust (maize)", name_ar="الصدأ العادي (ذرة)",
        crop_en="Maize", crop_ar="ذرة",
        summary_en="A rust fungus making cinnamon-brown pustules on corn leaves; usually minor but heavy infection cuts yield.",
        summary_ar="فطر صدأ بيعمل بثرات بنية قرفية على ورق الذرة؛ غالبًا بسيط بس الإصابة الشديدة بتقلّل المحصول.",
        symptoms_en=["Small cinnamon-brown raised pustules on both leaf sides.", "Pustules turn dark as they age.", "Heavy rust yellows and dries the leaves."],
        symptoms_ar=["بثرات بنية قرفية صغيرة بارزة على وجهي الورقة.", "البثرات بتغمق مع الوقت.", "الصدأ الكتير بيصفّر ويجفّف الورق."],
        management_en=["Grow resistant hybrids; most crops don't need spraying.", "If severe early, a triazole/strobilurin helps (see products below)."],
        management_ar=["ازرع هجن مقاومة؛ أغلب المحاصيل ما بتحتاجش رش.", "لو شديد بدري، الترايازول/الستروبيلورين بيساعد (شوف المنتجات تحت)."],
    ),
    "corn_northern_leaf_blight": DiseaseInfo(
        key="corn_northern_leaf_blight", name_en="Northern leaf blight (maize)", name_ar="لفحة الأوراق الشمالية (ذرة)",
        crop_en="Maize", crop_ar="ذرة",
        summary_en="A fungus making long cigar-shaped grey-green lesions; can cause big yield loss if it hits before silking.",
        summary_ar="فطر بيعمل بقع طويلة شكلها زي السيجار رمادية-خضرا؛ ممكن يخسّر محصول كتير لو ضرب قبل ظهور الحرير.",
        symptoms_en=["Long (2–15 cm) cigar-shaped grey-green to tan lesions.", "Lesions merge and blight large leaf areas.", "Starts on lower leaves and moves up."],
        symptoms_ar=["بقع طويلة (2–15 سم) شكل السيجار رمادية-خضرا للبني.", "البقع بتتجمع وتلفح مساحات كبيرة.", "بتبدأ من الورق السفلي وتطلع لفوق."],
        management_en=["Resistant hybrids, rotation, and residue burial.", "Fungicide near tasseling under high pressure (see products below)."],
        management_ar=["هجن مقاومة ودورة وطمر البقايا.", "مبيد حوالي طرد النورة تحت الضغط العالي (شوف المنتجات تحت)."],
    ),
    "grape_black_rot": DiseaseInfo(
        key="grape_black_rot", name_en="Black rot (grape)", name_ar="العفن الأسود (عنب)",
        crop_en="Grape", crop_ar="عنب",
        summary_en="A fungus that rots the berries into hard black 'mummies' and spots the leaves; needs early protectant sprays.",
        summary_ar="فطر بيعفّن الحبّات لحد ما تبقى زي «المومياء» السودا الناشفة وبيبقّع الورق؛ محتاج رش وقائي بدري.",
        symptoms_en=["Tan leaf spots with a dark border and tiny black dots inside.", "Berries brown, shrivel, and harden into black mummies.", "Worst in warm, wet spring weather."],
        symptoms_ar=["بقع بيج على الورق بحافة غامقة ونقط سودا صغيرة جوّاها.", "الحبّات بتبقى بنية وتنكمش وتتحوّل لمومياء سودا.", "أسوأ في ربيع دافي مبلّل."],
        management_en=["Prune for airflow, remove mummies and infected canes in winter.", "Protectant + systemic sprays from early shoots to fruit set (see products below)."],
        management_ar=["قلّم للتهوية، وشيل المومياوات والأفرع المصابة في الشتا.", "رش وقائي + جهازي من بداية الأفرع لعقد الثمار (شوف المنتجات تحت)."],
    ),
    "grape_leaf_blight": DiseaseInfo(
        key="grape_leaf_blight", name_en="Isariopsis leaf blight (grape)", name_ar="تبقّع/لفحة أوراق العنب",
        crop_en="Grape", crop_ar="عنب",
        summary_en="A fungal leaf blight (Isariopsis/Pseudocercospora) that browns and drops grape leaves in warm, humid weather.",
        summary_ar="لفحة فطرية على ورق العنب بتبني وتوقّع الورق في الجو الدافي الرطب.",
        symptoms_en=["Irregular brown-to-black blotches, often starting at the leaf edge.", "A faint dark mold on the underside.", "Early defoliation weakens the vine."],
        symptoms_ar=["بقع بنية لسودا غير منتظمة، بتبدأ كتير من حافة الورقة.", "عفن غامق خفيف تحت الورقة.", "تساقط الورق بدري بيضعّف العنب."],
        management_en=["Improve airflow and drainage; remove fallen leaves.", "Protectant fungicide program (see products below)."],
        management_ar=["حسّن التهوية والصرف، وشيل الورق الواقع.", "برنامج مبيد وقائي (شوف المنتجات تحت)."],
    ),
    "grape_esca": DiseaseInfo(
        key="grape_esca", name_en="Esca / black measles (grape)", name_ar="إسكا / حصبة العنب السودا",
        crop_en="Grape", crop_ar="عنب",
        summary_en="A complex of wood-rotting fungi inside the vine's trunk. There is NO spray cure — it's managed by pruning and vineyard hygiene.",
        summary_ar="مجموعة فطريات بتعفّن خشب جذع العنب من جوّه. مفيش رشّة بتشفيه — بيتدار بالتقليم ونظافة الكرم.",
        symptoms_en=["'Tiger-stripe' yellow/brown bands between the leaf veins.", "Dark spots on the berries ('measles'); sudden vine collapse in summer.", "Dark streaks in the wood when a cane is cut."],
        symptoms_ar=["خطوط صفرا/بنية «زي النمر» بين عروق الورق.", "نقط غامقة على الحبّات؛ موت مفاجئ للعنب في الصيف.", "خطوط غامقة في الخشب لما تقطع الفرع."],
        management_en=["Prune in dry weather, seal big cuts, remove and burn dead wood/arms.", "Use clean planting material; no fungicide cures it."],
        management_ar=["قلّم في جو ناشف، اقفل الجروح الكبيرة، وشيل واحرق الخشب الميت.", "استخدم شتلات نضيفة؛ مفيش مبيد بيشفيه."],
    ),
    "citrus_greening": DiseaseInfo(
        key="citrus_greening", name_en="Citrus greening (HLB)", name_ar="تخضّر الموالح (الـHLB / التنين الأصفر)",
        crop_en="Citrus / Orange", crop_ar="موالح / برتقال",
        summary_en="A deadly bacterial disease spread by the citrus psyllid. There is NO cure — control the psyllid and remove infected trees.",
        summary_ar="مرض بكتيري قاتل بتنقله حشرة بسيلا الموالح. مفيش علاج — كافح البسيلا وشيل الأشجار المصابة.",
        symptoms_en=["Blotchy, asymmetric yellowing of the leaves.", "Small, lopsided, bitter fruit that stays green at the bottom.", "Twig dieback and slow tree decline."],
        symptoms_ar=["اصفرار غير منتظم ومبقّع على الورق.", "ثمار صغيرة معوجّة مرّة وبتفضل خضرا من تحت.", "موت الأفرع وتدهور الشجرة ببطء."],
        management_en=["Use certified disease-free trees; control the psyllid vector.", "Remove and destroy infected trees fast; no chemical cures the tree."],
        management_ar=["استخدم شتلات معتمدة خالية من المرض؛ كافح حشرة البسيلا.", "شيل وأعدم الأشجار المصابة بسرعة؛ مفيش كيماوي بيشفي الشجرة."],
    ),
    "other_crop_disease": DiseaseInfo(
        key="other_crop_disease", name_en="Disease outside this app's main crops", name_ar="مرض خارج محاصيل التطبيق الأساسية",
        crop_en="", crop_ar="",
        summary_en="The image model matched a disease on a crop this app does not focus on (e.g. apple, peach, strawberry). It cannot give you a reviewed treatment program for it.",
        summary_ar="الموديل طابق مرض على محصول التطبيق مش متخصّص فيه (زي التفاح أو الخوخ أو الفراولة). مش قادر يديك برنامج علاج موثّق ليه.",
        symptoms_en=["See the predicted disease name above for the likely condition."],
        symptoms_ar=["شوف اسم المرض المتوقع فوق للحالة المحتملة."],
        management_en=["Confirm the crop and disease with a local agronomist before treating."],
        management_ar=["أكّد المحصول والمرض مع مهندس زراعي قبل العلاج."],
    ),
})


# Map the raw 38 PlantVillage model labels onto our knowledge-base keys.
_LABEL_ALIASES: dict[str, str] = {
    "Apple___Apple_scab": "other_crop_disease",
    "Apple___Black_rot": "other_crop_disease",
    "Apple___Cedar_apple_rust": "other_crop_disease",
    "Cherry_(including_sour)___Powdery_mildew": "powdery_mildew",
    "Corn_(maize)___Cercospora_leaf_spot Gray_leaf_spot": "corn_gray_leaf_spot",
    "Corn_(maize)___Common_rust_": "corn_common_rust",
    "Corn_(maize)___Northern_Leaf_Blight": "corn_northern_leaf_blight",
    "Grape___Black_rot": "grape_black_rot",
    "Grape___Esca_(Black_Measles)": "grape_esca",
    "Grape___Leaf_blight_(Isariopsis_Leaf_Spot)": "grape_leaf_blight",
    "Orange___Haunglongbing_(Citrus_greening)": "citrus_greening",
    "Peach___Bacterial_spot": "other_crop_disease",
    "Pepper,_bell___Bacterial_spot": "pepper_bacterial_spot",
    "Potato___Early_blight": "tomato_early_blight",
    "Potato___Late_blight": "tomato_late_blight",
    "Squash___Powdery_mildew": "powdery_mildew",
    "Strawberry___Leaf_scorch": "other_crop_disease",
    "Tomato___Bacterial_spot": "tomato_bacterial_spot",
    "Tomato___Early_blight": "tomato_early_blight",
    "Tomato___Late_blight": "tomato_late_blight",
    "Tomato___Leaf_Mold": "tomato_leaf_mold",
    "Tomato___Septoria_leaf_spot": "septoria_leaf_spot_tomato",
    "Tomato___Spider_mites Two-spotted_spider_mite": "tomato_spider_mites",
    "Tomato___Target_Spot": "tomato_target_spot",
    "Tomato___Tomato_Yellow_Leaf_Curl_Virus": "tomato_yellow_leaf_curl_virus",
    "Tomato___Tomato_mosaic_virus": "tomato_mosaic_virus",
}

# Which treatment program (from treatments.py) backs each disease key.
_TREATMENT_KEY: dict[str, str] = {
    "tomato_bacterial_spot": "bacterial_spot",
    "pepper_bacterial_spot": "bacterial_spot",
    "corn_gray_leaf_spot": "corn_foliar",
    "corn_common_rust": "corn_foliar",
    "corn_northern_leaf_blight": "corn_foliar",
    "grape_leaf_blight": "grape_black_rot",
}

# UI crop value -> the model-label prefix, so we can condition predictions on the
# crop the farmer selected (a PlantVillage model is far more honest within one crop).
MODEL_CROP_PREFIX: dict[str, str] = {
    "tomato": "Tomato___",
}

BANANA_MODEL_LABELS = {"cordana_leaf_spot", "sigatoka_leaf_spot", "panama_disease", "bunchy_top"}


# Crop label per disease key (the banana set + the assistant crops).
_CROPS: dict[str, tuple[str, str]] = {
    "cordana_leaf_spot": ("Banana", "موز"),
    "sigatoka_leaf_spot": ("Banana", "موز"),
    "panama_disease": ("Banana", "موز"),
    "bunchy_top": ("Banana", "موز"),
}

# Attach crop labels and the ranked treatment program to every disease entry.
for _key, _info in _DISEASES.items():
    _info.treatments = treatments_for(_TREATMENT_KEY.get(_key, _key))
    if _key in _CROPS and not _info.crop_en:
        _info.crop_en, _info.crop_ar = _CROPS[_key]


_UNKNOWN = DiseaseInfo(
    key="unknown",
    name_en="Unrecognized condition",
    name_ar="حالة غير معروفة",
    summary_en="No reference information is available for this label.",
    summary_ar="لا تتوفر معلومات مرجعية لهذه الحالة.",
    symptoms_en=[],
    symptoms_ar=[],
    management_en=["Inspect the field in person and consult an agronomist."],
    management_ar=["افحص الحقل ميدانيًا واستشر مهندسًا زراعيًا."],
)


_HEALTHY = DiseaseInfo(
    key="healthy",
    name_en="No disease signs detected",
    name_ar="مفيش علامات مرض",
    summary_en="The model did not match a disease pattern — the leaf looks healthy. Keep watching, as very early symptoms can be missed by a photo.",
    summary_ar="الموديل ملقاش نمط مرض — الورقة شكلها سليمة. فضل متابع، لأن الأعراض المبكرة جدًا ممكن تفوت على الصورة.",
    symptoms_en=["No clear lesions, mold, or wilting were matched."],
    symptoms_ar=["مفيش بقع أو عفن أو ذبول واضح اتطابق."],
    management_en=["Keep up routine scouting, balanced feeding, and clean fields.", "Re-check if you see spots, yellowing, or wilting later."],
    management_ar=["كمّل كشف دوري وتسميد متوازن وأرض نضيفة.", "افحص تاني لو شفت بقع أو اصفرار أو ذبول بعدين."],
)


# Reverse lookup so the case (which stores only the English display name) can recover
# the full bilingual entry for scenario/Arabic text.
_NAME_EN_INDEX: dict[str, DiseaseInfo] = {info.name_en: info for info in _DISEASES.values()}


def disease_by_name_en(name_en: str) -> DiseaseInfo | None:
    """Find a disease entry from its English display name (or None)."""
    return _NAME_EN_INDEX.get(name_en)


def disease_info(label: str) -> DiseaseInfo:
    """Return reviewed bilingual reference text for a predicted disease label.

    Accepts raw PlantVillage model labels (e.g. ``Tomato___Septoria_leaf_spot``)
    and our internal keys; maps both onto the knowledge base.
    """
    if label in _LABEL_ALIASES:
        label = _LABEL_ALIASES[label]
    elif label == "healthy" or label.endswith("___healthy"):
        return _HEALTHY
    return _DISEASES.get(label, _UNKNOWN)


def labels_for_crop(crop: str | None, labels: list[str]) -> list[str]:
    """Restrict model labels to the two crops exposed by the local demo."""
    crop = (crop or "").strip().lower()
    generic = {"healthy", "possible_leaf_disease"}
    if crop == "banana":
        return [label for label in labels if label in BANANA_MODEL_LABELS | generic]
    if crop == "tomato":
        return [label for label in labels if label.startswith("Tomato___") or label in generic]
    return []


def all_disease_keys() -> list[str]:
    return list(_DISEASES)
