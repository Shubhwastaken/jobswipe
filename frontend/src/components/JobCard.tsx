import { useState } from 'react'
import api from '../services/api'
import { useAuthStore } from '../store/authStore'

interface Props {
  job: any
  onApplied?: () => void
  isApplied?: boolean
}

const JobCard = ({ job, onApplied, isApplied = false }: Props) => {
  const studentId = useAuthStore((s) => s.studentId)
  const [applying, setApplying] = useState(false)
  const [applied, setApplied] = useState(isApplied)

  const applyToJob = async () => {
    if (!studentId) return
    setApplying(true)
    try {
      await api.post(`/applications/apply/${studentId}/${job.id}`)
      setApplied(true)
      onApplied?.()
    } catch (err: any) {
      console.error(err)
      alert(err.response?.data?.detail || 'Could not apply to this job. You may have already applied.')
    } finally {
      setApplying(false)
    }
  }

  const skillMatch = job.skill_match ? `${Math.round(job.skill_match * 100)}%` : null

  return (
    <div className="border-l-4 border-blue-500 bg-white p-6 rounded-lg shadow-sm hover:shadow-md transition">
      <div className="flex justify-between items-start mb-3">
        <div className="flex-1">
          <h3 className="font-bold text-lg text-gray-900">{job.role}</h3>
          <p className="text-gray-600 text-sm">{job.company_name}</p>
        </div>
        {skillMatch && (
          <span className="bg-green-100 text-green-800 px-3 py-1 rounded-full text-sm font-semibold">
            {skillMatch} match
          </span>
        )}
      </div>

      <div className="grid grid-cols-2 gap-4 text-sm text-gray-600 mb-4">
        <div>
          <p className="text-xs font-medium uppercase text-gray-500">CTC</p>
          <p className="font-medium">{job.ctc || 'Not specified'}</p>
        </div>
        <div>
          <p className="text-xs font-medium uppercase text-gray-500">Location</p>
          <p className="font-medium">{job.location || 'Remote'}</p>
        </div>
      </div>

      {job.required_skills && job.required_skills.length > 0 && (
        <div className="mb-4">
          <p className="text-xs font-medium uppercase text-gray-500 mb-2">Required Skills</p>
          <div className="flex flex-wrap gap-2">
            {job.required_skills.slice(0, 5).map((skill: string) => (
              <span key={skill} className="bg-gray-100 text-gray-800 px-2 py-1 rounded text-xs">
                {skill}
              </span>
            ))}
            {job.required_skills.length > 5 && (
              <span className="text-gray-500 text-xs">+{job.required_skills.length - 5} more</span>
            )}
          </div>
        </div>
      )}

      <button 
        onClick={applyToJob}
        disabled={applying || applied}
        className={`w-full p-2 rounded font-semibold transition ${
          applied 
            ? 'bg-green-100 text-green-800 cursor-not-allowed' 
            : 'bg-blue-600 text-white hover:bg-blue-700'
        }`}
      >
        {applying ? 'Applying...' : applied ? 'Applied' : 'Apply Now'}
      </button>
    </div>
  )
}

export default JobCard
