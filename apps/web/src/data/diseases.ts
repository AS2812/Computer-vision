// ─────────────────────────────────────────────────────────────────────────────
// Tomato disease knowledge base (10 PlantVillage tomato classes + healthy).
//
// Ported faithfully from the reviewed bilingual content in
// services/api/app/diseases.py and enriched for Phase 1 of the spec:
//   • a plain, memorable description,
//   • symptoms split into leaf / fruit / stem,
//   • cause type,
//   • lookalikes (linked by key to the confusable classes),
//   • a "today check" — what to look at by eye to confirm.
//
// HONESTY RULES baked in here:
//   • NO chemical product names or doses anywhere in this file. Treatment text is
//     category-level only ("a protectant fungicide programme", "a miticide").
//     Registered Egyptian label doses come ONLY from the rule-based gate (safety.ts)
//     after the chemical gate is unlocked — never from this file or the AI.
//   • Viruses are marked not curable; the host crop is user-selected, never
//     confirmed by the image model.
// ─────────────────────────────────────────────────────────────────────────────

export type Lang = "en" | "ar";

export interface Bi {
  en: string;
  ar: string;
}

export type CauseType = "fungal" | "oomycete" | "bacterial" | "viral" | "mite" | "none";

export interface TomatoDisease {
  /** Internal knowledge-base key (matches services/api/app/diseases.py keys). */
  key: string;
  /** Raw PlantVillage model label as emitted by the ONNX model. */
  rawLabel: string;
  /** Absolute index in the 38-class model output (frozen, guarded by a test). */
  modelIndex: number;
  name: Bi;
  /** Very short chip label. */
  short: Bi;
  cause: CauseType;
  /** A living pest, not a disease (changes the wording + needs a miticide). */
  isPest: boolean;
  /** False for viruses: there is no chemical cure for the pathogen itself. */
  curable: boolean;
  summary: Bi;
  symptomsLeaf: Bi[];
  symptomsFruit: Bi[];
  symptomsStem: Bi[];
  /** What to inspect on the plant by eye to confirm before treating. */
  todayCheck: Bi[];
  /** Keys of diseases this is routinely confused with (must exist in this set). */
  lookalikes: string[];
  /** Disease-specific nuance for Protect Now (generic steps live in protect.ts). */
  protectNote?: Bi;
  /** Category-level treatment note. NEVER a product or dose. */
  treatmentNote: Bi;
}

// Absolute tomato indices in the 38-class output, in model order (28..37).
// Cross-checked against ml/models/plant_disease_mobilenetv2.labels.json and
// services/api/app/calibration.py (Target Spot at index 34).
export const TOMATO_FIRST_INDEX = 28;

export const TOMATO_DISEASES: TomatoDisease[] = [
  {
    key: "tomato_bacterial_spot",
    rawLabel: "Tomato___Bacterial_spot",
    modelIndex: 28,
    name: { en: "Bacterial spot", ar: "التبقّع البكتيري" },
    short: { en: "Bacterial spot", ar: "تبقّع بكتيري" },
    cause: "bacterial",
    isPest: false,
    curable: true,
    summary: {
      en: "A bacterial disease (Xanthomonas) that spots both leaves and fruit. Important: bacteria are NOT cured by fungicides — copper-based protection plus clean practices are the control. It gets worse in warm, wet, splashing-rain weather.",
      ar: "مرض بكتيري (زانثوموناس) بيعمل بقع على الورق والثمار. مهم: البكتيريا ما بتتعالجش بالمبيدات الفطرية — الحماية بالنحاس مع النظافة هما المكافحة. بيزيد في الجو الدافي المبلّل والمطر الرشّاش.",
    },
    symptomsLeaf: [
      { en: "Small dark, greasy, water-soaked spots, often with a yellow halo.", ar: "بقع صغيرة غامقة مبلّلة زي الزيت، وحواليها هالة صفرا غالبًا." },
      { en: "Spots dry, tear, and can give leaves a ragged 'shot-hole' look.", ar: "البقع بتجف وتتقطّع وتدّي الورق شكل «التقب»." },
    ],
    symptomsFruit: [
      { en: "Raised, scabby, rough dark spots on the fruit skin.", ar: "بقع غامقة بارزة خشنة زي الجرب على قشرة الثمرة." },
    ],
    symptomsStem: [
      { en: "Dark, slightly raised streaks may appear on stems and leaf stalks.", ar: "خطوط غامقة بارزة شوية ممكن تظهر على الساق وأعناق الورق." },
    ],
    todayCheck: [
      { en: "Look for a yellow halo around fresh spots — bacterial spots often have one; many fungal spots do not.", ar: "دوّر على هالة صفرا حوالين البقع الطازة — التبقّع البكتيري غالبًا ليه هالة، وكتير من الفطريات لأ." },
      { en: "Check the fruit: scabby raised spots point to bacteria rather than a leaf-only fungus.", ar: "بُص على الثمرة: البقع البارزة الخشنة بتدل على بكتيريا مش فطر بيصيب الورق بس." },
    ],
    lookalikes: ["septoria_leaf_spot_tomato", "tomato_early_blight", "tomato_target_spot"],
    protectNote: {
      en: "Bacteria spread by splashing water and on hands/tools. Never work plants while wet, and use clean, certified seed/seedlings.",
      ar: "البكتيريا بتنتشر بالمياه الرشّاشة وعلى الإيدين والأدوات. ما تشتغلش في الزرع وهو مبلّل، واستخدم بذرة/شتلة نضيفة معتمدة.",
    },
    treatmentNote: {
      en: "Fungicides do NOT cure bacteria. Control is copper-based protection started early plus strict sanitation and rotation. Confirm the registered Egyptian copper product and dose with an agronomist before any spray.",
      ar: "المبيدات الفطرية ما بتشفيش البكتيريا. المكافحة حماية بالنحاس من بدري مع نظافة صارمة ودورة زراعية. أكّد المنتج النحاسي المسجّل في مصر وجرعته مع مهندس زراعي قبل أي رش.",
    },
  },
  {
    key: "tomato_early_blight",
    rawLabel: "Tomato___Early_blight",
    modelIndex: 29,
    name: { en: "Early blight", ar: "اللفحة المبكرة" },
    short: { en: "Early blight", ar: "لفحة مبكرة" },
    cause: "fungal",
    isPest: false,
    curable: true,
    summary: {
      en: "A fungal disease (Alternaria) that hits tomato leaves, stems, and fruit. It shows up in warm weather and on stressed or older plants, and can strip a plant of its lower leaves.",
      ar: "مرض فطري (ألترناريا) بيضرب ورق وسيقان وثمار الطماطم. بيظهر في الجو الدافي وعلى النبات المتعب أو الكبير، وممكن يوقّع الورق السفلي كله.",
    },
    symptomsLeaf: [
      { en: "Brown spots with clear rings inside, like a target or tree-rings — on the lowest, oldest leaves first.", ar: "بقع بنية جوّاها دواير واضحة زي الهدف أو قلب الشجرة — في الورق السفلي الكبير الأول." },
      { en: "A yellow zone around the spots; badly hit leaves dry and fall.", ar: "منطقة صفرا حوالين البقع، والورق المصاب بشدة بيجف ويقع." },
    ],
    symptomsFruit: [
      { en: "Dark, sunken, leathery rings on the fruit near the stem end.", ar: "دواير غامقة غايرة جلدية على الثمرة عند ناحية العنق." },
    ],
    symptomsStem: [
      { en: "Dark sunken lesions with concentric rings on the stem (collar rot on seedlings).", ar: "تقرّحات غامقة غايرة بدواير على الساق (تعفّن الطوق على الشتلات)." },
    ],
    todayCheck: [
      { en: "Confirm the disease started on the LOWEST leaves and is moving upward — that pattern fits early blight.", ar: "أكّد إن المرض بدأ من الورق السفلي وبيطلع لفوق — النمط ده بيخص اللفحة المبكرة." },
      { en: "Look closely for the bull's-eye rings inside each brown spot.", ar: "بُص كويس على دواير «عين الثور» جوّه كل بقعة بنية." },
    ],
    lookalikes: ["tomato_target_spot", "septoria_leaf_spot_tomato", "tomato_late_blight"],
    treatmentNote: {
      en: "Manageable with sanitation (remove lower infected leaves), dry foliage, rotation, balanced feeding, and — if pressure is high — a registered protectant fungicide programme. Confirm the Egyptian label dose with an agronomist first.",
      ar: "بيتدار بالنظافة (شيل الورق السفلي المصاب) وتجفيف الورق والدورة الزراعية والتسميد المتوازن، ولو الضغط عالي برنامج مبيد فطري وقائي مسجّل. أكّد الجرعة المصرية مع مهندس زراعي الأول.",
    },
  },
  {
    key: "tomato_late_blight",
    rawLabel: "Tomato___Late_blight",
    modelIndex: 30,
    name: { en: "Late blight", ar: "اللفحة المتأخرة" },
    short: { en: "Late blight", ar: "لفحة متأخرة" },
    cause: "oomycete",
    isPest: false,
    curable: true,
    summary: {
      en: "A fast, very destructive water-mould disease (Phytophthora infestans) — the one that caused the Irish potato famine. In cool, wet, foggy weather it can destroy a whole field in days, so act early and preventively.",
      ar: "مرض سريع ومدمّر جدًا من العفن المائي (فيتوفثورا) — هو اللي سبّب مجاعة البطاطس الأيرلندية زمان. في الجو البارد المبلّل والضباب ممكن يخرّب الغيط كله في أيام، فاتحرّك بدري ووقائي.",
    },
    symptomsLeaf: [
      { en: "Large greasy grey-green to brown blotches, often at the leaf tips and edges.", ar: "بقع كبيرة لونها رمادي-أخضر لبني زي الدهن، غالبًا في أطراف وحواف الورق." },
      { en: "A white fuzzy mould on the underside of the spot in humid mornings.", ar: "زغب أبيض تحت البقعة الصبح في الجو الرطب." },
    ],
    symptomsFruit: [
      { en: "Firm brown greasy rot on green fruit that spreads quickly.", ar: "عفن بني صلب دهني على الثمرة الخضرا بينتشر بسرعة." },
    ],
    symptomsStem: [
      { en: "Dark brown-black greasy lesions on stems and leaf stalks; the whole plant can collapse fast.", ar: "تقرّحات بني-أسود دهنية على الساق والأعناق، والنبات كله ممكن يقع بسرعة." },
    ],
    todayCheck: [
      { en: "In a humid morning, look under a fresh blotch for a faint white fuzzy mould — that is the late-blight signature.", ar: "في صباح رطب، بُص تحت البقعة الطازة على زغب أبيض خفيف — دي علامة اللفحة المتأخرة." },
      { en: "Check the weather: cool + wet + foggy spells make this an emergency — act preventively.", ar: "راقب الجو: البرد + البلل + الضباب بيخلّيها حالة طارئة — اتحرّك وقائي." },
    ],
    lookalikes: ["tomato_early_blight", "tomato_target_spot"],
    protectNote: {
      en: "This moves in days. Destroy infected plants immediately and never leave cull piles or volunteer potatoes nearby.",
      ar: "ده بيتحرّك في أيام. اعدم النباتات المصابة فورًا وما تسيبش كوم مخلّفات ولا بطاطس نابتة لوحدها جنبك.",
    },
    treatmentNote: {
      en: "Act before/at first signs with a registered protectant + systemic programme aimed at oomycetes, alongside destroying infected plants and improving drainage. Confirm the Egyptian label dose with an agronomist — timing is everything.",
      ar: "اتحرّك قبل/مع أول علامة ببرنامج وقائي + جهازي مسجّل موجّه للعفن المائي، مع إعدام النباتات المصابة وتحسين الصرف. أكّد الجرعة المصرية مع مهندس زراعي — التوقيت هو كل حاجة.",
    },
  },
  {
    key: "tomato_leaf_mold",
    rawLabel: "Tomato___Leaf_Mold",
    modelIndex: 31,
    name: { en: "Leaf mold", ar: "العفن الورقي" },
    short: { en: "Leaf mold", ar: "عفن ورقي" },
    cause: "fungal",
    isPest: false,
    curable: true,
    summary: {
      en: "A fungus (Passalora fulva) that thrives in humid greenhouses and tunnels. Lowering the humidity is half the battle — it rarely matters in dry open fields.",
      ar: "فطر بيحب الصوب والأنفاق الرطبة. تقليل الرطوبة نص الحل — نادرًا ما يكون مشكلة في الحقول المكشوفة الناشفة.",
    },
    symptomsLeaf: [
      { en: "Pale green to yellow blotches on the UPPER leaf surface.", ar: "بقع صفرا-خضرا باهتة على وش الورقة." },
      { en: "Olive-green to brown velvety mould on the UNDERSIDE right under those blotches.", ar: "عفن مخملي أخضر زيتوني لبني تحت الورقة تحت البقع بالظبط." },
      { en: "Leaves yellow, curl, dry, and drop.", ar: "الورق بيصفرّ ويتلوّي ويجف ويقع." },
    ],
    symptomsFruit: [
      { en: "Fruit is usually not spotted; loss comes from the plant losing its leaves.", ar: "الثمرة غالبًا ما بتتبقّعش؛ الخسارة بتيجي من فقدان النبات للورق." },
    ],
    symptomsStem: [
      { en: "Stems are usually clear; the mould stays on the foliage.", ar: "الساق غالبًا نضيفة؛ العفن بيفضل على الورق." },
    ],
    todayCheck: [
      { en: "Turn the leaf over: the velvety olive/brown mould on the underside under a yellow patch is the giveaway.", ar: "اقلب الورقة: العفن المخملي الزيتوني/البني تحتها تحت البقعة الصفرا هو الدليل." },
      { en: "Is it a greenhouse/tunnel with high humidity? That strongly supports leaf mold.", ar: "هل ده صوبة/نفق رطوبته عالية؟ ده بيدعم العفن الورقي بقوة." },
    ],
    lookalikes: ["tomato_late_blight", "tomato_target_spot"],
    protectNote: {
      en: "Humidity control IS the protection: vent and heat the greenhouse, widen spacing, and water early in the day so leaves dry fast.",
      ar: "التحكّم في الرطوبة هو الوقاية: هوّي وسخّن الصوبة، ووسّع المسافات، واروي الصبح بدري عشان الورق ينشف بسرعة.",
    },
    treatmentNote: {
      en: "First lower humidity and airflow; if it persists, a registered protectant fungicide programme helps. Confirm the Egyptian label dose with an agronomist first.",
      ar: "الأول قلّل الرطوبة وحسّن التهوية؛ لو استمر، برنامج مبيد فطري وقائي مسجّل بيساعد. أكّد الجرعة المصرية مع مهندس زراعي الأول.",
    },
  },
  {
    key: "septoria_leaf_spot_tomato",
    rawLabel: "Tomato___Septoria_leaf_spot",
    modelIndex: 32,
    name: { en: "Septoria leaf spot", ar: "تبقّع السبتوريا" },
    short: { en: "Septoria", ar: "سبتوريا" },
    cause: "fungal",
    isPest: false,
    curable: true,
    summary: {
      en: "A very common fungal leaf disease of tomato (Septoria lycopersici). It does not rot the fruit directly, but it strips the leaves, so the plant weakens and the fruit gets sun-scald and stays small. It loves warm, wet, humid weather.",
      ar: "مرض فطري منتشر جدًا في ورق الطماطم (سبتوريا). ما بيعفّنش الثمرة على طول، بس بيوقّع الورق فالنبات بيضعف والثمرة بتتحرق من الشمس وتفضل صغيرة. بيحب الجو الدافي المبلّل والرطوبة العالية.",
    },
    symptomsLeaf: [
      { en: "Many small round spots with grey/tan centres and a dark brown edge — starts on the lowest, oldest leaves.", ar: "بقع صغيرة كتير دايرية، وسطها رمادي/بيج وحواليها حافة بنية غامقة — بتبدأ في الورق السفلي الكبير." },
      { en: "Tiny black dots (the fungus bodies) in the centre of the spots.", ar: "نقط سودا صغيّرة جوّه البقع (دي أجسام الفطر)." },
      { en: "Heavily spotted leaves turn yellow, dry, and drop, working upward.", ar: "الورق المليان بقع بيصفرّ ويجف ويقع، ويطلع لفوق بالتدريج." },
    ],
    symptomsFruit: [
      { en: "Fruit is rarely spotted directly, but exposed fruit can sun-scald once the leaves are gone.", ar: "الثمرة نادرًا بتتبقّع مباشرة، بس الثمرة المكشوفة ممكن تتحرق من الشمس بعد ما الورق يقع." },
    ],
    symptomsStem: [
      { en: "Small spots can appear on stems and leaf stalks too.", ar: "بقع صغيرة ممكن تظهر على الساق والأعناق كمان." },
    ],
    todayCheck: [
      { en: "Use the tiny black dots in the centre of small round spots to separate Septoria from early blight (which has rings, not dots).", ar: "استخدم النقط السودا الصغيرة في وسط البقع الدايرية عشان تفرّق السبتوريا عن اللفحة المبكرة (اللي ليها دواير مش نقط)." },
      { en: "Confirm it started on the lowest leaves first.", ar: "أكّد إنها بدأت من الورق السفلي الأول." },
    ],
    lookalikes: ["tomato_early_blight", "tomato_target_spot", "tomato_bacterial_spot"],
    treatmentNote: {
      en: "Remove the lowest spotted leaves early, water at the base, mulch, and rotate away from tomato/potato for 2–3 seasons; start a registered protectant fungicide programme at first spots. Confirm the Egyptian label dose with an agronomist first.",
      ar: "شيل الورق السفلي المبقّع بدري، واروي من تحت، وغطّي الأرض بالتبن، ولا تزرع طماطم/بطاطس في نفس الأرض 2–3 مواسم؛ وابدأ برنامج مبيد فطري وقائي مسجّل من أول البقع. أكّد الجرعة المصرية مع مهندس زراعي الأول.",
    },
  },
  {
    key: "tomato_spider_mites",
    rawLabel: "Tomato___Spider_mites Two-spotted_spider_mite",
    modelIndex: 33,
    name: { en: "Spider mites (two-spotted)", ar: "العنكبوت الأحمر (ذو البقعتين)" },
    short: { en: "Spider mites", ar: "عنكبوت أحمر" },
    cause: "mite",
    isPest: true,
    curable: true,
    summary: {
      en: "This is NOT a disease — it is a tiny PEST (the two-spotted spider mite) that sucks the leaves. It explodes in hot, dry, dusty weather. It needs a miticide, not a fungicide, and broad insecticides often make it worse by killing its natural enemies.",
      ar: "دي مش مرض — دي آفة صغيّرة (العنكبوت الأحمر ذو البقعتين) بتمصّ الورق. بتزيد في الجو الحار الناشف المتربّن. محتاجة أكاروسيد مش مبيد فطري، والمبيدات الحشرية الواسعة كتير بتزوّدها لأنها بتقتل أعداءها الطبيعية.",
    },
    symptomsLeaf: [
      { en: "Fine pale speckling / stippling all over the leaf surface.", ar: "نقط باهتة دقيقة منتشرة على سطح الورق." },
      { en: "Tiny webbing on the underside and around the growing tips.", ar: "خيوط عنكبوت رفيعة تحت الورقة وحوالين الأطراف النامية." },
      { en: "Leaves go bronze, dry, and drop in bad infestations.", ar: "الورق بيبرنز ويجف ويقع في الإصابات الشديدة." },
    ],
    symptomsFruit: [
      { en: "Fruit is not spotted, but yield drops as the plant loses its leaves.", ar: "الثمرة ما بتتبقّعش، بس المحصول بيقلّ مع فقدان الورق." },
    ],
    symptomsStem: [
      { en: "Fine webbing may bridge between leaves and stems near the tips.", ar: "خيوط رفيعة ممكن توصل بين الورق والساق عند الأطراف." },
    ],
    todayCheck: [
      { en: "Tap a leaf over white paper — moving specks confirm live mites, not a disease.", ar: "خبّط ورقة فوق ورقة بيضا — لو لقيت نقط بتتحرّك يبقى دي حلم (عنكبوت) حيّة مش مرض." },
      { en: "Look for fine webbing under the leaf with a phone zoom or hand lens.", ar: "دوّر على خيوط رفيعة تحت الورقة بزووم الموبايل أو عدسة." },
    ],
    lookalikes: ["tomato_mosaic_virus"],
    protectNote: {
      en: "Wash dust off the foliage and keep plants well watered — drought stress makes mites explode. Protect natural predators; avoid broad insecticides.",
      ar: "اغسل التراب عن الورق وحافظ على ري الزرع كويس — العطش بيفجّر الحلم. احمِ الأعداء الطبيعية وابعد عن المبيدات الواسعة.",
    },
    treatmentNote: {
      en: "If it spreads, the correct tool is a registered miticide (acaricide), not a fungicide — and rotate chemistry to avoid resistance. Confirm the Egyptian label dose with an agronomist first.",
      ar: "لو انتشر، الأداة الصح أكاروسيد مسجّل مش مبيد فطري — وبدّل المجموعة الكيميائية عشان تتجنّب المقاومة. أكّد الجرعة المصرية مع مهندس زراعي الأول.",
    },
  },
  {
    key: "tomato_target_spot",
    rawLabel: "Tomato___Target_Spot",
    modelIndex: 34,
    name: { en: "Target spot", ar: "التبقّع الهدفي" },
    short: { en: "Target spot", ar: "تبقّع هدفي" },
    cause: "fungal",
    isPest: false,
    curable: true,
    summary: {
      en: "A fungus (Corynespora cassiicola) giving ringed 'target' lesions on leaves, stems, and fruit. It can defoliate quickly in humid weather, and it looks so much like early blight, bacterial spot, and Septoria that even the model splits its score across them.",
      ar: "فطر (كورينسبورا) بيدّي بقع حلقية «زي الهدف» على الورق والساق والثمار. بيوقّع الورق بسرعة في الجو الرطب، وبيشبه اللفحة المبكرة والتبقّع البكتيري والسبتوريا لدرجة إن الموديل نفسه بيوزّع ثقته عليهم.",
    },
    symptomsLeaf: [
      { en: "Brown spots with faint concentric rings (a target look), enlarging and merging.", ar: "بقع بنية بدواير خفيفة جوّاها (شكل الهدف)، بتكبر وتتجمّع." },
    ],
    symptomsFruit: [
      { en: "Sunken brown spots on the fruit, sometimes with rings.", ar: "بقع بنية غايرة على الثمرة، أحيانًا بدواير." },
    ],
    symptomsStem: [
      { en: "Elongated dark lesions on stems and leaf stalks.", ar: "تقرّحات غامقة مستطيلة على الساق والأعناق." },
    ],
    todayCheck: [
      { en: "Because target spot mimics early blight, Septoria, and bacterial spot, do not treat on the photo alone — confirm by eye and, ideally, with an agronomist.", ar: "علشان التبقّع الهدفي بيقلّد اللفحة المبكرة والسبتوريا والتبقّع البكتيري، ما تعالجش على الصورة لوحدها — أكّد بعينك ويُفضّل مع مهندس زراعي." },
      { en: "Look for spots on stems AND fruit together — target spot often hits all three.", ar: "دوّر على بقع على الساق والثمار مع بعض — التبقّع الهدفي غالبًا بيضرب التلاتة." },
    ],
    lookalikes: ["tomato_early_blight", "tomato_bacterial_spot", "septoria_leaf_spot_tomato"],
    treatmentNote: {
      en: "Improve airflow, avoid overhead watering, remove crop debris, and rotate; start a registered protectant fungicide programme at first spots. Because look-alikes share the same evidence, confirm the diagnosis and the Egyptian label dose with an agronomist first.",
      ar: "حسّن التهوية، وابعد عن الري من فوق، وشيل بقايا المحصول، ودوّر؛ وابدأ برنامج مبيد فطري وقائي مسجّل من أول البقع. وعلشان الأمراض الشبيهة بتشارك نفس الدليل، أكّد التشخيص والجرعة المصرية مع مهندس زراعي الأول.",
    },
  },
  {
    key: "tomato_yellow_leaf_curl_virus",
    rawLabel: "Tomato___Tomato_Yellow_Leaf_Curl_Virus",
    modelIndex: 35,
    name: { en: "Yellow leaf curl virus (TYLCV)", ar: "فيروس تجعّد واصفرار الأوراق (TYLCV)" },
    short: { en: "Yellow leaf curl", ar: "تجعّد واصفرار" },
    cause: "viral",
    isPest: false,
    curable: false,
    summary: {
      en: "A virus spread by the whitefly. There is NO chemical cure for the virus itself — you control the whitefly and remove infected plants. Resistant varieties and clean seedlings are the real defence.",
      ar: "فيروس بتنقله الذبابة البيضا. مفيش علاج كيميائي للفيروس نفسه — بتكافح الذبابة البيضا وتشيل الزرع المصاب. الأصناف المقاومة والشتلات النضيفة هما الدفاع الحقيقي.",
    },
    symptomsLeaf: [
      { en: "New leaves come out small, curled upward, and yellow at the edges.", ar: "الورق الجديد بيطلع صغيّر ومتجعّد لفوق ومصفرّ من الحواف." },
    ],
    symptomsFruit: [
      { en: "Flowers drop and few fruit set; the plant stays stunted and bushy.", ar: "الزهر بيقع والعقد قليل؛ النبات بيفضل متقزّم وكثيف." },
    ],
    symptomsStem: [
      { en: "Shortened internodes give a stunted, bushy plant; whiteflies cluster under leaves.", ar: "السلاميات قصيرة فالنبات متقزّم كثيف؛ والذبابة البيضا بتتجمّع تحت الورق." },
    ],
    todayCheck: [
      { en: "Shake a plant and watch for tiny white flies lifting off the underside — the vector.", ar: "هزّ النبات وبُص على ذباب أبيض صغيّر بيطير من تحت الورق — ده الناقل." },
      { en: "Upward leaf curl + yellow edges on the NEW growth points to the virus, not a fungus.", ar: "تجعّد الورق لفوق + اصفرار الحواف في النموّ الجديد بيدل على الفيروس مش فطر." },
    ],
    lookalikes: ["tomato_mosaic_virus"],
    protectNote: {
      en: "Rogue (remove) infected plants early, use whitefly sticky traps and nursery nets, and prefer resistant varieties — there is no spray that cures the virus.",
      ar: "شيل الزرع المصاب بدري، واستخدم مصايد صفرا للذبابة البيضا وشبك في المشتل، وفضّل الأصناف المقاومة — مفيش رشّة بتشفي الفيروس.",
    },
    treatmentNote: {
      en: "No chemical cures the virus. Management is whitefly control (traps, nets, rotated insecticides on the VECTOR), removing infected plants, and resistant seed. Confirm any insecticide and its Egyptian label dose with an agronomist.",
      ar: "مفيش كيماوي بيشفي الفيروس. الإدارة مكافحة الذبابة البيضا (مصايد، شبك، تبديل مبيدات على الناقل)، وشيل الزرع المصاب، وبذرة مقاومة. أكّد أي مبيد حشري وجرعته المصرية مع مهندس زراعي.",
    },
  },
  {
    key: "tomato_mosaic_virus",
    rawLabel: "Tomato___Tomato_mosaic_virus",
    modelIndex: 36,
    name: { en: "Mosaic virus (ToMV)", ar: "فيروس موزاييك الطماطم" },
    short: { en: "Mosaic virus", ar: "موزاييك" },
    cause: "viral",
    isPest: false,
    curable: false,
    summary: {
      en: "A very contagious virus spread by touch, tools, and hands. There is NO chemical cure — strict hygiene and resistant/certified seed are the control. Tobacco can carry it, so don't smoke near the plants.",
      ar: "فيروس معدي جدًا بينتقل باللمس والأدوات والإيدين. مفيش علاج كيميائي — النظافة الصارمة والبذرة المقاومة/المعتمدة هما المكافحة. الدخان ممكن ينقله، فما تدخّنش جنب الزرع.",
    },
    symptomsLeaf: [
      { en: "Light/dark green mosaic mottling on the leaves.", ar: "تبرقّش أخضر فاتح/غامق على الورق (موزاييك)." },
      { en: "Leaves narrow, wrinkled, and fern-like; the plant is stunted.", ar: "ورق ضيّق ومكرمش زي السرخس؛ نبات متقزّم." },
    ],
    symptomsFruit: [
      { en: "Uneven ripening and brown marks inside the fruit.", ar: "نضج غير منتظم وعلامات بنية جوّه الثمرة." },
    ],
    symptomsStem: [
      { en: "Overall stunting; no specific stem lesion.", ar: "تقزّم عام؛ مفيش تقرّح مميّز على الساق." },
    ],
    todayCheck: [
      { en: "The light/dark green mosaic mottle (not distinct round spots) on the leaf is the key sign.", ar: "التبرقّش الأخضر الفاتح/الغامق (مش بقع دايرية واضحة) على الورق هو العلامة المفتاح." },
      { en: "Did handling, tools, or tobacco contact the plants? That supports a contact-spread virus.", ar: "هل اللمس أو الأدوات أو الدخان وصل للزرع؟ ده بيدعم فيروس بينتقل باللمس." },
    ],
    lookalikes: ["tomato_yellow_leaf_curl_virus", "tomato_spider_mites"],
    protectNote: {
      en: "Wash hands and disinfect tools (milk or a bleach solution), remove infected plants, and use resistant/certified seed — no spray cures it.",
      ar: "اغسل إيدك وطهّر الأدوات (لبن أو محلول كلور)، وشيل الزرع المصاب، واستخدم بذرة مقاومة/معتمدة — مفيش رشّة بتشفيه.",
    },
    treatmentNote: {
      en: "No chemical cures the virus. Control is hygiene: disinfect hands/tools, remove infected plants, resistant/certified seed, and no tobacco near the crop.",
      ar: "مفيش كيماوي بيشفي الفيروس. المكافحة نظافة: تطهير الإيدين والأدوات، وشيل الزرع المصاب، وبذرة مقاومة/معتمدة، ومنع الدخان جنب الزرع.",
    },
  },
];

// Healthy is handled separately — it is the absence of a disease, not one of the
// ranked disease candidates the UI links to.
export const HEALTHY: TomatoDisease = {
  key: "healthy",
  rawLabel: "Tomato___healthy",
  modelIndex: 37,
  name: { en: "No disease signs detected", ar: "مفيش علامات مرض" },
  short: { en: "Healthy", ar: "سليمة" },
  cause: "none",
  isPest: false,
  curable: true,
  summary: {
    en: "The model did not match a disease pattern — the leaf looks healthy. Keep watching, because very early symptoms can be missed by a photo alone.",
    ar: "الموديل ملقاش نمط مرض — الورقة شكلها سليمة. فضل متابع، لأن الأعراض المبكرة جدًا ممكن تفوت على الصورة لوحدها.",
  },
  symptomsLeaf: [{ en: "No clear lesions, mould, streaks, or wilting were matched.", ar: "مفيش بقع أو عفن أو خطوط أو ذبول واضح اتطابق." }],
  symptomsFruit: [],
  symptomsStem: [],
  todayCheck: [
    { en: "Keep up routine scouting; re-check if you see spots, yellowing, or wilting later.", ar: "كمّل كشف دوري؛ وافحص تاني لو شفت بقع أو اصفرار أو ذبول بعدين." },
  ],
  lookalikes: [],
  treatmentNote: {
    en: "No treatment needed. Maintain balanced irrigation, field sanitation, and routine scouting.",
    ar: "مفيش علاج لازم. حافظ على ري متوازن ونظافة الحقل وكشف دوري.",
  },
};

const BY_KEY: Record<string, TomatoDisease> = Object.fromEntries(
  [...TOMATO_DISEASES, HEALTHY].map((d) => [d.key, d]),
);

/** Look up a disease (incl. healthy) by its internal key. */
export function diseaseByKey(key: string): TomatoDisease | undefined {
  return BY_KEY[key];
}

/** The display name in the active language, with a graceful fallback. */
export function diseaseName(key: string, lang: Lang): string {
  return BY_KEY[key]?.name[lang] ?? key;
}

/** The 10 disease classes (excluding healthy) ordered by model index. */
export const RANKED_DISEASES = TOMATO_DISEASES;
