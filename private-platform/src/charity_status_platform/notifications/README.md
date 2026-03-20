# Notifications

Purpose:

- reserved home for future internal notifications, support workflows, and private eventing coordination

Allowed contents:

- customer support notifications
- trial/billing/admin notification orchestration
- private event dispatch adapters and support workflow hooks

Forbidden contents:

- public-core reusable domain logic
- public API surface contracts

Dependency direction:

- may depend on `charity_status`
- may depend on private customer account, billing, and admin operation services
