export type ObstructionType =
  | 'water_tank'
  | 'staircase_room'
  | 'parapet'
  | 'tree_shade'
  | 'dish_antenna'
  | 'solar_water_heater'
  | 'other';

export type Severity = 'low' | 'medium' | 'high';

export interface Obstruction {
  id: string;
  obstruction_type: ObstructionType;
  /** Fractions of the image, 0 to 1. */
  bbox_x: number;
  bbox_y: number;
  bbox_w: number;
  bbox_h: number;
  severity: Severity;
}

export interface RoofAssessment {
  status: 'pending' | 'done' | 'failed';
  photo_url: string | null;
  /** Calculated in code from the LLM's usable fraction. */
  usable_area_sqm: number | null;
  max_kw_by_area: number | null;
  shade_risk: Severity | null;
  summary: string | null;
  obstructions: Obstruction[];
}
