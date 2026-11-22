// Match Russian swear words and common inflections at word boundaries.
// This only drives the mascot's expression.
const profanity =
  /^(?:бля(?:ть|д[а-я]*)?|сук(?:а|и|у|ой|ами|ах)|мудак(?:а|у|ом|и|ов|ам|ами|ах)?|долбоеб[а-я]*|(?:на|по|за|вы|про|пере|под|раз|у|от|до|с|в|о|об|при)?(?:пизд[а-я]+|ху(?:й|я|е|ю|и)[а-я]*|еб[аеилун][а-я]*))$/u;

export function hasProfanity(draft: string) {
  const words = draft
    .toLowerCase()
    .replaceAll('ё', 'е')
    .match(/[\p{L}\p{M}\p{N}_]+/gu);
  return words?.some((word) => profanity.test(word)) ?? false;
}
