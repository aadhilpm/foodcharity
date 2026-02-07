import { useFrappeGetCall } from 'frappe-react-sdk'

interface LocationOption {
  value: string
  label: string
  x?: number
  y?: number
}

export function useZones() {
  const { data, error, isLoading } = useFrappeGetCall<{ message: LocationOption[] }>(
    'foodcharity.api.get_zones',
    undefined,
    undefined,
    { revalidateOnFocus: false }
  )

  return {
    zones: data?.message || [],
    error,
    isLoading,
  }
}

export function useStreets(zoneNumber: string | null) {
  const { data, error, isLoading } = useFrappeGetCall<{ message: LocationOption[] }>(
    zoneNumber ? 'foodcharity.api.get_streets' : null,
    zoneNumber ? { zone_number: zoneNumber } : undefined,
    undefined,
    { revalidateOnFocus: false }
  )

  return {
    streets: data?.message || [],
    error,
    isLoading,
  }
}

export function useBuildings(zoneNumber: string | null, streetNumber: string | null) {
  const { data, error, isLoading } = useFrappeGetCall<{ message: LocationOption[] }>(
    zoneNumber && streetNumber ? 'foodcharity.api.get_buildings' : null,
    zoneNumber && streetNumber
      ? { zone_number: zoneNumber, street_number: streetNumber }
      : undefined,
    undefined,
    { revalidateOnFocus: false }
  )

  return {
    buildings: data?.message || [],
    error,
    isLoading,
  }
}
