export interface Job {
  id: string
  company_name: string
  role: string
  ctc: string
  location: string
  bias_score?: number
  skill_match?: number
}
