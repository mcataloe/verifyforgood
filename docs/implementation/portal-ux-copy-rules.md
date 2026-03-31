# Portal UX Copy Rules

## Tone

- Keep customer-facing copy clear, concise, trustworthy, and professional.
- Prefer direct task language over explanation of how the product is built.
- Use short descriptions only when they help a user complete an action.

## Avoid

- Environment labels such as `development`, `staging`, `Env:`, or similar runtime metadata.
- Internal architecture language such as `metadata`, `context boundary`, `system anchor`, `internal source`, `contract persistence`, `bootstrap`, or `environment surface`.
- Describing UI structure to users with phrases like `auth boundary`, `shared shell`, `detail surface`, or similar implementation framing.
- Implementation details such as `backend-managed`, `tenant-aware`, `provider boundary`, `model source`, `query execution`, or route/path references unless the user must act on them.
- Raw internal identifiers such as account IDs, workspace IDs, query IDs, raw slugs, or other internal-only references unless they are directly user-editable or required for support.

## Prefer

- Use customer-ready labels such as `Organization`, `Team`, `Billing`, `Usage`, `API Keys`, `Settings`, `Security`, and `Notifications`.
- Use task-focused headings such as `Account details`, `Create organization`, `Support contact`, or `Billing tools`.
- Hide internal identifiers when they are not useful to the customer.

| Avoid | Prefer |
| --- | --- |
| `organization context` | `organization` |
| `workspace context` | `account details` or remove |
| `backend-managed billing portal` | `billing portal` |
| `metadata` | remove or replace with a customer task label |
| raw ids, slugs, model references, query ids | hide unless directly user-actionable |

## Naming

- Default to plain product language that matches user intent.
- If a heading is already obvious, omit the subtitle instead of adding filler text.
- Keep labels scannable and customer-oriented.
