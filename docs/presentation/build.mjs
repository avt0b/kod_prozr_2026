import fs from 'node:fs/promises';
import path from 'node:path';
const {Presentation,PresentationFile}=await import(process.env.ARTIFACT_TOOL_MODULE??'@oai/artifact-tool');
const root=process.cwd();
const out=path.join(root,'.codex-build/slides');
await fs.mkdir(out,{recursive:true});
const deck=Presentation.create({slideSize:{width:1280,height:720}});
const font='Arial';
function text(slide,value,x,y,w,h,size=30,color='#182648',bold=false){
 const shape=slide.shapes.add({geometry:'textbox',position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});
 shape.text=value;shape.text.style={fontFamily:font,fontSize:size,color,bold};return shape;
}
function slide(title,notes){
 const s=deck.slides.add();s.background.fill='#F5F7FC';
 text(s,'КОД ПРОЗРАЧНОСТИ',64,30,900,30,18,'#1D3F9E',true);
 text(s,title,64,94,1148,110,46,'#182648',true);
 text(s,`${deck.slides.items.length.toString().padStart(2,'0')} / 08`,1120,660,100,28,16,'#69748B');
 text(s,'Синтетические данные · демонстрационный прототип',64,660,950,28,16,'#69748B');
 s.speakerNotes.text=notes;return s;
}
function lines(s,items,start=240){items.forEach((item,i)=>text(s,item,64,start+i*100,1120,85,30));}
let s=slide('Код прозрачности','20 с. Направление 04. Рабочее место аналитика подразделения по профилактике коррупционных правонарушений. Источник: docs/README.md и docs/demo.md. Все лица вымышлены.');
text(s,'Рабочее место аналитика\nпо профилактике коррупции',64,240,1100,170,56,'#1D3F9E',true);
text(s,'Полномочия служащего × связи × контракты органа',64,455,1100,80,30);
text(s,'Направление 04 · ноябрь 2026',64,568,1000,40,24,'#69748B');
s=slide('Задача и существующие решения','25 с. По материалам docs/README.md, docs/decisions.md ADR-02 и docs/demo.md. Позиционирование команды, без утверждений о полном функционале внешних систем. Ответ жюри: мы дополняем Посейдон; сравнения доходов и расходов в прототипе нет. Маркеры КНД РАНХиГС не воспроизводим.');
lines(s,['Аналитику нужно восстановить связи\nмежду должностью, людьми, компаниями и закупками.','«Посейдон»: контроль имущественных сведений.\nМаркеры РАНХиГС: контрольно-надзорная деятельность.','Наш фокус — возможный конфликт интересов\nв сфере полномочий конкретного служащего.'],218);
s=slide('Сценарий проверки','25 с. Источники: docs/demo.md; реальный прогон FastAPI + PostgreSQL 11.11.2026. Открыть обращение H1, затем профиль Соколова и выбрать R01. Обращение — сигнал, а не доказательство.');
text(s,'Обращение → профиль\nГраф → докладная',64,242,1130,130,46,'#1D3F9E',true);
text(s,'В тексте находятся сущности и признаки риска.\nСлужащий сопоставляется с профилем; R07 учитывает обращение.\nАналитик проверяет цепочку и формирует черновик.',64,410,1120,200,29);
s=slide('Архитектура','25 с. Источники: docs/contracts.md, docs/backend.md, docs/decisions.md ADR-03/04/05/08. Postgres хранит связи; backend собирает подграф. В проверке использован анализатор rules, LLM не подключена. При недоступности LLM предусмотрен фоллбэк.');
lines(s,['React + TypeScript + Cytoscape\nПрофиль, обращения, интерактивный граф','FastAPI → PostgreSQL\nСвязи, объяснимые правила, баллы и доказательства','LLM через OpenAI-совместимый порт\nРазбор текста; резервный анализ на правилах'],218);
s=slide('Демо: разбор обращения','45 с. Скриншот реального локального стенда FastAPI + PostgreSQL, 11.11.2026, docs/presentation/screenshots/appeal.png. Данные экспортированы из проверенных в репозитории моков в отдельную тестовую БД. H1 сопоставлен с Соколовым. Текущий фоллбэк rules выбрал procurement, а не ожидаемый conflict_of_interest: это открытое расхождение демо, не результат LLM. Повторный анализ также проверен.');
text(s,'Сущности в тексте\nКатегория и сигналы\nМаршрут обращения\nСвязанный служащий',64,240,360,280,30);
s.images.add({blob:new Uint8Array(await fs.readFile(path.join(root,'docs/presentation/screenshots/appeal.png'))),contentType:'image/png',fit:'contain',alt:'Разбор H1 на реальном локальном API',position:{left:420,top:202,width:800,height:390}});
text(s,'Проверка без LLM: анализатор на правилах',64,600,1110,36,24,'#69748B');
s=slide('Демо: цепочка R01','35 с. Скриншот docs/presentation/screenshots/graph.png с реального API. Соколов → супруга → ООО ДорСтройРесурс → 5 контрактов → его орган. Сумма приблизительная, потому что подписи API округлены. Выбор R01 приглушает остальные узлы. R07 и узел созданного обращения проверены. Докладная успешно сформирована на реальном бэкенде.');
text(s,'Служащий\n↓\nСупруга\n↓\nКомпания\n↓\nКонтракты органа',64,215,390,375,32,'#1D3F9E',true);
s.images.add({blob:new Uint8Array(await fs.readFile(path.join(root,'docs/presentation/screenshots/graph.png'))),contentType:'image/png',fit:'contain',alt:'Подсвеченная цепочка R01',position:{left:500,top:182,width:650,height:455}});
s=slide('Проверки и качество','35 с. 16 unit-тестов backend выполнены uv run pytest. 14 frontend unit-тестов: Unicode, смещения, группировка, цепочки, адаптеры. Сквозной браузерный прогон на FastAPI + Postgres прошёл. Precision/recall не измерены: цель make eval отсутствует. Это не метрики качества ML. До защиты нужно получить отчёт AI-08 и обновить этот слайд. Нельзя подставлять вымышленные числа.');
text(s,'16',64,226,240,95,82,'#1D3F9E',true);text(s,'unit-тестов бэкенда',64,326,470,50,27);
text(s,'14',670,226,240,95,82,'#1D3F9E',true);text(s,'unit-тестов фронтенда',670,326,470,50,27);
text(s,'Сквозной сценарий проверен на FastAPI + PostgreSQL',64,427,1140,60,30);
text(s,'Precision / recall пока не измерены: make eval ещё не реализован.\nРезультаты на синтетике требуют проверки на пилоте.',64,523,1140,90,25,'#69748B');
s=slide('Этика и развитие','30 с. Источники: docs/decisions.md ADR-09/11 и docs/demo.md. Это принципы проектирования, а не юридическое заключение о соблюдении 152-ФЗ. Ролевой доступ и полноценный аудит нельзя выдавать за реализованные: нужны до пилота. Ответы жюри: цель и минимизация данных; человек принимает решение; в реальном контуре локальная LLM. Развитие: кадровые интеграции, ЕГРЮЛ, ЕИС, калибровка на отметках аналитика. Пилот 2–3 месяца — предложение команды.');
lines(s,['Флаг требует проверки; решение принимает человек.\nДля демонстрации используются только вымышленные лица.','Перед пилотом: правовые основания, роли и аудит,\nлокальная LLM и оценка качества на данных пилота.','Далее: кадровые сведения, ЕГРЮЛ и ЕИС;\nкалибровка по подтверждённым и ложным сигналам.'],218);
await (await PresentationFile.exportPptx(deck)).save(path.join(out,'candidate.pptx'));
for(const [i,slide] of deck.slides.items.entries()){
 const png=await deck.export({slide,format:'png',scale:1});
 await fs.writeFile(path.join(out,`slide-${i+1}.png`),new Uint8Array(await png.arrayBuffer()));
}
console.log('Exported 8 editable slides and previews:',out);
