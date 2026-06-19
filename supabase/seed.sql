insert into public.model_versions (name, version, checksum, metrics, limitations, approved)
values (
  'banana_cordana_vgg19_int8',
  '2026-06-14-local-evaluation',
  'd7b5d07361999ef1fc86488ef2ab2309b0dd61e589a8d230a71c4b90ce2740ba',
  '{"source_validation_accuracy": 0.9067, "included_smoke_accuracy": 1.0, "cpu_mean_inference_seconds": 0.095, "isolated_runtime_rss_mb": 105.1, "field_accuracy": null}',
  '["Experimental local evaluation only", "Source data contains duplicate and conflicting labels", "No field accuracy is claimed"]',
  false
) on conflict do nothing;

insert into public.knowledge_articles (slug, title_ar, title_en, body_ar, body_en, reviewed)
values
  (
    'low-confidence',
    'النتائج منخفضة الثقة',
    'Low-confidence results',
    'أعد التقاط الصورة في إضاءة جيدة واستشر مختصًا قبل أي علاج.',
    'Retake the image in good light and consult a specialist before treatment.',
    true
  ),
  (
    'water-stress',
    'التحقق من الإجهاد المائي',
    'Water stress verification',
    'قارن الصورة ببيانات الري والطقس وافحص المنطقة ميدانيًا.',
    'Compare imagery with irrigation and weather records, then inspect the zone in person.',
    true
  ),
  (
    'tomato-resistant-varieties',
    'أصناف طماطم مقاومة',
    'Resistant tomato varieties',
    'أمثلة: Iron Lady وMountain Merit F1 وMountain Magic وPlum Regal F1 وInvincible وSkyway F1. اختار حسب المرض المحلي وتأكد من رموز المقاومة على عبوة البذور.',
    'Examples: Iron Lady, Mountain Merit F1, Mountain Magic, Plum Regal F1, Invincible, and Skyway F1. Choose for the local disease and verify resistance codes on the seed label.',
    true
  ),
  (
    'tomato-greenhouse-protection',
    'حماية الطماطم في الصوبة',
    'Tomato greenhouse protection',
    'الصوبة المُدارة كويس تقلل المطر وتناثر المياه، لكن التهوية الضعيفة والتكثف قد يزودا الأمراض. استخدم ري بالتنقيط وتهوية وشبك حشرات وكشف دوري.',
    'A well-managed greenhouse reduces rain and splash, but poor ventilation and condensation can increase disease. Use drip irrigation, ventilation, insect screens, and regular scouting.',
    true
  )
on conflict do nothing;
