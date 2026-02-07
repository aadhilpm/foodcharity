import { useState, useCallback, useMemo } from 'react'
import { useFrappePostCall } from 'frappe-react-sdk'
import { useDoctypeFields, DoctypeField } from '../hooks/useDoctypeFields'
import { useZones, useStreets, useBuildings } from '../hooks/useLocationData'
import DynamicField from './DynamicField'
import LocationPicker from './LocationPicker'

interface OrderFormProps {
  doctype: string
}

// Fields to exclude from public form (internal/admin fields)
const EXCLUDED_FIELDS = [
  'assigned_volunteer',
  'coordinate',
  'delivery_needed', // We'll derive this from order_type
]

// Fields that are layout elements, not data fields
const LAYOUT_FIELDTYPES = ['Section Break', 'Column Break', 'Tab Break']

export default function OrderForm({ doctype }: OrderFormProps) {
  const { fields, isLoading: fieldsLoading, error: fieldsError } = useDoctypeFields(doctype)
  const [formData, setFormData] = useState<Record<string, any>>({})
  const [submitted, setSubmitted] = useState(false)
  const [orderId, setOrderId] = useState<string | null>(null)

  // Location data hooks
  const { zones, isLoading: zonesLoading } = useZones()
  const { streets, isLoading: streetsLoading } = useStreets(formData.zone_number || null)
  const { buildings, isLoading: buildingsLoading } = useBuildings(
    formData.zone_number || null,
    formData.street_number || null
  )

  // Submit order using frappe-react-sdk
  const { call: submitOrder, loading: submitting, error: submitError } = useFrappePostCall(
    'foodcharity.api.create_guest_order'
  )

  // Filter fields for public form
  const visibleFields = useMemo(() => {
    return fields.filter((field) => {
      if (EXCLUDED_FIELDS.includes(field.fieldname)) return false
      if (LAYOUT_FIELDTYPES.includes(field.fieldtype)) return false
      if (field.hidden) return false
      if (field.read_only) return false
      return true
    })
  }, [fields])

  // Check if a field should be visible based on depends_on
  const isFieldVisible = useCallback(
    (field: DoctypeField): boolean => {
      if (!field.depends_on) return true

      // Parse depends_on expression (e.g., "eval:doc.delivery_needed ==\"Yes\"")
      const dependsOn = field.depends_on
      if (dependsOn.startsWith('eval:')) {
        const expr = dependsOn.replace('eval:', '').trim()
        try {
          // Replace doc.fieldname with actual values
          const evalExpr = expr.replace(/doc\.(\w+)/g, (_, fieldname) => {
            const value = formData[fieldname]
            if (value === undefined || value === null || value === '') return '""'
            return JSON.stringify(value)
          })
          return eval(evalExpr)
        } catch {
          return true
        }
      }
      return true
    },
    [formData]
  )

  // Check if a field is required based on mandatory_depends_on
  const isFieldRequired = useCallback(
    (field: DoctypeField): boolean => {
      if (field.reqd) return true
      if (!field.mandatory_depends_on) return false

      const mandatoryDependsOn = field.mandatory_depends_on
      if (mandatoryDependsOn.startsWith('eval:')) {
        const expr = mandatoryDependsOn.replace('eval:', '').trim()
        try {
          const evalExpr = expr.replace(/doc\.(\w+)/g, (_, fieldname) => {
            const value = formData[fieldname]
            if (value === undefined || value === null || value === '') return '""'
            return JSON.stringify(value)
          })
          return eval(evalExpr)
        } catch {
          return false
        }
      }
      return false
    },
    [formData]
  )

  const handleFieldChange = useCallback((fieldname: string, value: any) => {
    setFormData((prev) => {
      const newData = { ...prev, [fieldname]: value }

      // Handle copy_mobile_to_whatsapp checkbox
      if (fieldname === 'copy_mobile_to_whatsapp' && value) {
        newData.whatsapp_number = prev.mobile || ''
      }
      if (fieldname === 'mobile' && prev.copy_mobile_to_whatsapp) {
        newData.whatsapp_number = value
      }

      // Auto-set delivery_needed based on order_type
      if (fieldname === 'order_type') {
        newData.delivery_needed = value === 'Delivery' ? 'Yes' : 'No'
      }

      // Clear dependent fields when parent changes
      if (fieldname === 'zone_number') {
        newData.street_number = ''
        newData.building_number = ''
      }
      if (fieldname === 'street_number') {
        newData.building_number = ''
      }

      // Clear compound_name if accommodation_type changes
      if (fieldname === 'accommodation_type' && value !== 'Villa Compound') {
        newData.compound_name = ''
      }

      return newData
    })
  }, [])

  // Update coordinates when building is selected
  const handleBuildingSelect = useCallback(
    (buildingNumber: string) => {
      const building = buildings.find((b) => b.value === buildingNumber)
      if (building && building.x && building.y) {
        setFormData((prev) => ({
          ...prev,
          building_number: buildingNumber,
          coordinate: `${building.y},${building.x}`,
        }))
      } else {
        handleFieldChange('building_number', buildingNumber)
      }
    },
    [buildings, handleFieldChange]
  )

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    // Validate required fields
    const missingFields: string[] = []
    visibleFields.forEach((field) => {
      if (isFieldVisible(field) && isFieldRequired(field)) {
        const value = formData[field.fieldname]
        if (value === undefined || value === null || value === '') {
          missingFields.push(field.label || field.fieldname)
        }
      }
    })

    if (missingFields.length > 0) {
      alert(`Please fill in required fields: ${missingFields.join(', ')}`)
      return
    }

    try {
      const result = await submitOrder({ data: JSON.stringify(formData) })
      if (result?.message?.success) {
        setSubmitted(true)
        setOrderId(result.message.order_id)
      }
    } catch (err) {
      console.error('Submission error:', err)
    }
  }

  if (fieldsLoading) {
    return (
      <div className="form-container">
        <div className="loading">Loading form...</div>
      </div>
    )
  }

  if (fieldsError) {
    return (
      <div className="form-container">
        <div className="error">Error loading form. Please try again.</div>
      </div>
    )
  }

  if (submitted) {
    return (
      <div className="form-container">
        <div className="success-message">
          <div className="success-icon">&#10003;</div>
          <h2>Thank You!</h2>
          <p>Your order has been submitted successfully.</p>
          {orderId && <p className="order-id">Order ID: <strong>{orderId}</strong></p>}
          <button
            className="btn btn-primary"
            onClick={() => {
              setSubmitted(false)
              setOrderId(null)
              setFormData({})
            }}
          >
            Submit Another Order
          </button>
        </div>
      </div>
    )
  }

  // Group fields by sections for better organization
  const isDeliveryOrder = formData.order_type === 'Delivery'

  return (
    <div className="form-container">
      <div className="form-header">
        <h1>Biryani Challenge</h1>
        <p>Order Registration Form</p>
      </div>

      <form onSubmit={handleSubmit} className="order-form">
        {/* Contact Information Section */}
        <section className="form-section">
          <h3>Contact Information</h3>
          <div className="form-grid">
            {visibleFields
              .filter((f) => ['name1', 'mobile', 'contact_number', 'whatsapp_number', 'copy_mobile_to_whatsapp', 'order_co'].includes(f.fieldname))
              .map((field) =>
                isFieldVisible(field) ? (
                  <DynamicField
                    key={field.fieldname}
                    field={field}
                    value={formData[field.fieldname]}
                    onChange={(value) => handleFieldChange(field.fieldname, value)}
                    required={isFieldRequired(field)}
                  />
                ) : null
              )}
          </div>
        </section>

        {/* Order Details Section */}
        <section className="form-section">
          <h3>Order Details</h3>
          <div className="form-grid">
            {visibleFields
              .filter((f) => ['order_type', 'no_of_biriyani', 'contribution_amount'].includes(f.fieldname))
              .map((field) =>
                isFieldVisible(field) ? (
                  <DynamicField
                    key={field.fieldname}
                    field={field}
                    value={formData[field.fieldname]}
                    onChange={(value) => handleFieldChange(field.fieldname, value)}
                    required={isFieldRequired(field)}
                  />
                ) : null
              )}
          </div>
        </section>

        {/* Delivery Information Section - Only show for delivery orders */}
        {isDeliveryOrder && (
          <section className="form-section">
            <h3>Delivery Information</h3>
            <div className="form-grid">
              {/* Accommodation Area - from doctype options */}
              {visibleFields
                .filter((f) => f.fieldname === 'accommodation_area')
                .map((field) => (
                  <DynamicField
                    key={field.fieldname}
                    field={field}
                    value={formData[field.fieldname]}
                    onChange={(value) => handleFieldChange(field.fieldname, value)}
                    required={isFieldRequired(field)}
                  />
                ))}

              {/* Location Picker using QNAS API */}
              <LocationPicker
                zones={zones}
                streets={streets}
                buildings={buildings}
                zonesLoading={zonesLoading}
                streetsLoading={streetsLoading}
                buildingsLoading={buildingsLoading}
                zoneNumber={formData.zone_number || ''}
                streetNumber={formData.street_number || ''}
                buildingNumber={formData.building_number || ''}
                onZoneChange={(value) => handleFieldChange('zone_number', value)}
                onStreetChange={(value) => handleFieldChange('street_number', value)}
                onBuildingChange={handleBuildingSelect}
              />

              {/* Door Number */}
              {visibleFields
                .filter((f) => f.fieldname === 'door_number')
                .map((field) => (
                  <DynamicField
                    key={field.fieldname}
                    field={field}
                    value={formData[field.fieldname]}
                    onChange={(value) => handleFieldChange(field.fieldname, value)}
                    required={isFieldRequired(field)}
                  />
                ))}

              {/* Accommodation Type */}
              {visibleFields
                .filter((f) => f.fieldname === 'accommodation_type')
                .map((field) => (
                  <DynamicField
                    key={field.fieldname}
                    field={field}
                    value={formData[field.fieldname]}
                    onChange={(value) => handleFieldChange(field.fieldname, value)}
                    required={isFieldRequired(field)}
                  />
                ))}

              {/* Compound Name - only if Villa Compound */}
              {formData.accommodation_type === 'Villa Compound' &&
                visibleFields
                  .filter((f) => f.fieldname === 'compound_name')
                  .map((field) => (
                    <DynamicField
                      key={field.fieldname}
                      field={field}
                      value={formData[field.fieldname]}
                      onChange={(value) => handleFieldChange(field.fieldname, value)}
                      required={isFieldRequired(field)}
                    />
                  ))}
            </div>
          </section>
        )}

        {submitError && (
          <div className="error-message">
            Failed to submit order. Please try again.
          </div>
        )}

        <div className="form-actions">
          <button type="submit" className="btn btn-primary" disabled={submitting}>
            {submitting ? 'Submitting...' : 'Submit Order'}
          </button>
        </div>
      </form>
    </div>
  )
}
