# API Contract: Đặc tả 003

## GET `/api/v1/candidates/{candidate_id}/eligible-recruiters`

`200 OK`:

```json
{
  "candidate_id": "uuid",
  "total": 2,
  "strict_region": true,
  "require_active_campaign": true,
  "recruiters": []
}
```

`404`: `CANDIDATE_NOT_FOUND`.

`422`: `CANDIDATE_REGION_REQUIRED` khi bật strict region nhưng candidate không có region.
