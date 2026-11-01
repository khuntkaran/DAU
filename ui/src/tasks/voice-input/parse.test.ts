import { describe, expect, it } from 'vitest';
import { parseVoiceFields } from './parse';

describe('parseVoiceFields', () => {
  it.each([
    ['I use 330 units a month my budget is 2 lakh and my terrace is 40 square metres', 330, 200000, 40],
    ['my monthly use is 250 units', 250, null, null],
    ['budget two lakh fifty thousand', null, 250000, null],
    ['budget is ₹1,85,000 and roof area 55 sq m', null, 185000, 55],
    ['three hundred thirty units', 330, null, null],
    ['500 units 3 lakh budget 60 square meter roof', 500, 300000, 60],
    ['मेरी मासिक खपत 330 यूनिट है बजट 2 लाख है और छत 40 वर्ग मीटर की है', 330, 200000, 40],
    ['खपत तीन सौ यूनिट और बजट ढाई लाख रुपये', 300, 250000, null],
    ['૪૨૦ યુનિટ વપરાશ છે', 420, null, null],
    ['મારો માસિક વપરાશ 330 યુનિટ છે બજેટ બે લાખ છે અને ધાબું 40 ચોરસ મીટરનું છે', 330, 200000, 40],
    ['બજેટ અઢી લાખ', null, 250000, null],
  ])('reads "%s"', (transcript, units, budget, roof) => {
    expect(parseVoiceFields(transcript)).toEqual({ monthly_units: units, budget_inr: budget, roof_area_sqm: roof });
  });

  it('returns what was said, not sample values', () => {
    expect(parseVoiceFields('I use 123 units').monthly_units).toBe(123);
    expect(parseVoiceFields('I use 777 units').monthly_units).toBe(777);
  });

  it('leaves every field empty when no number was said', () => {
    expect(parseVoiceFields('hello I want solar on my house')).toEqual({
      monthly_units: null,
      budget_inr: null,
      roof_area_sqm: null,
    });
  });

  it('does not treat the electricity bill as the budget', () => {
    expect(parseVoiceFields('my bill is 3000 rupees').budget_inr).toBeNull();
  });

  it('treats a large unlabelled amount as the budget', () => {
    expect(parseVoiceFields('I can spend 2 lakh').budget_inr).toBe(200000);
  });

  it('converts square feet to square metres', () => {
    expect(parseVoiceFields('my roof is 500 square feet').roof_area_sqm).toBe(46.5);
  });
});
