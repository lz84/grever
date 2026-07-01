// 统一的前端显示映射

const MODE_LABELS: Record<string, string> = {
  engineering: '工程模式',
  research: '研究模式',
};

const DIVERSITY_LABELS: Record<string, string> = {
  best: '最优',
  portfolio: '组合',
};

export function getModeLabel(mode: string): string {
  return MODE_LABELS[mode] ?? mode;
}

export function getDiversityLabel(diversity: string): string {
  return DIVERSITY_LABELS[diversity] ?? diversity;
}

export function isResearchMode(mode: string): boolean {
  return mode === 'research';
}

export function isEngineeringMode(mode: string): boolean {
  return mode === 'engineering';
}
