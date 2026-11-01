/**
 * Reads form values out of what the household actually said, in English, Hindi
 * or Gujarati. Partner A's Whisper and LLM job can replace this when it works.
 * Only numbers that were spoken are returned: a field not mentioned stays null.
 */
import type { VoiceFields } from './types';

const SQUARE_FEET_PER_SQUARE_METRE = 10.764;
const MAX_KEYWORD_DISTANCE = 6;

const DIGITS: Record<string, string> = {};
for (const [index, digit] of [...'०१२३४५६७८९'].entries()) DIGITS[digit] = String(index);
for (const [index, digit] of [...'૦૧૨૩૪૫૬૭૮૯'].entries()) DIGITS[digit] = String(index);

const NUMBER_WORDS: Record<string, number> = {
  one: 1, two: 2, three: 3, four: 4, five: 5, six: 6, seven: 7, eight: 8, nine: 9, ten: 10,
  eleven: 11, twelve: 12, thirteen: 13, fourteen: 14, fifteen: 15, sixteen: 16, seventeen: 17,
  eighteen: 18, nineteen: 19, twenty: 20, thirty: 30, forty: 40, fifty: 50, sixty: 60, seventy: 70,
  eighty: 80, ninety: 90,
  एक: 1, दो: 2, तीन: 3, चार: 4, पांच: 5, पाँच: 5, छह: 6, छः: 6, सात: 7, आठ: 8, नौ: 9, दस: 10,
  बीस: 20, तीस: 30, चालीस: 40, पचास: 50, साठ: 60, सत्तर: 70, अस्सी: 80, नब्बे: 90,
  डेढ़: 1.5, ढाई: 2.5,
  બે: 2, ત્રણ: 3, ચાર: 4, પાંચ: 5, છ: 6, સાત: 7, આઠ: 8, નવ: 9, દસ: 10,
  વીસ: 20, ત્રીસ: 30, ચાલીસ: 40, પચાસ: 50, સાઠ: 60, સિત્તેર: 70, એંસી: 80, નેવું: 90,
  દોઢ: 1.5, અઢી: 2.5, એક: 1,
};

const MULTIPLIERS: Record<string, number> = {
  hundred: 100, सौ: 100, સો: 100,
  thousand: 1000, हज़ार: 1000, हजार: 1000, હજાર: 1000,
  lakh: 100000, lakhs: 100000, lac: 100000, लाख: 100000, લાખ: 100000,
};

const KEYWORDS = {
  units: ['unit', 'kwh', 'यूनिट', 'युनिट', 'યુનિટ'],
  budget: ['budget', 'बजट', 'બજેટ', 'rupee', 'rs', 'रुपय', 'रुपए', 'રૂપિયા'],
  roof: ['roof', 'terrace', 'square', 'sq', 'sqm', 'छत', 'वर्ग', 'ધાબ', 'અગાસી', 'ચોરસ', 'છત'],
};

// A spoken bill amount must not be mistaken for the budget.
const BILL = ['bill', 'बिल', 'બિલ'];
const BILL_DISTANCE = 3;

const FEET = ['feet', 'foot', 'ft', 'sqft', 'फीट', 'फुट', 'ફૂટ', 'ફીટ'];

type Field = keyof typeof KEYWORDS;

interface SpokenNumber {
  value: number;
  start: number;
  end: number;
}

function tokenize(text: string): string[] {
  const latinDigits = [...text.toLowerCase()].map((char) => DIGITS[char] ?? char).join('');
  return latinDigits
    .replace(/(\d),(?=\d)/g, '$1')
    .replace(/₹/g, ' rs ')
    .replace(/(\d)([^\d.\s])/g, '$1 $2')
    .split(/[\s,;:!?।|]+|\.(?!\d)/)
    .filter(Boolean);
}

function findNumbers(tokens: string[]): SpokenNumber[] {
  const numbers: SpokenNumber[] = [];
  let index = 0;
  while (index < tokens.length) {
    let total = 0;
    let current = 0;
    let cursor = index;
    for (; cursor < tokens.length; cursor += 1) {
      const token = tokens[cursor] ?? '';
      const plain = /^\d+(\.\d+)?$/.test(token) ? Number(token) : NUMBER_WORDS[token];
      const multiplier = MULTIPLIERS[token];
      if (plain !== undefined) current += plain;
      else if (multiplier === 100) current = (current || 1) * 100;
      else if (multiplier) {
        total += (current || 1) * multiplier;
        current = 0;
      } else break;
    }
    if (cursor > index) {
      numbers.push({ value: total + current, start: index, end: cursor - 1 });
      index = cursor;
    } else {
      index += 1;
    }
  }
  return numbers;
}

function gap(position: number, number: SpokenNumber) {
  if (position < number.start) return number.start - position;
  return position > number.end ? position - number.end : 0;
}

function isFeet(tokens: string[], number: SpokenNumber) {
  return tokens
    .slice(number.end + 1, number.end + 4)
    .some((token) => FEET.some((word) => token.startsWith(word)));
}

export function parseVoiceFields(transcript: string): VoiceFields {
  const tokens = tokenize(transcript);
  const numbers = findNumbers(tokens);

  const pairs: { field: Field; number: SpokenNumber; distance: number }[] = [];
  tokens.forEach((token, position) => {
    for (const field of Object.keys(KEYWORDS) as Field[]) {
      if (!KEYWORDS[field].some((word) => token.startsWith(word))) continue;
      for (const number of numbers) {
        const distance = gap(position, number);
        if (distance <= MAX_KEYWORD_DISTANCE) pairs.push({ field, number, distance });
      }
    }
  });

  // Closest pairs win, and each number and each field is used once.
  const chosen = new Map<Field, SpokenNumber>();
  const used = new Set<SpokenNumber>();
  tokens.forEach((token, position) => {
    if (!BILL.some((word) => token.startsWith(word))) return;
    for (const number of numbers) {
      if (gap(position, number) <= BILL_DISTANCE) used.add(number);
    }
  });
  for (const { field, number } of pairs.sort((a, b) => a.distance - b.distance)) {
    if (!chosen.has(field) && !used.has(number)) {
      chosen.set(field, number);
      used.add(number);
    }
  }

  // "Two lakh" is a budget even if the word budget was not said.
  if (!chosen.has('budget')) {
    const large = numbers.find((number) => !used.has(number) && number.value >= 10000);
    if (large) chosen.set('budget', large);
  }

  const roof = chosen.get('roof');
  let roofArea = roof?.value ?? null;
  if (roof && roofArea !== null && isFeet(tokens, roof)) {
    roofArea = Math.round((roofArea / SQUARE_FEET_PER_SQUARE_METRE) * 10) / 10;
  }

  return {
    monthly_units: chosen.get('units')?.value ?? null,
    budget_inr: chosen.get('budget')?.value ?? null,
    roof_area_sqm: roofArea,
  };
}
