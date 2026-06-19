export type Lang = "en" | "ar";

export interface Copy {
  brandTag: string;
  kicker: string;
  heroTitle: string;
  heroBody: string;
  analyzeImage: string;
  previewIdle: string;
  previewReady: string;
  previewHint: string;
  processingLocally: string;
  processing: string;
  realResults: string;
  runtime: string;
  processMemory: string;
  safetyReview: string;
  actionableAlerts: string;
  nextSteps: string;
  recommendedSteps: string;
  analysisSuite: string;
  confidence: string;
  matchScore: string;
  cropLabel: string;
  treatmentsTitle: string;
  showTreatments: string;
  tDose: string;
  tApply: string;
  tPhi: string;
  tHazard: string;
  tPrice: string;
  tWhy: string;
  readyEyebrow: string;
  readyTitle: string;
  readyBody: string;
  footer: string;
  aboutDisease: string;
  symptoms: string;
  management: string;
  diseaseDisclaimer: string;
  hide: string;
  openChat: string;
  closeChat: string;
  assistantEyebrow: string;
  assistantTitle: string;
  assistantReady: string;
  assistantOnline: string;
  assistantLocal: string;
  assistantOffline: string;
  assistantGreeting: string;
  assistantPlaceholder: string;
  assistantError: string;
  assistantThinking: string;
  assistantQuickQuestions: string[];
  you: string;
  assistantName: string;
}

export const copy: Record<Lang, Copy> = {
  en: {
    brandTag: "Egypt · Smart crop checkup",
    kicker: "Know your crop's disease from a photo",
    heroTitle: "Find out what's wrong with your crop from one photo.",
    heroBody:
      "Add one clear tomato leaf photo. The local model and an AI second opinion check it together and give one honest answer.",
    analyzeImage: "Check a photo",
    previewIdle: "Crop photo",
    previewReady: "Checked on your device",
    previewHint: "Add a clear photo of the leaf to start",
    processingLocally: "Checking your photo…",
    processing: "Check time",
    realResults: "Real analysis results",
    runtime: "Engine",
    processMemory: "Memory used",
    safetyReview: "Diagnosis check",
    actionableAlerts: "Confidence and safety",
    nextSteps: "Next step",
    recommendedSteps: "What to do now",
    analysisSuite: "Full checkup",
    confidence: "How sure",
    matchScore: "Visual match score (not diagnosis)",
    cropLabel: "Crop",
    treatmentsTitle: "Treatment options — best first",
    showTreatments: "Show treatment & products",
    tDose: "Dose",
    tApply: "How to spray",
    tPhi: "Wait before harvest",
    tHazard: "Hazard / care",
    tPrice: "Approx price",
    tWhy: "Why this rank",
    readyEyebrow: "Ready to check",
    readyTitle: "Add a clear photo of the crop leaf to start.",
    readyBody:
      "Your photo stays on this device. You'll get the likely disease, the simple signs to look for, and clear steps to protect the crop.",
    footer:
      "AgroVision Egypt · Results support, but do not replace, agronomist review.",
    aboutDisease: "Open diagnosis details",
    symptoms: "Signs to look for",
    management: "What to do",
    diseaseDisclaimer: "Show it to an agricultural engineer before spraying any treatment.",
    hide: "Hide",
    openChat: "Ask AI",
    closeChat: "Close",
    assistantEyebrow: "Farming assistant",
    assistantTitle: "Crop help in Arabic or English",
    assistantReady: "Ready",
    assistantOnline: "Online",
    assistantLocal: "Offline help",
    assistantOffline: "Offline",
    assistantGreeting: "Choose a case question to get treatment, irrigation, prevention, or greenhouse guidance.",
    assistantPlaceholder: "Ask about your crop…",
    assistantError: "Couldn't reach the assistant. Make sure the app's server is running.",
    assistantThinking: "Thinking…",
    assistantQuickQuestions: [
      "What is the safest tomato treatment plan?",
      "How do I tell Septoria from early blight on tomato?"
    ],
    you: "You",
    assistantName: "Assistant",
  },
  ar: {
    brandTag: "مصر · كشف ذكي على الزرع",
    kicker: "اعرف مرض زرعك من صورة",
    heroTitle: "اعرف زرعك تعبان من إيه من صورة واحدة.",
    heroBody:
      "صوّر الورقة صورة واضحة، وهتلاقي تشخيص سريع وبسيط مع خطوات عملية تحمي بيها محصولك.",
    analyzeImage: "افحص الصورة",
    previewIdle: "صورة الزرع",
    previewReady: "اتفحصت على جهازك",
    previewHint: "حِط صورة واضحة للورقة عشان نبدأ",
    processingLocally: "بنفحص الصورة…",
    processing: "وقت الفحص",
    realResults: "نتائج تحليل فعلية",
    runtime: "المحرك",
    processMemory: "الذاكرة المستخدمة",
    safetyReview: "فحص التشخيص",
    actionableAlerts: "الثقة والأمان",
    nextSteps: "الخطوة الجاية",
    recommendedSteps: "اعمل إيه دلوقتي",
    analysisSuite: "الفحص الكامل",
    confidence: "نسبة التأكد",
    matchScore: "درجة التطابق البصري (ليست تشخيصًا)",
    cropLabel: "المحصول",
    treatmentsTitle: "خيارات العلاج — الأحسن الأول",
    showTreatments: "اعرض العلاج والمنتجات",
    tDose: "الجرعة",
    tApply: "إزاي ترش",
    tPhi: "استنى قبل الحصاد",
    tHazard: "الخطورة / احترس",
    tPrice: "السعر التقريبي",
    tWhy: "ليه الترتيب ده",
    readyEyebrow: "جاهز للفحص",
    readyTitle: "حِط صورة واضحة لورقة الزرع عشان نبدأ.",
    readyBody:
      "الصورة بتفضل على جهازك. هتعرف المرض المتوقع، والعلامات اللي تبص عليها، وخطوات واضحة تحمي بيها الزرع.",
    footer:
      "AgroVision مصر · النتيجة بتساعد المهندس الزراعي وما بتغنيش عنه.",
    aboutDisease: "افتح تفاصيل التشخيص",
    symptoms: "العلامات اللي تبص عليها",
    management: "اعمل إيه",
    diseaseDisclaimer: "اعرضه على مهندس زراعي قبل ما ترش أي علاج.",
    hide: "إخفاء",
    openChat: "اسأل المساعد",
    closeChat: "اقفل",
    assistantEyebrow: "المساعد الزراعي",
    assistantTitle: "مساعدة في زرعك بالعربي أو الإنجليزي",
    assistantReady: "جاهز",
    assistantOnline: "متصل",
    assistantLocal: "مساعدة من غير نت",
    assistantOffline: "مش متصل",
    assistantGreeting: "اختار سؤال الحالة عشان تعرف العلاج أو الري أو الوقاية أو إدارة الصوبة.",
    assistantPlaceholder: "اسأل عن زرعك…",
    assistantError: "مش قادر أوصل للمساعد. اتأكد إن سيرفر التطبيق شغّال.",
    assistantThinking: "...بيفكّر",
    assistantQuickQuestions: [
      "ما هي خطة العلاج الأكثر أمانًا للطماطم؟",
      "أعرف منين الفرق بين السبتوريا واللفحة المبكرة في الطماطم؟"
    ],
    you: "إنت",
    assistantName: "المساعد",
  },
};
