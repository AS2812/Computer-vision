// ─────────────────────────────────────────────────────────────────────────────
// Bilingual UI copy (Arabic-first). The global AR↔EN toggle drives ALL of this,
// including tables — one language at a time. Phase BODY content (disease facts,
// economics labels) is bilingual inside the data modules; this file holds the
// chrome: pipeline, phase headers, the safety block, and the sidebar.
// ─────────────────────────────────────────────────────────────────────────────

import type { Bi, Lang } from "./diseases";

export type { Lang };

/** Pick the active-language string from any bilingual value. */
export function pick(bi: Bi, lang: Lang): string {
  return bi[lang];
}

export interface Strings {
  brand: string;
  brandTag: string;
  toggleTo: string; // label of the OTHER language
  // Permissions (optional, one-time)
  deviceServices: string;
  gpsExplain: string;
  useLocation: string;
  locationReady: string;
  locationRequesting: string;
  locationDenied: string;
  locationUnavailable: string;
  enableReminders: string;
  remindersEnabled: string;
  remindersDenied: string;
  // Capture
  cropFixed: string; // "Tomato"
  cropFixedNote: string;
  takePhoto: string;
  uploadPhoto: string;
  onePhotoHint: string;
  privacyNote: string;
  // Pipeline steps
  checkingOnDevice: string;
  checkedOnDevice: string;
  engine: string;
  memoryUsed: string;
  checkTime: string;
  qualityGate: string;
  qualityGood: string;
  qualityPoor: string;
  retakeTips: string;
  continueAnyway: string;
  leafGate: string;
  leafGateWarn: string;
  // Signals
  infectionExtent: string;
  infectionExtentNote: string; // "rough visual estimate, not segmentation"
  discoloration: string;
  yellowPixels: string;
  darkPixels: string;
  weatherPressure: string;
  weatherPressureNote: string;
  aiSecondOpinion: string;
  aiAgrees: string;
  aiDisagrees: string;
  aiOffline: string;
  aiCaveat: string;
  // Verdict
  screeningVerdict: string;
  notConfirmed: string;
  uncalibratedNote: string;
  hostCropNote: string;
  certaintyLow: string;
  certaintyMedium: string;
  certaintyHigh: string;
  topCandidates: string;
  matchScore: string;
  // Phase titles (story arc)
  phase1: string;
  phase1Sub: string;
  phase2: string;
  phase2Sub: string;
  phase3: string;
  phase3Sub: string;
  phase4: string;
  phase4Sub: string;
  phase5: string;
  phase5Sub: string;
  phase6: string;
  phase6Sub: string;
  // Phase 1
  symptomsLeaf: string;
  symptomsFruit: string;
  symptomsStem: string;
  causeType: string;
  lookalikes: string;
  todayCheck: string;
  photoCropCard: string;
  evidenceNote: string;
  // Phase 2
  protectNow: string;
  appliesAnyConfidence: string;
  scenarioHome: string;
  scenarioField: string;
  scenarioGreenhouse: string;
  doThis: string;
  avoidThis: string;
  // Phase 3
  confirmIt: string;
  confirmItIntro: string;
  addMorePhotos: string;
  // Phase 4
  treatmentOptions: string;
  nonChemicalFirst: string;
  chemicalGateLocked: string;
  chemicalGateWhy: string;
  apcVerify: string;
  qcapResidue: string;
  modeBenefit: string;
  modeRisk: string;
  modeCost: string;
  modeApc: string;
  modeFarmSize: string;
  seeProtectNow: string;
  // Phase 5
  worthIt: string;
  referenceEstimate: string;
  enterRealNumbers: string;
  perfarmSize: string;
  comparisonTable: string;
  netBenefit: string;
  worthLikely: string;
  worthAsk: string;
  worthMaybeNot: string;
  // Phase 6
  actionPlan: string;
  headline: string;
  today: string;
  next37: string;
  callExpertWhen: string;
  bestOverall: string;
  cheapestSafe: string;
  strongestAllowed: string;
  avoidChoice: string;
  // Safety block (shown ONCE)
  safetyTitle: string;
  safetyRules: string[];
  assumptionsTitle: string;
  // Sidebar
  assistantTitle: string;
  assistantHint: string;
  assistantPlaceholder: string;
  quickQuestions: string;
  egyptSources: string;
  provenanceTitle: string;
  downloads: string;
  savedCases: string;
  status_collecting: string;
  status_needs_expert: string;
  status_diagnosis: string;
  status_economics: string;
  status_report: string;
  // misc
  comingLater: string; // water-stress out of scope
  notSure: string;
  notTomato: string;
}

const EN: Strings = {
  brand: "AgroVision",
  brandTag: "Egypt · Tomato leaf checkup",
  toggleTo: "العربية",
  deviceServices: "Device services (optional)",
  gpsExplain: "Location is used ONLY to read local weather at analysis time. It never geotags or saves your photo location.",
  useLocation: "Use my location",
  locationReady: "Location ready",
  locationRequesting: "Requesting location…",
  locationDenied: "Location denied",
  locationUnavailable: "Location unavailable",
  enableReminders: "Enable reminders",
  remindersEnabled: "Reminders enabled",
  remindersDenied: "Reminders denied",
  cropFixed: "Tomato",
  cropFixedNote: "This app is tomato-only. Other crops and water-stress detection are coming later.",
  takePhoto: "Take a photo",
  uploadPhoto: "Upload a photo",
  onePhotoHint: "Add ONE clear tomato leaf photo — that is all we need.",
  privacyNote: "Your photo is checked on your device. It is only uploaded if you opt in.",
  checkingOnDevice: "Checking on your device…",
  checkedOnDevice: "Checked on your device",
  engine: "Engine",
  memoryUsed: "Memory",
  checkTime: "Check time",
  qualityGate: "Photo quality (heuristic)",
  qualityGood: "Photo looks clear enough.",
  qualityPoor: "The photo may be too small, blurry, or dark.",
  retakeTips: "Retake photo tips: fill the frame with one leaf, hold steady, use daylight, avoid shadows.",
  continueAnyway: "Continue anyway",
  leafGate: "Tomato-leaf check (model)",
  leafGateWarn: "This may not be a clear tomato leaf. Retake a close tomato-leaf photo in good light.",
  infectionExtent: "Infection extent (rough estimate)",
  infectionExtentNote: "A rough visual estimate from pixel colour — NOT a segmentation or a biological severity.",
  discoloration: "Discoloration",
  yellowPixels: "Yellow pixels",
  darkPixels: "Dark pixels",
  weatherPressure: "Weather pressure (heuristic)",
  weatherPressureNote: "A rule-of-thumb disease-pressure score from current weather — not a forecast of infection.",
  aiSecondOpinion: "AI second opinion",
  aiAgrees: "The AI second opinion agrees with the local model.",
  aiDisagrees: "The AI second opinion disagrees — treat the result as more uncertain.",
  aiOffline: "AI second opinion unavailable — showing the on-device result only.",
  aiCaveat: "The AI is one more opinion. It never sets doses and never unlocks chemicals.",
  screeningVerdict: "Screening result",
  notConfirmed: "NOT confirmed",
  uncalibratedNote: "This is an uncalibrated visual-match value, not the probability the diagnosis is correct.",
  hostCropNote: "Tomato was selected by you; the image model does not independently confirm the host crop.",
  certaintyLow: "Low certainty",
  certaintyMedium: "Medium certainty",
  certaintyHigh: "High certainty",
  topCandidates: "Top possibilities",
  matchScore: "Visual match",
  phase1: "Phase 1 — Diagnosis",
  phase1Sub: "See it",
  phase2: "Phase 2 — Protect Now",
  phase2Sub: "Stop it",
  phase3: "Phase 3 — Confirm It",
  phase3Sub: "Confirm it",
  phase4: "Phase 4 — Treatment Options",
  phase4Sub: "Treat it",
  phase5: "Phase 5 — Is It Worth It?",
  phase5Sub: "Cost it",
  phase6: "Phase 6 — Your Action Plan",
  phase6Sub: "Plan it",
  symptomsLeaf: "On the leaf",
  symptomsFruit: "On the fruit",
  symptomsStem: "On the stem",
  causeType: "Cause",
  lookalikes: "Looks like (confirm before treating)",
  todayCheck: "Today's check — look at this by eye",
  photoCropCard: "Photo quality & crop verification",
  evidenceNote: "Evidence",
  protectNow: "Protect now — safe, non-chemical, do it at any confidence",
  appliesAnyConfidence: "These steps cannot harm the crop and apply even before the diagnosis is confirmed.",
  scenarioHome: "Home garden",
  scenarioField: "Open-field block",
  scenarioGreenhouse: "Greenhouse",
  doThis: "Do this",
  avoidThis: "Avoid this",
  confirmIt: "Confirm it — raise certainty before spending money",
  confirmItIntro: "Answer what you can. Each answer updates the certainty band and the recommended treatment mode live.",
  addMorePhotos: "Add more photos: close leaf · underside · whole plant",
  treatmentOptions: "Treatment options — non-chemical first; chemicals stay behind a safety gate",
  nonChemicalFirst: "Start with the safe options. Chemical modes unlock only when the gate conditions are met.",
  chemicalGateLocked: "Locked — chemical gate",
  chemicalGateWhy: "Why locked",
  apcVerify: "Verify APC registration (crop + pest)",
  qcapResidue: "QCAP residue lab",
  modeBenefit: "Benefit",
  modeRisk: "Risk",
  modeCost: "Cost band",
  modeApc: "APC status",
  modeFarmSize: "Best farm size",
  seeProtectNow: "First do the Protect Now steps above — this phase is the escalation decision, not a repeat.",
  worthIt: "Is it worth it? — economics for the selected mode",
  referenceEstimate: "Reference estimate",
  enterRealNumbers: "Enter your real area + a local price to compute exact figures.",
  perfarmSize: "Per farm size",
  comparisonTable: "Cost-benefit comparison",
  netBenefit: "Net benefit",
  worthLikely: "Likely worth it",
  worthAsk: "Ask an engineer",
  worthMaybeNot: "May not pay off",
  actionPlan: "Your action plan",
  headline: "Recommendation",
  today: "Today",
  next37: "Next 3–7 days",
  callExpertWhen: "Call an expert when",
  bestOverall: "Best overall",
  cheapestSafe: "Cheapest safe",
  strongestAllowed: "Strongest allowed",
  avoidChoice: "Choice to avoid",
  safetyTitle: "Recommendation, assumptions & safety",
  safetyRules: [
    "This is a screening signal, not a lab diagnosis. Confirm before spraying.",
    "Low confidence blocks all chemical-category advice; the default is Confirm first.",
    "Stronger chemical modes stay locked until the diagnosis is confirmed AND APC registration is verified for tomato + that pest.",
    "Any chemical use needs the registered Egyptian label dose, PPE, REI, and PHI — and an Egyptian agricultural engineer must sign off first.",
    "Food-safety or residue concerns go to the QCAP lab.",
    "Never spray on the AI result alone, and never over-spray.",
  ],
  assumptionsTitle: "Assumptions",
  assistantTitle: "Farming assistant (AR / EN)",
  assistantHint: "Grounded in your photo evidence, weather, CAPMAS yield, APC registration, and the treatment rules.",
  assistantPlaceholder: "Ask about your tomato…",
  quickQuestions: "Quick questions",
  egyptSources: "Egypt sources",
  provenanceTitle: "Where the numbers come from",
  downloads: "Downloads",
  savedCases: "Saved cases",
  status_collecting: "collecting evidence",
  status_needs_expert: "needs expert",
  status_diagnosis: "diagnosis ready",
  status_economics: "economics ready",
  status_report: "report ready",
  comingLater: "Coming later",
  notSure: "Not sure yet",
  notTomato: "Not a tomato leaf?",
};

const AR: Strings = {
  brand: "AgroVision",
  brandTag: "مصر · كشف ورقة الطماطم",
  toggleTo: "English",
  deviceServices: "خدمات الجهاز (اختياري)",
  gpsExplain: "الموقع بيُستخدم بس لقراءة طقس المكان وقت التحليل. عمره ما بيحفظ مكان الصورة ولا بيعلّمها جغرافيًا.",
  useLocation: "استخدم موقعي",
  locationReady: "الموقع جاهز",
  locationRequesting: "بنطلب الموقع…",
  locationDenied: "الموقع مرفوض",
  locationUnavailable: "الموقع غير متاح",
  enableReminders: "فعّل التذكيرات",
  remindersEnabled: "التذكيرات مفعّلة",
  remindersDenied: "التذكيرات مرفوضة",
  cropFixed: "طماطم",
  cropFixedNote: "التطبيق للطماطم بس. محاصيل تانية وكشف الإجهاد المائي جايين بعدين.",
  takePhoto: "صوّر",
  uploadPhoto: "ارفع صورة",
  onePhotoHint: "حِط صورة واحدة واضحة لورقة طماطم — ده كل اللي محتاجينه.",
  privacyNote: "صورتك بتتفحص على جهازك. ما بترفعش إلا لو إنت وافقت.",
  checkingOnDevice: "بنفحص على جهازك…",
  checkedOnDevice: "اتفحصت على جهازك",
  engine: "المحرك",
  memoryUsed: "الذاكرة",
  checkTime: "وقت الفحص",
  qualityGate: "جودة الصورة (تقدير)",
  qualityGood: "الصورة شكلها واضحة كفاية.",
  qualityPoor: "الصورة ممكن تكون صغيرة أو مهزوزة أو غامقة.",
  retakeTips: "نصايح إعادة التصوير: املا الكادر بورقة واحدة، ثبّت إيدك، استخدم ضوء النهار، وابعد عن الظل.",
  continueAnyway: "كمّل برضه",
  leafGate: "فحص ورقة الطماطم (الموديل)",
  leafGateWarn: "ممكن دي ما تكونش ورقة طماطم واضحة. صوّر ورقة طماطم من قريب في إضاءة كويسة.",
  infectionExtent: "مدى الإصابة (تقدير تقريبي)",
  infectionExtentNote: "تقدير بصري تقريبي من لون البكسل — مش تجزئة (segmentation) ولا خطورة بيولوجية.",
  discoloration: "تغيّر اللون",
  yellowPixels: "بكسلات صفرا",
  darkPixels: "بكسلات غامقة",
  weatherPressure: "ضغط الطقس (تقدير)",
  weatherPressureNote: "درجة ضغط مرضي تقريبية من طقس اللحظة — مش تنبؤ بالإصابة.",
  aiSecondOpinion: "رأي ثانٍ بالذكاء الاصطناعي",
  aiAgrees: "الرأي الثاني بيتفق مع الموديل المحلي.",
  aiDisagrees: "الرأي الثاني مختلف — اعتبر النتيجة أقل تأكيدًا.",
  aiOffline: "الرأي الثاني غير متاح — بنعرض نتيجة الجهاز بس.",
  aiCaveat: "الذكاء الاصطناعي رأي زيادة. عمره ما بيحدّد جرعة ولا بيفك قفل الكيماويات.",
  screeningVerdict: "نتيجة فرز",
  notConfirmed: "غير مؤكّدة",
  uncalibratedNote: "دي قيمة تطابق بصري غير معايَرة، مش احتمال إن التشخيص صح.",
  hostCropNote: "إنت اللي اخترت الطماطم؛ موديل الصورة ما بيأكّدش المحصول لوحده.",
  certaintyLow: "تأكيد منخفض",
  certaintyMedium: "تأكيد متوسط",
  certaintyHigh: "تأكيد عالي",
  topCandidates: "أقرب الاحتمالات",
  matchScore: "تطابق بصري",
  phase1: "المرحلة ١ — التشخيص",
  phase1Sub: "شوفه",
  phase2: "المرحلة ٢ — حماية فورية",
  phase2Sub: "أوقفه",
  phase3: "المرحلة ٣ — أكّد",
  phase3Sub: "أكّده",
  phase4: "المرحلة ٤ — خيارات العلاج",
  phase4Sub: "عالجه",
  phase5: "المرحلة ٥ — تستاهل؟",
  phase5Sub: "احسبها",
  phase6: "المرحلة ٦ — خطة العمل",
  phase6Sub: "خطّط",
  symptomsLeaf: "على الورقة",
  symptomsFruit: "على الثمرة",
  symptomsStem: "على الساق",
  causeType: "السبب",
  lookalikes: "بيشبه (أكّد قبل العلاج)",
  todayCheck: "كشف النهاردة — بُص على ده بعينك",
  photoCropCard: "جودة الصورة وتأكيد المحصول",
  evidenceNote: "الدليل",
  protectNow: "حماية فورية — آمنة وبدون كيماويات، اعملها في أي مستوى ثقة",
  appliesAnyConfidence: "الخطوات دي ما بتضرّش الزرع وبتنفع حتى قبل تأكيد التشخيص.",
  scenarioHome: "جنينة بيت",
  scenarioField: "حقل مكشوف",
  scenarioGreenhouse: "صوبة",
  doThis: "اعمل ده",
  avoidThis: "بُعد عن ده",
  confirmIt: "أكّد — ارفع نسبة التأكيد قبل ما تصرف فلوس",
  confirmItIntro: "جاوب اللي تقدر عليه. كل إجابة بتحدّث مستوى التأكيد وطريقة العلاج المقترحة على طول.",
  addMorePhotos: "حِط صور أكتر: ورقة قريبة · تحت الورقة · النبات كله",
  treatmentOptions: "خيارات العلاج — بدون كيماويات الأول؛ الكيماويات وراء بوابة أمان",
  nonChemicalFirst: "ابدأ بالخيارات الآمنة. الأوضاع الكيميائية بتتفك بس لما شروط البوابة تتحقق.",
  chemicalGateLocked: "مقفول — بوابة الكيماويات",
  chemicalGateWhy: "ليه مقفول",
  apcVerify: "أكّد تسجيل لجنة المبيدات (محصول + آفة)",
  qcapResidue: "معمل متبقّيات QCAP",
  modeBenefit: "الفايدة",
  modeRisk: "الخطورة",
  modeCost: "شريحة التكلفة",
  modeApc: "حالة التسجيل",
  modeFarmSize: "أنسب حجم مزرعة",
  seeProtectNow: "اعمل الأول خطوات «الحماية الفورية» فوق — المرحلة دي قرار التصعيد مش تكرار.",
  worthIt: "تستاهل؟ — اقتصاديات الوضع المختار",
  referenceEstimate: "تقدير مرجعي",
  enterRealNumbers: "دخّل مساحتك الحقيقية + سعر محلي عشان نحسب أرقام مضبوطة.",
  perfarmSize: "حسب حجم المزرعة",
  comparisonTable: "مقارنة التكلفة والعائد",
  netBenefit: "صافي المكسب",
  worthLikely: "غالبًا تستاهل",
  worthAsk: "اسأل مهندس",
  worthMaybeNot: "ممكن ما تستاهلش",
  actionPlan: "خطة عملك",
  headline: "التوصية",
  today: "النهاردة",
  next37: "خلال ٣–٧ أيام",
  callExpertWhen: "اتصل بخبير لما",
  bestOverall: "الأحسن إجمالًا",
  cheapestSafe: "الأرخص الآمن",
  strongestAllowed: "الأقوى المسموح",
  avoidChoice: "اختيار تتجنّبه",
  safetyTitle: "التوصية والافتراضات والأمان",
  safetyRules: [
    "دي إشارة فرز، مش تشخيص معمل. أكّد قبل الرش.",
    "الثقة المنخفضة بتمنع كل نصايح الكيماويات؛ والوضع الافتراضي «أكّد الأول».",
    "الأوضاع الكيميائية الأقوى بتفضل مقفولة لحد ما التشخيص يتأكّد وكمان تسجيل لجنة المبيدات يتحقق للطماطم + الآفة دي.",
    "أي استخدام كيميائي محتاج الجرعة المصرية المسجّلة ومهمات الوقاية وفترة الأمان قبل الدخول وفترة ما قبل الحصاد — ولازم مهندس زراعي مصري يوافق الأول.",
    "أي قلق بخصوص سلامة الغذاء أو المتبقّيات يروح لمعمل QCAP.",
    "ما ترشّش أبدًا على نتيجة الذكاء الاصطناعي لوحدها، وما تزوّدش الرش.",
  ],
  assumptionsTitle: "الافتراضات",
  assistantTitle: "المساعد الزراعي (عربي / إنجليزي)",
  assistantHint: "مبني على دليل صورتك والطقس وإنتاجية CAPMAS وتسجيل لجنة المبيدات وقواعد العلاج.",
  assistantPlaceholder: "اسأل عن الطماطم بتاعتك…",
  quickQuestions: "أسئلة سريعة",
  egyptSources: "مصادر مصرية",
  provenanceTitle: "الأرقام جاية منين",
  downloads: "تنزيلات",
  savedCases: "الحالات المحفوظة",
  status_collecting: "بنجمع أدلة",
  status_needs_expert: "محتاج خبير",
  status_diagnosis: "التشخيص جاهز",
  status_economics: "الاقتصاديات جاهزة",
  status_report: "التقرير جاهز",
  comingLater: "جاي بعدين",
  notSure: "لسه مش متأكّد",
  notTomato: "مش ورقة طماطم؟",
};

export const STRINGS: Record<Lang, Strings> = { en: EN, ar: AR };
