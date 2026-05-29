export const JOB_TABLE_SECTIONS = [
  { key: 'product-elements', label: '产品要素' },
  { key: 'fee-rates', label: '运营费率' },
  { key: 'lock-periods', label: '份额锁定期' },
  { key: 'share-classes', label: '分级份额' },
  { key: 'subscription-fee-rates', label: '申赎费率' },
] as const

export const TABLE_KEYS = JOB_TABLE_SECTIONS.map((s) => s.key)

export type TableKey = (typeof JOB_TABLE_SECTIONS)[number]['key']

export const JOB_FIELD_B = {
  label: '字段 B',
  routeName: 'job-field-b' as const,
}

const TABLE_KEY_SET = new Set<string>(TABLE_KEYS)

export function isValidTableKey(v: string): v is TableKey {
  return TABLE_KEY_SET.has(v)
}

export function sectionLabel(key: TableKey): string {
  const row = JOB_TABLE_SECTIONS.find((s) => s.key === key)
  return row?.label ?? key
}

/** Download filename per table section (exported xlsx). */
export const TABLE_DOWNLOAD_FILES: Record<TableKey, string> = {
  'product-elements': 'product_elements.xlsx',
  'fee-rates': 'fee_rates.xlsx',
  'lock-periods': 'lock_periods.xlsx',
  'share-classes': 'share_classes.xlsx',
  'subscription-fee-rates': 'subscription_fee_rates.xlsx',
}
