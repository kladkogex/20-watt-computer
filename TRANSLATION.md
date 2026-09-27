# Translating «Компьютер на 20 ваттах»

The Russian sources in `ru/` are the original. Translations live in `en/` (English), `zh/` (Chinese, simplified), `ja/` (Japanese), `ko/` (Korean), `es/` (Spanish)
and `pt/` (Portuguese, Brazilian), with the same file layout and file names as `ru/`:

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

The book's four-letter codes become Latin codes in both translations (written with `\nt{…}` exactly as in Russian):

| Russian | Code (all languages) | Transmitter (EN) | Transmitter (ZH) |
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

| Russian | English | Chinese | Japanese | Korean | Spanish | Portuguese (BR) |
|---|---|---|---|---|---|---|
| адресная шина | address bus | 寻址总线 | アドレスバス | 주소 버스 | bus de direcciones | barramento de endereços |
| широковещательный канал / сигнал | broadcast channel / signal | 广播通道 / 广播信号 | ブロードキャストチャネル / 信号 | 브로드캐스트 채널 / 신호 | canal / señal de difusión | canal / sinal de difusão |
| регистр управления | control register | 控制寄存器 | 制御レジスタ | 제어 레지스터 | registro de control | registrador de controle |
| медиатор | transmitter | 神经递质 | 神経伝達物質 | 신경전달물질 | neurotransmisor | neurotransmissor |
| рецептор (ионотропный / метаботропный) | receptor (ionotropic / metabotropic) | 受体（离子型 / 代谢型） | 受容体（イオンチャネル型 / 代謝型） | 수용체(이온성 / 대사성) | receptor (ionotrópico / metabotrópico) | receptor (ionotrópico / metabotrópico) |
| импульс | spike | 脉冲 | スパイク | 스파이크 | espiga | disparo |
| пачка (импульсов) | burst | 簇放电 | バースト | 버스트 | ráfaga | rajada |
| частотный код / временной код | rate code / timing code | 频率编码 / 时间编码 | レート符号 / タイミング符号 | 발화율 부호 / 타이밍 부호 | código de frecuencia / código temporal | código de taxa / código temporal |
| интегратор с утечкой | leaky integrator | 泄漏积分器 | 漏れ積分器 | 누설 적분기 | integrador con fugas | integrador com vazamento |
| порог | threshold | 阈值 | 閾値 | 문턱값 | umbral | limiar |
| вес (связи) | (synaptic) weight | （突触）权重 | （シナプス）重み | (시냅스) 가중치 | peso (sináptico) | peso (sináptico) |
| след | eligibility trace | 资格迹 | 適格度トレース | 적격 흔적 | traza de elegibilidad | traço de elegibilidade |
| правило трёх множителей | three-factor rule | 三因子规则 | 三要素則 | 3요소 규칙 | regla de tres factores | regra de três fatores |
| ошибка предсказания награды | reward-prediction error | 奖励预测误差 | 報酬予測誤差 | 보상 예측 오차 | error de predicción de la recompensa | erro de predição de recompensa |
| объёмная передача | volume transmission | 容积传递 | 容積伝達 | 체적 전달 | transmisión de volumen | transmissão por volume |
| ритмоводитель | pacemaker | 起搏器 | ペースメーカー | 페이스메이커 | marcapasos | marca-passo |
| коэффициент усиления | gain | 增益 | ゲイン | 이득 | ganancia | ganho |
| шунтирующее торможение | shunting inhibition | 分流抑制 | シャント抑制 | 분로 억제 | inhibición de derivación | inibição por derivação |
| победитель забирает всё | winner-take-all | 赢者通吃 | 勝者総取り | 승자독식 | el ganador se lo lleva todo | o vencedor leva tudo |
| детектор совпадений | coincidence detector | 符合检测器 | 同時検出器 | 동시성 검출기 | detector de coincidencias | detector de coincidência |
| расширитель | expander (expansion layer) | 扩展层 | 拡張層 | 확장층 | capa de expansión | camada de expansão |
| грибовидное тело | mushroom body | 蘑菇体 | キノコ体 | 버섯체 | cuerpo fungiforme | corpo cogumelo |
| щуп | probe | 探针 | プローブ | 프로브 | sonda | sonda |
| интерфейс мозг—компьютер | brain–computer interface | 脑机接口 | ブレイン・コンピュータ・インターフェース | 뇌-컴퓨터 인터페이스 | interfaz cerebro-computadora | interface cérebro-computador |
| культура (нейронов) | (neuronal) culture | （神经元）培养物 | （神経細胞の）培養 | (신경세포) 배양 | cultivo (neuronal) | cultura (neuronal) |
| решётка электродов | electrode array | 电极阵列 | 電極アレイ | 전극 배열 | matriz de electrodos | matriz de eletrodos |
| розыгрыш (в Pong) | rally | 回合 | ラリー | 랠리 | peloteo | rali |
| удар / промах | hit / miss | 击中 / 未击中 | ヒット / ミス | 히트 / 미스 | acierto / fallo | acerto / erro |
| утверждение (жёлтая рамка) | proposition | 命题 | 命題 | 명제 | proposición | proposição |
| задача | exercise | 习题 | 問題 | 연습문제 | ejercicio | exercício |
| статусы приложения D: измерено / теория / модель / оценка / гипотеза | measured / theory / model / estimate / hypothesis | 已测量 / 理论 / 模型 / 估计 / 假说 | 測定済み / 理論 / モデル / 推定 / 仮説 | 측정됨 / 이론 / 모델 / 추정 / 가설 | medido / teoría / modelo / estimación / hipótesis | medido / teoria / modelo / estimativa / hipótese |
| бегло (пути чтения) | skim | 略读 | 流し読み | 훑어보기 | lectura rápida | leitura rápida |
| щелчок (в популярной версии = импульс) | click | 咔嗒 | カチッ | 딸깍 | clic | clique |
| провод | wire | 导线 | 配線 | 전선 | cable | fio |
| машина (мозг как машина) | the machine | 这台机器 | マシン | 기계 | la máquina | a máquina |

For terms not listed, use the standard term of neuroscience or electrical engineering in the target language.

## Style

- Keep the book's voice: short declarative sentences, engineering framing, no history or anecdotes, no anatomy tours.
- Never write "without a clock" / «без часов» / "没有时钟" as a slogan (the Russian original avoids it deliberately).
- English: US spelling, serial comma, "we" for the author as in the original.
- Japanese: です/ます is not used; write in the plain expository style (である調). Korean: 평서문 expository style (-다).
- Spanish: neutral Latin-American-friendly Spanish; Portuguese: Brazilian.
- Chinese: simplified characters, full-width punctuation in running text (，。：；（）), half-width inside math and
  code; a space between Chinese and Latin/number runs is optional but be consistent within a file (prefer none,
  except around inline math which ctex handles).
- Quotes: EN "…"; ZH “…”. Russian «…» must not remain.
