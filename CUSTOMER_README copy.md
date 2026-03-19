# Charity Status API — Customer Guide & Pricing

## Overview

Charity Status API gives you a single, reliable way to **verify, analyze, and monitor U.S. nonprofit organizations**—without stitching together IRS data, filings, and external sources yourself.

Built for modern platforms, compliance teams, and data-driven organizations, the API delivers **fast, deterministic, and explainable results** you can trust in production.

---

## Why Customers Choose Charity Status API

- **Instant Verification** — Validate nonprofit status in milliseconds  
- **Compliance Confidence** — Detect revocations, inconsistencies, and risks  
- **Financial Insight** — Leverage Form 990 data without parsing XML yourself  
- **Scalable by Design** — From startups to enterprise pipelines  
- **Transparent Results** — No black-box scoring  

---

## Core Use Cases

- Donor platforms validating charities at checkout  
- Grant systems performing due diligence  
- Vendor onboarding pipelines screening nonprofits  
- Internal compliance and audit workflows  
- Data teams building nonprofit intelligence datasets  

---

## Getting Started

1. Receive your API credentials (API Key or OAuth)
2. Call:

```
POST /v1/verify
```

3. Get structured results including:
- IRS status
- organization metadata
- risk flags
- verification outcome

---

## API Endpoints

```
GET    /v1/nonprofit/{ein}
GET    /v1/nonprofit/{ein}/filings
GET    /v1/nonprofits/search
GET    /v1/nonprofits/{ein}/sources
GET    /v1/nonprofits/{ein}/compliance
GET    /v1/nonprofits/{ein}/federal-awards

POST   /v1/verify
POST   /v1/verify/batch
```

---

## Pricing & Plans

Simple, scalable pricing designed to grow with you.

### Free — $0/month
Best for evaluation and small projects

- 250 requests/month  
- 10 requests/minute  
- Basic nonprofit verification  

---

### Starter — $29/month
For small teams and early-stage products

- 1,000 requests/month  
- 30 requests/minute  
- Verification + risk flags  

---

### Growth — $99/month
For scaling platforms and automation workflows

- 10,000 requests/month  
- 120 requests/minute  
- Batch verification (up to 100)  
- Financial trends + benchmarking  

---

### Pro — $299/month
For production-grade systems

- 100,000 requests/month  
- 600 requests/minute  
- Batch verification (up to 1,000)  
- Monitoring capabilities  
- State registry access (as available)  

---

### Enterprise — Custom Pricing
For high-volume and mission-critical systems

- 1,000,000+ requests/month  
- 5,000 requests/minute  
- Advanced monitoring  
- Priority support  
- Custom integrations  

Contact us for tailored pricing.

---

## Overage Pricing

If you exceed your plan:

- Free: $0.005/request  
- Starter: $0.004/request  
- Growth: $0.003/request  
- Pro: $0.002/request  
- Enterprise: custom  

---

## Feature Highlights

### Verification
Fast EIN-based validation with deterministic results.

### Financial Insights
Form 990 analysis without the heavy lifting.

### Risk Flags
Surface potential issues instantly.

### Batch Processing
Validate thousands of nonprofits efficiently.

### Monitoring (Pro+)
Track changes over time and stay compliant.

---

## Data Sources

- IRS Exempt Organizations  
- IRS Form 990 filings  
- Federal award datasets  
- State registries (rolling rollout)  
- Optional third-party providers  

---

## Integration Model

- API-first (no dashboard required)
- Secure credential provisioning
- Designed for backend and pipeline integration

---

## Built for Developers

- Clean REST API  
- Consistent schemas  
- Predictable responses  
- Easy to integrate  

---

## What’s Coming Next

- Self-service dashboard  
- Webhooks & event-driven monitoring  
- Full 50-state registry coverage  
- Third-party data marketplace  

---

## Ready to Get Started?

Start verifying nonprofits in minutes.

Contact us to:
- receive API access
- choose a plan
- integrate into your system

---

**Charity Status API — Trust your data. Verify with confidence.**
