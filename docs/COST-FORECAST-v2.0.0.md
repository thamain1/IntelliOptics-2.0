# IntelliOptics 2.0 - Cost Forecast Analysis

**Date:** January 20, 2026
**Version:** v2.0.0
**Purpose:** Multi-tenant cost projection for 10, 20, 50, and 100 customer sites

---

## Executive Summary

This document provides cost forecasting for IntelliOptics 2.0 deployment at scale, analyzing shared vs. per-customer resources to optimize cost efficiency.

---

## 1. Resource Classification

### Shared Resources (Fixed Cost)
These resources are shared across all customers and do not scale linearly:

| Resource | Base Cost | Notes |
|----------|-----------|-------|
| Azure Container Registry | $20/month | Single registry for all images |
| Azure Service Bus (Namespace) | $10/month | Shared queues, scales with throughput |
| Application Insights | $10/month | Centralized monitoring |
| **Total Fixed** | **$40/month** | |

### Shared with Scaling (Step Function)
These resources are shared but require upgrades at certain thresholds:

| Resource | Tier | Cost | Capacity |
|----------|------|------|----------|
| PostgreSQL Flexible | B1ms (1 vCore) | $25/month | ~10 sites |
| PostgreSQL Flexible | B2s (2 vCore) | $50/month | ~25 sites |
| PostgreSQL Flexible | D2s_v3 (2 vCore) | $100/month | ~50 sites |
| PostgreSQL Flexible | D4s_v3 (4 vCore) | $200/month | ~100 sites |

### Per-Customer Resources (Linear Scaling)
These resources scale with customer count:

| Resource | Cost per Customer | Notes |
|----------|-------------------|-------|
| Blob Storage | $2-5/month | ~20GB images per site |
| Service Bus Throughput | $1-2/month | Message volume per site |
| SendGrid (if enabled) | $0.50/month | Email volume per site |
| **Total Variable** | **$3.50-7.50/month** | Per customer site |

---

## 2. Cost Forecast by Scale

### 10 Customer Sites

| Category | Resource | Monthly Cost |
|----------|----------|--------------|
| **Fixed** | Container Registry | $20 |
| | Service Bus Namespace | $10 |
| | Application Insights | $10 |
| **Shared DB** | PostgreSQL B1ms | $25 |
| **Per-Customer** | Blob Storage (10 × $3) | $30 |
| | Service Bus Throughput (10 × $1) | $10 |
| **TOTAL** | | **$105/month** |

| Metric | Value |
|--------|-------|
| Total Monthly Cost | $105 |
| Cost per Customer | **$10.50/month** |
| Annual Cost | $1,260 |

---

### 20 Customer Sites

| Category | Resource | Monthly Cost |
|----------|----------|--------------|
| **Fixed** | Container Registry | $20 |
| | Service Bus Namespace | $10 |
| | Application Insights | $10 |
| **Shared DB** | PostgreSQL B2s (scaled up) | $50 |
| **Per-Customer** | Blob Storage (20 × $3) | $60 |
| | Service Bus Throughput (20 × $1) | $20 |
| **TOTAL** | | **$170/month** |

| Metric | Value |
|--------|-------|
| Total Monthly Cost | $170 |
| Cost per Customer | **$8.50/month** |
| Annual Cost | $2,040 |
| Savings vs 10 sites (per customer) | 19% |

---

### 50 Customer Sites

| Category | Resource | Monthly Cost |
|----------|----------|--------------|
| **Fixed** | Container Registry | $20 |
| | Service Bus Standard | $15 |
| | Application Insights | $15 |
| **Shared DB** | PostgreSQL D2s_v3 | $100 |
| **Per-Customer** | Blob Storage (50 × $3) | $150 |
| | Service Bus Throughput (50 × $1) | $50 |
| **TOTAL** | | **$350/month** |

| Metric | Value |
|--------|-------|
| Total Monthly Cost | $350 |
| Cost per Customer | **$7.00/month** |
| Annual Cost | $4,200 |
| Savings vs 10 sites (per customer) | 33% |

---

### 100 Customer Sites

| Category | Resource | Monthly Cost |
|----------|----------|--------------|
| **Fixed** | Container Registry | $20 |
| | Service Bus Standard | $20 |
| | Application Insights | $25 |
| **Shared DB** | PostgreSQL D4s_v3 | $200 |
| **Per-Customer** | Blob Storage (100 × $3) | $300 |
| | Service Bus Throughput (100 × $1) | $100 |
| | Bandwidth/Egress | $50 |
| **TOTAL** | | **$715/month** |

| Metric | Value |
|--------|-------|
| Total Monthly Cost | $715 |
| Cost per Customer | **$7.15/month** |
| Annual Cost | $8,580 |
| Savings vs 10 sites (per customer) | 32% |

---

## 3. Comparative Summary

| Sites | Monthly Total | Per Customer | Annual Total | Efficiency Gain |
|-------|---------------|--------------|--------------|-----------------|
| 10 | $105 | $10.50 | $1,260 | Baseline |
| 20 | $170 | $8.50 | $2,040 | 19% savings |
| 50 | $350 | $7.00 | $4,200 | 33% savings |
| 100 | $715 | $7.15 | $8,580 | 32% savings |

### Cost Per Customer Trend

```
Per-Customer Cost by Scale
$12 ┤
$11 ┤
$10 ┤ ●──────────── 10 sites ($10.50)
$9  ┤      ╲
$8  ┤       ●────── 20 sites ($8.50)
$7  ┤         ╲
$6  ┤          ●─●─ 50-100 sites ($7.00-$7.15)
$5  ┤
    └────────────────────────────────
        10    20    50    100  Sites
```

**Key Insight:** Optimal efficiency is reached around 50 sites. Beyond that, per-customer costs stabilize as database and infrastructure scaling offset economies of scale.

---

## 4. Edge Deployment Considerations

If customers deploy edge infrastructure (on-premise inference), additional costs apply:

### Edge Hardware (One-Time per Site)
| Component | Cost |
|-----------|------|
| Edge Server (NVIDIA GPU) | $3,000-8,000 |
| Network Infrastructure | $500-1,000 |
| Installation | $500-1,000 |
| **Total One-Time** | **$4,000-10,000** |

### Edge Operating Costs (Monthly per Site)
| Component | Cost |
|-----------|------|
| Electricity (~200W × 24/7) | $15-30 |
| Internet Connectivity | $50-100 |
| Maintenance Reserve | $50 |
| **Total Monthly** | **$115-180** |

### Hybrid Model Cost (Cloud + Edge)

| Sites | Cloud Cost | Edge Cost (monthly) | Total Monthly |
|-------|------------|---------------------|---------------|
| 10 | $105 | $1,500 | $1,605 |
| 20 | $170 | $3,000 | $3,170 |
| 50 | $350 | $7,500 | $7,850 |
| 100 | $715 | $15,000 | $15,715 |

---

## 5. Usage-Based Projections

### Storage Growth Model
Assuming each site generates:
- 100 detection queries/day
- Average image size: 500KB
- Retention: 90 days

| Sites | Daily Images | Storage (90 days) | Monthly Cost |
|-------|--------------|-------------------|--------------|
| 10 | 1,000 | 45 GB | $2.25 |
| 20 | 2,000 | 90 GB | $4.50 |
| 50 | 5,000 | 225 GB | $11.25 |
| 100 | 10,000 | 450 GB | $22.50 |

### High-Volume Scenario (500 queries/day per site)

| Sites | Daily Images | Storage (90 days) | Monthly Cost |
|-------|--------------|-------------------|--------------|
| 10 | 5,000 | 225 GB | $11.25 |
| 20 | 10,000 | 450 GB | $22.50 |
| 50 | 25,000 | 1.1 TB | $56.25 |
| 100 | 50,000 | 2.25 TB | $112.50 |

---

## 6. Break-Even Analysis

### Minimum Viable Pricing

To achieve break-even with 20% margin:

| Sites | Monthly Cost | Per Customer | Min Price (20% margin) |
|-------|--------------|--------------|------------------------|
| 10 | $105 | $10.50 | $13.00/month |
| 20 | $170 | $8.50 | $11.00/month |
| 50 | $350 | $7.00 | $9.00/month |
| 100 | $715 | $7.15 | $9.00/month |

### Recommended Pricing Tiers

| Tier | Features | Suggested Price | Margin at 50 sites |
|------|----------|-----------------|-------------------|
| Basic | Cloud only, 100 queries/day | $15/month | 53% |
| Professional | Cloud + email alerts | $25/month | 72% |
| Enterprise | Cloud + edge + SMS | $50/month | 86% |

---

## 7. Scaling Recommendations

### 1-10 Sites (Startup Phase)
- Use PostgreSQL B1ms ($25/month)
- Standard tier for all services
- Single region deployment
- **Target: <$15/customer**

### 11-25 Sites (Growth Phase)
- Upgrade to PostgreSQL B2s ($50/month)
- Consider reserved instances (1-year: 30% savings)
- Implement monitoring alerts
- **Target: <$10/customer**

### 26-50 Sites (Scale Phase)
- Upgrade to PostgreSQL D2s_v3 ($100/month)
- Add read replica for reporting
- Multi-region consideration
- **Target: <$8/customer**

### 51-100+ Sites (Enterprise Phase)
- Upgrade to PostgreSQL D4s_v3 ($200/month)
- Implement caching layer (Redis)
- Consider dedicated Service Bus
- **Target: <$8/customer**

---

## 8. Cost Optimization Strategies

### Immediate Savings
| Strategy | Potential Savings |
|----------|-------------------|
| Reserved Instances (1-year) | 30-40% on compute |
| Reserved Instances (3-year) | 50-60% on compute |
| Blob Storage Tiering | 20-40% on storage |
| Dev/Test Pricing | 50% on non-prod |

### Architectural Optimizations
| Strategy | Impact |
|----------|--------|
| Image compression | 30-50% storage reduction |
| Intelligent tiering | Auto-archive old data |
| CDN for static assets | Reduced egress costs |
| Connection pooling | Smaller DB tier viable |

### Projected Savings with Optimizations

| Sites | Base Cost | With Optimizations | Savings |
|-------|-----------|-------------------|---------|
| 10 | $105 | $85 | $20 (19%) |
| 20 | $170 | $130 | $40 (24%) |
| 50 | $350 | $260 | $90 (26%) |
| 100 | $715 | $520 | $195 (27%) |

---

## 9. Summary

### Key Findings

1. **Economy of Scale**: Per-customer costs drop significantly from 10 to 50 sites (33% reduction)

2. **Sweet Spot**: 50 sites offers optimal efficiency at ~$7.00/customer/month

3. **Shared Resources**: Database and infrastructure sharing provides major cost benefits

4. **Edge Costs**: On-premise deployment adds $115-180/month per site in operating costs

5. **Pricing Recommendation**: $15-25/month per customer provides healthy margins at all scales

### Final Cost Matrix

| Scale | Cloud Only | With Edge | Per Customer (Cloud) |
|-------|------------|-----------|---------------------|
| 10 sites | $105/mo | $1,605/mo | $10.50 |
| 20 sites | $170/mo | $3,170/mo | $8.50 |
| 50 sites | $350/mo | $7,850/mo | $7.00 |
| 100 sites | $715/mo | $15,715/mo | $7.15 |

---

## Appendix: Assumptions

- Azure pricing as of January 2026 (East US region)
- Standard tier services unless otherwise noted
- 100 queries/day baseline per site
- 90-day image retention
- No reserved instance discounts applied to base calculations
- Edge operating costs based on US averages

---

## Contact

For detailed cost analysis or custom scenarios, contact the DevOps team.
