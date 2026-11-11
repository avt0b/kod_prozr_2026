from src.modules.assistant.domain.answer import Answer, Question, Source

# Справка по правилам — чтобы заглушка отвечала по делу хотя бы на вопросы о методике.
RULES_HELP = {
    "R01": "служащий или родственник — учредитель/руководитель поставщика своего органа "
    "(273-ФЗ ст. 10, 11)",
    "R02": "служащий — учредитель/руководитель действующей коммерческой организации (79-ФЗ ст. 17)",
    "R07": "служащий упомянут в обращениях с признаками коррупции",
}


class FakeAssistant:
    """Заглушка порта AssistantInterface: детерминированный ответ без LLM и без БД."""

    async def ask(self, question: Question) -> Answer:
        text = question.text.upper()
        mentioned = [code for code in RULES_HELP if code in text]
        if mentioned:
            body = "; ".join(f"{code} — {RULES_HELP[code]}" for code in mentioned)
            return Answer(
                answer=f"Справка по правилам: {body}.",
                sources=tuple(Source(type="rule", id=code, label=code) for code in mentioned),
            )
        return Answer(
            answer=(
                "Ассистент работает в демонстрационном режиме и пока не отвечает на "
                "произвольные вопросы. Спросите о правилах риска, например: «что такое R01?»."
            ),
            sources=(),
        )
