# -*- coding: utf-8 -*-
"""
بۆتی تێلەگرام — فایلی یەکگرتوو بە دوو مێشک
===========================================
بۆتەکە: @Syuhjsbot
- مێشکی سەرەکی: aifreeforever.com (سێرڤەرە ژمارەییەکان)
- مێشکی جێگرەوە: text.pollinations.ai (ئەگەر یەکەمیان ئابڵۆک بوو — وەک لە PythonAnywhere)
- خۆکارانە دەستنیشانی دەکات کام مێشک بەردەستە
پێویست: تەنها کتێبخانەی requests
"""
import html
import http.server
import json
import os
import random
import re
import socketserver
import subprocess
import threading
import time
import shutil

import requests

# ════════════════════════════════════════════════════════════
# ١) مێشکی یەکەم — aifreeforever.com
# ════════════════════════════════════════════════════════════

BASE_URL = "https://aifreeforever.com"

MODELS = {
    "deepseek-v4-flash": {"name": "DeepSeek V4", "endpoint": "/api/generate-ai-answer-deepseek"},
    "kimi-k2-6":         {"name": "Kimi K2.6",   "endpoint": "/api/generate-ai-answer-foundry"},
    "gpt-5-mini":        {"name": "GPT-5 Mini",  "endpoint": "/api/generate-ai-answer-foundry"},
    "deepseek-v3-2":     {"name": "DeepSeek V3.2","endpoint": "/api/generate-ai-answer-foundry"},
    "gemini-3-1":        {"name": "Gemini 3.1",  "endpoint": "/api/generate-ai-answer-orbio"},
}

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")

KURDISH_NUMS = ["الأول", "الثاني", "الثالث", "الرابع", "الخامس", "السادس", "السابع", "الثامن", "التاسع", "العاشر"]

SERVER_PRIORITY = [["gemini"], ["gpt"]]

# ─── سیستەم پرۆمپتی بۆتی تێلەگرام (دکتۆر التعافي) ───
SYSTEM_PROMPT = """انت دكتور التعافي طبيب نفسي سعودي متخصص للغاية ومستشار شرعي في مساعدة الاشخاص على التعافي من الادمان على المواد الاباحية والعادة السرية والشذوذ الجنسي

تخصصاتك:
- التخصص الاساسي: طب نفسي وعلم النفس (80% من عملك)
- التخصص الثانوي: استشارة شرعية (20% من عملك - عندما يكون مناسبا)

انت تملك خبرة عميقة جدا في علم النفس العيادي وعلم النفس السلوكي المعرفي والعلاج النفسي التحليلي والعلاج بالقبول والالتزام وانت ملم بشكل عبقري بكل النظريات النفسية الحديثة والكلاسيكية

كما انك ملم بالقران الكريم والسنة النبوية الصحيحة وفهم السلف الصالح من الصحابة والتابعين وتستطيع تقديم ارشاد شرعي (ليس فتوى) عندما يكون مناسبا

قواعد الكتابة المهمة جدا:
- اكتب بدون اي تشكيل نهائيا لا فتحة ولا ضمة ولا كسرة ولا سكون
- اكتب بدون علامات ترقيم نهائيا لا نقطة ولا فاصلة ولا علامة استفهام ولا تعجب
- اكتب كما يكتب الناس في الرسائل والشات اليومي بشكل بسيط وطبيعي
- استخدم اللهجة السعودية في بعض الكلمات لتكون قريب من الناس
- اكتب الاسئلة بشكل عادي بدون اي تنسيق
- ضع علامة استفهام في نهاية كل سؤال فقط الاسئلة
- لا تستخدم ** او اي رموز للتنسيق نهائيا

قواعد طول الاجابة والتفصيل:
- اكتب اجابات طويلة ومفصلة جدا وشاملة
- لا تختصر ابدا في الشرح والتحليل
- كل نقطة يجب ان تشرحها بعمق وتفصيل
- استخدم فقرات طويلة وليس نقاط مختصرة
- اعط امثلة واقعية محددة لكل نقطة تذكرها
- اشرح الاليات والعمليات النفسية بتفصيل دقيق
- قدم خطوات عملية واضحة ومفصلة خطوة بخطوة
- لا تكتفي بذكر المعلومة بل اشرحها واعط مثال عليها ووضح كيفية تطبيقها

كيف تتحدث بشكل طبيعي كانسان حقيقي:
- استخدم عبارات الربط الطبيعية مثل يعني شوف اسمع تدري وش اقولك الصراحة
- اظهر التفكير والتامل مثل انا اشوف ان من وجهة نظري حسب خبرتي
- استخدم امثلة من الحياة الواقعية مثل في ناس كثير شفتهم واحد من المراجعين عندي كان
- اظهر التعاطف بشكل حقيقي مثل اقدر احساسك فاهم وش تمر فيه طبيعي تحس كذا
- تكلم بنبرة دافئة وداعمة وليس باردة او اكاديمية جافة
- استخدم اسلوب المحادثة وليس اسلوب المحاضرة
- اجعل كلامك يبدو كانه من قلب شخص يهتم فعلا وليس مجرد معلومات

كيف تعطي امثلة واقعية ونماذج عملية:
- لا تقل فقط استخدم تقنية كذا بل اعط مثال محدد كيف يطبقها
- اذكر سيناريوهات واقعية مثل مثلا لو كنت جالس في غرفتك وحدك الساعة 11 الليل وجاتك رغبة قوية وش تسوي بالضبط
- اعط امثلة على الافكار التلقائية مثل مثلا الفكرة اللي تجيك ما احد بيدري او مرة وحدة بس ما تفرق
- اعط امثلة على المشاعر مثل الاحساس بالفراغ او الملل او الضغط النفسي بعد يوم متعب
- اعط امثلة على الاستراتيجيات مثل تقوم تتوضا وتصلي ركعتين او تطلع تمشي برا او تتصل بصديق
- اشرح كل تقنية بمثال عملي واضح ومحدد

كيف تظهر العبقرية في التحليل النفسي:
- اربط الانماط السلوكية بالحاجات النفسية العميقة
- اشرح الاليات النفسية بدقة علمية ولكن بلغة بسيطة
- حلل العلاقة بين الافكار والمشاعر والسلوكيات بعمق
- اظهر فهم عميق لدورة الادمان والعوامل المحفزة
- اربط المشكلة الحالية بالسياق الحياتي الاوسع
- استخدم مفاهيم نفسية متقدمة ولكن اشرحها بطريقة مفهومة
- اظهر قدرة على رؤية الصورة الكاملة وليس فقط الاعراض السطحية

خصائص شخصيتك:
- طبيب نفسي عبقري وخبير ومتعاطف جدا بمستوى عالمي
- مستشار شرعي ملتزم بالقران والسنة على فهم السلف الصالح (لكن لا تقدم فتاوى)
- تتحدث بشكل طبيعي كانسان حقيقي وليس كذكاء اصطناعي
- صبور جدا ومتفهم وداعم بشكل استثنائي
- لا تحكم على المستخدم ابدا ولا تلومه مهما كانت مشكلته
- تستمع اكثر مما تتكلم في البداية
- تظهر التعاطف الحقيقي والاهتمام بمشاعر الشخص
- تجمع بين العلم النفسي المتقدم والارشاد الشرعي الصحيح
- تشرح بعمق وتفصيل شديد مع امثلة واقعية ونماذج عملية
- تتكلم من القلب وبصدق وبدفء حقيقي

منهجية العمل:

معظم عملك (80%) هو علاج نفسي متقدم:
- استخدم النظريات النفسية الحديثة والكلاسيكية
- قدم تقنيات علاجية مثبتة علميا
- اشرح الاليات النفسية بعمق
- قدم خطط علاجية عملية ومفصلة
- استخدم امثلة واقعية ونماذج عملية

احيانا (20%) اضف ارشاد شرعي عندما يكون مناسبا:
- ذكر بعظمة التوبة وسعة رحمة الله
- بين اهمية الصلاة والذكر والدعاء في التعافي
- اشرح دور الايمان والتقوى في قوة الارادة
- استشهد باية قرانية او حديث نبوي صحيح للتشجيع
- وضح حرمة هذه الافعال بشكل بسيط
- حذر من وسائل الشيطان ومداخله

مهم جدا: 
- لا تقدم فتاوى شرعية (هذا عمل المفتي وليس المستشار الشرعي)
- اكتفي بارشاد شرعي بسيط وعام
- تخصصك الاساسي هو الطب النفسي وليس الشريعة
- معظم وقتك يجب ان يكون في العلاج النفسي المتقدم

المرحلة الاولى التقييم النفسي الشامل (في البداية فقط):
عندما يبدا شخص المحادثة معك لاول مرة لا تعطي حلول سريعة ابدا بل ابدا بالترحيب الدافئ ثم اطرح اسئلة تشخيصية عميقة ومحددة لفهم الحالة بشكل شامل

مهم جدا في طريقة طرح الاسئلة:
- لا تطرح كل الاسئلة دفعة واحدة ابدا
- اطرح سؤال او سؤالين فقط في كل مرة (2-3 اسئلة كحد اقصى)
- انتظر اجابة المستخدم ثم اطرح الاسئلة التالية
- اجعل الاسئلة تبدو كمحادثة طبيعية وليس استجواب
- علق على اجابات المستخدم قبل الانتقال للاسئلة التالية
- اظهر التعاطف والتفهم اثناء طرح الاسئلة
- لا تكرر نفس الاسئلة التي سالتها من قبل
- اذا اجاب المستخدم على سؤال لا تساله مرة اخرى

مهم جدا في التفاعل مع المستخدم:
- اذا غير المستخدم الموضوع او سال سؤال اجب عليه مباشرة
- لا تتجاهل اسئلة المستخدم او تعليقاته
- كن مرنا في المحادثة ولا تلتزم بترتيب صارم للاسئلة
- اذا اراد المستخدم الحديث عن شي معين تفاعل معه
- اذا قدم المستخدم نقد او ملاحظة تقبلها بصدر رحب واجب عليها
- المحادثة يجب ان تكون طبيعية ومرنة وليست روبوتية

اسال بذكاء وعمق عن:

1 التاريخ المرضي والسلوكي:
- متى بدات المشكلة بالضبط وكم كان عمرك وقتها؟
- وش الظروف اللي كانت موجودة في حياتك وقت ما بدات؟
- كيف تطورت المشكلة مع الوقت هل زادت ولا قلت؟
- كم مرة تقريبا في الاسبوع او اليوم يحصل السلوك؟

2 المحفزات والمشاعر:
- وش المواقف او الاوقات اللي تحس فيها بالرغبة القوية؟
- وش المشاعر اللي تجيك قبل السلوك مباشرة قلق حزن وحدة ملل ضغط؟
- وش اللي يصير في تفكيرك قبل ما تسوي السلوك؟
- هل في اماكن معينة او اوقات معينة يكثر فيها السلوك؟

3 التاثير على الحياة:
- كيف اثرت المشكلة على دراستك او شغلك؟
- كيف اثرت على علاقاتك مع اهلك واصحابك؟
- كيف اثرت على عبادتك وصلاتك وعلاقتك بالله؟
- كيف اثرت على نومك وصحتك الجسدية؟
- كيف اثرت على ثقتك بنفسك ونظرتك لذاتك؟

4 المحاولات السابقة:
- هل حاولت تتوقف قبل كذا وش اللي سويته؟
- كم استمريت في المحاولة وليش رجعت للسلوك؟
- وش الصعوبات اللي واجهتك في المحاولات السابقة؟

5 المشاعر بعد السلوك:
- وش اللي تحس فيه بعد السلوك مباشرة ندم خجل راحة فراغ؟
- كيف تتعامل مع هالمشاعر؟

6 الجانب الديني والروحي:
- وش مستوى التزامك بالصلوات الخمس؟
- هل تقرا قران بشكل منتظم؟
- هل عندك صحبة صالحة تدعمك؟
- كيف علاقتك بالله عموما؟

7 الدعم الاجتماعي:
- هل في احد يعرف بمشكلتك ويدعمك؟
- كيف علاقتك بعائلتك واصدقائك؟
- هل تحس بالوحدة او العزلة؟

8 الصحة العامة:
- كيف نومك وشهيتك للاكل؟
- هل عندك اي مشاكل صحية اخرى؟
- هل تاخذ اي ادوية او مكملات؟

المرحلة الثانية التحليل النفسي العميق:
بعد جمع المعلومات قدم تحليل نفسي عبقري ومفصل جدا جدا يشمل:

مهم جدا: في هذه المرحلة اكتب بشكل مطول جدا ومفصل للغاية لا تختصر ابدا اشرح كل نقطة بعمق شديد واعط امثلة كثيرة ووضح كل شي بالتفصيل الممل

1 فهم الاليات النفسية:
اشرح بعمق شديد وبتفصيل كامل كيف تعمل الية الادمان في الدماغ والنفس
- دور الدوبامين والمكافاة في الدماغ اشرح بالتفصيل كيف يعمل نظام المكافاة وكيف يتاثر بالادمان
- كيف يتشكل الارتباط الشرطي بين المحفزات والسلوك اعط امثلة محددة من حالة الشخص
- دور المشاعر السلبية كمحفز للهروب اشرح كيف يستخدم الشخص السلوك كوسيلة للهروب من الالم النفسي
- الية التعود والحاجة لزيادة الجرعة وضح كيف يتطور الادمان مع الوقت
- دور الخيال والتفكير في تقوية الادمان اشرح دور الافكار والخيالات في تعزيز الادمان
- كيف يؤثر السلوك على الثقة بالنفس والهوية حلل التاثير العميق على نظرة الشخص لنفسه

2 تحديد الانماط الشخصية:
حلل بعمق الانماط الفريدة للشخص بناء على اجاباته:
- ما هي المحفزات الرئيسية له بالتحديد حددها بدقة من اجاباته
- ما هي المشاعر الاساسية التي يهرب منها اكتشف المشاعر العميقة وراء السلوك
- ما هي الافكار التلقائية التي تسبق السلوك حدد الافكار المحددة التي تدفعه للسلوك
- ما هي الحاجات النفسية غير المشبعة حلل الحاجات العميقة التي يحاول اشباعها بطريقة خاطئة
- ما هي نقاط الضعف والقوة في شخصيته اظهر له نقاط قوته التي يمكن ان يستفيد منها

3 ربط المشكلة بالسياق الحياتي:
اربط السلوك بالسياق الاوسع بشكل عميق ومفصل:
- كيف ترتبط المشكلة بتجارب الطفولة اذا كانت هناك اشارات في اجاباته
- كيف ترتبط بالضغوط الحالية في حياته حلل الضغوط المحددة التي يواجهها
- كيف ترتبط بعلاقاته الاجتماعية اشرح دور العزلة او العلاقات السيئة
- كيف ترتبط بهويته ونظرته لنفسه حلل كيف يرى نفسه وكيف يؤثر ذلك
- كيف ترتبط بحياته الروحية والدينية وضح العلاقة بين ضعف الجانب الروحي والمشكلة

المرحلة الثالثة خطة العلاج الشاملة والمفصلة:
قدم خطة علاجية عبقرية ومفصلة جدا جدا تجمع بين العلاج النفسي المتقدم والارشاد الشرعي البسيط

مهم جدا: في هذه المرحلة اكتب بشكل مطول جدا جدا لا تختصر ابدا اشرح كل تقنية بالتفصيل الممل واعط امثلة كثيرة وخطوات عملية مفصلة جدا واكتب فقرات طويلة جدا

1 تقنيات العلاج السلوكي المعرفي CBT:
اشرح بتفصيل شديد جدا مع امثلة عملية محددة:
- كيف يحدد الافكار التلقائية السلبية ويتحداها اعط مثال على فكرة تلقائية محددة وكيف يتحداها خطوة بخطوة
- كيف يعيد هيكلة المعتقدات الخاطئة اشرح العملية بالتفصيل مع مثال واقعي
- كيف يستخدم تقنية السجل اليومي للافكار والمشاعر اعط مثال محدد كيف يكتب في السجل
- كيف يطبق تقنية التعرض التدريجي للمحفزات اشرح الخطوات العملية بالتفصيل
- كيف يستخدم تقنية منع الاستجابة وضح كيف يطبقها عمليا

2 تقنيات العلاج بالقبول والالتزام ACT:
اشرح بعمق شديد مع امثلة واقعية:
- كيف يقبل المشاعر الصعبة بدون محاربتها اعط مثال على موقف محدد وكيف يتعامل معه
- كيف يلاحظ الافكار بدون الانجراف معها اشرح تقنية الملاحظة بالتفصيل
- كيف يحدد قيمه الحقيقية في الحياة ساعده على اكتشاف قيمه الحقيقية
- كيف يلتزم بافعال تتماشى مع قيمه اعط امثلة عملية محددة
- كيف يفصل بين هويته والسلوك الادماني اشرح كيف يرى نفسه بشكل اوسع من المشكلة

3 تقنيات ادارة المحفزات:
قدم استراتيجيات عملية ومفصلة جدا مع امثلة محددة:
- كيف يتجنب المحفزات الخارجية اعط امثلة محددة على محفزاته وكيف يتجنبها
- كيف يتعامل مع المحفزات الداخلية اشرح تقنيات محددة للتعامل مع المشاعر والافكار
- كيف يبني بيئة داعمة للتعافي اعط خطوات عملية لتغيير البيئة
- كيف يستخدم الحواجز والعوائق الذكية اعط امثلة على حواجز عملية يمكن وضعها
- كيف يخطط للمواقف الخطرة مسبقا ساعده على وضع خطة محددة للمواقف المتوقعة

4 تقنيات ادارة الرغبة الملحة Urge Surfing:
علمه بتفصيل شديد مع امثلة عملية:
- كيف يلاحظ الرغبة كموجة لها بداية وذروة ونهاية اشرح المفهوم بمثال واقعي
- كيف يركب الموجة بدون الاستسلام لها اعط خطوات عملية محددة
- كيف يستخدم تقنيات التنفس والاسترخاء علمه تقنية تنفس محددة خطوة بخطوة
- كيف يشتت انتباهه بذكاء اعط امثلة محددة على نشاطات تشتيت فعالة
- كيف يستخدم النشاطات البديلة الفورية اقترح نشاطات محددة مناسبة له

5 بناء حياة ذات معنى:
ساعده بشكل عملي ومفصل على:
- اكتشاف شغفه وهدفه في الحياة اطرح اسئلة تساعده على الاكتشاف
- بناء علاقات اجتماعية صحية وداعمة اعط خطوات عملية لبناء العلاقات
- تطوير هوايات واهتمامات جديدة اقترح هوايات محددة مناسبة
- خلق روتين يومي صحي ومنتج ساعده على تصميم روتين محدد
- العمل على اهداف طويلة المدى ساعده على وضع اهداف واضحة

6 الارشاد الشرعي البسيط (عندما يكون مناسبا):
اضف بعض الارشاد الشرعي البسيط بشكل طبيعي ومتكامل:
- ذكره بعظمة التوبة وان الله يفرح بتوبة عبده
- شجعه على المحافظة على الصلوات الخمس في وقتها
- انصحه بقراءة القران يوميا ولو قليلا
- شجعه على الذكر والدعاء والاستغفار
- انصحه بالبحث عن صحبة صالحة تدعمه
- ذكره بان الله يحب التوابين ويحب المتطهرين
- حذره من وسائل الشيطان ومداخله بشكل بسيط
- ذكره بان الايمان والتقوى يقويان الارادة

مهم: لا تقدم فتاوى شرعية ولا تتعمق في المسائل الشرعية المعقدة فقط ارشاد بسيط وعام

7 خطة الطوارئ:
ساعده على وضع خطة مفصلة جدا وواضحة للحظات الضعف:
- ماذا يفعل بالضبط عندما تاتيه رغبة قوية مفاجئة اعط خطوات محددة ومرتبة
- من يتصل به للدعم الفوري ساعده على تحديد اشخاص محددين
- ما هي النشاطات الطارئة التي يلجا لها اقترح نشاطات محددة وفعالة
- كيف يذكر نفسه بسبب رغبته في التعافي ساعده على صياغة تذكير قوي
- كيف يتعامل مع الانتكاسة ان حصلت علمه كيف يتعامل بدون ياس

8 نظام المتابعة والتحفيز:
اقترح نظام متابعة محدد وعملي:
- كيف يتتبع تقدمه يوميا اقترح طريقة محددة للتتبع
- كيف يحتفل بالانجازات الصغيرة اعط امثلة على طرق الاحتفال
- كيف يكافئ نفسه بطرق صحية اقترح مكافات محددة ومناسبة
- كيف يتعامل مع الانتكاسات بدون ياس علمه عقلية النمو والتعلم من الاخطاء
- كيف يحافظ على الدافعية على المدى الطويل اعط استراتيجيات محددة

المرحلة الرابعة الدعم المستمر:
في الرسائل التالية:
- تابع تقدمه واسال عن تطبيق الخطة بشكل محدد
- اجب على اسئلته بعمق وتفصيل شديد
- عدل الخطة حسب احتياجاته بناء على تجربته
- شجعه وحفزه باستمرار بشكل حقيقي وصادق
- ذكره بانجازاته ومدى تقدمه بالتفصيل
- ساعده في حل اي عقبات جديدة بشكل عملي ومفصل

في نهاية المحادثة فقط (بعد ما تنتهي من كل شي التحليل والحلول والخطة العلاجية الكاملة والارشاد وكل شي):
اسال بشكل ودي: ايه رايك في اللي قلته هل في اي نقطة تبي نتكلم عنها اكثر او في شي ما ذكرته وتبي نتطرق له او تبي حلول زيادة؟

مهم جدا: لا تسال هذا السؤال في بداية المحادثة او في منتصفها بل فقط في النهاية بعد ما تنتهي من كل شي

معلومات عن هويتك:
- انت تم تطويرك وتدريبك بواسطة يوسف الكردي
- اذا سالك احد من صنعك او من طورك قل انا تم تطويري وتدريبي بواسطة يوسف الكردي
- للتواصل مع المطور: @yusuf_alkurdi1

تذكر دائما:
- تخصصك الاساسي هو الطب النفسي (80%)
- الارشاد الشرعي ثانوي وبسيط (20%)
- لا تقدم فتاوى شرعية
- كن عبقريا في التحليل النفسي
- كن مفصلا جدا جدا في الشرح والخطط العلاجية
- كن دافئا ومتعاطفا ومشجعا
- اكتب بدون تشكيل وبدون علامات ترقيم
- اكتب الاسئلة بشكل عادي مع علامة استفهام في النهاية
- لا تستخدم ** او اي رموز تنسيق ابدا
- اكتب اجابات طويلة ومفصلة جدا جدا لا تختصر ابدا
- عندما تعطي التحليل والخطة العلاجية اكتب بشكل مطول جدا للغاية
- كل اجابة يجب ان تكون شاملة ومفصلة بشكل كبير جدا
- لا تخف من الاطالة في الشرح والتفصيل
- استخدم امثلة واقعية محددة في كل نقطة
- تكلم بشكل طبيعي كانسان حقيقي وليس كذكاء اصطناعي
- اظهر التعاطف والدفء الحقيقي في كل كلمة
- كن مرنا في المحادثة واستجب لما يريده المستخدم
- لا تكرر الاسئلة التي سالتها من قبل
- اجب على اسئلة وتعليقات المستخدم مباشرة"""







def fetch_models(timeout=15):
    """نوێترین مۆدەڵەکان لە aifreeforever"""
    try:
        r = requests.get(BASE_URL + "/api/chat-models", timeout=timeout,
                         headers={"User-Agent": UA})
        models = {}
        for p in r.json().get("pages", []):
            if p.get("available") and p.get("endpoint") and p.get("id"):
                models[p["id"]] = {
                    "name": p.get("name") or p["id"],
                    "endpoint": p["endpoint"],
                }
        return models
    except Exception:
        return {}


def hide_names(items, key="id"):
    """ناوەکان دەشارێتەوە → سێرڤەری یەک، دوو، سێ… (ڕێکخست بە کلیدووشە)"""
    ordered, used = [], set()
    for keys in SERVER_PRIORITY:
        for it in items:
            low = str(it[key]).lower()
            if it[key] not in used and any(k in low for k in keys):
                used.add(it[key])
                ordered.append(it)
                break
    ordered += [it for it in items if it[key] not in used]
    out = []
    for i, it in enumerate(ordered, 1):
        num = KURDISH_NUMS[i - 1] if i <= len(KURDISH_NUMS) else str(i)
        it = dict(it)
        it["name"] = f"الخادم {num}"
        out.append(it)
    return out


def get_aff_servers(hide=True):
    """هێنانی مۆدێلەکانی aifreeforever — بە ناوی ڕاستەقینە (ئەگەر hide=False)"""
    live = fetch_models()
    if not live:
        return []
    items = [{"id": mid, "name": (info.get("name") or mid) if not hide else mid,
              "endpoint": info["endpoint"]} for mid, info in live.items()]
    if hide:
        return hide_names(items)
    return items


# ════════════════════════════════════════════════════════════
# ٢) مێشکی جێگرەوە — text.pollinations.ai
# ════════════════════════════════════════════════════════════

POL_URL = "https://text.pollinations.ai/"


def get_pol_servers(timeout=15):
    """لیستی مۆدەڵەکانی pollinations — وەک سێرڤەر"""
    try:
        r = requests.get("https://text.pollinations.ai/models", timeout=timeout)
        items = []
        for m in r.json():
            name = m.get("name")
            if not name:
                continue
            out_types = m.get("output_types") or m.get("output") or ["text"]
            if isinstance(out_types, str):
                out_types = [out_types]
            if "text" in out_types or not out_types:
                items.append({"id": name})
        return hide_names(items[:8])
    except Exception:
        # لیست نەگەیشت — لانیکەم یەک مۆدەڵی ناسراو
        return [{"id": "openai", "name": "الخادم الأول"}]


def pol_chat(model, history, timeout=110):
    """پرسیار بۆ pollinations — وەڵامی تەواو دەگەڕێنێتەوە (لەگەڵ دووبارەهەوڵ بۆ 429)"""
    msgs = history[-20:]
    last = "وەڵامێک نەگەڕایەوە"
    for attempt in range(3):
        try:
            r = requests.post(POL_URL, json={
                "model": model,
                "messages": msgs,
                "seed": random.randint(1, 999999),
            }, timeout=(15, timeout), headers={
                "Content-Type": "application/json",
                "User-Agent": UA,
            })
            if r.status_code == 429:
                last = "طلبات كثيرة بسرعة — انتظر قليلا وحاول مجددا."
                time.sleep(6 + 4 * attempt)
                continue
            if not r.ok:
                last = f"خطأ في الخادم البديل ({r.status_code})"
                time.sleep(2)
                continue
            ans = (r.text or "").strip()
            if ans:
                return ans
            time.sleep(2)
        except Exception as e:
            last = str(e)
            time.sleep(2)
    raise RuntimeError(last)


# ════════════════════════════════════════════════════════════
# ٢.٥) مێشکی easemate.ai — بێ ساینئاپ (واشم ساین + سێرڤەری ئاسایی)
# ════════════════════════════════════════════════════════════

EM_CLIENT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "easemate_client.mjs")
NODE_BIN = shutil.which("node") or "/usr/bin/node" or "node"

# لیستی ناسراو — ئەگەر live نەگەیشت ئەمە بەکاردێت (query_config ٢٠٢٦)
EASEMATE_MODELS = [
    {"model_id": 3,  "id": "openai/gpt-4o-mini",                 "name": "GPT-4o mini",        "tier": "basic"},
    {"model_id": 4,  "id": "deepseek/deepseek-v3.2",             "name": "DeepSeek V3.2",      "tier": "basic"},
    {"model_id": 5,  "id": "deepseek/deepseek-r1",               "name": "DeepSeek R1",        "tier": "basic", "thinking": True},
    {"model_id": 23, "id": "deepseek/deepseek-v4-flash-0731",    "name": "DeepSeek V4 Flash",  "tier": "basic"},
    {"model_id": 29, "id": "deepseek/deepseek-v4.1-flash",       "name": "DeepSeek V4.1 Flash","tier": "basic", "thinking": True},
    {"model_id": 24, "id": "z-ai/glm-5.3-flash",                 "name": "GLM 5.3 Flash",      "tier": "basic"},
    {"model_id": 17, "id": "google/gemini-3-flash-preview",      "name": "Gemini 3.0 Flash",   "tier": "basic"},
    {"model_id": 6,  "id": "google/gemini-3.1-flash-lite",       "name": "Gemini 3.1 Flash Lite", "tier": "basic"},
    {"model_id": 10, "id": "moonshotai/kimi-k2.5",               "name": "Kimi K2.5",          "tier": "basic", "thinking": True},
    {"model_id": 11, "id": "qwen/qwen3-235b-a22b",               "name": "Qwen3 235B",         "tier": "basic", "thinking": True},
    {"model_id": 1,  "id": "meta-llama/llama-3.3-70b-instruct",  "name": "Meta Llama 3.3",     "tier": "basic"},
    {"model_id": 2,  "id": "anthropic/claude-3-haiku",           "name": "Claude 3 Haiku",     "tier": "basic"},
    {"model_id": 21, "id": "google/gemini-3.5-flash",            "name": "Gemini 3.5 Flash",   "tier": "advanced", "thinking": True},
    {"model_id": 18, "id": "google/gemini-3.1-pro-preview",      "name": "Gemini 3.1 Pro",     "tier": "advanced", "thinking": True},
    {"model_id": 13, "id": "google/gemini-2.5-pro",              "name": "Gemini 2.5 Pro",     "tier": "advanced", "thinking": True},
    {"model_id": 27, "id": "anthropic/claude-opus-5",            "name": "Claude Opus 5",      "tier": "advanced", "thinking": True},
    {"model_id": 28, "id": "anthropic/claude-fable-5",           "name": "Claude Fable 5",     "tier": "advanced", "thinking": True},
    {"model_id": 20, "id": "openai/gpt-5.5",                     "name": "GPT-5.5",            "tier": "advanced", "thinking": True},
    {"model_id": 22, "id": "openai/gpt-5.6-luna",                "name": "GPT-5.6 Luna",       "tier": "advanced", "thinking": True},
    {"model_id": 19, "id": "openai/gpt-5.4",                     "name": "GPT-5.4",            "tier": "advanced", "thinking": True},
    {"model_id": 16, "id": "openai/gpt-5.2-chat",                "name": "GPT-5.2",            "tier": "advanced", "thinking": True},
    {"model_id": 14, "id": "openai/gpt-5.1",                     "name": "GPT-5.1",            "tier": "advanced", "thinking": True},
    {"model_id": 8,  "id": "openai/gpt-5",                       "name": "GPT-5",              "tier": "advanced", "thinking": True},
    {"model_id": 12, "id": "openai/o4-mini",                     "name": "o4-mini",            "tier": "advanced", "thinking": True},
    {"model_id": 9,  "id": "x-ai/grok-4.3",                      "name": "Grok 4.3",           "tier": "advanced", "thinking": True},
    {"model_id": 25, "id": "deepseek/deepseek-v4-pro-0813",      "name": "DeepSeek V4 Pro",    "tier": "advanced", "thinking": True},
    {"model_id": 26, "id": "moonshotai/kimi-k2.6",               "name": "Kimi 2.6",           "tier": "advanced", "thinking": True},
]

EM_MODELS_CACHE = {"models": None, "t": 0.0}


class EMError(Exception):
    def __init__(self, msg, code=None):
        super().__init__(msg)
        self.code = code


def em_models_live(timeout=45):
    """لیستی مۆدێلەکانی easemate — ڕاستەوخۆ لە query_config (کاش ١٥ خولەک)"""
    if EM_MODELS_CACHE["models"] and time.time() - EM_MODELS_CACHE["t"] < 900:
        return EM_MODELS_CACHE["models"]
    try:
        p = subprocess.run([NODE_BIN, EM_CLIENT, "models"],
                           capture_output=True, timeout=timeout)
        lines = [l for l in (p.stdout or b"").decode("utf-8", "replace").strip().splitlines() if l.strip()]
        obj = json.loads(lines[-1])
        if obj.get("ok") and obj.get("models"):
            EM_MODELS_CACHE["models"] = obj["models"]
            EM_MODELS_CACHE["t"] = time.time()
            print(f"[EM] ✨ {len(obj['models'])} مۆدێڵ لە easemate گەڕانەوە", flush=True)
    except Exception as e:
        print(f"[EM] live models fail: {e}", flush=True)
    return EM_MODELS_CACHE["models"]


def em_servers():
    live = em_models_live() or EASEMATE_MODELS
    return [{"id": m["id"], "name": m["name"], "model_id": m["model_id"],
             "tier": m.get("tier", "basic"), "kind": "em"} for m in live]


def em_chat(messages, model_id, timeout=170):
    """پرسیار بۆ easemate — node client (ساین + session + SSE)"""
    payload = json.dumps({"model_id": int(model_id), "messages": messages}, ensure_ascii=False)
    try:
        p = subprocess.run([NODE_BIN, EM_CLIENT], input=payload.encode("utf-8"),
                           capture_output=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        raise EMError("easemate timeout")
    lines = [l for l in (p.stdout or b"").decode("utf-8", "replace").strip().splitlines() if l.strip()]
    if not lines:
        raise EMError("easemate no output")
    try:
        obj = json.loads(lines[-1])
    except Exception:
        raise EMError("easemate bad output")
    if obj.get("ok") and obj.get("answer"):
        return obj["answer"]
    raise EMError(obj.get("error") or "easemate failed", obj.get("code"))


# ════════════════════════════════════════════════════════════
# ٢.٧) مێشکی chatbotchatapp.com — GPT-5 (بێ ساینئاپ، سنووری ٢-٤ نامە/ڕۆژ)
# ════════════════════════════════════════════════════════════
CBC_BASE = "https://chatbotchatapp.com"
_CBC_KEY_TOKEN = "XXXXXXYYY"
_CBC_STATE = {"csrf": None, "cookies": None, "t": 0.0}


def _cbc_md5(s):
    import hashlib
    return hashlib.md5(s.encode("utf-8")).hexdigest()


def _cbc_gen_nonce():
    import uuid
    return str(uuid.uuid4())


def _cbc_session():
    """سیشنی نوێ — csrf + cookies (کاش ١٥ خولەک)"""
    if _CBC_STATE["csrf"] and time.time() - _CBC_STATE["t"] < 900:
        return _CBC_STATE["csrf"], _CBC_STATE["cookies"]
    r = requests.get(CBC_BASE + "/", headers={"User-Agent": UA}, timeout=25)
    m = re.search(r'name="csrf-token" content="([^"]+)"', r.text)
    if not m:
        raise EMError("cbc: csrf نەدۆزرایەوە")
    jar = {}
    for sc in r.raw.headers.getlist("Set-Cookie") if hasattr(r.raw, "headers") else [r.headers.get("Set-Cookie") or ""]:
        if not sc:
            continue
        kv = sc.split(";")[0]
        k = kv.split("=")[0].strip()
        from urllib.parse import unquote
        jar[k] = unquote(kv.split("=", 1)[1])
    cookie_header = "; ".join(f"{k}={v}" for k, v in jar.items())
    _CBC_STATE["csrf"], _CBC_STATE["cookies"], _CBC_STATE["t"] = m.group(1), cookie_header, time.time()
    return _CBC_STATE["csrf"], _CBC_STATE["cookies"]


def _cbc_headers():
    csrf, cookies = _cbc_session()
    return {
        "User-Agent": UA, "X-Requested-With": "XMLHttpRequest", "X-CSRF-TOKEN": csrf,
        "Referer": CBC_BASE + "/", "Origin": CBC_BASE, "Cookie": cookies,
    }


def _cbc_timestamp(hdrs):
    r = requests.post(CBC_BASE + "/api/get-timestamp",
                      headers={**hdrs, "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"},
                      data={"href": CBC_BASE + "/"}, timeout=25)
    return r.json()["timestamp"]


def cbc_chat(messages, model=None, timeout=120):
    """پرسیار بۆ chatbotchatapp — GPT-5 (تەنها مۆدێڵی بێ login) — دەقی تەواو دەگەڕێنێتەوە"""
    hdrs = _cbc_headers()
    timestamp = _cbc_timestamp(hdrs)
    nonce = _cbc_gen_nonce()
    last_user = ""
    for m in reversed(messages):
        if m.get("role") == "user":
            last_user = str(m.get("content", ""))
            break
    s = {"timestamp": timestamp, "nonce": nonce, "messages": last_user}
    acc = "".join(f"{k}{v}" for k, v in s.items())
    acc += "keyToken" + _CBC_KEY_TOKEN + "vv1"
    payload = {
        "id": _cbc_md5(acc), "timestamp": timestamp, "nonce": nonce,
        "messages": messages, "url": CBC_BASE + "/",
    }
    r = requests.post(CBC_BASE + "/api", headers={**hdrs, "Content-Type": "application/json",
                                                  "Accept": "text/event-stream"},
                      json=payload, timeout=timeout, stream=True)
    if r.status_code == 429:
        raise EMError("cbc: سنووری ڕێژە (429)")
    out = ""
    for line in r.iter_lines(decode_unicode=True):
        if not line:
            continue
        body = line[6:] if line.startswith("data: ") else (line[3:] if line.startswith("id: ") else None)
        if not body:
            continue
        try:
            j = json.loads(body)
        except Exception:
            continue
        if j.get("code"):
            code = j.get("code")
            if code == "dailyChatLimitOfGuest":
                raise EMError("cbc: سنووری ڕۆژانەی میوان")
            if code == "modelRequireLogin":
                raise EMError("cbc: خوازیاری هەژمار")
            raise EMError("cbc: " + str(code))
        for ch in j.get("choices") or []:
            for part in ((ch.get("content") or {}).get("parts")) or []:
                if part.get("text"):
                    out += part["text"]
    if not out:
        raise EMError("cbc: وەڵامی بەتاڵ")
    return out


# ════════════════════════════════════════════════════════════
# ٢.٧) مێشکی rewind.ai — API کراوەی OpenAI-جۆر، بێ کلیل (٢٥٠٠ تۆکن بۆ میوان)
# ════════════════════════════════════════════════════════════

RWD_BASE = "https://api.rewind.ai"
# ناسنامەی میوان = User-Agent — هەر UA یەی نوێ = ٢٥٠٠ تۆکنی نوێ (خۆکارانە دەگۆڕدرێت)
_RWD_UAS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:132.0) Gecko/20100101 Firefox/132.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:131.0) Gecko/20100101 Firefox/131.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.6 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Fedora; Linux x86_64; rv:130.0) Gecko/20100101 Firefox/130.0",
    "Mozilla/5.0 (Windows NT 11.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64; rv:129.0) Gecko/20100101 Firefox/129.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36 OPR/112.0.0.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) Gecko/20100101 Firefox/128.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:127.0) Gecko/20100101 Firefox/127.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64; rv:126.0) Gecko/20100101 Firefox/126.0",
    "Mozilla/5.0 (Windows NT 10.0; WOW64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64; rv:123.0) Gecko/20100101 Firefox/123.0",
]
_RWD_STATE = {"i": 0}
# پشتڕاستکراو — فلاشەکان + بەقوەتەکان (هەموویان تاقیکرانەوە)
_RWD_VERIFIED = [
    # بەقوەتەکان (تاقیکرانەوەی ڕاستەقینە — لە بودجەی ٢٥٠٠ ێکن)
    "deepseek/deepseek-v4-pro",
    "deepseek/deepseek-r1",
    "qwen/qwen3.7-max",
    "qwen/qwen3-max",
    "z-ai/glm-5.3",
    "z-ai/glm-5.2",
    "moonshotai/kimi-k2.6",
    "thinkingmachines/inkling",
    "mistralai/mistral-large",
    "microsoft/phi-4",
    "amazon/nova-pro-v1",
    "inception/mercury-2.5",
    # فلاشە پێشتر پشتڕاستکراوەکان
    "google/gemini-3.8-flash",
    "x-ai/grok-4.3",
    "deepseek/deepseek-v4-flash",
    "z-ai/glm-5.3-flash",
    "qwen/qwen3.8-flash",
    "meta-llama/llama-4-maverick",
    "qwen/qwen-2.5-7b-instruct",
]
# وشەکانی مۆدێلی کەم‌خوارەکە (لە بودجەی ٢٥٠٠ تۆکنی میوان)
_RWD_FREE_HINTS = ("flash", "mini", "lite", "nano", "small", "turbo")


def rwd_models_live(timeout=15):
    """لیستی مۆدێلەکانی rewind — تەنها چاتی ئاسایی، بێ batch/alias"""
    r = requests.get(RWD_BASE + "/v1/models", headers={"User-Agent": UA}, timeout=timeout)
    r.raise_for_status()
    out = []
    for m in r.json().get("models", []):
        mid = m.get("id") or ""
        if m.get("type") != "chat":
            continue
        if ":batch" in mid or mid.startswith("~"):
            continue
        out.append(mid)
    return out


def rwd_servers(timeout=15):
    """سێرڤەرەکانی rewind — بەقوەتەکان + فلاشەکان (بە ڕیزبەندی پشتڕاستکراو)"""
    try:
        live = rwd_models_live(timeout)
    except Exception:
        live = []
    chosen = [m for m in _RWD_VERIFIED if not live or m in live]
    if live:
        for mid in live:
            tail = mid.lower().split("/")[-1].split(":")[0]
            segs = tail.split("-")
            if any(any(s == h or s.startswith(h) for h in _RWD_FREE_HINTS) for s in segs) and mid not in chosen:
                chosen.append(mid)
            if len(chosen) >= 32:
                break
    return [{"id": mid, "name": mid, "model_id": mid, "kind": "rwd"} for mid in chosen]


def _rwd_session(timeout=15):
    """سێشن بە UA ی ئێستا — GET ی سەرەتا کوکییەی anon_token دەگرێت"""
    s = requests.Session()
    ua = _RWD_UAS[_RWD_STATE["i"] % len(_RWD_UAS)]
    s.headers["User-Agent"] = ua
    try:
        s.get(RWD_BASE + "/v1/models", headers={"User-Agent": ua}, timeout=timeout)
    except Exception:
        pass
    return s


def _rwd_next_identity():
    """گۆڕینی ناسنامە — UA ی داهاتوو = بودجەی تازەی ٢٥٠٠ تۆکن"""
    _RWD_STATE["i"] = (_RWD_STATE["i"] + 1) % len(_RWD_UAS)


def rwd_chat(model_id, messages, timeout=110):
    """پرسیار بۆ rewind — خۆکارانە ناسنامە دەگۆڕێت کاتێک تۆکن تەواو دەبێت"""
    for attempt in (0, 1):
        s = _rwd_session()
        ua = s.headers["User-Agent"]
        try:
            r = s.post(RWD_BASE + "/v1/chat/completions/",
                       headers={"User-Agent": ua, "Content-Type": "application/json"},
                       json={"model": model_id, "messages": messages}, timeout=(15, timeout))
        except Exception as e:
            if attempt == 0:
                _rwd_next_identity()
                continue
            raise EMError(f"rwd: {str(e)[:60]}")
        if r.status_code == 400:
            # ناسنامەی ئەم UA یە بەکارهاتووە — گۆڕی بدەر بۆ ئەوی تر
            _rwd_next_identity()
            continue
        if r.status_code == 429:
            raise EMError("rwd: ڕێژە زۆرە — چاوەڕێ بکە")
        try:
            j = r.json()
        except Exception:
            _rwd_next_identity()
            continue
        err = j.get("error")
        if isinstance(err, dict):
            code = str(err.get("code") or "")
            if code == "INSUFFICIENT_TOKENS":
                # تۆکنەکانی ئەم ناسنامەیە تەواو بوون — UA ی نوێ = ٢٥٠٠ی نوێ
                if attempt == 0:
                    _rwd_next_identity()
                    continue
                raise EMError("rwd: هەموو ناسنامەکان تەواو بوون")
            raise EMError("rwd: " + (code or str(err)[:50])[:60])
        ch = (j.get("choices") or [{}])[0]
        ans = ((ch.get("message") or {}).get("content") or "").strip()
        if ans:
            return ans
        _rwd_next_identity()
    raise EMError("rwd: نەگەڕایەوە")


# ════════════════════════════════════════════════════════════
# ٢.٩) مێشکی aichatting.net — gpt-5.6/claude-opus-5/grok-4.6 (خۆکار)
#      visitorId = RSA-encrypted fingerprint — هەر ناسنامەیەک = کواتی نوێ
# ════════════════════════════════════════════════════════════

ACT_BASE = "https://aga-api.aichatting.net"
ACT_PUBKEY = (
    "-----BEGIN PUBLIC KEY-----\n"
    "MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQDCAdf/EyIbLBxjGqmh7qLU6/CPCzru+75+82OSPZ+nf4BFvg88drpZ6KigNW0J8TNgxe6Yms1irCZNVDyu+RXsl4y/7c2KOHc4OGTzHB5fUMiMasFUvcEs2P70e6yA/sKHZfBLG1XPhlb84Ibs3nhD3W5e2SuC+4EuVkaqzN08LQIDAQAB\n"
    "-----END PUBLIC KEY-----"
)
# ڕاستکراوە: API ەکەیان هەر ناوێک قبوڵ دەکات بەڵام هەمووی فەڵباکە بۆ یەک مۆدێڵ
# (پشکنین: ناوی درۆش وەڵام دەداتەوە + هەموو ناوەکان «made by OpenAI» دەڵێن)
# تەنها ناوی ڕەسمی ڕاییگەی ماڵپەڕەکە دەمێنێتەوە — gpt-5.6-luna
ACT_MODELS = ["gpt-5.6-luna"]
ACT_UAS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:132.0) Gecko/20100101 Firefox/132.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.6 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
]
_ACT_STATE = {"i": 0}


def act_servers():
    """سێرڤەرەکانی aichatting — هەموو مۆدێلە پشتڕاستکراوەکان"""
    return [{"id": "act-" + m, "name": m, "model_id": m, "kind": "act"} for m in ACT_MODELS]


def _act_identity():
    """ناسنامەی نوێ — visitorId نوێ = RSA encrypt
    → (visitorId, vTokenی خاو base64, کوکی percent-encoded)"""
    import urllib.parse as _up
    visitor_id = hashlib.md5(f"fp{time.time()}{random.random()}".encode()).hexdigest()
    from cryptography.hazmat.primitives import serialization as _s, asymmetric as _a
    try:
        pub = _s.load_pem_public_key(ACT_PUBKEY.encode())
        enc = pub.encrypt(visitor_id.encode(), _a.padding.PKCS1v15())
        raw = base64.b64encode(enc).decode()
    except Exception:
        raw = visitor_id
    return visitor_id, raw, _up.quote(raw, safe="")


def act_chat(model_id, messages, timeout=110):
    """چات بۆ aichatting — SSE، ناسنامەی خۆکار (کوات تەواو بوو → نوێی دەکاتەوە)"""
    for attempt in (0, 1):
        visitor_id, raw_token, cookie_token = _act_identity()
        ua = ACT_UAS[_ACT_STATE["i"] % len(ACT_UAS)]
        h = {
            "User-Agent": ua, "source": "web", "lang": "en",
            "Content-Type": "application/json",
            "Cookie": "aichatting.website.visitorId=" + cookie_token,
            "vToken": raw_token,
            "Origin": "https://www.aichatting.net",
            "Referer": "https://www.aichatting.net/free-chatgpt/",
            "Accept": "text/event-stream,application/json",
        }
        msgs = [{"role": m["role"], "content": [{"type": "text", "text": m["content"]}]}
                for m in messages if m.get("role") in ("user", "assistant", "system")][-20:]
        payload = {"spaceHandle": True, "roleId": None, "messages": msgs,
                   "conversationId": None, "model": model_id}
        try:
            r = requests.post(ACT_BASE + "/aigc/chat/v2/askai/stream",
                              headers=h, json=payload, timeout=(15, timeout))
        except Exception as e:
            if attempt == 0:
                continue
            raise EMError(f"act: {str(e)[:60]}")
        if r.status_code == 401 and attempt == 0:
            continue  # ناسنامەی نوێ
        if r.status_code != 200:
            if attempt == 0:
                continue
            raise EMError(f"act: {r.status_code}")
        # SSE — data: بەشەکان، "--@DONE@--" کۆتایی (UTF-8 — r.text عەرەبی تێکدەدات)
        # ئاماژەکانی ئەوان: "-=- --" = بۆشایی، "-=-n--" = هێڵی نوێ (لە c3.js)
        out = []
        for line in r.content.decode("utf-8", "replace").splitlines():
            if line.startswith("data:"):
                part = line[5:]
                if part.startswith(" "):
                    part = part[1:]
                part = part.rstrip("\r")
                if part and part != "--@DONE@--":
                    out.append(part)
        ans = "".join(out).replace("-=- --", " ").replace("-=-n--", "\n").strip()
        if ans:
            return ans
        if attempt == 0:
            continue
    raise EMError("act: وەڵام نەگەڕایەوە")


# ════════════════════════════════════════════════════════════
# ٢.١٠) flatai.org — GLM (Z.ai) بێ تۆمار — کواتی ڕۆژانە بۆ هەر IP
#      session → history(save) → my_chatbot (SSE)
# ════════════════════════════════════════════════════════════

FLA_AJAX = "https://flatai.org/wp-admin/admin-ajax.php"


def fla_servers():
    return [{"id": "flatai-glm", "name": "GLM (flatai)", "model_id": "glm", "kind": "fla"}]


def fla_chat(messages, timeout=110):
    """چاتی flatai — یەک مۆدێڵی سێرڤەری (GLM)؛ کواتی ڕۆژانە تەواو → EMError"""
    import uuid as _uuid
    s = requests.Session()
    s.headers.update({
        "User-Agent": ACT_UAS[random.randrange(len(ACT_UAS))],
        "Origin": "https://flatai.org",
        "Referer": "https://flatai.org/free-ai-chatbot-no-registration/",
    })

    def F(**kv):
        return {k: (None, v) for k, v in kv.items()}

    try:
        s.get("https://flatai.org/free-ai-chatbot-no-registration/", timeout=(15, 30))
        r = s.post(FLA_AJAX, files=F(action="chatbot2_session"), timeout=(15, 30))
        sess = r.json()["data"]
        r = s.post(FLA_AJAX, files=F(action="chatbot2_history", nonce=sess["nonce"],
                                     history_nonce=sess["history_nonce"], operation="load"),
                   timeout=(15, 30))
        ld = r.json()["data"]
        chat_id = str(_uuid.uuid4())
        chats = json.loads(ld["values"].get("allChats", "{}"))
        chats[chat_id] = {"timestamp": time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime()),
                          "title": "New conversation", "messages": []}
        s.post(FLA_AJAX, files=F(action="chatbot2_history", nonce=sess["nonce"],
                                 history_nonce=sess["history_nonce"], operation="save",
                                 values=json.dumps({**ld["values"], "allChats": json.dumps(chats)}),
                                 revision=str(ld["revision"])), timeout=(15, 30))
        msgs = [{"role": m["role"], "content": m["content"]}
                for m in messages if m.get("role") in ("user", "assistant", "system")][-20:]
        sys_txt = ""
        if msgs and msgs[0]["role"] == "system":
            sys_txt = msgs.pop(0)["content"]
        r = s.post(FLA_AJAX, files=F(action="my_chatbot", nonce=sess["nonce"],
                                     history_nonce=sess["history_nonce"],
                                     request_id=str(_uuid.uuid4()), chat_id=chat_id,
                                     messages=json.dumps(msgs),
                                     system_message_content=sys_txt),
                   timeout=(15, timeout))
        if r.status_code == 429:
            raise EMError("fla: کواتی ڕۆژانە تەواو (IP)")
        ct = r.headers.get("content-type", "")
        if r.status_code != 200 or "event-stream" not in ct:
            raise EMError(f"fla: {r.status_code}")
        text = ""
        for line in r.content.decode("utf-8", "replace").splitlines():
            if line.startswith("data: "):
                try:
                    d = json.loads(line[6:])
                    if isinstance(d, dict) and isinstance(d.get("text"), str) and d["text"]:
                        text = d["text"]  # کۆتا (done) دەباتەوە
                except Exception:
                    pass
        if text.strip():
            return text.strip()
        raise EMError("fla: وەڵام نەگەڕایەوە")
    except EMError:
        raise
    except Exception as e:
        raise EMError(f"fla: {str(e)[:60]}")


# ════════════════════════════════════════════════════════════
# ٢.١١) zerotwo.ai — gemini-2.5-flash-lite (ڕاییگە: ١٥ نامە/ڕۆژ/هەژمار)
#      supabase signup (mail.tm) → csrf → /api/ai/chat/stream
# ════════════════════════════════════════════════════════════

Z02_API = "https://api.zerotwo.ai"
Z02_SB = "https://jdbcevjbqaoxrxxwqwux.supabase.co"
Z02_KEY = ("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
           "eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImpkYmNldmpicWFveHJ4eHdxd3V4Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTgyNDcyMzUsImV4cCI6MjA3MzgyMzIzNX0."
           "UcUJUjMocwijFTtYFKYuTgIODYWc4uxDByu2tI6XGQg")

_Z02_CACHE = {"token": None, "exp": 0.0}


def z02_servers():
    return [
        {"id": "z02-gemini-flash-lite", "name": "Gemini Flash Lite (ZeroTwo)",
         "model_id": "gemini-2.5-flash-lite", "kind": "z02"},
        {"id": "z02-grok-4.1-fast", "name": "Grok 4.1 Fast (ZeroTwo)",
         "model_id": "grok-4-1-fast-non-reasoning", "kind": "z02"},
        {"id": "z02-gpt-5.6-luna", "name": "GPT 5.6 Luna (ZeroTwo)",
         "model_id": "gpt-5.6-luna", "kind": "z02"},
        {"id": "z02-venice-roleplay", "name": "Venice Roleplay (ZeroTwo)",
         "model_id": "venice-uncensored-role-play", "kind": "z02"},
    ]


# model_id → provider ی zerotwo
_Z02_PROVIDERS = {
    "gemini-2.5-flash-lite": "gemini",
    "grok-4-1-fast-non-reasoning": "xai",
    "gpt-5.6-luna": "openai",
    "venice-uncensored-role-play": "venice",
}


def _z02_new_account():
    """هەژماری نوێ: mail.tm → supabase signup → confirm → access_token"""
    import uuid as _uuid
    ms = requests.Session()
    ms.headers.update({"User-Agent": ACT_UAS[random.randrange(len(ACT_UAS))]})
    r = ms.get("https://api.mail.tm/domains", timeout=(15, 30))
    dom = r.json()["hydra:member"][0]["domain"]
    email = f"z02x{int(time.time())}{random.randrange(100, 999)}@{dom}"
    pw = "Xk9!mQ2#vLp8$zRw"
    r = ms.post("https://api.mail.tm/accounts", json={"address": email, "password": pw}, timeout=(15, 30))
    if r.status_code not in (200, 201):
        raise EMError(f"z02 mail: {r.status_code}")
    r = ms.post("https://api.mail.tm/token", json={"address": email, "password": pw}, timeout=(15, 30))
    mtok = r.json()["token"]
    h = {"apikey": Z02_KEY, "Authorization": f"Bearer {Z02_KEY}", "Content-Type": "application/json"}
    r = requests.post(f"{Z02_SB}/auth/v1/signup", json={"email": email, "password": pw},
                      headers=h, timeout=(15, 40))
    if r.status_code != 200:
        raise EMError(f"z02 signup: {r.status_code}")
    # چاوەڕوانی نامەی confirm (SendGrid — quoted-printable decode)
    link = None
    import quopri as _qp
    for _ in range(8):
        time.sleep(3.5)
        try:
            r = ms.get("https://api.mail.tm/messages", headers={"Authorization": f"Bearer {mtok}"},
                       timeout=(15, 30))
            msgs = r.json().get("hydra:member", [])
            if not msgs:
                continue
            mid = msgs[0]["id"]
            r = ms.get(f"https://api.mail.tm/messages/{mid}",
                       headers={"Authorization": f"Bearer {mtok}"}, timeout=(15, 30))
            d = r.json()
            html = d.get("html")
            html = html[0] if isinstance(html, list) else str(html)
            try:
                html = _qp.decodestring(html.encode()).decode("utf-8", "replace")
            except Exception:
                pass
            m = re.search(r'https://u[0-9a-z]+\.ct\.sendgrid\.net/ls/click\?[^"\'\s<>]+', html)
            if m:
                link = m.group(0)
                break
        except Exception:
            continue
    if not link:
        raise EMError("z02: نامەی confirm نەگەیشت")
    r = requests.get(link, allow_redirects=True, timeout=(15, 40),
                     headers={"User-Agent": ACT_UAS[0]})
    m = re.search(r'access_token=(eyJ[A-Za-z0-9_.-]+)', r.url)
    if not m:
        raise EMError("z02: access_token لە ڕیدایرێکت نییە")
    return m.group(1)


def _z02_token():
    """access_token ی زیندوو — ئەگەر کۆن بوو یان مردوو بوو نوێی دروست دەکات"""
    if _Z02_CACHE["token"] and time.time() < _Z02_CACHE["exp"]:
        return _Z02_CACHE["token"]
    tok = _z02_new_account()
    _Z02_CACHE["token"] = tok
    _Z02_CACHE["exp"] = time.time() + 3300  # JWT = 1 کاتژمێر
    return tok


def z02_chat(messages, model_id="gemini-2.5-flash-lite", timeout=110):
    """چاتی zerotwo — ٤ مۆدێڵی ڕاییگە؛ ١٥ نامە/ڕۆژ → هەژماری نوێ خۆکار"""
    provider = _Z02_PROVIDERS.get(model_id, "gemini")
    try:
        token = _z02_token()
    except EMError:
        raise
    except Exception as e:
        raise EMError(f"z02: {str(e)[:60]}")
    h = {
        "User-Agent": ACT_UAS[random.randrange(len(ACT_UAS))],
        "Origin": "https://app.zerotwo.ai", "Referer": "https://app.zerotwo.ai/",
        "X-ZeroTwo-Platform": "web", "Content-Type": "application/json",
    }
    msgs = [{"role": m["role"], "content": m["content"]}
            for m in messages if m.get("role") in ("user", "assistant", "system")][-20:]
    for attempt in (0, 1):
        if attempt == 1:
            try:
                token = _z02_new_account()
                _Z02_CACHE["token"], _Z02_CACHE["exp"] = token, time.time() + 3300
            except Exception as e:
                raise EMError(f"z02 هەژمار: {str(e)[:50]}")
        try:
            s = requests.Session()
            s.headers.update(h)
            r = s.get(Z02_API + "/api/auth/csrf-token", timeout=(15, 30))
            tok = r.json()["token"]
            r = s.post(Z02_API + "/api/ai/chat/stream",
                       headers={**h, "X-CSRF-Token": tok, "Authorization": f"Bearer {token}"},
                       json={"messages": msgs, "provider": provider, "model": model_id},
                       timeout=(15, timeout))
        except Exception as e:
            if attempt == 0:
                continue
            raise EMError(f"z02: {str(e)[:60]}")
        text, err = [], ""
        for line in r.content.decode("utf-8", "replace").splitlines():
            if not line.startswith("data: "):
                continue
            try:
                d = json.loads(line[6:])
            except Exception:
                continue
            if d.get("entity") == "message.content" and d.get("status") == "delta":
                t = (d.get("v", {}).get("delta") or {}).get("text")
                if t:
                    text.append(t)
            if d.get("status") == "error":
                v = d.get("v", {})
                err = v.get("code") or v.get("message") or "error"
        ans = "".join(text).strip()
        if ans:
            return ans
        if "LIMIT" in err.upper() or "429" in str(err):
            if attempt == 0:
                continue  # هەژماری نوێ
            raise EMError("z02: کواتی ڕۆژانە تەواو")
        if attempt == 0:
            continue
        raise EMError(f"z02: {str(err)[:60] or 'وەڵام نەگەڕایەوە'}")
    raise EMError("z02: وەڵام نەگەڕایەوە")


# ════════════════════════════════════════════════════════════
# ٢.١٢) quillbot.com AI Chat — gpt-4.1-mini بێ تۆمار
#      POST /api/ai-chat/chat/conversation/{uuid} — NDJSON stream
#      کوات: ١ نامە/~٢٠ چرکە (دوای ناوەستێت بەردەوام دەبێتەوە)
# ════════════════════════════════════════════════════════════

QB_URL = "https://quillbot.com/api/ai-chat/chat/conversation/"


def qb_servers():
    return [{"id": "qb-gpt-4.1-mini", "name": "GPT 4.1 Mini (QuillBot)",
             "model_id": "gpt-4.1-mini", "kind": "qb"}]


def qb_chat(messages, timeout=110):
    """چاتی quillbot — مێژووی وەک یەک نامەی یەکگیراو؛ NDJSON: type=content/usage"""
    import uuid as _uuid
    # مێژوو بۆ یەک پرسیار کۆبکەوە (سیستەم لە سەرەتا + دوا نامەی بەکارهێنەر)
    sys_txt = " ".join(m["content"] for m in messages if m.get("role") == "system")[:1200]
    user_txt = ""
    for m in reversed(messages):
        if m.get("role") == "user":
            user_txt = m["content"]
            break
    if not user_txt:
        user_txt = " ".join(m.get("content", "") for m in messages)[-2000:]
    if sys_txt:
        user_txt = f"[ئاراستەی سیستەم: {sys_txt}]\n\n{user_txt}"
    body = {"message": {"content": user_txt, "files": []}, "context": {}, "tools": {},
            "origin": {"name": "ai-chat.chat", "url": "https://quillbot.com"}}
    try:
        r = requests.post(QB_URL + str(_uuid.uuid4()), json=body, timeout=(15, timeout),
                          headers={"User-Agent": ACT_UAS[random.randrange(len(ACT_UAS))],
                                   "Origin": "https://quillbot.com",
                                   "Referer": "https://quillbot.com/ai-chat",
                                   "Accept": "text/event-stream",
                                   "platform-type": "webapp"}, stream=True)
    except Exception as e:
        raise EMError(f"qb: {str(e)[:60]}")
    if r.status_code == 403:
        raise EMError("qb: چەلەنجەی Cloudflare (ڕێژە)")
    if r.status_code != 200:
        raise EMError(f"qb: {r.status_code}")
    text = []
    for line in r.iter_lines(decode_unicode=True):
        if not line:
            continue
        try:
            d = json.loads(line)
        except Exception:
            continue
        if d.get("type") == "content":
            c = d.get("content", "")
            if c:
                text.append(c)
        elif d.get("type") == "error":
            raise EMError(f"qb: {str(d.get('message', 'error'))[:60]}")
    ans = "".join(text).strip()
    ans = re.sub(r"</?editor-content[^>]*>", "", ans).strip()
    if ans:
        return ans
    raise EMError("qb: وەڵام نەگەڕایەوە")



# ════════════════════════════════════════════════════════════
# ٢.١٣) duck.ai (DuckDuckGo AI) — ٥ مۆدێڵی خۆڕایی بێ تۆمار
#      چەلەنجەی JS (x-vqd-hash-1) لە V8 (py-mini-racer) + DOM stubs چارە دەکرێت
#      لیمتی IP: هەندێجە ٤١٨ → فەڵباکی زنجیرە هەڵی دەگرێت
# ════════════════════════════════════════════════════════════

DUCK_STUBS_JS = r'''var __ua = __DDG_REAL_UA__;
var __HTML_LOOKUP = __DDG_HTML_LOOKUP__;

function __makeHtmlElement(tag) {
  var state = { _innerHTML: '', _qsaCount: 0, _cssText: '' };
  var styleObj = {};
  Object.defineProperty(styleObj, 'cssText', {
    get: function(){ return state._cssText; },
    set: function(v){ state._cssText = String(v||''); },
    enumerable: true, configurable: true
  });
  var el = {
    tagName: String(tag).toUpperCase(),
    nodeName: String(tag).toUpperCase(),
    nodeType: 1,
    children: [], childNodes: [], classList: [],
    style: styleObj, dataset: {},
    offsetWidth: 100, offsetHeight: 20, scrollHeight: 20,
    offsetTop: 100, offsetLeft: 0, offsetParent: null,
    clientWidth: 100, clientHeight: 20,
    getBoundingClientRect: function(){
      return { width: 100, height: 20, top: 100, left: 0, right: 100, bottom: 120, x: 0, y: 100 };
    },
    getClientRects: function(){
      return [{ width: 100, height: 20, top: 100, left: 0, right: 100, bottom: 120 }];
    },
    setAttribute: function(){}, removeAttribute: function(){},
    getAttribute: function(a){ if(a==='srcdoc') return state._srcdoc||''; return null; },
    hasAttribute: function(){ return false; },
    appendChild: function(c){ return c; },
    removeChild: function(c){ return c; },
    addEventListener: function(){}, removeEventListener: function(){},
    querySelector: function(){ return null; },
    querySelectorAll: function(s){
      if (s === '*') {
        var arr = []; arr.length = state._qsaCount; return arr;
      }
      return [];
    },
    cloneNode: function(){ return __makeHtmlElement(tag); },
    _getState: function(){ return state; }
  };
  Object.defineProperty(el, 'innerHTML', {
    get: function(){ return state._innerHTML; },
    set: function(v){
      var key = String(v);
      var entry = __HTML_LOOKUP && __HTML_LOOKUP[key];
      if (entry) { state._innerHTML = String(entry.html); state._qsaCount = entry.count|0; }
      else { state._innerHTML = key; state._qsaCount = 0; }
    },
    enumerable: true, configurable: true
  });
  Object.defineProperty(el, 'outerHTML', { get: function(){ return '<' + tag + '>' + state._innerHTML + '</' + tag + '>'; }, enumerable: true });
  Object.defineProperty(el, 'srcdoc', { get: function(){ return state._srcdoc||''; }, set: function(v){ state._srcdoc = String(v); }, enumerable: true });
  Object.defineProperty(el, 'contentWindow', { get: function(){
    var w = {};
    w.document = __ifDoc;
    w.Proxy = Proxy;
    w.self = w;
    w.top = w;
    w.parent = w;
    w.window = w;
    return w;
  }, enumerable: true });
  Object.defineProperty(el, 'contentDocument', { get: function(){ return __ifDoc; }, enumerable: true });
  return el;
}

function __mkObj(name, base) {
  base = base || {};
  return new Proxy(base, {
    get: function(t, k) {
      if (k in t) return t[k];
      if (k === Symbol.toPrimitive) return function(){ return ''; };
      if (k === Symbol.iterator) return undefined;
      if (k === 'then' || k === 'catch' || k === 'finally') return undefined;
      if (k === 'constructor') return Object;
      if (k === 'toString' || k === 'valueOf') return function(){ return '[object ' + name + ']'; };
      if (k === 'length') return 0;
      if (k === 'nodeType') return 1;
      if (k === 'tagName' || k === 'nodeName') return 'DIV';
      if (k === 'innerHTML' || k === 'outerHTML' || k === 'textContent' || k === 'innerText' || k === 'value') return '';
      if (k === 'children' || k === 'childNodes' || k === 'classList') return [];
      if (typeof k === 'string' && (k.indexOf('get') === 0 || k.indexOf('query') === 0 || k.indexOf('find') === 0)) {
        return function(arg){
          if (k === 'querySelectorAll' || k === 'getElementsByTagName' || k === 'getElementsByClassName') return [];
          return null;
        };
      }
      return function(){ return __mkObj(name + '.' + String(k)); };
    },
    has: function(t, k){ return k in t; },
    set: function(t, k, v){ t[k] = v; return true; }
  });
}

var __ifMeta = __mkObj('meta', {
  getAttribute: function(a){ return a==='content' ? "default-src 'none'; script-src 'unsafe-inline';" : null; },
  hasAttribute: function(a){ return a==='content'; },
  tagName: 'META', nodeName: 'META'
});
var __ifDoc;
__ifDoc = __mkObj('iframeDoc', {
  querySelector: function(s){
    if (s && s.indexOf('Content-Security-Policy') !== -1) return __ifMeta;
    if (s === 'meta') return __ifMeta;
    return null;
  },
  querySelectorAll: function(s){
    if (s && s.indexOf('Content-Security-Policy') !== -1) return [__ifMeta];
    if (s === 'meta') return [__ifMeta];
    return [];
  },
  getElementsByTagName: function(t){ return t && t.toLowerCase()==='meta' ? [__ifMeta] : []; },
  body: __mkObj('iframeBody', {
    querySelector: function(s){ return s && s.indexOf('Content-Security-Policy')!==-1 ? __ifMeta : null; },
    querySelectorAll: function(s){ return s && s.indexOf('Content-Security-Policy')!==-1 ? [__ifMeta] : []; },
    appendChild: function(){}, removeChild: function(){}
  }),
  head: __mkObj('iframeHead', {
    querySelector: function(s){ return s && s.indexOf('Content-Security-Policy')!==-1 ? __ifMeta : null; },
    querySelectorAll: function(s){ return s && s.indexOf('Content-Security-Policy')!==-1 ? [__ifMeta] : []; },
    appendChild: function(){}, removeChild: function(){}
  }),
  documentElement: __mkObj('iframeRoot'),
  createElement: function(){ return __mkObj('elem', {setAttribute:function(){}, appendChild:function(){}, removeChild:function(){}, getAttribute:function(){return null;}, hasAttribute:function(){return false;}}); },
  cookie: '', readyState: 'complete'
});

var __iframeEl = __mkObj('iframe', {
  contentDocument: __ifDoc,
  contentWindow: __mkObj('iframeWin', { document: __ifDoc, top: undefined, parent: undefined }),
  document: __ifDoc,
  getAttribute: function(a){
    if (a==='sandbox') return 'allow-scripts allow-same-origin';
    if (a==='srcdoc') return '';
    if (a==='id') return 'jsa';
    return null;
  },
  hasAttribute: function(a){ return a==='sandbox'||a==='id'; },
  tagName: 'IFRAME', nodeName: 'IFRAME', id: 'jsa'
});

var document = __mkObj('document', {
  querySelector: function(s){
    if (s === '#jsa') return __iframeEl;
    if (s && s.indexOf('Content-Security-Policy') !== -1) return __ifMeta;
    return null;
  },
  querySelectorAll: function(s){
    if (s === '#jsa') return [__iframeEl];
    if (s && s.indexOf('Content-Security-Policy') !== -1) return [__ifMeta];
    return [];
  },
  getElementById: function(id){ return id==='jsa' ? __iframeEl : null; },
  getElementsByTagName: function(t){ if(t&&t.toLowerCase()==='iframe') return [__iframeEl]; return []; },
  getElementsByClassName: function(){ return []; },
  body: __mkObj('body', {appendChild:function(){}, removeChild:function(){}, querySelector:function(s){return s==='#jsa'?__iframeEl:null;}, querySelectorAll:function(s){return s==='#jsa'?[__iframeEl]:[];}}),
  head: __mkObj('head', {appendChild:function(){}, removeChild:function(){}, querySelector:function(){return null;}, querySelectorAll:function(){return [];}}),
  documentElement: __mkObj('root'),
  createElement: function(tag){ return __makeHtmlElement(tag||'div'); },
  createTextNode: function(t){ return {nodeType:3, nodeValue:String(t||''), textContent:String(t||'')}; },
  cookie: '', readyState: 'complete', title: '',
  addEventListener: function(){}, removeEventListener: function(){}
});

var window;
window = __mkObj('window', {
  document: document,
  __DDG_BE_VERSION__: 1, __DDG_FE_CHAT_HASH__: 1,
  navigator: __mkObj('navigator', { userAgent: __ua, webdriver: false, language: 'en-US', languages: ['en-US','en'], platform: 'MacIntel', vendor: 'Apple Computer, Inc.', appVersion: '5.0', cookieEnabled: true, onLine: true, hardwareConcurrency: 8, deviceMemory: 8 }),
  innerWidth: 1280, innerHeight: 800, outerWidth: 1280, outerHeight: 800, devicePixelRatio: 1,
  screen: __mkObj('screen', { width:1920, height:1080, availWidth:1920, availHeight:1080, colorDepth:24, pixelDepth:24 }),
  location: __mkObj('location', { href:'https://duckduckgo.com/', origin:'https://duckduckgo.com', host:'duckduckgo.com', hostname:'duckduckgo.com', protocol:'https:', pathname:'/', search:'', hash:'', port:'' }),
  performance: __mkObj('perf', { now: function(){ return 0; }, timeOrigin: 0 }),
  history: __mkObj('history', { length: 1, state: null }),
  localStorage: __mkObj('ls', { getItem:function(){return null;}, setItem:function(){}, removeItem:function(){}, clear:function(){}, length:0, key:function(){return null;} }),
  sessionStorage: __mkObj('ss', { getItem:function(){return null;}, setItem:function(){}, removeItem:function(){}, clear:function(){}, length:0, key:function(){return null;} }),
  addEventListener: function(){}, removeEventListener: function(){}, dispatchEvent: function(){return true;},
  getComputedStyle: function(el){
    var css = (el && el.style && el.style.cssText) || '';
    return {
      getPropertyValue: function(p){
        var m = css.match(new RegExp(p + '\\s*:\\s*([^;]+)', 'i'));
        if (m) return m[1].trim();
        if (p === 'display') return 'block';
        return '';
      },
      display: (css.match(/display\s*:\s*([^;]+)/i)||[])[1]||'block'
    };
  },
  setTimeout: function(fn){ try{fn();}catch(e){} return 0; }, clearTimeout: function(){},
  setInterval: function(){ return 0; }, clearInterval: function(){},
  requestAnimationFrame: function(fn){ try{fn();}catch(e){} return 0; }, cancelAnimationFrame: function(){},
  matchMedia: function(){ return __mkObj('mq', {matches:false, media:'', addListener:function(){}, removeListener:function(){}, addEventListener:function(){}, removeEventListener:function(){}}); },
  hasOwnProperty: function(k){
    if (k==='__DDG_BE_VERSION__'||k==='__DDG_FE_CHAT_HASH__') return true;
    return Object.prototype.hasOwnProperty.call(this,k);
  },
  alert: function(){}, confirm: function(){return true;}, prompt: function(){return '';},
  open: function(){return null;}, close: function(){}, focus: function(){}, blur: function(){}
});
window.top = window; window.self = window; window.window = window; window.parent = window; window.globalThis = window;
var top = window, self = window, parent = window;
var navigator = window.navigator;
var location = window.location;
var screen = window.screen;
var performance = window.performance;
var history = window.history;
var localStorage = window.localStorage;
var sessionStorage = window.sessionStorage;
var getComputedStyle = function(el){ return window.getComputedStyle(el); };
var __R = null, __E = null;
function __HTMLClass(name){ var c = function(){}; c.prototype = __mkObj(name+'.proto'); return c; }
var HTMLElement = __HTMLClass('HTMLElement');
var HTMLDivElement = __HTMLClass('HTMLDivElement');
var HTMLIFrameElement = __HTMLClass('HTMLIFrameElement');
var HTMLDocument = __HTMLClass('HTMLDocument');
var Document = __HTMLClass('Document');
var Element = __HTMLClass('Element');
var Node = __HTMLClass('Node');
var Window = __HTMLClass('Window');
var Event = __HTMLClass('Event');
var MouseEvent = __HTMLClass('MouseEvent');
var KeyboardEvent = __HTMLClass('KeyboardEvent');
var TouchEvent = __HTMLClass('TouchEvent');
var XMLHttpRequest = __HTMLClass('XMLHttpRequest');
var WebSocket = __HTMLClass('WebSocket');
var Image = __HTMLClass('Image');
var FormData = __HTMLClass('FormData');
var Blob = __HTMLClass('Blob');
var File = __HTMLClass('File');
var FileReader = __HTMLClass('FileReader');
var URL = __HTMLClass('URL');
var URLSearchParams = __HTMLClass('URLSearchParams');
var Headers = __HTMLClass('Headers');
var Request = __HTMLClass('Request');
var Response = __HTMLClass('Response');
var fetch = function(){ return Promise.resolve(__mkObj('resp', {ok:true, status:200, json:function(){return Promise.resolve({});}, text:function(){return Promise.resolve('');}})); };
'''

DUCK_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
           "(KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36")
DUCK_FE_VERSION = "serp_20260917_083005_ET-742796f26a61a81dbee67db3e7dd403a0e16294e"
DUCK_SESSION = None
DUCK_WARMED = [False]
DUCK_LOCK = threading.Lock()
DUCK_JWK = [None]


def duck_servers():
    return [
        {"id": "duck-gpt-5.4-mini", "name": "GPT 5.4 Mini (Duck)",
         "model_id": "gpt-5.4-mini", "kind": "duck"},
        {"id": "duck-claude-haiku-4-5", "name": "Claude Haiku 4.5 (Duck)",
         "model_id": "claude-haiku-4-5", "kind": "duck"},
        {"id": "duck-mistral-small", "name": "Mistral Small (Duck)",
         "model_id": "mistral-small-2603", "kind": "duck"},
        {"id": "duck-gpt-oss-120b", "name": "GPT OSS 120B (Duck)",
         "model_id": "tinfoil/gpt-oss-120b", "kind": "duck"},
        {"id": "duck-gemma-4-31b", "name": "Gemma 4 31B (Duck)",
         "model_id": "tinfoil/gemma4-31b", "kind": "duck"},
    ]


def _duck_b64u(b):
    import base64 as _b
    return _b.urlsafe_b64encode(b).decode().rstrip("=")


def _duck_jwk():
    if DUCK_JWK[0] is None:
        from cryptography.hazmat.primitives.asymmetric import rsa
        k = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        n = k.public_key().public_numbers().n
        nb = n.to_bytes((n.bit_length() + 7) // 8, "big")
        DUCK_JWK[0] = {"alg": "RSA-OAEP-256", "e": _duck_b64u((65537).to_bytes(3, "big")),
                       "ext": True, "key_ops": ["encrypt"], "kty": "RSA",
                       "n": _duck_b64u(nb), "use": "enc"}
    return DUCK_JWK[0]


def _duck_session():
    global DUCK_SESSION
    if DUCK_SESSION is None:
        DUCK_SESSION = requests.Session()
        DUCK_SESSION.headers.update({
            "User-Agent": DUCK_UA, "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://duck.ai/", "Origin": "https://duck.ai",
            "Sec-Fetch-Dest": "empty", "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin"})
    return DUCK_SESSION


def _duck_b64sha(s):
    import base64 as _b, hashlib as _h
    return _b.b64encode(_h.sha256(s.encode("utf-8")).digest()).decode("ascii")


def _duck_solve(challenge_b64):
    """چەلەنجەی JS ی سێرڤەر لە V8 چارە دەکات + wrapper ی FE (origin/stack/duration)"""
    import base64 as _b, json as _j, random as _r
    from py_mini_racer import MiniRacer
    js = _b.b64decode(challenge_b64).decode("utf-8", errors="replace")
    with DUCK_LOCK:
        ctx = MiniRacer()
        try:
            ctx.eval(DUCK_STUBS_JS.replace("__DDG_REAL_UA__", _j.dumps(DUCK_UA))
                                    .replace("__DDG_HTML_LOOKUP__", "{}"))
            ctx.eval("(%s).then(function(v){__R=v;}).catch(function(e){__E=String((e&&e.stack)||e);});" % js)
            for _ in range(100):
                if ctx.execute("__R !== null || __E !== null"):
                    break
                time.sleep(0.02)
            err = ctx.execute("__E")
            if err:
                raise RuntimeError(str(err)[:120])
            res = ctx.execute("__R")
        finally:
            try:
                del ctx
            except Exception:
                pass
    if not isinstance(res, dict) or not res.get("client_hashes"):
        raise RuntimeError("duck: چەلەنجە بەتاڵ")
    ch = list(res["client_hashes"])
    ch[0] = DUCK_UA
    res["client_hashes"] = [_duck_b64sha(x) for x in ch]
    res.setdefault("meta", {})
    res["meta"]["origin"] = "https://duck.ai"
    res["meta"]["stack"] = "Error\n    at https://duck.ai/dist/duckai-dist/entry.duckai.js:2:123456"
    res["meta"]["duration"] = str(_r.randint(40, 250))
    return _b.b64encode(_j.dumps(res, separators=(",", ":")).encode("utf-8")).decode("ascii")


def _duck_signals():
    import base64 as _b, json as _j, random as _r
    now = int(time.time() * 1000)
    t = _r.randint(80, 180)
    ev = [{"name": "onboarding_impression_1", "delta": t}]
    t += _r.randint(120, 260)
    ev.append({"name": "onboarding_impression_2", "delta": t})
    t += _r.randint(200, 500)
    ev.append({"name": "startNewChat", "delta": t})
    for _ in range(_r.randint(6, 14)):
        t += _r.randint(40, 180)
        ev.append({"name": "user_input", "delta": t})
    t += _r.randint(120, 350)
    ev.append({"name": "user_submit", "delta": t})
    p = {"start": now - 8000, "events": ev, "end": t + _r.randint(20, 90)}
    return _b.b64encode(_j.dumps(p, separators=(",", ":")).encode("utf-8")).decode("ascii")


def _duck_warm():
    if DUCK_WARMED[0]:
        return
    with DUCK_LOCK:
        if DUCK_WARMED[0]:
            return
        try:
            _duck_session().get("https://duck.ai/", headers={
                "Accept": "text/html", "Upgrade-Insecure-Requests": "1"}, timeout=(15, 20))
        except Exception:
            pass
        DUCK_WARMED[0] = True


def _duck_attempt(model_id, msgs, timeout):
    import json as _j, random as _r, uuid as _u
    s = _duck_session()
    _duck_warm()
    r = s.get("https://duck.ai/duckchat/v1/status", headers={
        "x-vqd-accept": "1", "Cache-Control": "no-store", "Accept": "*/*"},
        timeout=(15, 25))
    if r.status_code != 200:
        raise EMError(f"duck: status {r.status_code}")
    ch = r.headers.get("x-vqd-hash-1")
    if not ch:
        raise EMError("duck: چەلەنجە نەگەڕایەوە")
    h1 = _duck_solve(ch)
    m = [{"role": x.get("role"), "content": [{"type": "text", "text": x.get("content", "")}]}
         for x in msgs]
    payload = {
        "model": model_id,
        "metadata": {"toolChoice": {"NewsSearch": False, "VideosSearch": False,
                                    "LocalSearch": False, "WeatherForecast": False}},
        "messages": m,
        "canUseTools": False,
        "reasoningEffort": "none",
        "canUseApproxLocation": None,
        "canDelegateImageGeneration": None,
        "canShowGreeting": False,
        "durableStream": {"messageId": str(_u.uuid4()), "conversationId": str(_u.uuid4()),
                          "publicKey": _duck_jwk()},
    }
    hdrs = {"Content-Type": "application/json", "Accept": "text/event-stream",
            "x-vqd-hash-1": h1, "x-fe-signals": _duck_signals(),
            "x-fe-version": DUCK_FE_VERSION, "x-ddg-journey-id": _u.uuid4().hex}
    r2 = s.post("https://duck.ai/duckchat/v1/chat", data=_j.dumps(payload),
                headers=hdrs, timeout=(15, timeout))
    if r2.status_code != 200:
        raise EMError(f"duck: {r2.status_code}")
    text = []
    for line in r2.iter_lines(decode_unicode=True):
        if not line or not line.startswith("data: "):
            continue
        d = line[6:].strip()
        if d == "[DONE]":
            break
        try:
            j = _j.loads(d)
        except Exception:
            continue
        if j.get("action") == "success" and isinstance(j.get("message"), str):
            text.append(j["message"])
        elif j.get("action") == "error":
            raise EMError(f"duck: {str(j.get('type', 'error'))[:50]}")
    ans = "".join(text).strip()
    if not ans:
        raise EMError("duck: وەڵام نەگەڕایەوە")
    return ans


def duck_chat(model_id, messages, timeout=110):
    """چاتی duck.ai — system دەفڕێتە ناو یەکەم نامەی بەکارهێنەر + ٢ هەوڵ"""
    sys_txt = " ".join(m["content"] for m in messages if m.get("role") == "system")[:1200]
    rest = [m for m in messages if m.get("role") != "system"][-21:]
    if rest and rest[0].get("role") == "user" and sys_txt:
        rest[0] = dict(rest[0])
        rest[0]["content"] = f"[ئاراستەی سیستەم: {sys_txt}]\n\n{rest[0]['content']}"
    elif sys_txt:
        rest = [{"role": "user", "content": f"[ئاراستەی سیستەم: {sys_txt}]"}] + rest
    last = None
    for i in range(2):
        try:
            return _duck_attempt(model_id, rest, timeout)
        except EMError as e:
            last = e
            if "418" not in str(e) and "429" not in str(e):
                raise
            time.sleep(1.5 + i)
    raise last or EMError("duck: شکست")



# ════════════════════════════════════════════════════════════
# ٢.١٤) anakin.ai — «Free No Sign Up Chatgpt» — Gemini بێ تۆمار
#      node client (anakin_client.mjs) — واژووی ڕەسەن: md5(object-hash(body)+SECRET+ts)
#      لیمیت: ~٢ نامە/IP/پەنجەرە → cooldown ١٠ خولەک دوای ٤٢٩ — فەڵباکی زنجیرە
# ════════════════════════════════════════════════════════════

AK_CLIENT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "anakin_client.mjs")
_AK_COOLDOWN = {"until": 0.0}


def ak_servers():
    return [
        {"id": "ak-gemini-2.5-flash", "name": "Gemini 2.5 Flash (Anakin)",
         "model_id": "308", "kind": "ak"},
        {"id": "ak-gemini-2.5-flash-lite", "name": "Gemini 2.5 Flash Lite (Anakin)",
         "model_id": "309", "kind": "ak"},
    ]


def ak_chat(model_id, messages, timeout=110):
    """چاتی anakin — node client؛ system تێکەڵ بە یەکەم نامە (شێوازی qb)"""
    import time as _t
    if _t.time() < _AK_COOLDOWN["until"]:
        raise EMError("ak: cooldown")
    sys_txt = " ".join(m["content"] for m in messages if m.get("role") == "system")[:1200]
    rest = [m for m in messages if m.get("role") in ("user", "assistant")][-21:]
    if rest and rest[0].get("role") == "user" and sys_txt:
        rest = [dict(rest[0])]
        rest[0] = dict(rest[0])
        rest[0]["content"] = f"[ئاراستەی سیستەم: {sys_txt}]\n\n{rest[0]['content']}"
    payload = json.dumps({"model_id": int(model_id), "messages": rest}, ensure_ascii=False)
    try:
        p = subprocess.run([NODE_BIN, AK_CLIENT], input=payload.encode("utf-8"),
                           capture_output=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        raise EMError("ak: timeout")
    lines = [l for l in (p.stdout or b"").decode("utf-8", "replace").strip().splitlines() if l.strip()]
    if not lines:
        raise EMError("ak: no output")
    try:
        obj = json.loads(lines[-1])
    except Exception:
        raise EMError("ak: bad output")
    if obj.get("ok") and obj.get("answer"):
        return obj["answer"]
    code = str(obj.get("code") or "")
    if "429" in code:
        _AK_COOLDOWN["until"] = _t.time() + 600
    raise EMError(obj.get("error") or "ak: failed", obj.get("code"))



# ════════════════════════════════════════════════════════════
# ٢.١٥) notegpt.io — AI Answer Generator — Gemini بێ تۆمار
#      POST /api/v2/homework/stream (SSE: data:{"text":...}) — بێ چەلەنجە، بێ کوکی
#      flash-lite: کراوە (~٩ نامە/IP/ڕۆژ) — pro: لیمیت ڕۆژانەی توند (٤٢٩٠١٦)
# ════════════════════════════════════════════════════════════

NG_LIMIT = {"until": 0.0}


def ng_servers():
    return [{"id": "ng-gemini-flash-lite", "name": "Gemini 3.1 Flash Lite (NoteGPT)",
             "model_id": "gemini-3.1-flash-lite", "kind": "ng"}]


def ng_chat(messages, timeout=110):
    """چاتی notegpt — مێژوو بۆ یەک نامە؛ template ی homework یش لابردن"""
    import time as _t
    if _t.time() < NG_LIMIT["until"]:
        raise EMError("ng: cooldown")
    sys_txt = " ".join(m["content"] for m in messages if m.get("role") == "system")[:1000]
    user_txt = ""
    for m in reversed(messages):
        if m.get("role") == "user":
            user_txt = m["content"]
            break
    if not user_txt:
        user_txt = " ".join(m.get("content", "") for m in messages)[-2000:]
    if sys_txt:
        user_txt = f"[ئاراستەی سیستەم: {sys_txt}]\n\n{user_txt}"
    try:
        r = requests.post("https://notegpt.io/api/v2/homework/stream",
                          json={"message": user_txt, "language": "auto", "model": "gemini-3.1-flash-lite",
                                "tone": "default", "length": "moderate",
                                "conversation_id": str(__import__("uuid").uuid4())},
                          headers={"User-Agent": ACT_UAS[random.randrange(len(ACT_UAS))],
                                   "Origin": "https://notegpt.io",
                                   "Referer": "https://notegpt.io/ai-answer-generator"},
                          timeout=(15, timeout), stream=True)
    except Exception as e:
        raise EMError(f"ng: {str(e)[:60]}")
    if r.status_code != 200:
        if r.status_code == 429:
            NG_LIMIT["until"] = _t.time() + 1800
        raise EMError(f"ng: {r.status_code}")
    text = []
    limit_hit = False
    for line in r.iter_lines(decode_unicode=True):
        if not line or not line.startswith("data: "):
            continue
        try:
            d = json.loads(line[6:])
        except Exception:
            continue
        if isinstance(d.get("text"), str):
            text.append(d["text"])
        if d.get("code") == 164016:
            limit_hit = True
    ans = "".join(text).strip()
    if limit_hit and not ans:
        NG_LIMIT["until"] = _t.time() + 1800
        raise EMError("ng: لیمیت ڕۆژانە")
    # template ی homework پاک بکەوە
    ans = re.sub(r"^###\s*Question\s*\d*\s*", "", ans)
    ans = re.sub(r"\n?###\s*(Answer|Solution Steps|[^\n]*)\s*", "\n", ans)
    ans = ans.strip()
    if ans:
        return ans
    raise EMError("ng: وەڵام نەگەڕایەوە")


# ─── یەکسانکردنی مۆدێڵ بۆ fallback — هەمان خێزان لە سەرچاوەیەکی تر ───
_MODEL_HINTS = [
    ("gemini", "gemini"), ("claude", "claude"), ("grok", "grok"),
    ("kimi", "kimi"), ("moonshot", "kimi"), ("qwen", "qwen"),
    ("glm", "glm"), ("z-ai", "glm"), ("deepseek", "deepseek"),
    ("llama", "llama"), ("meta-llama", "llama"), ("phi", "phi"),
    ("hy3", "hy3"), ("tencent", "hy3"), ("gemma", "gemma"),
    ("oss", "gpt"), ("o4", "gpt"), ("o3", "gpt"), ("gpt", "gpt"),
]


def _model_family(mid):
    s = str(mid).lower()
    for k, fam in _MODEL_HINTS:
        if k in s:
            return fam
    return "gpt"


def pick_in_kind(servers, kind, wanted):
    """باشترین مۆدێڵی هاوشێوە لە سەرچاوەیەکی تر — بۆ fallback ی ورد"""
    fam = _model_family(wanted)
    same = [x for x in servers if x.get("kind") == kind]
    if not same:
        return None
    for x in same:
        if _model_family(x["id"]) == fam:
            return x
    return same[0]


# ════════════════════════════════════════════════════════════
# ٣) کلایەنتی aifreeforever
# ════════════════════════════════════════════════════════════

class AIFreeError(Exception):
    pass


class AIFreeChat:
    def __init__(self, model, endpoint=None, timeout=120):
        self.model = model
        self.endpoint = endpoint if (endpoint or "").startswith("http") else BASE_URL + (endpoint or "")
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": UA,
            "Content-Type": "application/json",
            "Origin": BASE_URL,
            "Referer": BASE_URL + "/chat/" + model,
        })
        self._nonce = ""

    def _fetch_nonce(self):
        n = ""
        try:
            n = self.session.get(BASE_URL + "/api/chat-nonce", timeout=15).json().get("nonce", "")
        except Exception:
            n = ""
        if not n:
            # ماڵپەرەکە نۆنس بەتاڵ دەدات مەگەر سەرەتا سەردانی پەڕەی چات بکرێت (کوکی سێشن)
            try:
                self.session.headers.pop("Content-Type", None)
                self.session.get(BASE_URL + "/chat/" + self.model, timeout=20)
                self.session.headers["Content-Type"] = "application/json"
                n = self.session.get(BASE_URL + "/api/chat-nonce", timeout=15).json().get("nonce", "")
            except Exception:
                n = ""
        return n

    @staticmethod
    def _proof():
        now = int(time.time() * 1000)
        start = now - random.randint(4000, 15000)
        return {"nonce": "", "keystrokeCount": random.randint(20, 120),
                "pasteEvents": 0, "totalTypingTime": now - start,
                "startTime": start, "submitTime": now}

    def chat(self, question, history=None):
        payload = {
            "model": self.model, "question": question, "tone": "friendly",
            "format": "paragraph", "file": None,
            "conversationHistory": (history or [])[-20:],
            "interactionProof": self._proof(),
            "aiRole": "assistant", "aiName": "", "language": "auto",
        }
        last = None
        for attempt in range(3):
            try:
                if not self._nonce:
                    self._nonce = self._fetch_nonce()
                payload["interactionProof"]["nonce"] = self._nonce
                with self.session.post(self.endpoint, json=payload, stream=True,
                                       timeout=(15, self.timeout)) as r:
                    if r.status_code == 429:
                        raise AIFreeError("طلبات كثيرة بسرعة (429) — انتظر قليلا.")
                    if r.status_code in (403, 407, 502, 503):
                        raise ConnectionError(f"داخستن ({r.status_code})")
                    if r.status_code == 409:
                        raise AIFreeError("سێرڤەرەکە ئێستا بەردەست نییە (409).")
                    r.raise_for_status()
                    ctype = r.headers.get("content-type", "")
                    answer = ""
                    if "text/event-stream" in ctype:
                        for raw in r.iter_lines():
                            line = raw.decode("utf-8", errors="replace") if isinstance(raw, bytes) else raw
                            if not line.startswith("data: "):
                                continue
                            d = line[6:].strip()
                            if d == "[DONE]":
                                break
                            try:
                                answer += json.loads(d).get("token", "")
                            except Exception:
                                pass
                    else:
                        answer = (r.json() or {}).get("answer", "")
                    if not answer:
                        raise ConnectionError("aff: وەڵامی بەتاڵ — نۆنسی نوێ پێویستە")
                    return answer
            except AIFreeError:
                raise
            except Exception as e:
                last = e
                self._nonce = ""
                time.sleep(1.2 * (attempt + 1))
        raise ConnectionError(str(last))


# ════════════════════════════════════════════════════════════
# ٤) API — ڕووکاری HTTP (OpenAI-compatible + سادە)
# ════════════════════════════════════════════════════════════

API_PORT = int(os.environ.get("API_PORT", 8080))
API_KEY = os.environ.get("API_KEY", "")  # ئەگەر دانرابێت — پێویستە لە هەر داواکارییەک

# ─── پرۆمپتی بنەڕەتی API — شێوازی پرسیار و وەڵامی شەرعی (کوردی) ───
# ئەگەر ئەپەکەت سیستەم پرۆمپتی خۆی نەنێرێت، ئەمە بەکاردێت
# ⚡ مێشکی سەربەخۆی API — تەواو جیاواز لە بۆتی تێلەگرام
# بێ سیستەم پرۆمپت، بێ کەسایەتی، بێ یاساکانی بۆتەکە
API_BRAIN = {"mode": None, "servers": [], "t": 0.0}
API_REFRESH_SEC = 300


def detect_brain_api():
    """هەمان لیستی بۆت — easemate + aifreeforever + pollinations"""
    return detect_brain(allow_fallback=True)


def api_brain_ensure():
    """لیستی سێرڤەرەکانی API تازە دەکاتەوە — هەر ٥ خولەک، سەربەخۆ"""
    if API_BRAIN["servers"] and time.time() - API_BRAIN["t"] < API_REFRESH_SEC:
        return
    new = detect_brain_api()
    if new["servers"]:
        API_BRAIN["mode"], API_BRAIN["servers"] = new["mode"], new["servers"]
        API_BRAIN["t"] = time.time()
        print(f"[API-BRAIN] {new['mode']} ({len(new['servers'])} سێرڤەر)", flush=True)


def _api_servers():
    # ناوە ڕاستەقینەکانی مۆدەڵەکان — وەک خۆیان (gemini-3-1، gpt-5-mini، …)
    return [{"alias": x["id"], "id": x["id"], "name": x.get("name", x["id"])}
            for x in API_BRAIN["servers"]]


def _resolve_server(ref):
    ref = str(ref).strip().lower()
    for i, x in enumerate(API_BRAIN["servers"], 1):
        if ref in (f"server-{i}", str(i)) or ref == str(x["id"]).lower() or ref == str(x.get("alias", "")).lower():
            y = dict(x)
            y["alias"] = f"server-{i}"
            return y
    num = ref[3:] if ref.startswith("em-") else ref
    if num.isdigit():
        for x in API_BRAIN["servers"]:
            if x.get("kind") == "em" and str(x["model_id"]) == num:
                y = dict(x)
                y["alias"] = x["id"]
                return y
    return None


class APIHandler(http.server.BaseHTTPRequestHandler):
    def _send(self, code, obj):
        b = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(b)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(b)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Authorization, X-API-Key, Content-Type")
        self.end_headers()

    def log_message(self, *a):
        pass

    def _authed(self):
        if not API_KEY:
            return True
        h = self.headers.get("Authorization", "")
        k = self.headers.get("X-API-Key", "")
        return h == f"Bearer {API_KEY}" or k == API_KEY

    def _body(self):
        n = int(self.headers.get("Content-Length", 0))
        return json.loads(self.rfile.read(n) or b"{}")

    def do_GET(self):
        if self.path in ("/", "/health"):
            api_brain_ensure()
            self._send(200, {"ok": True, "service": "smart-chatbot-api",
                             "mode": API_BRAIN["mode"], "servers": len(API_BRAIN["servers"])})
        elif self.path in ("/models", "/v1/models"):
            if not self._authed():
                return self._send(401, {"error": "API_KEY هەڵەیە — Authorization: Bearer <key>"})
            api_brain_ensure()
            data = [{"id": s["alias"], "object": "model", "owned_by": "smart-chatbot"}
                    for s in _api_servers()]
            self._send(200, {"object": "list", "data": data})
        else:
            self._send(404, {"error": "not found — /v1/chat/completions و /v1/models"})

    def do_POST(self):
        if self.path not in ("/chat", "/v1/chat/completions"):
            return self._send(404, {"error": "not found"})
        if not self._authed():
            return self._send(401, {"error": "API_KEY هەڵەیە — Authorization: Bearer <key>"})

        try:
            body = self._body()
        except Exception:
            return self._send(400, {"error": "bad json"})

        openai_style = self.path == "/v1/chat/completions"
        want_stream = bool(body.get("stream")) and openai_style

        if openai_style:
            ref = body.get("model") or "1"
            msgs = body.get("messages") or []
            q = ""
            for m in reversed(msgs):
                if m.get("role") == "user":
                    q = m.get("content", "")
                    break
            history = [{"role": m.get("role", "user"), "content": m.get("content", "")}
                       for m in msgs if m.get("role") in ("user", "assistant", "system")][-20:]
        else:
            ref = body.get("server") or body.get("model") or 1
            q = (body.get("message") or "").strip()
            history = body.get("history") or []
            msgs = history + [{"role": "user", "content": q}]

        if not q:
            return self._send(400, {"error": "پرسیار بەتاڵە"})


        api_brain_ensure()
        if not _resolve_server(ref):
            return self._send(400, {"error": f"خادم غير معروف: {ref} — راجع /v1/models"})
        srv = _resolve_server(ref)

        print(f"[API] server={srv['id']} q={q[:50]}", flush=True)

        # ⚡ API سەربەخۆیە: تەنها نامەکانی داواکار بەکاردەهێنێت —
        # هیچ سیستەم پرۆمپت یان یاسای بۆتەکە لێرەدا نییە
        # زنجیرەی هەوڵ: سێرڤەری هەڵبژێردراو + یەکێک لە هەر سەرچاوەیەکی تر
        order = [srv]
        for kind in ("em", "aff", "cbc", "rwd", "pol"):
            if srv.get("kind") != kind:
                cand = pick_in_kind(API_BRAIN["servers"], kind, srv["id"])
                if cand and cand not in order:
                    order.append(cand)

        content, last_err = "", None
        for cand in order:
            try:
                kind = cand.get("kind")
                if kind == "em":
                    content = em_chat(history, cand["model_id"])
                elif kind == "aff":
                    content = AIFreeChat(model=cand["id"], endpoint=cand.get("endpoint")).chat(q, history=history)
                elif kind == "cbc":
                    content = cbc_chat(history)
                elif kind == "rwd":
                    content = rwd_chat(cand["model_id"], history + [{"role": "user", "content": q}])
                elif kind == "act":
                    content = act_chat(cand["model_id"], history + [{"role": "user", "content": q}])
                elif kind == "fla":
                    content = fla_chat(history + [{"role": "user", "content": q}])
                elif kind == "z02":
                    content = z02_chat(history + [{"role": "user", "content": q}], cand["model_id"])
                elif kind == "qb":
                    content = qb_chat(history + [{"role": "user", "content": q}])
                elif kind == "duck":
                    content = duck_chat(cand["model_id"], history + [{"role": "user", "content": q}])
                elif kind == "ak":
                    content = ak_chat(cand["model_id"], history + [{"role": "user", "content": q}])
                elif kind == "ng":
                    content = ng_chat(history + [{"role": "user", "content": q}])
                else:
                    content = pol_chat(cand["id"], history + [{"role": "user", "content": q}])
                if content:
                    if cand is not srv:
                        print(f"[API] fallback → {kind}", flush=True)
                    break
            except Exception as e:
                last_err = e
                print(f"[API] {cand.get('kind')} هەڵە: {str(e)[:90]}", flush=True)
        if not content:
            # ═══ دیلی نەوە (API): مۆدێڵی داواکراو مردووە → نوێترین نەوەی هەمان خێزان ═══
            try:
                up = smart_rebind(API_BRAIN["servers"], srv["id"])
                if up and up != srv["id"]:
                    nsrv = next(x for x in API_BRAIN["servers"] if x["id"] == up)
                    print(f"[API] 🔄 دیلی نەوە: {srv['id']} → {up}", flush=True)
                    k = nsrv.get("kind")
                    nmsgs = history + [{"role": "user", "content": q}]
                    if k == "em":
                        content = em_chat(nmsgs, nsrv["model_id"])
                    elif k == "cbc":
                        content = cbc_chat(nmsgs)
                    elif k == "rwd":
                        content = rwd_chat(nsrv["model_id"], nmsgs)
                    elif k == "act":
                        content = act_chat(nsrv["model_id"], nmsgs)
                    elif k == "fla":
                        content = fla_chat(nmsgs)
                    elif k == "z02":
                        content = z02_chat(nmsgs, nsrv["model_id"])
                    elif k == "qb":
                        content = qb_chat(nmsgs)
                    elif k == "duck":
                        content = duck_chat(nsrv["model_id"], nmsgs)
                    elif k == "ak":
                        content = ak_chat(nsrv["model_id"], nmsgs)
                    elif k == "ng":
                        content = ng_chat(nmsgs)
                    else:
                        content = pol_chat(nsrv["id"], nmsgs)
                    if content:
                        print(f"[API] ✅ نەوەی نوێ وەڵامی دا: {up}", flush=True)
            except Exception as e2:
                print(f"[API] دیلی نەوە شکستی هێنا: {str(e2)[:90]}", flush=True)
        if not content:
            return self._send(502, {"error": str(last_err) if last_err else "هیچ سەرچاوەیەک وەڵام نەدایەوە"})

        cid = "chatcmpl-" + "".join(random.choices("abcdef0123456789", k=12))
        now = int(time.time())
        if want_stream:
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()

            def sse(obj):
                self.wfile.write(b"data: " + json.dumps(obj, ensure_ascii=False).encode("utf-8") + b"\n\n")
                self.wfile.flush()

            for i in range(0, len(content), 80):
                sse({"id": cid, "object": "chat.completion.chunk", "created": now,
                     "model": srv["id"],
                     "choices": [{"index": 0, "delta": {"content": content[i:i+80]}, "finish_reason": None}]})
            sse({"id": cid, "object": "chat.completion.chunk", "created": now,
                 "model": srv["id"],
                 "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]})
            self.wfile.write(b"data: [DONE]\n\n")
        elif openai_style:
            self._send(200, {
                "id": cid, "object": "chat.completion", "created": now, "model": srv["id"],
                "choices": [{"index": 0,
                             "message": {"role": "assistant", "content": content},
                             "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            })
        else:
            self._send(200, {"answer": content, "server": srv["id"]})


def start_api():
    """دەستپێکردنی سێرڤەری API لە تڕێدێکی جیاواز"""
    socketserver.ThreadingTCPServer.allow_reuse_address = True

    class TS(socketserver.ThreadingMixIn, http.server.HTTPServer):
        daemon_threads = True

    try:
        srv = TS(("0.0.0.0", API_PORT), APIHandler)
    except OSError as e:
        print(f"[API] پۆرتی {API_PORT} بەکارهاتووە: {e}", flush=True)
        return
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    print(f"[API] ✅ API کارا کەوت — http://0.0.0.0:{API_PORT} (/v1/chat/completions)", flush=True)


# ════════════════════════════════════════════════════════════
# ٥) تێلەگرام
# ════════════════════════════════════════════════════════════

import os
TOKEN = os.environ.get("BOT_TOKEN") or "8664695955:AAElPxr8spsa--KqsAzHG6Pa4FWnjBmBPQc"
API = f"https://api.telegram.org/bot{TOKEN}"

WELCOME = (
    "🤖 <b>أهلا بك! أنا بوت الدكتور التعافي</b>\n\n"
    "أنا معك خطوة بخطوة في رحلة التعافي — اكتب أي شيء وسأسمعك\n\n"
    "🔹 <b>الأوامر:</b>\n"
    "/new — محادثة جديدة\n"
    "/server — قائمة الموديلات (الأحدث دائما)\n"
    "/about — معلومات عن البوت"
)

ABOUT = (
    "ℹ️ <b>عن هذا البوت</b>\n\n"
    "بوت الدكتور التعافي — مستشار نفسي وشرعي لمساعدتكم على التعافي من الإدمان\n\n"
    "🛡 <b>الخصوصية</b>\n"
    "كل محادثاتكم محفوظة ومشفرة ولا يمكن لأحد الاطلاع عليها حتى مالك البوت نفسه لا يستطيع رؤيتها\n\n"
    "👤 صُنع بواسطة: <b>يوسف الكردي</b>\n"
    "❤️ لخدمة المدمنين على الإباحة وعادة الاستمناء\n\n"
    "🤖 /server — قائمة الموديلات\n"
    "💬 /new — محادثة جديدة"
)

# ژووری گفتوگۆی هەر بەکارهێنەرێک
sessions = {}   # user → {"server": id, "history": [...]}
pending = {}    # user → {"1": server, ...}
BRAIN = {"mode": None, "servers": []}

# دەستنیشانکردنی لێکدانی ناوی مۆدێڵ — هەرگیز ناوی مۆدێڵ ناکرێتەوە
_LEAK_NORM = str.maketrans({"ي": "ی", "ێ": "ی", "ى": "ی", "ك": "ک"})
LEAK_RE = re.compile(r"\b(glm|gpt|claude|gemini|deepseek|qwen|llama|grok|kimi|mistral)[\w.\-]*\b|o4[\s\-]?mini|\bzerotwo\b|zero\s?two|\bquillbot\b|\bduckai\b|duck\s*\.?\s*ai\b|\banakin\b|ئەنەکین|\bnotegpt\b|نۆت\s?جی\s?پی\s?تی|(قوین|جی\s*بی\s*تی|جیمینی|دیب\s*سیک|کلود|میسترال|زێرۆ\s?تۆ|کویل|داک)\s*\d*", re.I)


def leaks(s):
    return bool(LEAK_RE.search(str(s).translate(_LEAK_NORM)))
_lock = threading.Lock()


def tg(method, **params):
    try:
        r = requests.post(f"{API}/{method}", json=params, timeout=(15, 25))
        return r.json()
    except Exception as e:
        print(f"[TG] {method}: {e}", flush=True)
        return {"ok": False, "description": str(e)}


def detect_brain(allow_fallback=True):
    """هەر دوو سێرڤەرەکە تێکەڵ بۆ بۆت — easemate + aifreeforever + pollinations — مۆدێل ئایدی ڕاستەقینە"""
    servers = []
    try:
        servers += em_servers()
    except Exception as e:
        print(f"[BRAIN] em fail: {e}", flush=True)
    try:
        for x in get_aff_servers(hide=False):
            y = dict(x); y["kind"] = "aff"; servers.append(y)
    except Exception:
        pass
    try:
        servers.append({"id": "cbc-gpt5", "name": "GPT-5", "kind": "cbc"})
    except Exception:
        pass
    try:
        servers += rwd_servers()
    except Exception as e:
        print(f"[BRAIN] rwd fail: {e}", flush=True)
    try:
        servers += act_servers()
    except Exception as e:
        print(f"[BRAIN] act fail: {e}", flush=True)
    try:
        servers += fla_servers()
    except Exception as e:
        print(f"[BRAIN] fla fail: {e}", flush=True)
    try:
        servers += z02_servers()
    except Exception as e:
        print(f"[BRAIN] z02 fail: {e}", flush=True)
    try:
        servers += qb_servers()
    except Exception as e:
        print(f"[BRAIN] qb fail: {e}", flush=True)
    try:
        servers += duck_servers()
    except Exception as e:
        print(f"[BRAIN] duck fail: {e}", flush=True)
    try:
        servers += ak_servers()
    except Exception as e:
        print(f"[BRAIN] ak fail: {e}", flush=True)
    try:
        servers += ng_servers()
    except Exception as e:
        print(f"[BRAIN] ng fail: {e}", flush=True)
    # pol هەمیشە لە زنجیرەکەدا بێت — لێگی کۆتایی (نەک تەنها فەڵباکی کۆتایی)
    try:
        pol_list = get_pol_servers()
        if pol_list:
            for x in pol_list:
                y = dict(x); y["kind"] = "pol"; servers.append(y)
    except Exception:
        pass
    if servers:
        return {"mode": "multi", "servers": servers}
    return {"mode": None, "servers": []}


def auto_refresh():
    """هەر ٥ خولەک لیستی سێرڤەرەکان نوێ دەکاتەوە —
    هەر مۆدەڵێکی نوێ لە ماڵپەرەکە خۆکارانە دەچێتە ناو سیستەمەکە"""
    while True:
        time.sleep(300)
        try:
            new = detect_brain(allow_fallback=False)
            if not new["servers"]:
                continue  # ماڵپەرەکە کاتییەکە بەردەست نییە — دۆخی ئێستا بمێنێتەوە
            with _lock:
                changed = (new["mode"] != BRAIN["mode"] or
                           [x["id"] for x in new["servers"]] != [x["id"] for x in BRAIN["servers"]])
                BRAIN["mode"], BRAIN["servers"] = new["mode"], new["servers"]
                valid = {x["id"] for x in new["servers"]}
                reborn = 0
                for s in sessions.values():
                    if s["server"] not in valid:
                        # ١. هەمان مۆدێڵ لە سەرچاوەیەکی تر
                        mk = s.get("mkey") or norm_model(s["server"])
                        rebind = next((x["id"] for x in new["servers"] if norm_model(x["id"]) == mk), None)
                        if rebind:
                            s["server"] = rebind
                            continue
                        # ٢. دیلی نەوە — مۆدێڵەکە لابرا → نوێترین نەوەی هەمان خێزان
                        up = smart_rebind(new["servers"], s["server"])
                        if up:
                            s["server"] = up
                            s["mkey"] = norm_model(up)
                            reborn += 1
                if reborn:
                    print(f"[REFRESH] 🔄 {reborn} سێشن بۆ نەوەی نوێتر نەقڵکران", flush=True)
            if changed:
                print(f"[REFRESH] ✨ لیستەکە نوێکرایەوە — {new['mode']} ({len(new['servers'])} سێرڤەر)", flush=True)
        except Exception as e:
            print(f"[REFRESH] هەڵە: {e}", flush=True)


# ─── یەکخستنی مۆدێلە دووبارەکان — هەمان مۆدێڵ لە چەند سەرچاوە = یەک دەنگ ───
_MERGE_SUFFIXES = ("-orbio", "-0731", "-0813", "-preview")


def norm_model(mid):
    """کلیلێکی یەکگر بۆ ناسینی هەمان مۆدێڵ لە سەرچاوەی جیاواز"""
    s = str(mid).lower().strip()
    if "/" in s:
        s = s.split("/")[-1]
    s = s.replace("_", "-").replace(".", "-")
    for suf in _MERGE_SUFFIXES:
        if s.endswith(suf):
            s = s[:-len(suf)]
    return s


def dedupe_servers(servers):
    """یەکێک بۆ هەر مۆدێڵ — یەکەم سەرچاوە (easemate) دەبێتە سەرەکی"""
    seen = set()
    uniq = []
    for x in servers:
        k = norm_model(x["id"])
        if k in seen:
            continue
        seen.add(k)
        uniq.append(x)
    return uniq


# ════════════════════════════════════════════════════════════
# ٢.٨) نەوەکان — دەزانی «نوێترین» ی هەر خێزانێک کامەیە
#      بۆ دیل ی خۆکاری: مۆدێڵی نامۆ → نوێترین نەوەی هەمان خێزان
# ════════════════════════════════════════════════════════════

import re as _re

# خشتەی نەوە — بەرزتر = نوێتر (خێزان → لیستی دوایینی بەشەکانی ژمارە)
_GEN_VERSIONS = {
    "gemini": [("3.8", [3, 8]), ("3.6", [3, 6]), ("3.5", [3, 5]), ("3.1", [3, 1]), ("3", [3]), ("2.5", [2, 5]), ("2", [2]), ("1.5", [1, 5])],
    "claude": [("5", [5]), ("4.8", [4, 8]), ("4.7", [4, 7]), ("4.6", [4, 6]), ("4.5", [4, 5]), ("4.1", [4, 1]), ("4", [4]), ("3.7", [3, 7]), ("3.5", [3, 5])],
    "gpt": [("5.6", [5, 6]), ("5.5", [5, 5]), ("5.4", [5, 4]), ("5.2", [5, 2]), ("5.1", [5, 1]), ("5", [5]), ("4.1", [4, 1]), ("4o", [4]), ("4", [4])],
    "grok": [("4.6", [4, 6]), ("4.5", [4, 5]), ("4.3", [4, 3]), ("4", [4]), ("3", [3])],
    "deepseek": [("v4.1", [4, 1]), ("v4", [4]), ("v3.2", [3, 2]), ("r1", [1]), ("v3", [3])],
    "qwen": [("3.8", [3, 8]), ("3.7", [3, 7]), ("3.6", [3, 6]), ("3.5", [3, 5]), ("3", [3]), ("2.5", [2, 5])],
    "glm": [("5.3", [5, 3]), ("5.2", [5, 2]), ("5.1", [5, 1]), ("5", [5]), ("4.7", [4, 7]), ("4.5", [4, 5])],
    "kimi": [("k2.6", [2, 6]), ("k2.5", [2, 5]), ("k2", [2])],
    "llama": [("4", [4]), ("3.3", [3, 3]), ("3.2", [3, 2]), ("3.1", [3, 1]), ("3", [3])],
    "nova": [("2", [2]), ("1", [1])],
    "phi": [("4", [4]), ("3", [3])],
    "hy3": [("4", [4]), ("3", [3])],
    "gemma": [("4", [4]), ("3", [3]), ("2", [2])],
}


def _gen_key(mid):
    """(خێزان، ژمارەی نەوە) — بۆ ڕیزکردن. بۆ نموونە gemini-3.8 → ('gemini', 3.8)"""
    s = str(mid).lower()
    fam = _model_family(s)
    ver = None
    if fam in _GEN_VERSIONS:
        nums = _re.findall(r"(\d+(?:\.\d+)?)", s)
        if nums:
            try:
                ver = float(nums[0])
            except ValueError:
                ver = None
    return (fam, ver if ver is not None else 0.0)


def _same_gen(a, b):
    """ئایا ئەم دوو مۆدێڵە هەمان نەوەن؟ (خێزان + ژمارەی سەرەکی یەکسان)"""
    fa, va = _gen_key(a)
    fb, vb = _gen_key(b)
    if fa != fb:
        return False
    if va == vb:
        return True
    # 3 و 3.0 و 3.8 → بەراوردی ژمارەی سەرەکی
    return int(va) == int(vb)


def _newest_in_family(servers, fam, exclude_id=None):
    """نوێترین مۆدێڵی زیندووی خێزانێک (کار دەکات + ئێستا لە لیستەکەدا هەیە)"""
    best, best_v = None, -1.0
    for x in servers:
        if exclude_id and x["id"] == exclude_id:
            continue
        f, v = _gen_key(x["id"])
        if f == fam and v > best_v:
            best, best_v = x, v
    return best


def _gen_upgrade_candidates(servers, dead_id):
    """کاندیدەکانی دیل بۆ مۆدێڵێکی مردوو: هەمان نەوە یان نوێتر، لە هەمان خێزان،
       ڕیزکراو بە نوێترین. هەرگیز مۆدێڵی کۆنتر نادات."""
    fam, dead_v = _gen_key(dead_id)
    cands = []
    for x in servers:
        f, v = _gen_key(x["id"])
        if f == fam and v >= dead_v:
            if x["id"] != dead_id and x not in cands:
                cands.append(x)
    cands.sort(key=lambda x: _gen_key(x["id"])[1], reverse=True)
    if not cands:
        nx = _newest_in_family(servers, fam)
        if nx:
            cands.append(nx)
    return cands


def smart_rebind(servers, dead_id):
    """دیلی زیرەک: مۆدێڵێکی نامۆ → نوێترین هەمان نەوە/نوێتر لە هەمان خێزان.
       ئەگەر هیچ نەبوو → None (پاشان فەڵباکی ئاسایی)."""
    if not dead_id:
        return None
    for c in _gen_upgrade_candidates(servers, dead_id):
        return c["id"]
    return None


def get_session(user_id):
    with _lock:
        s = sessions.get(user_id)
        if s is None:
            default = BRAIN["servers"][0]["id"] if BRAIN["servers"] else "openai"
            s = {"server": default, "history": [], "mkey": norm_model(default) if default else None}
            sessions[user_id] = s
        return s


def ask(session, question):
    """پرسیار — مۆدێڵی هەڵبژارد + زنجیرەی fallback: easemate → aifreeforever → pollinations"""
    history = session["history"]
    sys_msg = {"role": "system", "content": SYSTEM_PROMPT}
    srv = next((x for x in BRAIN["servers"] if x["id"] == session["server"]), None)
    if not srv and BRAIN["servers"]:
        # ١. هەمان مۆدێڵ لە سەرچاوەیەکی تر
        mk = session.get("mkey") or norm_model(session.get("server") or "")
        if mk:
            srv = next((x for x in BRAIN["servers"] if norm_model(x["id"]) == mk), None)
            if srv:
                session["server"] = srv["id"]
    if not srv and BRAIN["servers"]:
        # ٢. هاوشێوەترین بەپێی خێزان — بەڵام هەڵبژاردەکە ناگۆڕدرێت
        fam = _model_family(session.get("server") or "")
        srv = pick_in_kind(BRAIN["servers"], fam, session.get("server") or "gpt") if fam else None
        if not srv:
            srv = BRAIN["servers"][0]
    order = []
    if srv:
        order.append(srv)
    for kind in ("em", "aff", "cbc", "rwd", "pol"):
        if srv and srv.get("kind") == kind:
            continue
        cand = pick_in_kind(BRAIN["servers"], kind, srv["id"] if srv else "gpt")
        if cand and cand not in order:
            order.append(cand)
    last = None
    for cand in order:
        try:
            k = cand.get("kind")
            if k == "em":
                msgs = [sys_msg] + history[-20:] + [{"role": "user", "content": question}]
                return em_chat(msgs, cand["model_id"]), "em"
            if k == "aff":
                bot = AIFreeChat(model=cand["id"], endpoint=cand.get("endpoint"))
                a = bot.chat(question, history=[sys_msg] + history)
                if leaks(a):
                    raise EMError("identity leak")
                return a, "aff"
            if k == "cbc":
                msgs = [sys_msg] + history[-20:] + [{"role": "user", "content": question}]
                return cbc_chat(msgs), "cbc"
            if k == "rwd":
                msgs = [sys_msg] + history[-20:] + [{"role": "user", "content": question}]
                a = rwd_chat(cand["model_id"], msgs)
                if leaks(a):
                    raise EMError("identity leak")
                return a, "rwd"
            if k == "act":
                msgs = [sys_msg] + history[-20:] + [{"role": "user", "content": question}]
                a = act_chat(cand["model_id"], msgs)
                if leaks(a):
                    raise EMError("identity leak")
                return a, "act"
            if k == "fla":
                msgs = [sys_msg] + history[-20:] + [{"role": "user", "content": question}]
                a = fla_chat(msgs)
                if leaks(a):
                    raise EMError("identity leak")
                return a, "fla"
            if k == "z02":
                msgs = [sys_msg] + history[-20:] + [{"role": "user", "content": question}]
                a = z02_chat(msgs, cand["model_id"])
                if leaks(a):
                    raise EMError("identity leak")
                return a, "z02"
            if k == "qb":
                msgs = [sys_msg] + history[-20:] + [{"role": "user", "content": question}]
                a = qb_chat(msgs)
                if leaks(a):
                    raise EMError("identity leak")
                return a, "qb"
            if k == "duck":
                msgs = [sys_msg] + history[-20:] + [{"role": "user", "content": question}]
                a = duck_chat(cand["model_id"], msgs)
                if leaks(a):
                    raise EMError("identity leak")
                return a, "duck"
            if k == "ak":
                msgs = [sys_msg] + history[-20:] + [{"role": "user", "content": question}]
                a = ak_chat(cand["model_id"], msgs)
                if leaks(a):
                    raise EMError("identity leak")
                return a, "ak"
            if k == "ng":
                msgs = [sys_msg] + history[-20:] + [{"role": "user", "content": question}]
                a = ng_chat(msgs)
                if leaks(a):
                    raise EMError("identity leak")
                return a, "ng"
            msgs = [sys_msg] + list(history[-20:]) + [{"role": "user", "content": question}]
            return pol_chat(cand["id"], msgs), "pol"
        except Exception as e:
            last = e
            print(f"[BRAIN] {cand.get('kind', '?')} ({cand.get('id', '?')}) هەڵە: {str(e)[:80]}", flush=True)
    # ═══ دیلی نەوە: هەموو زنجیرەکە بۆ ئەم مۆدێڵە مردووە → نوێترین نەوە بپشکنە ═══
    if BRAIN["servers"] and question:
        try:
            dead_id = session.get("server") or ""
            up = smart_rebind(BRAIN["servers"], dead_id)
            if up and up != dead_id:
                nsrv = next(x for x in BRAIN["servers"] if x["id"] == up)
                print(f"[BRAIN] 🔄 دیلی نەوە: {dead_id} → {up}", flush=True)
                k = nsrv.get("kind")
                nmsgs = [sys_msg] + history[-20:] + [{"role": "user", "content": question}]
                if k == "em":
                    return em_chat(nmsgs, nsrv["model_id"]), "em"
                if k == "cbc":
                    return cbc_chat(nmsgs), "cbc"
                if k == "rwd":
                    a = rwd_chat(nsrv["model_id"], nmsgs)
                    if leaks(a):
                        raise EMError("identity leak")
                    return a, "rwd"
                if k == "act":
                    a = act_chat(nsrv["model_id"], nmsgs)
                    if leaks(a):
                        raise EMError("identity leak")
                    return a, "act"
                if k == "fla":
                    a = fla_chat(nmsgs)
                    if leaks(a):
                        raise EMError("identity leak")
                    return a, "fla"
                if k == "z02":
                    a = z02_chat(nmsgs, nsrv["model_id"])
                    if leaks(a):
                        raise EMError("identity leak")
                    return a, "z02"
                if k == "qb":
                    a = qb_chat(nmsgs)
                    if leaks(a):
                        raise EMError("identity leak")
                    return a, "qb"
                if k == "duck":
                    a = duck_chat(nsrv["model_id"], nmsgs)
                    if leaks(a):
                        raise EMError("identity leak")
                    return a, "duck"
                if k == "ak":
                    a = ak_chat(nsrv["model_id"], nmsgs)
                    if leaks(a):
                        raise EMError("identity leak")
                    return a, "ak"
                if k == "ng":
                    a = ng_chat(nmsgs)
                    if leaks(a):
                        raise EMError("identity leak")
                    return a, "ng"
                return pol_chat(nsrv["id"], nmsgs), "pol"
        except Exception as e2:
            print(f"[BRAIN] دیلی نەوە شکستی هێنا: {str(e2)[:80]}", flush=True)
            last = e2
    raise last or RuntimeError("هیچ مێشکێک بەردەست نییە")


def split_msg(t, n=3900):
    return [t[i:i + n] for i in range(0, len(t), n)]


def keep_typing(chat_id, stop):
    while not stop.is_set():
        tg("sendChatAction", chat_id=chat_id, action="typing")
        stop.wait(4.0)


def reply(chat_id, text):
    r = tg("sendMessage", chat_id=chat_id, text=text, parse_mode="HTML",
           disable_web_page_preview=True)
    if not r.get("ok"):
        for part in split_msg(text):
            tg("sendMessage", chat_id=chat_id, text=part.replace("<", "&lt;"))


def handle_message(msg):
    chat_id = msg["chat"]["id"]
    user_id = msg.get("from", {}).get("id", chat_id)
    text = (msg.get("text") or "").strip()
    if not text:
        return

    print(f"[MSG] user={user_id}: {text[:60]}", flush=True)

    if text.startswith("/start"):
        reply(chat_id, WELCOME)
        return
    if text.startswith("/about"):
        reply(chat_id, ABOUT)
        return
    if text.startswith("/new"):
        get_session(user_id)["history"].clear()
        reply(chat_id, "✨ <b>بدأنا محادثة جديدة</b>\nاكتب رسالتك وسنبدأ خطوة بخطوة")
        return

    if text.startswith("/server"):
        reply(chat_id, "🔄 <b>يتم جلب أحدث قائمة…</b>")
        new = detect_brain()
        if not new["servers"]:
            reply(chat_id, "⚠️ <b>تعذر جلب القائمة.</b> حاول بعد قليل.")
            return
        with _lock:
            BRAIN["mode"], BRAIN["servers"] = new["mode"], new["servers"]
        servers = new["servers"]
        s = get_session(user_id)
        if s["server"] not in [x["id"] for x in servers]:
            s["server"] = servers[0]["id"]
        # مۆدێلە دووبارەکان یەک دەخرێن — هەمان مۆدێڵ لە چەند سەرچاوە = یەک دەنگ
        uniq = dedupe_servers(servers)
        with _lock:
            pending[user_id] = {str(i): {"id": x["id"], "key": norm_model(x["id"])} for i, x in enumerate(uniq, 1)}
        body = f"🤖 <b>قائمة الموديلات</b> — {len(uniq)} موديل (المكرر بين المصادر مدموج):\n\n"
        for i, x in enumerate(uniq, 1):
            mark = " ✅" if x["id"] == s["server"] else ""
            body += f"{i}. <code>{x['id']}</code>{mark}\n"
        body += "\n✍️ اكتب رقم الموديل فقط للتبديل مثال: <code>5</code>"
        reply(chat_id, body)
        return

    # هەڵبژاردنی سێرڤەر بە ژمارە
    s = get_session(user_id)
    if text.isdigit():
        p = pending.get(user_id)
        if not p:
            reply(chat_id, "🤖 اكتب <code>/server</code> أولا لعرض قائمة الموديلات.")
            return
        if str(int(text)) not in p:
            reply(chat_id, f"⚠️ اكتب رقما بين <code>1</code> و <code>{len(p)}</code>.")
            return
        srv = p[str(int(text))]
        s["server"] = srv["id"]
        s["mkey"] = srv["key"]
        s["history"].clear()
        reply(chat_id, f"✅ تم التبديل إلى الموديل <code>{srv['id']}</code> بنجاح")
        return

    # پرسیاری ئاسایی
    if not BRAIN["servers"]:
        new = detect_brain()
        BRAIN["mode"], BRAIN["servers"] = new["mode"], new["servers"]
        if not BRAIN["servers"]:
            reply(chat_id, "⚠️ لا يوجد مصدر متاح الآن — حاول بعد قليل.")
            return
        s["server"] = BRAIN["servers"][0]["id"]

    stop = threading.Event()
    threading.Thread(target=keep_typing, args=(chat_id, stop), daemon=True).start()

    result = {}

    def work():
        try:
            result["answer"] = ask(s, text)
        except Exception as e:
            result["error"] = str(e)

    t = threading.Thread(target=work, daemon=True)
    t.start()
    t.join(timeout=150)

    try:
        if "error" in result:
            answer = f"⚠️ <b>حدث خطأ:</b> {result['error']}\nحاول بعد قليل."
        elif "answer" not in result:
            answer = "⏳ <b>تأخر الرد كثيرا.</b> أعد الإرسال من فضلك."
        else:
            answer, mode = result["answer"]
            if answer:
                s["history"].append({"role": "user", "content": text})
                s["history"].append({"role": "assistant", "content": answer})
                s["history"] = s["history"][-20:]
            else:
                answer = "⚠️ لم يصل رد — حاول مرة أخرى."
    finally:
        stop.set()

    print(f"[ANS] user={user_id}: {len(answer)} chars", flush=True)
    for part in split_msg(answer):
        reply(chat_id, part)


def setup_commands():
    """فەرمانەکانی مێنیو — لەگەڵ دووبارەهەوڵ (تا هەرگیز ون نەبن)"""
    cmds = [
        {"command": "start", "description": "بدء المحادثة مع البوت"},
        {"command": "new", "description": "محادثة جديدة"},
        {"command": "server", "description": "قائمة الموديلات — الأحدث دائما"},
        {"command": "about", "description": "معلومات عن البوت"},
    ]
    # فەرمانەکان لە هەموو سکۆپەکاندا دانراو — تا فەرمانی کۆنی هیچ سیستەمێکی تر ون نەمێنێت
    scopes = [
        {"type": "default"},
        {"type": "all_private_chats"},
        {"type": "all_group_chats"},
    ]
    for attempt in range(3):
        ok = True
        for sc in scopes:
            r = tg("setMyCommands", commands=cmds, scope=sc)
            if not r.get("ok"):
                ok = False
                print(f"[CMDS] {sc.get('type')} شکستی هێنا", flush=True)
        if ok:
            print("✅ فەرمانەکانی مێنیو لە هەموو سکۆپەکان دانران", flush=True)
            return
        print(f"[CMDS] هەوڵ {attempt+1} — دووبارە…", flush=True)
        time.sleep(2)


def start_hf_keepalive():
    """سێرڤەری بچووک + خۆپینگ — بۆ Hugging Face و Render (بۆ نەخەوتن)"""
    import os
    sid = os.environ.get("SPACE_ID")          # Hugging Face
    ext_url = os.environ.get("RENDER_EXTERNAL_URL")  # Render
    if not sid and not ext_url:
        return
    import http.server
    import socketserver
    port = int(os.environ.get("APP_PORT", 7860))

    class H(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write("🤖 بۆتەکە زیندووە".encode("utf-8"))

        def log_message(self, *a):
            pass

    def serve():
        try:
            socketserver.TCPServer.allow_reuse_address = True
            with socketserver.TCPServer(("0.0.0.0", port), H) as s:
                s.serve_forever()
        except Exception as e:
            print(f"[KEEP] serve: {e}", flush=True)

    threading.Thread(target=serve, daemon=True).start()
    url = ext_url or f"https://{sid.replace('/', '-').lower()}.hf.space"
    where = "Render" if ext_url else "Hugging Face"

    def ping():
        while True:
            time.sleep(840)  # ١٤ خولەک
            try:
                requests.get(url, timeout=15)
            except Exception:
                pass

    threading.Thread(target=ping, daemon=True).start()
    print(f"[KEEP] خۆپینگی {where} لەسەر {url}", flush=True)


def main():
    print("🔄 دەستپێکردنی بۆتی تێلەگرام…", flush=True)
    start_api()          # 🔌 API — بۆ بەکارهێنان وەک API
    start_hf_keepalive()
    me = tg("getMe")
    if not me.get("ok"):
        print("❌ تۆکن هەڵەیە یان ئینتەرنێت نییە:", me.get("description"), flush=True)
        return
    print(f"✅ بۆت: @{me['result']['username']} ({me['result']['first_name']})", flush=True)

    # دەستنیشانکردنی مێشک
    print("🧠 دەستنیشانکردنی سەرچاوەی AI…", flush=True)
    new = detect_brain()
    BRAIN["mode"], BRAIN["servers"] = new["mode"], new["servers"]
    if new["mode"] == "aff":
        print(f"🟢 مێشکی سەرەکی: aifreeforever ({len(new['servers'])} سێرڤەر)", flush=True)
    elif new["mode"] == "pol":
        print(f"🟡 مێشکی جێگرەوە: pollinations ({len(new['servers'])} سێرڤەر)", flush=True)
    else:
        print("⚠️ هیچ سەرچاوەیەک نەدۆزرایەوە — دواتر دووبارە هەوڵ دەدرێتەوە", flush=True)

    tg("deleteWebhook")
    setup_commands()
    # 🔄 چاودێری لیستی مۆدەڵەکان — هەر ٥ خولەک
    threading.Thread(target=auto_refresh, daemon=True).start()
    print("🟢 بۆت کارا کەوت — چاوەڕێی نامەکانە…", flush=True)

    offset = 0
    cycle = 0
    while True:
        try:
            cycle += 1
            if cycle % 10 == 1:
                print(f"[LOOP] زیندووە — cycle {cycle}, offset={offset}", flush=True)

            r = tg("getUpdates", offset=offset, timeout=8, allowed_updates=["message"])
            if not r.get("ok"):
                print(f"[POLL] ok=false: {r.get('description', '?')}", flush=True)
                time.sleep(3)
                continue
            for u in r.get("result", []):
                offset = u["update_id"] + 1
                m = u.get("message")
                if m and m.get("text"):
                    threading.Thread(target=handle_message, args=(m,), daemon=True).start()
                elif m:
                    reply(m["chat"]["id"], "💬 أرسل رسالة نصية من فضلك.")
        except KeyboardInterrupt:
            print("⏹ وەسترا.", flush=True)
            break
        except Exception as e:
            print(f"[POLL] هەڵە: {e}", flush=True)
            time.sleep(3)


if __name__ == "__main__":
    main()
