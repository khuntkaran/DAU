import { delay } from '@/shared/mock/store';
import type { RuleCitation, RuleSet } from './types';

const CABINET = 'https://www.pib.gov.in/PressReleasePage.aspx?PRID=2010133&reg=48&lang=2';
const SOLAR_REVOLUTION = 'https://www.pib.gov.in/PressReleaseIframePage.aspx?PRID=2111106&reg=48&lang=2';

const citations: Record<string, RuleCitation> = {
  CFA_SLAB_1: { title: 'CFA for the first 2 kW', source: 'PIB, Cabinet approves PM-Surya Ghar', url: CABINET, status: 'confirmed' },
  CFA_SPECIAL: { title: 'Higher CFA in special category states', source: 'Quick Estimate, PM Surya Ghar FAQ', url: 'https://quickestimate.co/blog/pm-surya-ghar-faq', status: 'verify' },
  SIZE_BANDS: { title: 'Suitable system size by monthly use', source: "PIB, PM Surya Ghar, India's Solar Revolution", url: SOLAR_REVOLUTION, status: 'confirmed' },
  ROOF_AREA: { title: 'About 10 m² of shadow-free roof per kW', source: 'Secured Engineers, shadow-free area calculator', url: 'https://www.securedengineers.com/solar-shadow-free-area-calculator/', status: 'verify' },
  BENCHMARK_COST: { title: 'Benchmark cost per kW', source: 'MNRE draft guidelines for PM-Surya Ghar', url: 'https://solarrooftop.pmsuryaghar.gov.in/notification/172_notification.pdf', status: 'verify' },
  GENERATION: { title: 'Generation of about 120 kWh per kW per month', source: 'SuryaSetu assumption, within vendor estimates of 110-130 kWh', url: null, status: 'assumption' },
  TARIFF_DEFAULT: { title: 'Sample tariff of ₹6.50 per kWh', source: 'SuryaSetu assumption, not a DISCOM tariff', url: null, status: 'assumption' },
};

export async function getCurrentRules(): Promise<RuleSet> {
  await delay(0);
  return { version: 'pm_surya_ghar_v2024_03', checked_on: '2026-11-01', citations };
}
