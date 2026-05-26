# Phase 10：集成与文档 — 实现模式

**映射日期：** 2026-05-26

## 懒加载面板模式

```typescript
const loaded = ref(false)
async function onExpand() {
  if (loaded.value) return
  data.value = await getPathB(jobId)
  loaded.value = true
}
```

## 状态行着色（ValidationPanel）

| status | Element Plus |
|--------|----------------|
| fail | `danger` row-class |
| warn | `warning` |
| pass | 默认（仅「显示 pass」时） |

## 下载扩展

```typescript
export type DownloadKind = ... | 'subscription-fee-rates'
```

`JobDetail` 第五按钮与 `downloadBlob(jobId, 'subscription-fee-rates', 'subscription_fee_rates.xlsx')`

---

*Phase: 10-integration-docs*
