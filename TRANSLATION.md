# Editions of The 20-Watt Computer

Every edition has its own folder with the same file layout and file names: `ru/` (Russian), `en/` (English),
`zh/` (Chinese, simplified), `ja/` (Japanese), `ko/` (Korean), `es/` (Spanish), `pt/` (Portuguese, Brazilian),
`uk/` (Ukrainian), `fr/` (French), `vi/` (Vietnamese) and `ar/` (Arabic, right-to-left; built with LuaLaTeX). New editions are made from `ru/`:

| Russian | Translation `<lang>` |
|---|---|
| `ru/main.tex` | `<lang>/main.tex` (prepared; zh, ja, ko build with XeLaTeX) |
| `ru/chapters/*.tex` | `<lang>/chapters/*.tex` |
| `ru/answers/NN.tex` | `<lang>/answers/NN.tex` |
| `ru/supplement/NN.tex`, `bib_NN.tex` | `<lang>/supplement/…` |
| `ru/paperback/*` | `<lang>/paperback/*` |

`figures/` and `models/` are shared by all editions. Instructor solutions (`ru/solutions/`, private) are not translated.

## What stays identical

- Every `\label`, `\ref`, `\eqref`, `\cite`, `\bibitem` key, file name and `\input` line.
- All mathematics, numbers and units' values. Units become international: мс → ms, мВ → mV, Гц → Hz,
  мкм → µm (`\um`), мМ → mM, имп/с → spikes/s (EN) / 次/秒 or Hz as appropriate (ZH).
- Document structure: the same chapters, sections, figures, tables, exercises, key boxes (`keyblock`, `empheq`)
  and their order. Nothing is added or dropped.
- TikZ figures: translate every text label inside nodes; keep coordinates and styles. If a longer label no longer
  fits, shorten the wording rather than moving drawing elements.

## Neuron type codes

Every edition, Russian included, uses the same Latin four-letter codes, written with `\nt{…}`:

| Former Russian code | Code (all editions) | Transmitter (EN) | Transmitter (ZH) |
|---|---|---|---|
| ГЛУТ | GLUT | glutamate | 谷氨酸 |
| ГАМК | GABA | GABA | γ-氨基丁酸（GABA） |
| ГЛИЦ | GLYC | glycine | 甘氨酸 |
| АЦЕТ | ACET | acetylcholine | 乙酰胆碱 |
| ДОФА | DOPA | dopamine | 多巴胺 |
| СЕРО | SERO | serotonin | 血清素（5-羟色胺） |
| НОРА | NORA | noradrenaline (norepinephrine) | 去甲肾上腺素 |
| АДРЕ | ADRE | adrenaline | 肾上腺素 |
| ГИСТ | HIST | histamine | 组胺 |
| АСПА | ASPA | aspartate | 天冬氨酸 |

«ГЛУТ-нейрон» → "GLUT neuron" / "GLUT 神经元"; «ГЛУТ-сеть» → "GLUT network" / "GLUT 网络".

## Glossary

Use these terms consistently: several translators work on each language in parallel.

| Russian | English | Chinese | Japanese | Korean | Spanish | Portuguese (BR) | Ukrainian | French | Vietnamese | Arabic |
|---|---|---|---|---|---|---|---|---|---|---|
| адресная шина | address bus | 寻址总线 | アドレスバス | 주소 버스 | bus de direcciones | barramento de endereços | адресна шина | bus d'adresses | bus địa chỉ | ناقل العناوين |
| широковещательный канал / сигнал | broadcast channel / signal | 广播通道 / 广播信号 | ブロードキャストチャネル / 信号 | 브로드캐스트 채널 / 신호 | canal / señal de difusión | canal / sinal de difusão | широкомовний канал / сигнал | canal / signal de diffusion | kênh / tín hiệu quảng bá | قناة / إشارة بثّ |
| регистр управления | control register | 控制寄存器 | 制御レジスタ | 제어 레지스터 | registro de control | registrador de controle | регістр керування | registre de contrôle | thanh ghi điều khiển | سجل التحكم |
| медиатор | transmitter | 神经递质 | 神経伝達物質 | 신경전달물질 | neurotransmisor | neurotransmissor | медіатор | neurotransmetteur | chất dẫn truyền thần kinh | ناقل عصبي |
| рецептор (ионотропный / метаботропный) | receptor (ionotropic / metabotropic) | 受体（离子型 / 代谢型） | 受容体（イオンチャネル型 / 代謝型） | 수용체(이온성 / 대사성) | receptor (ionotrópico / metabotrópico) | receptor (ionotrópico / metabotrópico) | рецептор (іонотропний / метаботропний) | récepteur (ionotrope / métabotrope) | thụ thể (hướng ion / hướng chuyển hóa) | مستقبل (مؤين التوجه / أيضي التوجه) |
| импульс | spike | 脉冲 | スパイク | 스파이크 | espiga | disparo | імпульс | potentiel d'action (impulsion) | xung (điện thế hoạt động) | نبضة (جهد فعل) |
| пачка (импульсов) | burst | 簇放电 | バースト | 버스트 | ráfaga | rajada | пачка (імпульсів) | bouffée | chùm xung | رشقة |
| частотный код / временной код | rate code / timing code | 频率编码 / 时间编码 | レート符号 / タイミング符号 | 발화율 부호 / 타이밍 부호 | código de frecuencia / código temporal | código de taxa / código temporal | частотний код / часовий код | code de fréquence / code temporel | mã tần số / mã thời gian | ترميز التردد / ترميز التوقيت |
| интегратор с утечкой | leaky integrator | 泄漏积分器 | 漏れ積分器 | 누설 적분기 | integrador con fugas | integrador com vazamento | інтегратор із витоком | intégrateur à fuite | bộ tích phân rò | مكامل تسريبي |
| порог | threshold | 阈值 | 閾値 | 문턱값 | umbral | limiar | поріг | seuil | ngưỡng | عتبة |
| вес (связи) | (synaptic) weight | （突触）权重 | （シナプス）重み | (시냅스) 가중치 | peso (sináptico) | peso (sináptico) | вага (зв'язку) | poids (synaptique) | trọng số (khớp thần kinh) | وزن (مشبكي) |
| след | eligibility trace | 资格迹 | 適格度トレース | 적격 흔적 | traza de elegibilidad | traço de elegibilidade | слід | trace d'éligibilité | vết đủ điều kiện | أثر الأهلية |
| правило трёх множителей | three-factor rule | 三因子规则 | 三要素則 | 3요소 규칙 | regla de tres factores | regra de três fatores | правило трьох множників | règle à trois facteurs | quy tắc ba thừa số | قاعدة العوامل الثلاثة |
| ошибка предсказания награды | reward-prediction error | 奖励预测误差 | 報酬予測誤差 | 보상 예측 오차 | error de predicción de la recompensa | erro de predição de recompensa | помилка передбачення винагороди | erreur de prédiction de la récompense | sai số dự đoán phần thưởng | خطأ التنبؤ بالمكافأة |
| объёмная передача | volume transmission | 容积传递 | 容積伝達 | 체적 전달 | transmisión de volumen | transmissão por volume | об'ємна передача | transmission volumique | truyền dẫn thể tích | النقل الحجمي |
| ритмоводитель | pacemaker | 起搏器 | ペースメーカー | 페이스메이커 | marcapasos | marca-passo | ритмоводій | stimulateur (pacemaker) | bộ tạo nhịp | ناظمة الإيقاع |
| коэффициент усиления | gain | 增益 | ゲイン | 이득 | ganancia | ganho | коефіцієнт підсилення | gain | hệ số khuếch đại | الكسب |
| шунтирующее торможение | shunting inhibition | 分流抑制 | シャント抑制 | 분로 억제 | inhibición de derivación | inibição por derivação | шунтувальне гальмування | inhibition shuntante | ức chế sun | تثبيط تحويلي |
| победитель забирает всё | winner-take-all | 赢者通吃 | 勝者総取り | 승자독식 | el ganador se lo lleva todo | o vencedor leva tudo | переможець забирає все | le gagnant rafle tout | kẻ thắng lấy tất | الفائز يأخذ كل شيء |
| детектор совпадений | coincidence detector | 符合检测器 | 同時検出器 | 동시성 검출기 | detector de coincidencias | detector de coincidência | детектор збігів | détecteur de coïncidences | bộ phát hiện trùng khớp | كاشف التزامن |
| расширитель | expander (expansion layer) | 扩展层 | 拡張層 | 확장층 | capa de expansión | camada de expansão | розширювач | couche d'expansion | lớp mở rộng | طبقة التوسيع |
| грибовидное тело | mushroom body | 蘑菇体 | キノコ体 | 버섯체 | cuerpo fungiforme | corpo cogumelo | грибоподібне тіло | corps pédonculé | thể nấm | الجسم الفطري |
| щуп | probe | 探针 | プローブ | 프로브 | sonda | sonda | щуп | sonde | đầu dò | مسبار |
| интерфейс мозг—компьютер | brain–computer interface | 脑机接口 | ブレイン・コンピュータ・インターフェース | 뇌-컴퓨터 인터페이스 | interfaz cerebro-computadora | interface cérebro-computador | інтерфейс мозок—комп'ютер | interface cerveau-ordinateur | giao diện não–máy tính | واجهة الدماغ والحاسوب |
| культура (нейронов) | (neuronal) culture | （神经元）培养物 | （神経細胞の）培養 | (신경세포) 배양 | cultivo (neuronal) | cultura (neuronal) | культура (нейронів) | culture (neuronale) | mẫu nuôi cấy (nơ-ron) | مزرعة (عصبونات) |
| решётка электродов | electrode array | 电极阵列 | 電極アレイ | 전극 배열 | matriz de electrodos | matriz de eletrodos | ґратка електродів | matrice d'électrodes | mảng điện cực | مصفوفة أقطاب |
| розыгрыш (в Pong) | rally | 回合 | ラリー | 랠리 | peloteo | rali | розіграш | échange | lượt đánh | جولة |
| удар / промах | hit / miss | 击中 / 未击中 | ヒット / ミス | 히트 / 미스 | acierto / fallo | acerto / erro | удар / промах | renvoi / raté | trúng / trượt | إصابة / إخفاق |
| утверждение (жёлтая рамка) | proposition | 命题 | 命題 | 명제 | proposición | proposição | твердження | proposition | mệnh đề | قضية |
| задача | exercise | 习题 | 問題 | 연습문제 | ejercicio | exercício | задача | exercice | bài tập | تمرين |
| статусы приложения D: измерено / теория / модель / оценка / гипотеза | measured / theory / model / estimate / hypothesis | 已测量 / 理论 / 模型 / 估计 / 假说 | 測定済み / 理論 / モデル / 推定 / 仮説 | 측정됨 / 이론 / 모델 / 추정 / 가설 | medido / teoría / modelo / estimación / hipótesis | medido / teoria / modelo / estimativa / hipótese | виміряно / теорія / модель / оцінка / гіпотеза | mesuré / théorie / modèle / estimation / hypothèse | đã đo / lý thuyết / mô hình / ước tính / giả thuyết | مُقاس / نظرية / نموذج / تقدير / فرضية |
| бегло (пути чтения) | skim | 略读 | 流し読み | 훑어보기 | lectura rápida | leitura rápida | побіжно | survol | đọc lướt | قراءة سريعة |
| щелчок (в популярной версии = импульс) | click | 咔嗒 | カチッ | 딸깍 | clic | clique | клацання | clic | tách | نقرة |
| провод | wire | 导线 | 配線 | 전선 | cable | fio | провід | fil | dây dẫn | سلك |
| машина (мозг как машина) | the machine | 这台机器 | マシン | 기계 | la máquina | a máquina | машина | la machine | cỗ máy | الآلة |

For terms not listed, use the standard term of neuroscience or electrical engineering in the target language.

## Style

- Keep the book's voice: short declarative sentences, engineering framing, no history or anecdotes, no anatomy tours.
- Never write "without a clock" / «без часов» / "没有时钟" as a slogan; the book avoids it deliberately.
- Never write that an edition is a translation or that another edition is the original (no "translated from …" lines).
- English: US spelling, serial comma, "we" for the author.
- Japanese: です/ます is not used; write in the plain expository style (である調). Korean: 평서문 expository style (-다).
- Spanish: neutral Latin-American-friendly Spanish; Portuguese: Brazilian; Ukrainian: modern standard Ukrainian (not a calque of the Russian).
- French: standard French typography (babel inserts the spaces before : ; ! ? — do not type them); «guillemets» are allowed in French only.
- Vietnamese: full diacritics; Latin codes and math unchanged.
- Arabic: Modern Standard Arabic; text is right-to-left, math stays left-to-right; keep Latin codes, numbers and symbols in Western digits; wrap Latin words in \foreignlanguage{english}{…} where direction matters.
- Chinese: simplified characters, full-width punctuation in running text (，。：；（）), half-width inside math and
  code; a space between Chinese and Latin/number runs is optional but be consistent within a file (prefer none,
  except around inline math which ctex handles).
- Quotes: EN "…"; ZH “…”. «…» only where they are the standard marks of the language (ru, uk, fr).
