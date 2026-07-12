---
title: User Provisioning Policy
author: Daniel Kim
department: Infrastructure
version: v1.5
last_reviewed: 2025-01-18
status: retired
---

# User Provisioning Policy

**Version:** v1.5  
**Owner:** Daniel Kim (Infrastructure)  
**Last Reviewed:** 2025-01-18  
**Status:** Retired

## 1. Purpose

This document establishes the user provisioning policy for the organization. It is maintained by the Infrastructure department and applies to all personnel and systems in scope below.

## 2. Scope

This policy applies to the following groups: admins, all users, contractors, developers, employees.

## 3. Obligations

### 3.1 Api

API obligations govern how internal and external interfaces must be secured.

- **[Recommended]** All Users recommended api.

### 3.2 Provisioning

Provisioning obligations define how user accounts are created and deprovisioned.

- **[Recommended]** All Users recommended provisioning. (Reference: DES)
- **[Mandatory]** All Users required provisioning.
- **[Prohibited]** Admins prohibited provisioning.

### 3.3 Physical

Physical security obligations cover access to offices, data centers, and equipment.

- **[Mandatory]** Admins shall physical.

### 3.4 Cloud

Cloud obligations apply to infrastructure and services hosted with cloud providers.

- **[Mandatory]** Employees shall cloud.

### 3.5 Privacy

Privacy obligations govern the collection, use, and disclosure of personal data.

- **[Mandatory]** Employees required privacy. (Reference: DES)

### 3.6 Encryption

Encryption obligations specify how data must be protected at rest and in transit.

- **[Mandatory]** Developers shall encryption.

### 3.7 Mobile

Mobile device obligations apply to any device used to access company resources.

- **[Mandatory]** Employees required mobile. (Reference: SHA-1)

### 3.8 Monitoring

Monitoring obligations define what systems must be observed and alerted on.

- **[Mandatory]** All Users must monitoring.

### 3.9 Access

Access control obligations define who may reach which systems and data.

- **[Mandatory]** Contractors shall access.

### 3.10 Change

Change management obligations govern how modifications to production systems are approved.

- **[Mandatory]** Employees shall change. (Reference: FTP)

## 5. Review History

| Version | Reviewed | Reviewer | Notes |
|---|---|---|---|
| v1.5 | 2025-01-18 | Daniel Kim | Overdue for review; scheduled review cycle exceeded. |
