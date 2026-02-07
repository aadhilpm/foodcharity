import { useFrappeGetCall } from 'frappe-react-sdk'

export interface DoctypeField {
  fieldname: string
  fieldtype: string
  label: string
  options?: string
  reqd?: number
  depends_on?: string
  mandatory_depends_on?: string
  default?: string
  description?: string
  read_only?: number
  hidden?: number
}

export function useDoctypeFields(doctype: string) {
  const { data, error, isLoading, mutate } = useFrappeGetCall<{ message: DoctypeField[] }>(
    'foodcharity.api.get_doctype_fields',
    { doctype },
    undefined,
    {
      revalidateOnFocus: false,
      revalidateIfStale: false,
    }
  )

  return {
    fields: data?.message || [],
    error,
    isLoading,
    refetch: mutate,
  }
}
