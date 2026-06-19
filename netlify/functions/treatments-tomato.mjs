const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "content-type",
  "Access-Control-Allow-Methods": "GET, OPTIONS",
};

const APC_URL = "https://www1.apc.gov.eg/en/search.aspx";
const TODAY = new Date().toISOString().slice(0, 10);

function json(statusCode, body) {
  return {
    statusCode,
    headers: { ...CORS, "Content-Type": "application/json" },
    body: JSON.stringify(body),
  };
}

function source(source, title, url, price = "") {
  return {
    source,
    title,
    url,
    price_text: price,
    availability_en: "check stock",
    availability_ar: "أكد التوفر",
    checked_at: TODAY,
    live: true,
    note_en: "Online Egyptian retail/dealer page. Verify APC registration, exact formulation, pack size, current stock, and label before buying.",
    note_ar: "صفحة بيع/مورد أونلاين داخل مصر. أكد التسجيل في لجنة المبيدات والتركيبة والعبوة والتوفر واللافتة قبل الشراء.",
  };
}

function product(rank, name_en, name_ar, frac, dose_en, dose_ar, application_en, application_ar, phi_en, phi_ar, hazard_en, hazard_ar, price_en, price_ar, note_en, note_ar, price_sources = []) {
  return {
    rank,
    name_en,
    name_ar,
    frac,
    dose_en,
    dose_ar,
    application_en,
    application_ar,
    phi_en,
    phi_ar,
    hazard_en,
    hazard_ar,
    price_en,
    price_ar,
    price_sources,
    note_en,
    note_ar,
  };
}

export const prevention = {
  en: [
    "Confirm the diagnosis before any chemical spray.",
    "Scout twice weekly, especially lower leaves and leaf undersides.",
    "Remove heavily infected leaves and dispose of them away from the crop.",
    "Keep foliage dry with drip irrigation, morning irrigation, spacing, pruning, and ventilation.",
    "Verify APC registration for tomato and the exact pest/disease before buying any pesticide.",
    "Rotate FRAC/IRAC groups and do not repeat one systemic group back-to-back.",
  ],
  ar: [
    "أكد التشخيص قبل أي رش كيماوي.",
    "اكشف مرتين أسبوعيًا، خصوصًا الورق السفلي وظهر الورقة.",
    "شيل الأوراق المصابة بشدة وتخلص منها بعيد عن الزراعة.",
    "خلي الورق ناشف: ري تنقيط، ري الصبح، مسافات، تقليم، وتهوية.",
    "أكد تسجيل لجنة المبيدات للطماطم والآفة/المرض بالضبط قبل شراء أي مبيد.",
    "بدل مجموعات FRAC/IRAC وما تكررش نفس المجموعة الجهازية ورا بعض.",
  ],
};

export const catalogs = {
  tomato_spider_mites: {
    disease_name_en: "Spider mites (tomato)",
    disease_name_ar: "العنكبوت الأحمر (طماطم)",
    treatments: [
      product(
        1,
        "Acaricide/miticide registered for tomato spider mites",
        "أكاروسيد/مبيد حلم مسجل للعنكبوت الأحمر على الطماطم",
        "IRAC: rotate",
        "Use only the registered Egyptian label dose after confirmation.",
        "استخدم فقط الجرعة المسجلة على اللافتة المصرية بعد التأكيد.",
        "Spray only after confirming live mites/webbing; cover leaf undersides and rotate mode of action.",
        "ارشه فقط بعد تأكيد وجود حلم حي/خيوط؛ غطّي ظهر الورقة وبدل مجموعة التأثير.",
        "Follow product label",
        "حسب لافتة المنتج",
        "Can harm beneficial mites/insects; resistance risk is high if repeated.",
        "قد يضر الأعداء الحيوية؛ خطر المقاومة عالي مع التكرار.",
        "Confirm locally; prices vary by active ingredient and pack size.",
        "أكد محليًا؛ السعر يختلف حسب المادة الفعالة والعبوة.",
        "Spider mites need an acaricide, not a fungicide. Do not spray while diagnosis is low confidence.",
        "العنكبوت الأحمر يحتاج أكاروسيد مش مبيد فطري. لا ترش والثقة منخفضة.",
        [
          source("APC", "Egypt pesticide registration search", APC_URL),
          source("AgriMisr", "Mectiam 1.8% acaricide 100 cc / 250 cc and Kani Mite 15% 500 ml listings", "https://agrimisr.com/index.php?category_id=831&dispatch=categories.view&items_per_page=24&layout=products_without_options&sort_by=popularity&sort_order=asc", "120 EGP / 100 cc; 270 EGP / 250 cc; 3700 EGP / 500 ml listed online"),
          source("Shoura Online", "Biomectin 120 cm acaricide", "https://shouraonline.com/product/Biomectin_120CM", "220 EGP listed online; page marked out of stock"),
          source("Mobidat Star", "Stra Mactin acaricide 100 ml", "https://mobidatstar.store/product/%D8%B3%D8%AA%D8%B1%D8%A7-%D9%85%D8%A7%D9%83%D8%AA%D9%8A%D9%86-100%D9%85%D9%84%D9%84/", "85 EGP sale price listed online"),
          source("Local dealer", "Ask for registered tomato spider-mite acaricide", APC_URL, "Verify exact current local price and stock"),
        ],
      ),
    ],
  },
  tomato_late_blight: {
    disease_name_en: "Late blight (tomato)",
    disease_name_ar: "اللفحة المتأخرة (طماطم)",
    treatments: [
      product(1, "Metalaxyl-M + mancozeb family", "عائلة ميتالاكسيل-م + مانكوزيب", "FRAC 4 + M03", "Label dose only", "جرعة اللافتة فقط", "Preventive/early use after agronomist confirmation; rotate.", "وقائي/بداية الإصابة بعد تأكيد مهندس؛ مع التبديل.", "Follow label", "حسب اللافتة", "Resistance and residue risk if overused.", "خطر مقاومة ومتبقيات مع سوء الاستخدام.", "Online pages often list Ridomil-family packs; confirm current stock.", "توجد صفحات أونلاين لعائلة ريدوميل؛ أكد التوفر.", "Useful only when registered for tomato late blight and used correctly.", "ينفع فقط لو مسجل للطماطم واللفحة المتأخرة وباستخدام صحيح.", [source("AgriCash", "Ridomil Gold MZ 68% WG 400 g", "https://kz.agricash.app/shop/ridomil-gold/"), source("Cowboyzz Egypt", "RidomilGold MZ 68%", "https://cowboyzz.com/products/ridomilgold-mz-68-%D8%B1%D9%8A%D8%AF%D9%88%D9%85%D9%8A%D9%84-%D8%AC%D9%88%D9%84%D8%AF-68-%D8%A7%D9%85-%D8%B0%D8%AF")]),
      product(2, "Mandipropamid-family product", "عائلة مانديبروباميد", "FRAC 40", "Label dose only", "جرعة اللافتة فقط", "Use in rotation under confirmed oomycete pressure.", "يستخدم بالتبادل عند تأكيد ضغط العفن المائي.", "Follow label", "حسب اللافتة", "Do not repeat one group back-to-back.", "لا تكرر نفس المجموعة ورا بعض.", "Confirm current dealer price.", "أكد سعر التاجر الحالي.", "Rotation option; verify formulation and APC registration.", "خيار للتبديل؛ أكد التركيبة والتسجيل.", [source("ERADCO", "Revus Top 500 SC", "https://eradco.online/ar/%D8%B1%D9%8A%D9%81%D9%88%D8%B3-%D8%AA%D9%88%D8%A8-500-%D8%A5%D8%B3-%D8%B3%D9%8A---syngenta---%D8%A5%D9%8A%D8%B1%D8%A7%D8%AF%D9%83%D9%88/p1170295695")]),
    ],
  },
  tomato_early_blight: {
    disease_name_en: "Early blight (tomato)",
    disease_name_ar: "اللفحة المبكرة (طماطم)",
    treatments: [
      product(1, "Mancozeb-family protectant", "عائلة مانكوزيب الوقائية", "FRAC M03", "Label dose only", "جرعة اللافتة فقط", "Protectant program after confirmation; cover lower leaves.", "برنامج وقائي بعد التأكيد؛ غطّي الورق السفلي.", "Follow label", "حسب اللافتة", "Protective only; repeat misuse increases residue risk.", "وقائي؛ سوء التكرار يزود خطر المتبقيات.", "Confirm online/dealer price.", "أكد السعر أونلاين/محليًا.", "Good low-resistance protectant option when registered.", "خيار وقائي جيد قليل المقاومة عند التسجيل.", [source("AgroKima", "Hi-Manco 80% mancozeb 750 g", "https://agrokima.com/ar/products/hi-manco-750g"), source("AgriMisr", "Mancozeb-family fungicide listings", "https://agrimisr.com/")]),
      product(2, "Difenoconazole-family product", "عائلة ديفينوكونازول", "FRAC 3", "Label dose only", "جرعة اللافتة فقط", "Use only after confirmation and rotate with protectants.", "استخدمه فقط بعد التأكيد وبدله مع الوقائيات.", "Follow label", "حسب اللافتة", "Resistance risk if repeated.", "خطر مقاومة مع التكرار.", "Confirm current price.", "أكد السعر الحالي.", "Systemic option; do not use alone repeatedly.", "خيار جهازي؛ لا يستخدم وحده بتكرار.", [source("AgriMisr", "Difenoconazole-family listings", "https://agrimisr.com/")]),
    ],
  },
  septoria_leaf_spot_tomato: {
    disease_name_en: "Septoria leaf spot (tomato)",
    disease_name_ar: "تبقّع السبتوريا (طماطم)",
    treatments: [
      product(1, "Chlorothalonil-family protectant", "عائلة كلوروثالونيل الوقائية", "FRAC M05", "Label dose only", "جرعة اللافتة فقط", "Protectant after confirmation; improve sanitation and airflow.", "وقائي بعد التأكيد؛ حسن النظافة والتهوية.", "Follow label", "حسب اللافتة", "Residue/PHI risk if label ignored.", "خطر متبقيات لو اللافتة اتكسرت.", "Confirm current dealer price.", "أكد سعر التاجر الحالي.", "Protectant option for confirmed leaf-spot pressure.", "خيار وقائي عند تأكيد ضغط تبقعات الورق.", [source("AgriMisr", "Chlorothalonil-family listings", "https://agrimisr.com/")]),
      product(2, "Mancozeb-family protectant", "عائلة مانكوزيب الوقائية", "FRAC M03", "Label dose only", "جرعة اللافتة فقط", "Rotate with other registered protectants.", "بدله مع وقائيات مسجلة أخرى.", "Follow label", "حسب اللافتة", "Do not overuse.", "لا تفرط في الاستخدام.", "Confirm online/dealer price.", "أكد السعر أونلاين/محليًا.", "Useful as part of a protectant rotation.", "مفيد ضمن برنامج تبديل وقائي.", [source("AgroKima", "Hi-Manco 80% mancozeb 750 g", "https://agrokima.com/ar/products/hi-manco-750g")]),
    ],
  },
  tomato_target_spot: {
    disease_name_en: "Target spot (tomato)",
    disease_name_ar: "التبقّع الهدفي (طماطم)",
    treatments: [
      product(1, "Azoxystrobin-family product", "عائلة أزوكسيستروبين", "FRAC 11", "Label dose only", "جرعة اللافتة فقط", "Use only after confirmation and rotate with protectants.", "استخدمه فقط بعد التأكيد وبدله مع الوقائيات.", "Follow label", "حسب اللافتة", "High resistance risk if repeated.", "خطر مقاومة عالي مع التكرار.", "Confirm current market price.", "أكد السعر الحالي.", "Use only when registered for tomato target spot.", "يستخدم فقط عند التسجيل للطماطم والتبقع الهدفي.", [source("AgriMisr", "Azoxystrobin-family listings", "https://agrimisr.com/")]),
    ],
  },
  tomato_bacterial_spot: {
    disease_name_en: "Bacterial spot (tomato)",
    disease_name_ar: "التبقّع البكتيري (طماطم)",
    treatments: [
      product(1, "Copper-family protectant", "عائلة النحاس الوقائية", "FRAC/BM M01", "Label dose only", "جرعة اللافتة فقط", "Protective use only after confirmation; avoid working wet plants.", "استخدام وقائي فقط بعد التأكيد؛ تجنب العمل والنبات مبتل.", "Follow label", "حسب اللافتة", "Phytotoxicity/residue risk if label ignored.", "خطر سمية نباتية/متبقيات عند مخالفة اللافتة.", "Confirm current price and registration.", "أكد السعر والتسجيل الحالي.", "Fungicides do not cure bacteria; copper is protective only.", "الفطريات لا تعالج البكتيريا؛ النحاس وقائي فقط.", [source("AgriMisr", "Copper fungicide listings", "https://agrimisr.com/")]),
    ],
  },
  tomato_leaf_mold: {
    disease_name_en: "Leaf mold (tomato)",
    disease_name_ar: "العفن الورقي (طماطم)",
    treatments: [
      product(1, "Registered protectant fungicide program", "برنامج مبيد فطري وقائي مسجل", "Rotate", "Label dose only", "جرعة اللافتة فقط", "First lower humidity and improve greenhouse ventilation.", "الأول قلل الرطوبة وحسن تهوية الصوبة.", "Follow label", "حسب اللافتة", "Chemicals fail if humidity stays high.", "الكيماوي ضعيف لو الرطوبة فضلت عالية.", "Confirm locally.", "أكد محليًا.", "Humidity control is the main treatment.", "تقليل الرطوبة هو العلاج الأساسي.", [source("APC", "Egypt pesticide registration search", APC_URL)]),
    ],
  },
};

for (const key of ["tomato_yellow_leaf_curl_virus", "tomato_mosaic_virus", "healthy"]) {
  catalogs[key] = {
    disease_name_en: key === "healthy" ? "Healthy tomato" : "Tomato virus condition",
    disease_name_ar: key === "healthy" ? "طماطم سليمة" : "حالة فيروسية في الطماطم",
    treatments: [],
  };
}

catalogs.tomato_mosaic_virus = {
  disease_name_en: "Tomato mosaic virus",
  disease_name_ar: "فيروس موزاييك الطماطم",
  treatments: [
    product(
      1,
      "Sanitation and infected-plant removal",
      "نظافة وإزالة النبات المصاب",
      "Non-chemical",
      "No pesticide dose; remove infected material and disinfect tools.",
      "لا توجد جرعة مبيد؛ أزل الأجزاء/النباتات المصابة وطهر الأدوات.",
      "Mark suspect plants, remove badly infected plants, bag residues, and work from clean plants to infected plants.",
      "علّم النباتات المشتبه بها، أزل الشديد منها، اجمع المخلفات في كيس، واشتغل من النظيف للمصاب.",
      "Not applicable",
      "غير منطبق",
      "Main risk is spreading virus mechanically by hands, tools, or tobacco contact.",
      "الخطر الأساسي هو نقل الفيروس ميكانيكيًا باليد أو الأدوات أو ملامسة الدخان/التبغ.",
      "No pesticide purchase; budget for labor, bags, and disinfectant. Confirm local prices.",
      "لا يوجد شراء مبيد؛ احسب تكلفة العمالة والأكياس والمطهر وأكد السعر محليًا.",
      "There is no curative pesticide for tomato mosaic virus.",
      "لا يوجد مبيد يشفي فيروس موزاييك الطماطم.",
      [
        source("ARC", "Plant disease diagnosis and hygiene confirmation", "https://www.arc.sci.eg/", "No chemical treatment price; management cost is labor/local materials"),
        source("APC", "Do not buy pesticide unless registration matches crop and pest", APC_URL, "No virus-curing pesticide purchase recommended"),
      ],
    ),
    product(
      2,
      "Clean seedlings, resistant seed, and prevention for next planting",
      "شتلات نظيفة وبذور/أصناف مقاومة للموسم القادم",
      "Prevention",
      "Use supplier label and agronomist advice; no pesticide dose.",
      "اتبع بيانات المورد ونصيحة المهندس؛ لا توجد جرعة مبيد.",
      "Use certified clean transplants, avoid saving seed from infected plants, remove weeds/volunteer tomatoes, and keep tobacco away from workers and crop.",
      "استخدم شتلات نظيفة موثوقة، لا تحفظ بذرة من نباتات مصابة، أزل الحشائش والطماطم المتطوعة، وابعد التبغ عن العمال والزرع.",
      "Not applicable",
      "غير منطبق",
      "Buying weak or infected seedlings can restart the disease before symptoms appear.",
      "شراء شتلات ضعيفة أو مصابة قد يعيد المرض قبل ظهور الأعراض.",
      "Seedling/seed prices vary by nursery and cultivar; verify locally.",
      "أسعار الشتلات/البذور تختلف حسب المشتل والصنف؛ أكدها محليًا.",
      "This is the highest-value prevention step for virus problems.",
      "هذه أهم خطوة وقائية في مشاكل الفيروسات.",
      [
        source("ARC", "Confirm clean planting material with local extension/diagnosis", "https://www.arc.sci.eg/", "Verify nursery/seed price locally"),
      ],
    ),
  ],
};

catalogs.tomato_yellow_leaf_curl_virus = {
  disease_name_en: "Tomato yellow leaf curl virus",
  disease_name_ar: "فيروس تجعد واصفرار أوراق الطماطم",
  treatments: [
    product(
      1,
      "Rogue infected plants and reduce whitefly pressure",
      "إزالة المصاب وتقليل ضغط الذبابة البيضاء",
      "IPM / vector management",
      "No virus-curing dose; any whitefly product must be APC-registered for tomato and whitefly.",
      "لا توجد جرعة تشفي الفيروس؛ أي منتج للذبابة البيضاء لازم يكون مسجل للطماطم والذبابة البيضاء.",
      "Remove badly infected young plants, use insect-proof netting/sticky monitoring, control weeds, and verify any whitefly pesticide with APC first.",
      "أزل النباتات الصغيرة المصابة بشدة، استخدم شبك/مصائد مراقبة، اكافح الحشائش، وتحقق من أي مبيد للذبابة البيضاء في APC أولًا.",
      "Follow label if using a registered whitefly product",
      "حسب اللافتة إذا استُخدم منتج مسجل للذبابة البيضاء",
      "Spraying after infection will not cure the plant; wrong insecticide use wastes money and increases resistance.",
      "الرش بعد الإصابة لا يشفي النبات؛ المبيد الغلط يهدر المال ويزود المقاومة.",
      "Sticky traps/netting/whitefly-control prices vary; verify current local quotes.",
      "أسعار المصائد/الشبك/مكافحة الذبابة البيضاء تختلف؛ أكد السعر المحلي.",
      "Focus on the vector and clean seedlings, not a virus cure.",
      "ركز على الناقل والشتلات النظيفة، وليس علاج الفيروس نفسه.",
      [
        source("APC", "Verify tomato + whitefly pesticide registration", APC_URL, "Verify current product and price locally"),
        source("ARC", "Confirm TYLCV diagnosis and whitefly management", "https://www.arc.sci.eg/", "No direct virus-cure price"),
      ],
    ),
  ],
};

catalogs.healthy = {
  disease_name_en: "Healthy tomato",
  disease_name_ar: "طماطم سليمة",
  treatments: [
    product(
      1,
      "Routine scouting and prevention",
      "كشف دوري ووقاية",
      "Prevention",
      "No treatment dose.",
      "لا توجد جرعة علاج.",
      "Scout twice weekly, keep foliage dry, remove old debris, and record any new spots before buying pesticides.",
      "اكشف مرتين أسبوعيًا، حافظ على جفاف الورق، أزل المخلفات القديمة، وسجل أي بقع جديدة قبل شراء مبيدات.",
      "Not applicable",
      "غير منطبق",
      "Unneeded pesticide use costs money and can create residue/resistance problems.",
      "استخدام مبيد بلا داعي يهدر المال وقد يسبب متبقيات/مقاومة.",
      "No pesticide purchase recommended.",
      "لا يوجد شراء مبيد موصى به.",
      "Keep monitoring; very early symptoms can be missed by one image.",
      "استمر في المتابعة؛ الأعراض المبكرة جدًا قد لا تظهر في صورة واحدة.",
      [source("ARC", "Routine crop monitoring", "https://www.arc.sci.eg/", "No treatment cost")],
    ),
  ],
};

const checkedPriceSignals = [
  { disease: "tomato_late_blight", source: "AgriCash", contains: "Ridomil", price: "720 EGP / 400 g listed online" },
  { disease: "tomato_late_blight", source: "Cowboyzz Egypt", contains: "Ridomil", price: "435 LE / 500 g listed online; sold out on page" },
  { disease: "tomato_late_blight", source: "ERADCO", contains: "Revus", price: "632.50 SAR / 1 L listed online; out of stock and not an Egypt price" },
  { disease: "tomato_early_blight", source: "AgroKima", contains: "Hi-Manco", price: "0.00 shown on source page; price unavailable, verify by phone/local dealer" },
  { disease: "septoria_leaf_spot_tomato", source: "AgroKima", contains: "Hi-Manco", price: "0.00 shown on source page; price unavailable, verify by phone/local dealer" },
];

for (const signal of checkedPriceSignals) {
  const entry = catalogs[signal.disease];
  for (const treatment of entry?.treatments ?? []) {
    for (const src of treatment.price_sources ?? []) {
      if (src.source === signal.source && src.title.includes(signal.contains)) {
        src.price_text = signal.price;
      }
    }
  }
}

for (const entry of Object.values(catalogs)) {
  for (const treatment of entry.treatments ?? []) {
    for (const src of treatment.price_sources ?? []) {
      if (!src.price_text && src.source !== "APC") src.price_text = "No parsed online price; verify current dealer quote";
    }
  }
}

export async function handler(event) {
  if (event.httpMethod === "OPTIONS") return { statusCode: 204, headers: CORS, body: "" };
  if (event.httpMethod !== "GET") return json(405, { error: "Method not allowed" });
  const pathKey = String(event.path || "").split("/").filter(Boolean).pop() || "";
  const queryKey = event.queryStringParameters?.disease_key || "";
  const diseaseKey = queryKey && queryKey !== ":key"
    ? queryKey
    : (pathKey && pathKey !== "treatments-tomato" ? decodeURIComponent(pathKey) : "");
  const entry = catalogs[diseaseKey];
  if (!entry) return json(404, { error: "No reviewed tomato treatment catalog for this disease." });
  return json(200, {
    disease_key: diseaseKey,
    disease_name_en: entry.disease_name_en,
    disease_name_ar: entry.disease_name_ar,
    crop: "tomato",
    treatments: entry.treatments,
    availability: {
      status_en: "Verify current Egyptian registration in APC, then confirm stock with a local pesticide dealer or agricultural association.",
      status_ar: "أكد التسجيل المصري الحالي في لجنة المبيدات، وبعدها أكد التوفر من محل مبيدات أو جمعية زراعية محلية.",
      apc_url: APC_URL,
      price_status_en: "Online sources are dealer/market signals, not official prices. Confirm the exact current price locally before buying.",
      price_status_ar: "مصادر الأونلاين مؤشرات سوق/تجار وليست أسعار رسمية. أكد السعر الحالي بالضبط محليًا قبل الشراء.",
    },
    prevention,
  });
}
