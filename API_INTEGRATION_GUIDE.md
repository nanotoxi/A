# SaneForce AI Sales Assistant — API Integration Guide

**Base URL:** `https://a-production-19cf.up.railway.app`  
**Interactive Docs:** `https://a-production-19cf.up.railway.app/docs`  
**Version:** 1.0.0

---

## Overview

The SaneForce AI API gives your software access to an AI-powered sales intelligence layer. Send a natural language question from a sales rep, get a plain English answer backed by live data. No dashboards, no reports — just answers.

You can integrate this into any platform: mobile apps, web apps, WhatsApp bots, CRMs, or internal tools.

---

## Quick Start (Under 2 Minutes)

Try this in your terminal right now:

```bash
curl -X POST https://a-production-19cf.up.railway.app/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "Which stores should I visit tomorrow?", "rep_id": 2}'
```

You should get back a natural language answer in under 3 seconds.

---

## Authentication

This is a POC build. Authentication is handled by passing `rep_id` in every request. The API scopes all data to that rep automatically — a sales rep cannot see another rep's data.

> **Production note:** JWT-based authentication will replace `rep_id` in the production build. Your integration code should be written to accept a token header swap later.

---

## Rep IDs for Testing

| rep_id | Name | Role | Territory |
|--------|------|------|-----------|
| 1 | Arjun Mehta | Manager | Mumbai (sees all reps) |
| 2 | Ravi Sharma | Sales Rep | Mumbai North |
| 3 | Priya Nair | Sales Rep | Mumbai South |
| 4 | Suresh Patil | Sales Rep | Pune |
| 5 | Kavita Joshi | Sales Rep | Ahmedabad |

---

## Rate Limits

| Endpoint | Limit |
|----------|-------|
| `POST /chat` | 10 requests / minute per IP |
| `GET /recommendations` | 20 requests / minute per IP |
| All other endpoints | 30 requests / minute per IP |

When exceeded, the API returns `429 Too Many Requests`. Build a retry with exponential backoff or show a "please wait" message to the user.

---

## Endpoints

---

### 1. POST /chat

The main AI endpoint. Send any sales question in natural language, get a plain English answer.

**Request**

```
POST /chat
Content-Type: application/json
```

```json
{
  "question": "Which of my stores are underperforming this week?",
  "rep_id": 2
}
```

| Field | Type | Required | Rules |
|-------|------|----------|-------|
| `question` | string | Yes | 3–500 characters |
| `rep_id` | integer | Yes | Must be ≥ 1 |

**Response**

```json
{
  "answer": "Your three lowest performing stores this week are Lucky General Store (Borivali), Patel Brothers (Dahisar), and Sharma Kirana (Bandra). Lucky General Store hasn't been visited in 14 days — I'd recommend making that your first stop.",
  "query_executed": "SELECT store_id, store_name ... (internal SQL)",
  "data_freshness": "live",
  "rep_context": {
    "rep_id": 2,
    "name": "Ravi Sharma",
    "territory": "Mumbai North"
  }
}
```

**Sample questions you can send:**

```
"Which stores should I visit tomorrow?"
"What products are not selling at Store 7?"
"Which stores haven't I visited in over 7 days?"
"Give me a pre-visit briefing for Store 12"
"Which store had the biggest sales drop this month?"
"What should I push at Store 5 this week?"
"Which sales approach has the highest success rate in my territory?"
"What approach has worked best for selling SKU-204?"
"How can I refine my approach for low-tier stores?"
"What do top performing reps do differently?"
"Compare my performance vs last month"
```

---

### 2. GET /stores/low-performing

Returns the bottom 5 stores by revenue for a rep's territory this month. Pure database query — fast, no AI involved.

**Request**

```
GET /stores/low-performing?rep_id=2
```

**Response**

```json
{
  "stores": [
    {
      "store_id": 1,
      "store_name": "Sharma Kirana",
      "location": "Bandra",
      "revenue_this_month": 1200.0,
      "last_visit_date": "2026-05-25",
      "days_since_visit": 9
    },
    {
      "store_id": 3,
      "store_name": "Lucky General Store",
      "location": "Borivali",
      "revenue_this_month": 340.0,
      "last_visit_date": "2026-05-20",
      "days_since_visit": 14
    }
  ]
}
```

**Use this for:** Dashboard widgets, rep home screens, "priority stores" lists.

---

### 3. GET /stores/{store_id}/products

Returns the full product sell-through breakdown for a specific store this month. Shows which products are moving and which are not.

**Request**

```
GET /stores/7/products?rep_id=2
```

**Response**

```json
{
  "store_id": 7,
  "store_name": "Goregaon General",
  "products": [
    {
      "product_name": "Biscuits 100g",
      "sku": "SKU-101",
      "units_sold_this_month": 24,
      "status": "selling_well"
    },
    {
      "product_name": "Shampoo 400ml",
      "sku": "SKU-204",
      "units_sold_this_month": 3,
      "status": "slow_moving"
    },
    {
      "product_name": "Mixed Fruit 500ml",
      "sku": "SKU-302",
      "units_sold_this_month": 0,
      "status": "not_selling"
    }
  ]
}
```

**Status values:**

| Status | Meaning |
|--------|---------|
| `selling_well` | 10+ units sold this month |
| `slow_moving` | 1–9 units sold this month |
| `not_selling` | 0 units sold this month |

**Use this for:** Pre-visit briefing screens, product performance panels.

---

### 4. GET /recommendations

Returns visit priority recommendations and product push suggestions for a rep, generated from live data patterns.

**Request**

```
GET /recommendations?rep_id=2
```

**Response**

```json
{
  "visit_recommendations": [
    {
      "store_id": 3,
      "store_name": "Lucky General Store",
      "reason": "not visited in 14 days, revenue down 40% vs last week",
      "priority": "high"
    },
    {
      "store_id": 6,
      "store_name": "Patel Brothers",
      "reason": "not visited in 11 days",
      "priority": "high"
    }
  ],
  "product_push_recommendations": [
    {
      "store_id": 2,
      "product_name": "Mixed Fruit 500ml",
      "reason": "Top seller at other stores but zero movement at City Mart this month"
    }
  ]
}
```

**Priority values:** `high`, `medium`

**Use this for:** Daily planning screens, push notifications, rep task lists.

---

### 5. GET /alerts

Returns proactive alerts for a rep — stores not visited, revenue drops, stalled products. Call this on login or on a schedule to surface issues without the rep having to ask.

**Request**

```
GET /alerts?rep_id=2
```

**Response**

```json
{
  "alerts": [
    {
      "type": "store_not_visited",
      "message": "Lucky General Store (Borivali) has not been visited in 14 days",
      "severity": "high"
    },
    {
      "type": "sales_drop",
      "message": "City Mart revenue dropped 51% vs last week",
      "severity": "high"
    }
  ]
}
```

**Alert types:**

| type | Meaning |
|------|---------|
| `store_not_visited` | Store hasn't been visited beyond threshold |
| `sales_drop` | Revenue dropped 20%+ week-on-week |

**Severity values:** `high`, `medium`

**Use this for:** Notification banners, alert badges, WhatsApp message triggers.

---

### 6. GET /health

Use this to check if the API is up before making other calls.

**Request**

```
GET /health
```

**Response**

```json
{
  "status": "ok",
  "version": "1.0.0",
  "db": "connected"
}
```

---

## Error Reference

| HTTP Code | Meaning | What to do |
|-----------|---------|------------|
| `200` | Success | Read the response |
| `404` | Rep or store not found | Check the `rep_id` or `store_id` value |
| `422` | Validation error | Check request body — question too short/long, or invalid rep_id |
| `429` | Rate limit exceeded | Wait and retry. Implement exponential backoff |
| `500` | Server error | Retry once. If persistent, contact support |

**Example 422 response:**
```json
{
  "detail": [
    {
      "type": "string_too_short",
      "loc": ["body", "question"],
      "msg": "String should have at least 3 characters"
    }
  ]
}
```

---

## Code Examples

### JavaScript / Fetch (Web or React Native)

```javascript
// Ask the AI a question
async function askSalesAI(question, repId) {
  const response = await fetch('https://a-production-19cf.up.railway.app/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question, rep_id: repId })
  });

  if (!response.ok) {
    if (response.status === 429) throw new Error('Too many requests — please wait');
    throw new Error(`API error: ${response.status}`);
  }

  const data = await response.json();
  return data.answer;
}

// Get alerts on login
async function getAlerts(repId) {
  const response = await fetch(
    `https://a-production-19cf.up.railway.app/alerts?rep_id=${repId}`
  );
  const data = await response.json();
  return data.alerts;
}

// Usage
const answer = await askSalesAI("Which stores should I visit tomorrow?", 2);
console.log(answer);

const alerts = await getAlerts(2);
alerts.forEach(alert => console.log(`[${alert.severity.toUpperCase()}] ${alert.message}`));
```

---

### Python

```python
import requests

BASE_URL = "https://a-production-19cf.up.railway.app"

def ask_sales_ai(question: str, rep_id: int) -> str:
    response = requests.post(
        f"{BASE_URL}/chat",
        json={"question": question, "rep_id": rep_id},
        timeout=15
    )
    response.raise_for_status()
    return response.json()["answer"]

def get_alerts(rep_id: int) -> list:
    response = requests.get(f"{BASE_URL}/alerts", params={"rep_id": rep_id})
    response.raise_for_status()
    return response.json()["alerts"]

def get_low_performing_stores(rep_id: int) -> list:
    response = requests.get(
        f"{BASE_URL}/stores/low-performing",
        params={"rep_id": rep_id}
    )
    response.raise_for_status()
    return response.json()["stores"]

# Usage
answer = ask_sales_ai("What approach works best for SKU-204?", rep_id=2)
print(answer)

for alert in get_alerts(rep_id=2):
    print(f"[{alert['severity'].upper()}] {alert['message']}")
```

---

### Node.js (axios)

```javascript
const axios = require('axios');

const api = axios.create({
  baseURL: 'https://a-production-19cf.up.railway.app',
  timeout: 15000
});

// Ask the AI
const { data } = await api.post('/chat', {
  question: 'Which store had the biggest sales drop this month?',
  rep_id: 2
});
console.log(data.answer);

// Get recommendations
const recs = await api.get('/recommendations', { params: { rep_id: 2 } });
console.log(recs.data.visit_recommendations);
```

---

### Flutter / Dart

```dart
import 'dart:convert';
import 'package:http/http.dart' as http;

const baseUrl = 'https://a-production-19cf.up.railway.app';

Future<String> askSalesAI(String question, int repId) async {
  final response = await http.post(
    Uri.parse('$baseUrl/chat'),
    headers: {'Content-Type': 'application/json'},
    body: jsonEncode({'question': question, 'rep_id': repId}),
  );

  if (response.statusCode == 200) {
    return jsonDecode(response.body)['answer'];
  } else {
    throw Exception('API error: ${response.statusCode}');
  }
}

Future<List<dynamic>> getAlerts(int repId) async {
  final response = await http.get(
    Uri.parse('$baseUrl/alerts?rep_id=$repId'),
  );
  return jsonDecode(response.body)['alerts'];
}
```

---

---

## Integration Patterns

### Pattern 1 — Chat Screen

Call `POST /chat` when the rep submits a message. Display `answer` as the AI reply. Optionally show a typing indicator while waiting (responses typically take 1–3 seconds).

```
Rep types message → POST /chat → show answer in chat bubble
```

### Pattern 2 — Home Screen Dashboard

Call these three on login to populate the rep's home screen in parallel:

```
GET /alerts              → show alert banner with badge count
GET /recommendations     → show "Visit today" card list
GET /stores/low-performing → show bottom 5 stores widget
```

### Pattern 3 — Pre-Visit Briefing

Before a rep visits a store, auto-fetch context:

```
GET /stores/{store_id}/products  → show which products are moving
POST /chat with question:
  "Give me a pre-visit briefing for Store {store_id}"  → AI summary
```

### Pattern 4 — Push Notifications (Scheduled)

Run a nightly job that calls `/alerts` for each rep and sends a push notification or WhatsApp message if `severity = "high"` alerts exist.

```
Cron job (nightly) → GET /alerts for each rep → 
  if high severity → send push notification / WhatsApp
```

---

## Response Time Expectations

| Endpoint | Typical Response Time |
|----------|-----------------------|
| `GET /health` | < 100ms |
| `GET /stores/low-performing` | < 200ms |
| `GET /stores/{id}/products` | < 200ms |
| `GET /alerts` | < 300ms |
| `GET /recommendations` | < 300ms |
| `POST /chat` | 1–3 seconds (AI processing) |

For `/chat`, show a loading state in your UI. Do not set your HTTP timeout below 15 seconds.

---

## Security Notes for Integrators

- All responses include security headers (`X-Frame-Options`, `X-Content-Type-Options`, etc.) — no action needed on your side
- Never log or store the raw API responses if they contain personal store or rep data
- The `query_executed` field in `/chat` responses is for debugging — do not display it to end users
- In production, `rep_id` will be replaced by a JWT token — design your integration to pass a header rather than a body field for the identity

---

## Support

For integration questions or issues, contact the SaneForce technical team with:
1. The full request you sent (endpoint + body)
2. The full response received
3. The timestamp of the request
