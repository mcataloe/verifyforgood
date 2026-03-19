# Charity Status API for Customers

## Overview

Charity Status API helps customers verify and monitor U.S. nonprofits using IRS Exempt Organizations data, Form 990 filing data, and selected enrichment sources.

Typical customer workflows include:

- verifying a nonprofit by EIN
- searching for nonprofits by name
- reviewing filing history
- inspecting source-level data
- checking compliance and federal-award views
- managing organization-level integration settings

## Customer Endpoints

Primary customer-facing endpoints:

- `GET /v1/nonprofit/{ein}`
- `GET /v1/nonprofit/{ein}/filings`
- `GET /v1/nonprofits/search`
- `GET /v1/nonprofits/{ein}/sources`
- `GET /v1/nonprofits/{ein}/sources/{source_name}`
- `GET /v1/nonprofits/{ein}/compliance`
- `GET /v1/nonprofits/{ein}/federal-awards`
- `POST /v1/verify`
- `POST /v1/verify/batch`
- `GET /v1/organization/settings`
- `PUT /v1/organization/settings`

Admin account-management routes under `/v1/admin/...` are not part of the standard customer surface.

## Authentication

Customer access is currently modeled through:

- API keys
- OAuth client credentials

Customers can also manage account-level overage behavior through `GET/PUT /v1/organization/settings`. The `billing.allowOverage` setting is available on all plans.

## Subscription Plans

The platform currently models these plan codes:

- `free`
- `starter`
- `growth`
- `pro`
- `enterprise`

Internal aliases currently resolve as:

- `developer` -> `free`
- `team` -> `growth`
- `business` -> `pro`

## Plan Benefits

### Free

- Monthly requests: `250`
- Batch verification: not included
- Rate limit: `10` requests per minute
- Customer-visible capabilities:
  - nonprofit verification

### Starter

- Monthly requests: `1,000`
- Batch verification: not included
- Rate limit: `30` requests per minute
- Customer-visible capabilities:
  - nonprofit verification
  - risk flags

### Growth

- Monthly requests: `10,000`
- Batch verification: up to `100` batch items
- Rate limit: `120` requests per minute
- Customer-visible capabilities:
  - nonprofit verification
  - risk flags
  - financial trends
  - benchmarking
  - batch verification

### Pro

- Monthly requests: `100,000`
- Batch verification: up to `1,000` batch items
- Rate limit: `600` requests per minute
- Customer-visible capabilities:
  - nonprofit verification
  - risk flags
  - financial trends
  - benchmarking
  - state registry access
  - monitoring
  - batch verification
  - organization settings

### Enterprise

- Monthly requests: `1,000,000`
- Batch verification: up to `5,000` batch items
- Rate limit: `5,000` requests per minute
- Customer-visible capabilities:
  - nonprofit verification
  - risk flags
  - financial trends
  - benchmarking
  - state registry access
  - monitoring
  - batch verification
  - organization settings

## Pricing Notes

This repository currently defines plan entitlements and overage-ready billing fields, but it does not define customer-facing monthly subscription prices.

The billing model currently includes:

- included monthly usage by plan
- feature access by plan
- request-rate limits
- overage unit pricing

Default overage behavior:

- pay-per-request overage is enabled by default for all plans
- customers can disable overage account-wide with `billing.allowOverage=false`
- when overage is disabled, requests that would exceed the included monthly limit return `429`

Current overage rates in the model:

- `free`: `$0.005` per overage unit
- `starter`: `$0.004` per overage unit
- `growth`: `$0.003` per overage unit
- `pro`: `$0.002` per overage unit
- `enterprise`: `$0.001` per overage unit

## Tenant Setup

Each managed customer account includes:

- account ID
- organization name
- tenant EIN
- subscription status
- plan code

When a tenant is created through the admin control plane, both organization name and EIN are required. EIN values may be submitted as `123456789` or `12-3456789` and are stored in normalized 9-digit form.

## Product Notes

- The API is currently focused on U.S. nonprofits.
- Deterministic verification and scoring are implemented today.
- Some premium integrations and billing/payment workflows are scaffolded and may still be rollout-dependent.
- Feature availability is enforced by plan entitlements in the platform layer.
