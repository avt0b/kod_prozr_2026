/**
 * Сборка презентации F-17 на pptxgenjs.
 *
 *   npm ci --prefix docs/presentation && node docs/presentation/build.mjs
 *
 * Входы: eval/report.json (слайд 7, читается при каждой сборке), screenshots/*.png и
 * screenshots/stand.json (их пишет screenshots.mjs). Выход: kod-prozrachnosti-review.pptx
 * рядом со скриптом или путь из OUT. REPORT переопределяет путь к отчёту метрик.
 */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import pptxgen from 'pptxgenjs';

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, '../..');
const shots = path.join(here, 'screenshots');
const reportPath = path.resolve(process.env.REPORT ?? path.join(root, 'eval/report.json'));
const outPath = path.resolve(process.env.OUT ?? path.join(here, 'kod-prozrachnosti-review.pptx'));

const readJson = (file) => JSON.parse(fs.readFileSync(file, 'utf8'));
if (!fs.existsSync(reportPath)) {
  throw new Error(
    `Нет ${reportPath}: сначала make seed && make eval (слайд 7 без метрик не собираем)`,
  );
}
const report = readJson(reportPath);
const standPath = path.join(shots, 'stand.json');
const stand = fs.existsSync(standPath) ? readJson(standPath) : null;
const SHOTS = [
  'overview',
  'ranking-top',
  'profile-head',
  'appeal-main',
  'graph-card',
  'report-page',
];
for (const name of SHOTS) {
  if (!fs.existsSync(path.join(shots, `${name}.png`))) {
    throw new Error(`Нет screenshots/${name}.png: снимите стенд командой node screenshots.mjs`);
  }
}

// ------------------------------------------------------------------ форматирование
const num = (v, digits = 2) => (v == null ? '—' : Number(v).toFixed(digits).replace('.', ','));
const pr = (m) => (m ? `${num(m.precision)} / ${num(m.recall)}` : '—');
const seconds = (s) => {
  if (s == null) return '—';
  if (s < 0.001) return '< 1 мс';
  if (s < 1) return `${Math.round(s * 1000)} мс`;
  return `${num(s, 1)} с`;
};
const ruDate = (iso) => new Date(iso).toLocaleDateString('ru-RU', { timeZone: 'Europe/Moscow' });
const CATEGORY = {
  bribe: 'Взятка',
  conflict_of_interest: 'Конфликт интересов',
  procurement: 'Закупки',
  abuse_of_power: 'Превышение полномочий',
  other: 'Другое',
};

// ------------------------------------------------------------------ метрики из report.json
/**
 * Движки разбора обращений. Формат src.eval: appeals = {fallback: {...}, "llm:<модель>": {...}}.
 * Допускаем и варианты: appeals.llm, вложенные модели {llm: {"<модель>": {...}}} и блок верхнего
 * уровня report.llm. Блок с метриками узнаём по полю is_corruption.
 */
function appealEngines(rep) {
  const engines = [];
  const visit = (key, value) => {
    if (!value || typeof value !== 'object') return;
    if (value.is_corruption) {
      engines.push({ key, metrics: value });
      return;
    }
    for (const [k, v] of Object.entries(value)) visit(`${key}:${k}`, v);
  };
  for (const [k, v] of Object.entries(rep.appeals ?? {})) visit(k, v);
  if (rep.llm) visit('llm', rep.llm);
  const isLlm = (key) => key.toLowerCase().startsWith('llm');
  return engines
    .filter((e, i, all) => all.findIndex((o) => o.key === e.key) === i)
    .sort((a, b) => Number(isLlm(a.key)) - Number(isLlm(b.key)))
    .map((e) => ({
      ...e,
      llm: isLlm(e.key),
      title: isLlm(e.key)
        ? `LLM ${e.key.split(':').slice(1).join(':') || ''}`.trim()
        : e.key === 'fallback'
          ? 'Правила (фоллбэк)'
          : e.key,
    }));
}

const rules = report.rules ?? {};
const perRule = Object.entries(rules.per_rule ?? {}).sort(([a], [b]) => a.localeCompare(b));
const ruleCodes = perRule.map(([code]) => code);
const minOf = (field) => (perRule.length ? Math.min(...perRule.map(([, m]) => m[field])) : null);
const rulePairs = perRule.reduce((sum, [, m]) => sum + (m.tp ?? 0) + (m.fn ?? 0), 0);
const engines = appealEngines(report);
const llmEngine = engines.find((e) => e.llm);
const baseEngine = engines.find((e) => !e.llm);
if (!perRule.length && !engines.length) throw new Error(`В ${reportPath} нет метрик rules/appeals`);

// ------------------------------------------------------------------ оформление
const C = {
  bg: 'F5F7FC',
  ink: '182648',
  blue: '1D3F9E',
  muted: '69748B',
  line: 'D5DBE8',
  card: 'FFFFFF',
  accent: 'E8EDF8',
};
const FONT = 'Arial';
const TOTAL = 8;
const px = (v) => v / 96; // макет в пикселях холста 1280×720, LAYOUT_WIDE = 13,33×7,5 дюйма

const pptx = new pptxgen();
pptx.layout = 'LAYOUT_WIDE';
pptx.title = 'Код прозрачности';
pptx.subject = 'Рабочее место аналитика по профилактике коррупции';
pptx.company = 'Команда «Код прозрачности»';
pptx.lang = 'ru-RU';
pptx.theme = { headFontFace: FONT, bodyFontFace: FONT };

function text(slide, value, x, y, w, h, size = 30, color = C.ink, opts = {}) {
  slide.addText(value, {
    x: px(x),
    y: px(y),
    w: px(w),
    h: px(h),
    fontFace: FONT,
    fontSize: size * 0.75,
    color,
    margin: 0,
    valign: 'top',
    fit: 'none',
    ...opts,
  });
}
function box(slide, x, y, w, h, fill = C.card, line = C.line) {
  slide.addShape(pptx.ShapeType.roundRect, {
    x: px(x),
    y: px(y),
    w: px(w),
    h: px(h),
    fill: { color: fill },
    line: { color: line, width: 0.75 },
    rectRadius: 0.06,
  });
}
/** Размер PNG из заголовка IHDR. */
function pngSize(file) {
  const buf = fs.readFileSync(file);
  if (buf.toString('ascii', 1, 4) !== 'PNG') throw new Error(`${file}: не PNG`);
  return { w: buf.readUInt32BE(16), h: buf.readUInt32BE(20) };
}
/** Скриншот в рамке, вписанный в прямоугольник с сохранением пропорций; возвращает размер. */
function shot(slide, name, x, y, maxW, maxH, alt) {
  const file = path.join(shots, `${name}.png`);
  const size = pngSize(file);
  const k = Math.min(maxW / size.w, maxH / size.h);
  const w = size.w * k;
  const h = size.h * k;
  slide.addShape(pptx.ShapeType.rect, {
    x: px(x - 1),
    y: px(y - 1),
    w: px(w + 2),
    h: px(h + 2),
    fill: { color: C.card },
    line: { color: C.line, width: 0.75 },
  });
  slide.addImage({ path: file, x: px(x), y: px(y), w: px(w), h: px(h), altText: alt });
  return { w, h };
}
function slide(title, notes) {
  const s = pptx.addSlide();
  s.background = { color: C.bg };
  const n = pptx.slides.length;
  text(s, 'КОД ПРОЗРАЧНОСТИ', 64, 30, 900, 26, 18, C.blue, { bold: true, charSpacing: 1 });
  text(s, title, 64, 62, 1152, 64, 42, C.ink, { bold: true });
  text(s, 'Синтетические данные · демонстрационный прототип', 64, 668, 900, 24, 16, C.muted);
  text(
    s,
    `${String(n).padStart(2, '0')} / ${String(TOTAL).padStart(2, '0')}`,
    1116,
    668,
    100,
    24,
    16,
    C.muted,
    {
      align: 'right',
    },
  );
  s.addNotes(notes);
  return s;
}
/** Тезисы с акцентной полосой слева. */
function points(s, items, start = 168, step = 150) {
  items.forEach(([head, body], i) => {
    const y = start + i * step;
    s.addShape(pptx.ShapeType.rect, {
      x: px(64),
      y: px(y),
      w: px(6),
      h: px(104),
      fill: { color: C.blue },
      line: { type: 'none' },
    });
    text(s, head, 96, y + 4, 1120, 44, 30, C.ink, { bold: true });
    text(s, body, 96, y + 52, 1120, 52, 25, C.muted);
  });
}

const shotDate = stand ? ruDate(stand.taken_at) : null;
const shotSource = stand
  ? `Скриншоты сняты ${shotDate} скриптом docs/presentation/screenshots.mjs на локальном стенде FastAPI + PostgreSQL с сидами data/generated (не моки).`
  : 'Скриншоты: docs/presentation/screenshots, источник не записан (нет stand.json).';
const engineFallback = stand?.appeal?.engine === 'fallback';

// ------------------------------------------------------------------ 1. Титул
let s = slide(
  'Код прозрачности',
  '20 с. Направление 04. Рабочее место аналитика подразделения по профилактике коррупционных правонарушений. ' +
    'Источник: docs/README.md и docs/demo.md. Все лица вымышлены. Справа — главная страница стенда: счётчики служащих, флагов и обращений.',
);
text(s, 'Рабочее место аналитика\nпо профилактике коррупции', 64, 190, 560, 150, 44, C.blue, {
  bold: true,
});
text(s, 'Полномочия служащего × связи × контракты органа', 64, 370, 540, 80, 28);
text(s, 'Направление 04 · ноябрь 2026', 64, 480, 540, 36, 22, C.muted);
shot(s, 'overview', 648, 190, 568, 400, 'Главная страница: счётчики и топ-10 по риску');

// ------------------------------------------------------------------ 2. Задача и аналоги
s = slide(
  'Задача и существующие решения',
  '25 с. По материалам docs/README.md, docs/decisions.md ADR-02 и docs/demo.md. Позиционирование команды, без утверждений ' +
    'о полном функционале внешних систем. Ответ жюри: мы дополняем «Посейдон»; сравнения доходов и расходов в прототипе нет. ' +
    'Маркеры КНД РАНХиГС не воспроизводим.',
);
points(s, [
  [
    'Аналитику нужно восстановить связи',
    'между должностью, людьми, компаниями и закупками органа.',
  ],
  [
    '«Посейдон» и маркеры РАНХиГС',
    '«Посейдон» — имущественные сведения; РАНХиГС — контрольно-надзорная деятельность.',
  ],
  [
    'Наш фокус — возможный конфликт интересов',
    'в сфере полномочий конкретного служащего: что он решает и с кем связан.',
  ],
]);

// ------------------------------------------------------------------ 3. Сценарий
const moved = stand?.before && stand?.after;
const flagsLine = stand?.flags?.length ? stand.flags.join(', ') : 'R01, R05, R06, R07';
s = slide(
  'Сценарий проверки',
  '25 с. Источник: docs/demo.md. ' +
    shotSource +
    (moved
      ? ` Соколов до обращения H1: ${stand.before.rank}-е место, балл ${stand.before.score}; после: ${stand.after.rank}-е место, балл ${stand.after.score}.`
      : '') +
    ` Флаги в профиле: ${flagsLine}. В тексте обращения находятся сущности и признаки риска, служащий сопоставляется ` +
    'с профилем, R07 учитывает обращение. Обращение — сигнал, а не доказательство.',
);
text(s, 'Обращение  →  рейтинг  →  профиль и граф  →  докладная', 64, 146, 1152, 40, 28, C.blue, {
  bold: true,
});
const top = shot(
  s,
  'ranking-top',
  64,
  200,
  1152,
  270,
  'Верх рейтинга служащих после демо-обращения',
);
const head3 = shot(
  s,
  'profile-head',
  64,
  200 + top.h + 18,
  1152,
  110,
  'Шапка профиля Соколова: балл и флаги',
);
text(
  s,
  (moved
    ? `Соколов: ${stand.before.rank}-е место (${stand.before.score}) → ${stand.after.rank}-е (${stand.after.score}) после обращения; `
    : '') + 'у каждого флага объяснение, цепочка и норма',
  64,
  200 + top.h + 18 + head3.h + 16,
  1152,
  30,
  20,
);
text(
  s,
  'Обращение — сигнал, а не доказательство. Решение принимает аналитик.',
  64,
  626,
  1152,
  30,
  20,
  C.muted,
);

// ------------------------------------------------------------------ 4. Архитектура
s = slide(
  'Архитектура',
  '25 с. Источники: docs/contracts.md, docs/backend.md, docs/decisions.md ADR-03/04/05/08. Postgres хранит связи; ' +
    'backend собирает подграф и считает объяснимые правила. LLM подключается через OpenAI-совместимый порт; ' +
    'при её недоступности разбор обращений идёт на правилах (фоллбэк), поток не встаёт.' +
    (engineFallback ? ' На стенде для скриншотов LLM не была подключена.' : ''),
);
const layers = [
  ['React + TypeScript + Cytoscape', 'Рейтинг, профиль, обращения, интерактивный граф связей'],
  ['FastAPI → PostgreSQL', 'Связи, объяснимые правила R01–R08, баллы и доказательства'],
  [
    'LLM через OpenAI-совместимый порт',
    'Разбор текста обращений и докладной; резервный анализ на правилах',
  ],
];
layers.forEach(([head, body], i) => {
  const y = 160 + i * 160;
  box(s, 64, y, 1152, 124);
  text(s, head, 100, y + 22, 1080, 40, 30, C.blue, { bold: true });
  text(s, body, 100, y + 70, 1080, 36, 24, C.muted);
  if (i < layers.length - 1) text(s, '↕', 620, y + 124, 40, 36, 26, C.muted, { align: 'center' });
});

// ------------------------------------------------------------------ 5. Разбор обращения
const category = stand?.appeal?.category;
s = slide(
  'Демо: разбор обращения',
  '45 с. ' +
    shotSource +
    ' Демо-обращение H1 создано через форму и сопоставлено с Соколовым. ' +
    (engineFallback
      ? `LLM на стенде не подключена, разбор сделан правилами (engine: fallback), категория «${CATEGORY[category] ?? category}». ` +
        (category && category !== 'conflict_of_interest'
          ? 'Ожидаемая по сценарию категория — conflict_of_interest: это открытое расхождение фоллбэка, ответ в интерфейсе не подменяем. '
          : '')
      : stand?.appeal?.engine
        ? `Разбор сделан LLM (engine: ${stand.appeal.engine}), категория «${CATEGORY[category] ?? category}». `
        : '') +
    'Если LLM не отвечает дольше 20 с, говорим: «Система работает и без LLM, на правилах».',
);
text(
  s,
  'Сущности  ·  категория и сигналы  ·  маршрут  ·  связанный служащий',
  64,
  146,
  1152,
  40,
  26,
  C.blue,
  {
    bold: true,
  },
);
const ap = shot(s, 'appeal-main', 64, 200, 1152, 405, 'Разбор демо-обращения H1 на реальном API');
text(
  s,
  stand?.appeal
    ? engineFallback
      ? `Разбор без LLM: анализатор на правилах · категория «${CATEGORY[category] ?? category}»`
      : `Разбор: LLM · категория «${CATEGORY[category] ?? category}»`
    : 'Разбор обращения на реальном API',
  64,
  200 + ap.h + 16,
  1152,
  32,
  20,
  C.muted,
);

// ------------------------------------------------------------------ 6. Цепочка R01 и докладная
s = slide(
  'Демо: цепочка R01 и докладная',
  '35 с. ' +
    shotSource +
    ' Соколов → супруга → ООО «ДорСтройРесурс» → 5 контрактов → его департамент. Выбор флага R01 подсвечивает цепочку ' +
    'и приглушает остальные узлы. Справа — черновик докладной, сформированный на реальном бэкенде: факты, источники, ' +
    'ссылки на 273-ФЗ; решение принимает человек.',
);
const g = shot(s, 'graph-card', 64, 146, 640, 500, 'Граф связей с подсвеченной цепочкой R01');
const rx = 64 + g.w + 32;
text(
  s,
  'Служащий → супруга →\nООО-поставщик → контракты органа',
  rx,
  146,
  1216 - rx,
  76,
  26,
  C.blue,
  { bold: true },
);
const rep = shot(s, 'report-page', rx, 240, 1216 - rx, 360, 'Черновик докладной записки');
text(
  s,
  'Черновик докладной: факты, источники, ссылки на 273-ФЗ',
  rx,
  240 + rep.h + 12,
  1216 - rx,
  26,
  18,
  C.muted,
);

// ------------------------------------------------------------------ 7. Метрики
const n = (e) => e?.metrics?.appeals;
s = slide(
  'Метрики качества: make eval',
  '35 с. Числа читаются из eval/report.json при сборке (build.mjs), руками не правятся. ' +
    `${report.note ? `${report.note[0].toUpperCase()}${report.note.slice(1)}. ` : ''}` +
    (perRule.length
      ? `Правила ${ruleCodes[0]}–${ruleCodes.at(-1)}: минимальные precision ${num(minOf('precision'))} и recall ${num(minOf('recall'))} ` +
        `на ${rulePairs} заложенных парах. Совпадение полное, потому что генератор и правила написаны по одной спецификации: ` +
        'это проверка согласованности, а не обобщающей способности. '
      : '') +
    engines
      .map(
        (e) =>
          `${e.title} (${n(e)} обращений): is_corruption P/R/F1 ${num(e.metrics.is_corruption.precision)}/` +
          `${num(e.metrics.is_corruption.recall)}/${num(e.metrics.is_corruption.f1)}, категория macro-F1 ` +
          `${num(e.metrics.category_macro_f1)}, привязка P/R ${pr(e.metrics.linking)}, медиана ${seconds(e.metrics.seconds?.median)}.`,
      )
      .join(' ') +
    (llmEngine ? '' : ' LLM-метрик в отчёте нет: показываем фоллбэк на правилах.'),
);

/** Подпись к LLM-столбцу: размер выборки и сколько ответов дала сама LLM, а не фоллбэк. */
function llmNote() {
  const m = llmEngine.metrics;
  const same = baseEngine && n(baseEngine) === n(llmEngine);
  const own = m.engines?.llm;
  return (
    (same
      ? `Оба движка — на одних и тех же ${n(llmEngine)} обращениях. `
      : `LLM — на ${n(llmEngine)} обращениях. `) +
    (own != null && own !== m.appeals
      ? `Ответов самой LLM ${own} из ${m.appeals}, остальные — фоллбэк.`
      : '')
  ).trim();
}

// Левая колонка: риск-правила.
text(s, 'Риск-правила', 64, 150, 560, 32, 24, C.blue, { bold: true });
const tiles = [
  perRule.length && [
    `${num(minOf('precision'))} / ${num(minOf('recall'))}`,
    `precision / recall ${ruleCodes[0]}–${ruleCodes.at(-1)}, ${rulePairs} заложенных пар`,
  ],
  rules.noise_cases && [
    `${rules.noise_cases.without_false_flags}/${rules.noise_cases.total}`,
    'ложноположительных кейсов без лишних флагов',
  ],
  rules.R08 && [
    `${rules.R08.found}/${rules.R08.planted}`,
    `R08 (ML): найдено аномалий; флагов на «чистых» — ${rules.R08.flags_on_clean_officials}`,
  ],
  rules.ranking && [
    num(rules.ranking['precision@10']),
    `precision@10 рейтинга${rules.ranking['precision@20'] != null ? ` (@20 — ${num(rules.ranking['precision@20'])})` : ''}`,
  ],
].filter(Boolean);
tiles.forEach(([value, label], i) => {
  const x = 64 + (i % 2) * 284;
  const y = 194 + Math.floor(i / 2) * 196;
  box(s, x, y, 268, 180);
  text(s, value, x + 20, y + 22, 236, 64, 46, C.blue, { bold: true });
  text(s, label, x + 20, y + 96, 236, 72, 18, C.ink);
});

// Правая колонка: обращения, один столбец на движок (фоллбэк и, если есть, LLM).
text(s, 'Разбор обращений', 656, 150, 560, 32, 24, C.blue, { bold: true });
const cell = (value, extra = {}) => ({ text: value, options: { ...extra } });
const head = { bold: true, color: C.card, fill: { color: C.blue } };
const metricRows = [
  ['Обращений', (m) => String(m.appeals ?? '—')],
  ['Коррупция: P / R', (m) => pr(m.is_corruption)],
  ['Коррупция: F1', (m) => num(m.is_corruption?.f1)],
  ['Категория: macro-F1', (m) => num(m.category_macro_f1)],
  ['Привязка к лицу: P / R', (m) => pr(m.linking)],
  ['Injection без поломки', (m) => m.injection_intact ?? '—'],
  ['Время: медиана / p95', (m) => `${seconds(m.seconds?.median)} / ${seconds(m.seconds?.p95)}`],
];
const tableEngines = engines.length ? engines : [{ title: '—', metrics: {} }];
const firstCol = tableEngines.length > 1 ? 236 : 300;
const headTitle = (e) => (e.llm ? e.title.replace(/^LLM\s+/, 'LLM\n') : e.title);
const colW = [firstCol, ...tableEngines.map(() => (560 - firstCol) / tableEngines.length)].map(px);
s.addTable(
  [
    [
      cell('Метрика', head),
      ...tableEngines.map((e) => cell(headTitle(e), { ...head, align: 'center', fontSize: 11 })),
    ],
    ...metricRows.map(([label, get], i) => [
      cell(label, { fill: { color: i % 2 ? C.card : C.accent } }),
      ...tableEngines.map((e) =>
        cell(get(e.metrics), {
          align: 'center',
          bold: true,
          fill: { color: i % 2 ? C.card : C.accent },
        }),
      ),
    ]),
  ],
  {
    x: px(656),
    y: px(194),
    w: px(560),
    colW,
    rowH: [px(54), ...metricRows.map(() => px(44))],
    fontFace: FONT,
    fontSize: 12.5,
    color: C.ink,
    valign: 'middle',
    margin: [0, px(12), 0, px(12)],
    border: { type: 'solid', pt: 0.75, color: C.line },
  },
);
text(
  s,
  `${report.note ? `${report.note[0].toUpperCase()}${report.note.slice(1)}. ` : ''}` +
    (llmEngine ? llmNote() : 'LLM-прогона в отчёте нет: показан фоллбэк на правилах.'),
  64,
  600,
  1152,
  56,
  18,
  C.muted,
);
if (!baseEngine && !llmEngine)
  console.warn('report.json: нет блока appeals, таблица обращений пустая');

// ------------------------------------------------------------------ 8. Этика
s = slide(
  'Этика, 152-ФЗ и развитие',
  '30 с. Источники: docs/decisions.md ADR-09/11 и docs/demo.md. Это принципы проектирования, а не юридическое заключение ' +
    'о соблюдении 152-ФЗ. Ролевой доступ и полноценный аудит нельзя выдавать за реализованные: нужны до пилота. Ответы жюри: ' +
    'цель и минимизация данных; человек принимает решение; в реальном контуре локальная LLM. Развитие: кадровые интеграции, ' +
    'ЕГРЮЛ, ЕИС, калибровка на отметках аналитика. Пилот 2–3 месяца — предложение команды.',
);
points(s, [
  [
    'Флаг требует проверки; решение принимает человек',
    'Для демонстрации используются только вымышленные лица.',
  ],
  [
    'Перед пилотом',
    'Правовые основания, роли и аудит, локальная LLM и оценка качества на данных пилота.',
  ],
  ['Далее', 'Кадровые сведения, ЕГРЮЛ и ЕИС; калибровка по подтверждённым и ложным сигналам.'],
]);

if (pptx.slides.length !== TOTAL)
  throw new Error(`Ожидалось ${TOTAL} слайдов, собрано ${pptx.slides.length}`);
await pptx.writeFile({ fileName: outPath });
console.log(
  `Собрано ${TOTAL} слайдов: ${path.relative(process.cwd(), outPath) || outPath}\n` +
    `Метрики: ${path.relative(root, reportPath)} (движки обращений: ${engines.map((e) => e.title).join(', ') || 'нет'})`,
);
