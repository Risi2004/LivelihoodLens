// Labels for the API's skill and hours ids, in the mock-up's order.
export const SKILLS = [
  { id: 'sewing', label: 'Sewing' },
  { id: 'cooking', label: 'Cooking & baking' },
  { id: 'beauty', label: 'Beauty & hair' },
  { id: 'electronics_repair', label: 'Phone & electronics repair' },
  { id: 'tutoring', label: 'Tutoring' },
  { id: 'handicrafts', label: 'Handicrafts' },
  { id: 'retail', label: 'Retail' },
]

// The invisible word joiners (⁠) stop "10–20" splitting across two lines at the dash.
export const HOURS = [
  { id: 'under10', label: 'Under 10' },
  { id: '10-20', label: '10⁠–⁠20' },
  { id: '20-40', label: '20⁠–⁠40' },
  { id: '40+', label: '40+' },
]

export const BUDGET = { min: 25_000, max: 300_000, step: 5_000, default: 75_000 }

export function skillLabel(id) {
  return SKILLS.find((skill) => skill.id === id)?.label ?? id
}

export function hoursLabel(id) {
  return HOURS.find((hours) => hours.id === id)?.label ?? id
}
