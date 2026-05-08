export type ActivityKind = 'ranking' | 'bias' | 'eligibility' | 'skills' | 'export';
export type ActivityTone = 'success' | 'warning' | 'info' | 'neutral';

export interface ActivityEntry {
  id: string;
  kind: ActivityKind;
  tone: ActivityTone;
  title: string;
  detail: string;
  actor: string;
  status: string;
  createdAt: string;
}

const ACTIVITY_STORAGE_KEY = 'jobswipe.activityLog';

export function readActivityLog(): ActivityEntry[] {
  try {
    const raw = window.localStorage.getItem(ACTIVITY_STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export function recordActivity(entry: Omit<ActivityEntry, 'id' | 'createdAt'>) {
  const nextEntry: ActivityEntry = {
    ...entry,
    id: `${Date.now()}-${Math.random().toString(16).slice(2)}`,
    createdAt: new Date().toISOString(),
  };

  const nextLog = [nextEntry, ...readActivityLog()].slice(0, 20);
  window.localStorage.setItem(ACTIVITY_STORAGE_KEY, JSON.stringify(nextLog));
  window.dispatchEvent(new CustomEvent('jobswipe:activity-log-updated'));
}
