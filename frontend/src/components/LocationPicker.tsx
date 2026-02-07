interface LocationOption {
  value: string
  label: string
  x?: number
  y?: number
}

interface LocationPickerProps {
  zones: LocationOption[]
  streets: LocationOption[]
  buildings: LocationOption[]
  zonesLoading: boolean
  streetsLoading: boolean
  buildingsLoading: boolean
  zoneNumber: string
  streetNumber: string
  buildingNumber: string
  onZoneChange: (value: string) => void
  onStreetChange: (value: string) => void
  onBuildingChange: (value: string) => void
}

export default function LocationPicker({
  zones,
  streets,
  buildings,
  zonesLoading,
  streetsLoading,
  buildingsLoading,
  zoneNumber,
  streetNumber,
  buildingNumber,
  onZoneChange,
  onStreetChange,
  onBuildingChange,
}: LocationPickerProps) {
  return (
    <div className="location-picker">
      <p className="location-hint">
        Use Qatar National Address to find your exact location (optional but recommended)
      </p>

      <div className="location-grid">
        {/* Zone Selection */}
        <div className="form-field">
          <label htmlFor="zone_number" className="form-label">
            Zone Number
          </label>
          <select
            id="zone_number"
            name="zone_number"
            value={zoneNumber}
            onChange={(e) => onZoneChange(e.target.value)}
            className="form-select"
            disabled={zonesLoading}
          >
            <option value="">
              {zonesLoading ? 'Loading zones...' : 'Select Zone'}
            </option>
            {zones.map((zone) => (
              <option key={zone.value} value={zone.value}>
                {zone.label}
              </option>
            ))}
          </select>
        </div>

        {/* Street Selection */}
        <div className="form-field">
          <label htmlFor="street_number" className="form-label">
            Street Number
          </label>
          <select
            id="street_number"
            name="street_number"
            value={streetNumber}
            onChange={(e) => onStreetChange(e.target.value)}
            className="form-select"
            disabled={!zoneNumber || streetsLoading}
          >
            <option value="">
              {!zoneNumber
                ? 'Select zone first'
                : streetsLoading
                ? 'Loading streets...'
                : 'Select Street'}
            </option>
            {streets.map((street) => (
              <option key={street.value} value={street.value}>
                {street.label}
              </option>
            ))}
          </select>
        </div>

        {/* Building Selection */}
        <div className="form-field">
          <label htmlFor="building_number" className="form-label">
            Building Number
          </label>
          <select
            id="building_number"
            name="building_number"
            value={buildingNumber}
            onChange={(e) => onBuildingChange(e.target.value)}
            className="form-select"
            disabled={!streetNumber || buildingsLoading}
          >
            <option value="">
              {!streetNumber
                ? 'Select street first'
                : buildingsLoading
                ? 'Loading buildings...'
                : 'Select Building'}
            </option>
            {buildings.map((building) => (
              <option key={building.value} value={building.value}>
                {building.label}
              </option>
            ))}
          </select>
        </div>
      </div>
    </div>
  )
}
