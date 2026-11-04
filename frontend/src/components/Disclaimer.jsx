// Same wording as the API's disclaimer. Pass the API's text when a response includes one.
const DISCLAIMER =
  'Demand indicator only. A gap can also exist for reasons the data cannot see, such as high rent or a business that closed there before.'

export default function Disclaimer({ text = DISCLAIMER, className = '' }) {
  return <p className={`text-sm leading-relaxed text-stone-600 ${className}`}>{text}</p>
}
