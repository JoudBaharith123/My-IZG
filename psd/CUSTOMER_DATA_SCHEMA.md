# Customer Data Schema

## Overview

Primary customer master used by Intelligent Zone Generator for zoning, routing, and reporting.

## File Details

- **Source file**: `Easyterrritory_26831_29_oct_2025.CSV`
- **CSV dialect**: Comma-separated, double-quoted values, UTF-8
- **Primary key**: `CusId`
- **Required minimum fields**: `CusId`, `Latitude`, `Longitude`, `Status`

## Column Definitions

| Column | Type | Required | Description |
| --- | --- | --- | --- |
| Area | string | optional | Commercial or sales territory grouping (e.g., Riyadh, Jeddah). |
| Region | string | optional | Higher-level geographic region that contains the area. |
| City | string | optional | Customer municipality/locality name. |
| Zone | string | optional | Operational zone identifier used for routing/assignment. |
| AgentId | string | optional | Internal code for the field agent or salesperson. |
| AgentName | string | optional | Human-readable name for the assigned agent. |
| CusId | string | required | Unique customer identifier in the source system. |
| CusName | string | required | Customer or outlet name displayed to agents. |
| BuyerPhone | string | optional | Primary purchasing contact phone number. |
| ReceiverPhone | string | optional | Delivery recipient phone number. |
| FinancePhone | string | optional | Finance/accounts contact phone number. |
| CH | string | optional | Top-level sales channel classification (e.g., Traditional Trade). |
| SubChannel | string | optional | Finer-grained channel segment (e.g., Small Grocery). |
| F | string | optional | Flag or attribute column; usage defined by business operations. |
| StartWeeks | integer | optional | Starting service week flag (allowed values: 1 or 2). |
| Days | string | optional | Service-day pattern or visit-day count indicator. |
| Latitude | decimal | required | Customer latitude in decimal degrees. |
| Longitude | decimal | required | Customer longitude in decimal degrees. |
| VAT | string | optional | Customer VAT registration number. |
| CR | string | optional | Commercial registration/licence identifier. |
| BL | string | optional | Business licence or municipality permit number. |
| createdDate | date | optional | Date the customer record was created (ISO 8601). |
| TotalDeliveredOrders | integer | optional | Historical count of fulfilled orders. |
| PaymentType | string | optional | Payment terms category (e.g., cash, credit). |
| CreditDays | integer | optional | Allowed credit period in days. |
| CreditLimit | decimal | optional | Monetary credit limit (typically SAR). |
| Status | string | required | Current customer lifecycle status (e.g., ACTIVE). |
| Validation | string | optional | Finance/operations validation status (e.g., Approved by Finance). |
| CreationType | string | optional | How the record was created (e.g., Agent Registration). |
| CheckIn | string | optional | Check-in requirement flag or workflow indicator. |
| CRExpiryDate | date | optional | Expiry date for the commercial registration licence. |
| BLExpiryDate | date | optional | Expiry date for the business licence. |
| StreetName | string | optional | Street component of the address. |
| DistrictName | string | optional | District or neighbourhood name. |
| AdditionalNum | string | optional | Supplemental address number (Saudi national address). |
| ZipCode | string | optional | Postal code. |
| BuildingNumber | string | optional | Building identifier in the national address. |
| DC | string | optional | Distribution center or depot servicing the customer. |
| AssignmentType | string | optional | How the customer was assigned (manual, automated, etc.). |
| Geocode Quality | string | optional | Confidence measure of the geocoded coordinates. |
| Full Corrected Address | string | optional | Normalized full address used after validation. |

## Data Quality Notes

- Coordinates must fall within Saudi Arabia bounds (16–32°N latitude, 34–56°E longitude).
- Phone numbers should be stored as strings to preserve leading zeros and formatting.
- Monetary fields (`CreditLimit`) should use consistent currency units and decimal precision.
- Date fields follow ISO 8601 (`YYYY-MM-DD`); verify timezone/offset requirements if present.
- Validate that `CusId` is unique and non-null before import.

