"""Reviewed bilingual crop guidance that works without internet or an image analysis."""

from __future__ import annotations

from dataclasses import dataclass


SOURCES = [
    "Cornell Vegetables: disease-resistant tomato varieties",
    "Cornell Vegetables: evaluation of late-blight-resistant tomato varieties",
    "Utah State University Extension: high tunnel production",
]

SOURCE_URLS = [
    "https://www.vegetables.cornell.edu/pest-management/disease-factsheets/disease-resistant-vegetable-varieties/disease-resistant-tomato-varieties/",
    "https://www.vegetables.cornell.edu/pest-management/disease-factsheets/disease-resistant-vegetable-varieties/evaluation-of-late-blight-resistant-tomato-varieties/",
    "https://extension.usu.edu/vegetableguide/production/high-tunnels",
]

TOMATO_VARIETIES = [
    {
        "name": "Iron Lady",
        "resistance_en": "Strong late-blight resistance using Ph-2 and Ph-3 genes.",
        "resistance_ar": "مقاومة قوية للّفحة المتأخرة بجيني Ph-2 وPh-3.",
    },
    {
        "name": "Mountain Merit F1",
        "resistance_en": "Early blight, late blight, Fusarium wilt races 1–3, root-knot nematode, TSWV, and Verticillium.",
        "resistance_ar": "اللفحة المبكرة والمتأخرة، وفيوزاريوم 1–3، ونيماتودا تعقد الجذور، وTSWV، وفرتيسيليوم.",
    },
    {
        "name": "Mountain Magic",
        "resistance_en": "Late-blight-resistant small-fruited tomato; performed strongly in Cornell trials.",
        "resistance_ar": "طماطم صغيرة الثمار مقاومة للّفحة المتأخرة وظهرت بنتائج قوية في تجارب كورنيل.",
    },
    {
        "name": "Plum Regal F1",
        "resistance_en": "Roma type with early blight, late blight, Fusarium 1–2, TSWV, and Verticillium resistance.",
        "resistance_ar": "صنف روما مقاوم للّفحة المبكرة والمتأخرة، وفيوزاريوم 1–2، وTSWV، وفرتيسيليوم.",
    },
    {
        "name": "Invincible",
        "resistance_en": "Broad package including late blight, Septoria, bacterial wilt, TYLCV, Fusarium, and Verticillium.",
        "resistance_ar": "حزمة مقاومة واسعة تشمل اللفحة المتأخرة وسبتوريا والذبول البكتيري وTYLCV وفيوزاريوم وفرتيسيليوم.",
    },
    {
        "name": "Skyway F1",
        "resistance_en": "Useful where TYLCV, TSWV, root-knot nematodes, and Fusarium wilt are important.",
        "resistance_ar": "مفيد عند انتشار TYLCV وTSWV ونيماتودا تعقد الجذور وذبول الفيوزاريوم.",
    },
]


@dataclass(frozen=True)
class TomatoResistantVarietyReference:
    name_en: str
    name_ar: str
    resistance_codes_en: str
    resistance_codes_ar: str
    disease_coverage_en: tuple[str, ...]
    disease_coverage_ar: tuple[str, ...]
    resistance_strength_en: str
    resistance_strength_ar: str
    prevention_only_warning_en: str
    prevention_only_warning_ar: str
    egypt_availability_status: str
    source_title: str
    source_organization: str
    source_url: str | None
    source_type: str
    source_kind: str
    source_note_en: str
    source_note_ar: str
    farmer_wording_en: str
    farmer_wording_ar: str


TOMATO_RESISTANT_VARIETY_RECORDS = (
    TomatoResistantVarietyReference(
        name_en="Iron Lady",
        name_ar="Iron Lady",
        resistance_codes_en="Ph-2, Ph-3, SLS-R, EBT",
        resistance_codes_ar="Ph-2، Ph-3، SLS-R، EBT",
        disease_coverage_en=(
            "Early blight",
            "Late blight",
            "Septoria leaf spot",
            "Fusarium wilt 1",
            "Fusarium wilt 2",
            "Verticillium wilt",
        ),
        disease_coverage_ar=(
            "اللفحة المبكرة",
            "اللفحة المتأخرة",
            "تبقع السبوتريا",
            "ذبول الفيوزاريوم 1",
            "ذبول الفيوزاريوم 2",
            "الفرتيسيليوم",
        ),
        resistance_strength_en="High for foliar blights and strong overall package.",
        resistance_strength_ar="قوية ضد اللفحات الورقية وحزمة مقاومة عامة قوية.",
        prevention_only_warning_en="Resistance slows the problem down; it does not cure an infected plant.",
        prevention_only_warning_ar="المقاومة بتبطئ المشكلة، لكنها لا تعالج النبات المصاب.",
        egypt_availability_status="not_verified_in_egypt",
        source_title="Cornell disease-resistant tomato varieties / Cornell variety page",
        source_organization="Cornell University",
        source_url="https://www.vegetables.cornell.edu/pest-management/disease-factsheets/disease-resistant-vegetable-varieties/disease-resistant-tomato-varieties/",
        source_type="official",
        source_kind="variety_knowledge",
        source_note_en="Resistance package verified in Cornell references; Egypt availability was not verified during generation.",
        source_note_ar="حزمة المقاومة موثقة في مراجع كورنيل؛ توافرها في مصر لم يُتحقق منه أثناء التوليد.",
        farmer_wording_en="Ask for Iron Lady only if your supplier can show the label codes and local stock.",
        farmer_wording_ar="اسأل عن Iron Lady فقط لو الموزع يقدر يوضح أكواد المقاومة والتوافر المحلي.",
    ),
    TomatoResistantVarietyReference(
        name_en="Stellar F1",
        name_ar="Stellar F1",
        resistance_codes_en="Resistance package published; exact seed-label code not verified in the reviewed source.",
        resistance_codes_ar="حزمة مقاومة منشورة؛ كود العبوة لم يُتحقق منه في المصدر المراجع.",
        disease_coverage_en=(
            "Early blight",
            "Late blight",
            "Septoria leaf spot",
            "Fusarium wilt 1",
            "Fusarium wilt 2",
            "Verticillium wilt",
        ),
        disease_coverage_ar=(
            "اللفحة المبكرة",
            "اللفحة المتأخرة",
            "تبقع السبوتريا",
            "ذبول الفيوزاريوم 1",
            "ذبول الفيوزاريوم 2",
            "الفرتيسيليوم",
        ),
        resistance_strength_en="High for the foliar disease package.",
        resistance_strength_ar="قوية في حزمة الأمراض الورقية.",
        prevention_only_warning_en="Still a prevention tool, not a cure for infected plants.",
        prevention_only_warning_ar="ما زالت أداة وقاية، وليست علاجًا للنبات المصاب.",
        egypt_availability_status="not_verified_in_egypt",
        source_title="New York adapted tomatoes with resistance to multiple fungal and bacterial diseases",
        source_organization="Cornell University",
        source_url="https://www.vegetables.cornell.edu/pest-management/disease-factsheets/disease-resistant-vegetable-varieties/new-york-adapted-tomatoes-with-resistance-to-multiple-fungal-and-bacterial-diseases-created-at-cornell/",
        source_type="official",
        source_kind="variety_knowledge",
        source_note_en="Reviewed Cornell breeding note; Egypt availability was not verified during generation.",
        source_note_ar="ملاحظة التربية من كورنيل؛ توافره في مصر لم يُتحقق منه أثناء التوليد.",
        farmer_wording_en="Ask the seed seller to confirm local stock before you treat it as a real recommendation.",
        farmer_wording_ar="اطلب من الموزع تأكيد التوافر المحلي قبل اعتباره توصية نهائية.",
    ),
    TomatoResistantVarietyReference(
        name_en="Seiger",
        name_ar="Seiger",
        resistance_codes_en="Exact resistance code not published in the reviewed source.",
        resistance_codes_ar="كود المقاومة الدقيق غير منشور في المصدر المراجع.",
        disease_coverage_en=("Early blight", "Late blight", "Septoria leaf spot"),
        disease_coverage_ar=("اللفحة المبكرة", "اللفحة المتأخرة", "تبقع السبوتريا"),
        resistance_strength_en="Moderate to strong for the three-disease package.",
        resistance_strength_ar="متوسطة إلى قوية في حزمة الأمراض الثلاثة.",
        prevention_only_warning_en="Useful only as part of a clean, dry, rotated cropping plan.",
        prevention_only_warning_ar="تفيد فقط ضمن خطة زراعة نظيفة وجافة ودوران محصولي.",
        egypt_availability_status="not_verified_in_egypt",
        source_title="Cornell disease-resistant tomato varieties",
        source_organization="Cornell University",
        source_url="https://www.vegetables.cornell.edu/pest-management/disease-factsheets/disease-resistant-vegetable-varieties/disease-resistant-tomato-varieties/",
        source_type="official",
        source_kind="variety_knowledge",
        source_note_en="Listed in Cornell disease-resistance references; Egypt availability was not verified during generation.",
        source_note_ar="مذكور في مراجع كورنيل للمقاومة؛ توافره في مصر لم يُتحقق منه أثناء التوليد.",
        farmer_wording_en="Treat Seiger as a supplier-check option, not a final buy recommendation.",
        farmer_wording_ar="اعتبر Seiger خيارًا يحتاج تأكيد موزع، وليس توصية شراء نهائية.",
    ),
    TomatoResistantVarietyReference(
        name_en="Mountain Merit F1",
        name_ar="Mountain Merit F1",
        resistance_codes_en="VFFFNTswvEbLb",
        resistance_codes_ar="VFFFNTswvEbLb",
        disease_coverage_en=(
            "Verticillium wilt",
            "Fusarium wilt 1",
            "Fusarium wilt 2",
            "Fusarium wilt 3",
            "Nematodes",
            "Tomato spotted wilt virus",
            "Late blight",
            "Early blight",
        ),
        disease_coverage_ar=(
            "الفرتيسيليوم",
            "ذبول الفيوزاريوم 1",
            "ذبول الفيوزاريوم 2",
            "ذبول الفيوزاريوم 3",
            "النيماتودا",
            "فيروس تبقع الطماطم المبرقش",
            "اللفحة المتأخرة",
            "اللفحة المبكرة",
        ),
        resistance_strength_en="Broad package, strong for multiple common tomato problems.",
        resistance_strength_ar="حزمة واسعة، قوية ضد عدة مشاكل شائعة في الطماطم.",
        prevention_only_warning_en="Broad resistance still needs sanitation, airflow, and local verification.",
        prevention_only_warning_ar="حتى المقاومة الواسعة تحتاج نظافة وتهوية وتحقق محلي.",
        egypt_availability_status="not_verified_in_egypt",
        source_title="Mountain Merit F1 tomato seeds",
        source_organization="Seeds 'n Such / Cornell-linked catalog references",
        source_url="https://seedsnsuch.com/products/mountain-merit-hybrid-tomato-seeds",
        source_type="official",
        source_kind="variety_knowledge",
        source_note_en="Resistance code package taken from catalog references; Egypt availability was not verified during generation.",
        source_note_ar="حزمة الأكواد مأخوذة من مراجع الكتالوج؛ توافرها في مصر لم يُتحقق منه أثناء التوليد.",
        farmer_wording_en="Do not treat it as a final recommendation until you confirm local stock and the label codes.",
        farmer_wording_ar="لا تعتبره توصية نهائية قبل تأكيد التوافر المحلي وأكواد العبوة.",
    ),
    TomatoResistantVarietyReference(
        name_en="Plum Regal F1",
        name_ar="Plum Regal F1",
        resistance_codes_en="VFFTswvEbLb",
        resistance_codes_ar="VFFTswvEbLb",
        disease_coverage_en=(
            "Early blight",
            "Late blight",
            "Fusarium wilt 1",
            "Fusarium wilt 2",
            "Tomato spotted wilt virus",
            "Verticillium wilt",
        ),
        disease_coverage_ar=(
            "اللفحة المبكرة",
            "اللفحة المتأخرة",
            "ذبول الفيوزاريوم 1",
            "ذبول الفيوزاريوم 2",
            "فيروس تبقع الطماطم المبرقش",
            "الفرتيسيليوم",
        ),
        resistance_strength_en="Useful package, especially for blight pressure and paste tomatoes.",
        resistance_strength_ar="حزمة مفيدة، خاصة مع ضغط اللفحات والطماطم المخصصة للصوص.",
        prevention_only_warning_en="Helpful, but it is not a substitute for field hygiene or APC verification.",
        prevention_only_warning_ar="مفيد، لكنه لا يغني عن نظافة الحقل أو تحقق APC.",
        egypt_availability_status="not_verified_in_egypt",
        source_title="Plum Regal tomato seed catalog references",
        source_organization="Seeds 'n Such / Johnny's / Cornell-linked references",
        source_url="https://seedsnsuch.com/products/plum-regal-hybrid-tomato-seeds",
        source_type="official",
        source_kind="variety_knowledge",
        source_note_en="Resistance package verified from catalog references; Egypt availability was not verified during generation.",
        source_note_ar="حزمة المقاومة موثقة في مراجع الكتالوج؛ توافرها في مصر لم يُتحقق منه أثناء التوليد.",
        farmer_wording_en="Ask the supplier for the label code and current Egypt stock before buying.",
        farmer_wording_ar="اسأل المورد عن كود العبوة والتوافر في مصر قبل الشراء.",
    ),
    TomatoResistantVarietyReference(
        name_en="Invincible",
        name_ar="Invincible",
        resistance_codes_en="V, F1-2, N, TYLCV, Eb, Lb, Ss, ToMV",
        resistance_codes_ar="V، F1-2، N، TYLCV، Eb، Lb، Ss، ToMV",
        disease_coverage_en=(
            "Tomato yellow leaf curl virus (TYLCV)",
            "Late blight",
            "Early blight",
            "Septoria leaf spot",
            "Bacterial wilt",
            "Fusarium wilt",
            "Verticillium wilt",
        ),
        disease_coverage_ar=(
            "فيروس تجعّد واصفرار أوراق الطماطم (TYLCV)",
            "اللفحة المتأخرة",
            "اللفحة المبكرة",
            "تبقع السبتوريا",
            "الذبول البكتيري",
            "ذبول الفيوزاريوم",
            "الفرتيسيليوم",
        ),
        resistance_strength_en="Broad package with strong TYLCV resistance — one of the more complete resistance profiles for TYLCV pressure fields.",
        resistance_strength_ar="حزمة واسعة مع مقاومة قوية لـ TYLCV — من أشمل ملفات المقاومة في حقول ضغط TYLCV.",
        prevention_only_warning_en="Resistance reduces new infection risk in next season — it does not cure plants infected in the current season.",
        prevention_only_warning_ar="المقاومة تقلل خطر الإصابة في الموسم القادم — لا تعالج النباتات المصابة في الموسم الحالي.",
        egypt_availability_status="not_verified_in_egypt",
        source_title="Invincible tomato variety resistance data",
        source_organization="Cornell University / AVRDC variety references",
        source_url=None,
        source_type="official",
        source_kind="variety_knowledge",
        source_note_en="Resistance package sourced from Cornell and AVRDC variety references; Egypt availability was not verified during generation.",
        source_note_ar="حزمة المقاومة مصدرها مراجع أصناف كورنيل وAVRDC؛ توافره في مصر لم يُتحقق منه أثناء التوليد.",
        farmer_wording_en="Ask your seed supplier whether Invincible or an equivalent TYLCV-resistant hybrid is available locally and check resistance codes on the label.",
        farmer_wording_ar="اسأل مورد البذور إذا كان Invincible أو هجين مقاوم لـ TYLCV مماثل متاح محليًا وتحقق من رموز المقاومة على العبوة.",
    ),
    TomatoResistantVarietyReference(
        name_en="Skyway F1",
        name_ar="Skyway F1",
        resistance_codes_en="V, F1-2, N, TYLCV, TSWV, ToMV",
        resistance_codes_ar="V، F1-2، N، TYLCV، TSWV، ToMV",
        disease_coverage_en=(
            "Tomato yellow leaf curl virus (TYLCV)",
            "Tomato spotted wilt virus (TSWV)",
            "Fusarium wilt",
            "Verticillium wilt",
            "Nematodes",
        ),
        disease_coverage_ar=(
            "فيروس تجعّد واصفرار أوراق الطماطم (TYLCV)",
            "فيروس تبقع الطماطم المبرقش (TSWV)",
            "ذبول الفيوزاريوم",
            "الفرتيسيليوم",
            "النيماتودا",
        ),
        resistance_strength_en="Strong TYLCV and TSWV resistance with soilborne disease package — useful in whitefly-pressure environments.",
        resistance_strength_ar="مقاومة قوية لـ TYLCV وTSWV مع حزمة أمراض التربة — مفيد في بيئات ضغط الذبابة البيضاء.",
        prevention_only_warning_en="Resistance reduces infection risk for future plantings — it cannot reverse damage in currently infected plants.",
        prevention_only_warning_ar="المقاومة تقلل خطر الإصابة للزراعات القادمة — لا يمكنها عكس الضرر في النباتات المصابة حاليًا.",
        egypt_availability_status="not_verified_in_egypt",
        source_title="Skyway F1 tomato variety resistance data",
        source_organization="Syngenta / AVRDC variety references",
        source_url=None,
        source_type="official",
        source_kind="variety_knowledge",
        source_note_en="Resistance package sourced from Syngenta and AVRDC variety references; Egypt availability was not verified during generation.",
        source_note_ar="حزمة المقاومة مصدرها مراجع أصناف سينجنتا وAVRDC؛ توافره في مصر لم يُتحقق منه أثناء التوليد.",
        farmer_wording_en="Confirm with your local seed supplier whether Skyway F1 or an equivalent TYLCV-resistant hybrid is stocked and check label resistance codes.",
        farmer_wording_ar="تأكد مع مورد البذور المحلي إذا كان Skyway F1 أو هجين مقاوم لـ TYLCV مماثل متاح وتحقق من رموز المقاومة على العبوة.",
    ),
)


def tomato_resistant_variety_records() -> tuple[TomatoResistantVarietyReference, ...]:
    return TOMATO_RESISTANT_VARIETY_RECORDS

PROTECTION_EN = [
    "Choose resistance for your main local problem; verify the exact resistance codes on the seed supplier label.",
    "Use certified clean seed/transplants and reject seedlings showing curl, mosaic, spots, or wilt.",
    "Scout at least twice weekly; remove virus-suspect plants early and take diseased debris out of the crop area.",
    "Use drip irrigation, water early, prevent splashing, and avoid keeping leaves wet overnight.",
    "Space, trellis, and prune plants for airflow; disinfect hands and tools between suspect plants.",
    "Control whiteflies and thrips using insect screens, sticky cards, and locally approved IPM because they spread major tomato viruses.",
    "Rotate away from tomato, potato, pepper, and eggplant when managing persistent soilborne and residue-borne diseases.",
    "Use balanced nutrition; excessive nitrogen creates dense, disease-prone growth.",
]

PROTECTION_AR = [
    "اختار المقاومة حسب أهم مرض عندك، وتأكد من رموز المقاومة المكتوبة على عبوة البذور.",
    "استخدم بذور وشتلات معتمدة ونظيفة، وارفض الشتلات اللي فيها تجعد أو موزاييك أو بقع أو ذبول.",
    "اكشف على النبات مرتين أسبوعيًا على الأقل، وشيل النبات المشتبه في إصابته بفيروس بدري واطلع المخلفات المصابة بره مكان الزراعة.",
    "استخدم الري بالتنقيط، واروي بدري، وامنع تناثر الميه، وما تسيبش الورق مبلول طول الليل.",
    "سيب مسافات واربط وقلم النبات عشان التهوية، وطهّر الإيد والأدوات بين النباتات المشتبه فيها.",
    "كافح الذبابة البيضاء والتربس بشبك الحشرات والكروت اللاصقة وبرنامج مكافحة متكاملة معتمد محليًا لأنهم بينقلوا فيروسات مهمة.",
    "دوّر المحصول بعيد عن الطماطم والبطاطس والفلفل والباذنجان عند مكافحة أمراض التربة والمخلفات المستمرة.",
    "استخدم تسميد متوازن؛ زيادة الآزوت تعمل نمو كثيف سهل الإصابة.",
]

GREENHOUSE_EN = (
    "A well-managed greenhouse or high tunnel can lower some tomato disease risk because it excludes rain "
    "and reduces splash and leaf wetness. It does not guarantee protection. Poor ventilation, condensation, "
    "crowded plants, or wet roots can increase Botrytis, powdery mildew, bacterial disease, and root rots. "
    "Use strong ventilation, drip irrigation, morning watering, clean entry practices, insect screens, sticky "
    "cards, and regular scouting. Do not claim a fixed percentage reduction without local trial data."
)

GREENHOUSE_AR = (
    "الصوبة أو النفق المُدار كويس ممكن يقلل خطر بعض أمراض الطماطم لأنه يمنع المطر وتناثر الميه ويقلل بلل الورق. "
    "لكن مش ضمان. التهوية الضعيفة والتكثف والزحمة أو زيادة بلل الجذور ممكن تزود البوتريتس والبياض الدقيقي "
    "والأمراض البكتيرية وأعفان الجذور. استخدم تهوية قوية وري بالتنقيط وري الصبح ونظافة عند الدخول وشبك حشرات "
    "وكروت لاصقة وكشف دوري. ما ينفعش نقول نسبة تقليل ثابتة من غير تجربة محلية."
)


def tomato_varieties_text(lang: str) -> str:
    is_ar = lang == "ar"
    header = (
        "أمثلة أصناف طماطم مقاومة — اختار حسب المرض المتكرر عندك وتأكد من توفرها ورموز المقاومة من مورد محلي:"
        if is_ar
        else "Examples of resistant tomato varieties — choose for your recurring disease and verify local availability and seed-label resistance codes:"
    )
    lines = [
        f"- {item['name']}: {item['resistance_ar' if is_ar else 'resistance_en']}"
        for item in TOMATO_VARIETIES
    ]
    footer = (
        "المقاومة تقلل الخطر لكنها لا تمنع الإصابة تمامًا، ولا تعوض النظافة والتهوية والمكافحة المتكاملة."
        if is_ar
        else "Resistance lowers risk but does not prevent every infection and does not replace sanitation, ventilation, and IPM."
    )
    return "\n".join([header, *lines, footer])


def tomato_varieties_text(lang: str) -> str:
    is_ar = lang == "ar"
    header = (
        "أصناف طماطم مقاومة مراجعة - هذه مراجع خصائص وليست تأكيدًا لتوفر السوق المصري:"
        if is_ar
        else "Reviewed resistant tomato varieties - these are reference traits, not a confirmed Egypt stock list:"
    )
    lines: list[str] = []
    for item in TOMATO_RESISTANT_VARIETY_RECORDS:
        name = item.name_ar if is_ar else item.name_en
        codes = item.resistance_codes_ar if is_ar else item.resistance_codes_en
        strength = item.resistance_strength_ar if is_ar else item.resistance_strength_en
        coverage = "، ".join(item.disease_coverage_ar if is_ar else item.disease_coverage_en)
        availability = {
            "verified_in_egypt": "متوفر في مصر",
            "not_verified_in_egypt": "لم يتم التحقق من توفره في مصر",
            "unknown": "التوفر في مصر غير معروف",
        }[item.egypt_availability_status]
        source_note = item.source_note_ar if is_ar else item.source_note_en
        farmer_wording = item.farmer_wording_ar if is_ar else item.farmer_wording_en
        lines.append(f"- {name}: {codes} | {strength} | {availability}")
        lines.append(f"  - {coverage}")
        lines.append(f"  - {source_note}")
        lines.append(f"  - {farmer_wording}")
    footer = (
        "المقاومة تقلل الخطر لكنها لا تمنع العدوى ولا تغني عن النظافة والتهوية والتأكيد المحلي."
        if is_ar
        else "Resistance lowers risk but does not prevent infection and does not replace sanitation, airflow, and local verification."
    )
    return "\n".join([header, *lines, footer])


def tomato_protection_text(lang: str) -> str:
    steps = PROTECTION_AR if lang == "ar" else PROTECTION_EN
    header = "خطة حماية عملية للطماطم:" if lang == "ar" else "Practical tomato crop-protection plan:"
    return "\n".join([header, *[f"{index}. {step}" for index, step in enumerate(steps, 1)]])


def greenhouse_text(lang: str) -> str:
    return GREENHOUSE_AR if lang == "ar" else GREENHOUSE_EN


def tomato_article(lang: str) -> dict[str, object]:
    return {
        "crop": "طماطم" if lang == "ar" else "Tomato",
        "varieties": TOMATO_VARIETIES,
        "protection_steps": PROTECTION_AR if lang == "ar" else PROTECTION_EN,
        "greenhouse_guidance": greenhouse_text(lang),
        "sources": SOURCE_URLS,
    }


def tomato_article(lang: str) -> dict[str, object]:
    is_ar = lang == "ar"
    varieties = [
        {
            "name": item.name_ar if is_ar else item.name_en,
            "resistance_en": item.resistance_strength_en,
            "resistance_ar": item.resistance_strength_ar,
            "availability": item.egypt_availability_status,
            "source_url": item.source_url,
        }
        for item in TOMATO_RESISTANT_VARIETY_RECORDS
    ]
    return {
        "crop": "Ø·Ù…Ø§Ø·Ù…" if is_ar else "Tomato",
        "varieties": varieties,
        "protection_steps": PROTECTION_AR if is_ar else PROTECTION_EN,
        "greenhouse_guidance": greenhouse_text(lang),
        "sources": SOURCE_URLS,
    }


def tomato_grounding(question: str, lang: str) -> str:
    normalized = question.lower()
    parts: list[str] = []
    if any(word in normalized for word in ["variet", "resistan", "cultivar", "صنف", "أصناف", "مقاوم"]):
        parts.append(tomato_varieties_text(lang))
    if any(word in normalized for word in ["greenhouse", "high tunnel", "protected", "صوبة", "صوبه", "بيت محمي", "نفق"]):
        parts.append(greenhouse_text(lang))
    if any(word in normalized for word in ["protect", "prevention", "practice", "ipm", "حماية", "وقاية", "ممارسات", "مكافحة"]):
        parts.append(tomato_protection_text(lang))
    return "\n\n".join(parts)
