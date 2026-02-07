import { DoctypeField } from '../hooks/useDoctypeFields'

interface DynamicFieldProps {
  field: DoctypeField
  value: any
  onChange: (value: any) => void
  required?: boolean
}

export default function DynamicField({ field, value, onChange, required }: DynamicFieldProps) {
  const { fieldname, fieldtype, label, options, description } = field

  // Parse options for Select fields (options come as newline-separated string)
  const getSelectOptions = (): string[] => {
    if (!options) return []
    return options.split('\n').filter((opt) => opt.trim() !== '')
  }

  const renderField = () => {
    switch (fieldtype) {
      case 'Data':
        return (
          <input
            type="text"
            id={fieldname}
            name={fieldname}
            value={value || ''}
            onChange={(e) => onChange(e.target.value)}
            className="form-input"
            required={required}
          />
        )

      case 'Int':
        return (
          <input
            type="number"
            id={fieldname}
            name={fieldname}
            value={value || ''}
            onChange={(e) => onChange(e.target.value ? parseInt(e.target.value, 10) : '')}
            className="form-input"
            min="0"
            required={required}
          />
        )

      case 'Currency':
      case 'Float':
        return (
          <input
            type="number"
            id={fieldname}
            name={fieldname}
            value={value || ''}
            onChange={(e) => onChange(e.target.value ? parseFloat(e.target.value) : '')}
            className="form-input"
            step="0.01"
            min="0"
            required={required}
          />
        )

      case 'Select':
        const selectOptions = getSelectOptions()
        return (
          <select
            id={fieldname}
            name={fieldname}
            value={value || ''}
            onChange={(e) => onChange(e.target.value)}
            className="form-select"
            required={required}
          >
            <option value="">Select {label}</option>
            {selectOptions.map((opt) => (
              <option key={opt} value={opt}>
                {opt}
              </option>
            ))}
          </select>
        )

      case 'Check':
        return (
          <div className="checkbox-wrapper">
            <input
              type="checkbox"
              id={fieldname}
              name={fieldname}
              checked={value || false}
              onChange={(e) => onChange(e.target.checked ? 1 : 0)}
              className="form-checkbox"
            />
            <label htmlFor={fieldname} className="checkbox-label">
              {label}
            </label>
          </div>
        )

      case 'Text':
      case 'Small Text':
        return (
          <textarea
            id={fieldname}
            name={fieldname}
            value={value || ''}
            onChange={(e) => onChange(e.target.value)}
            className="form-textarea"
            rows={3}
            required={required}
          />
        )

      case 'Phone':
        return (
          <input
            type="tel"
            id={fieldname}
            name={fieldname}
            value={value || ''}
            onChange={(e) => onChange(e.target.value)}
            className="form-input"
            required={required}
          />
        )

      case 'Date':
        return (
          <input
            type="date"
            id={fieldname}
            name={fieldname}
            value={value || ''}
            onChange={(e) => onChange(e.target.value)}
            className="form-input"
            required={required}
          />
        )

      case 'Time':
        return (
          <input
            type="time"
            id={fieldname}
            name={fieldname}
            value={value || ''}
            onChange={(e) => onChange(e.target.value)}
            className="form-input"
            required={required}
          />
        )

      case 'Datetime':
        return (
          <input
            type="datetime-local"
            id={fieldname}
            name={fieldname}
            value={value || ''}
            onChange={(e) => onChange(e.target.value)}
            className="form-input"
            required={required}
          />
        )

      default:
        // Fallback to text input for unknown types
        return (
          <input
            type="text"
            id={fieldname}
            name={fieldname}
            value={value || ''}
            onChange={(e) => onChange(e.target.value)}
            className="form-input"
            required={required}
          />
        )
    }
  }

  // Check fields have their own layout
  if (fieldtype === 'Check') {
    return (
      <div className="form-field form-field-check">
        {renderField()}
        {description && <p className="field-description">{description}</p>}
      </div>
    )
  }

  return (
    <div className="form-field">
      <label htmlFor={fieldname} className="form-label">
        {label}
        {required && <span className="required">*</span>}
      </label>
      {renderField()}
      {description && <p className="field-description">{description}</p>}
    </div>
  )
}
