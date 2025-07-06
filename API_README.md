# UK Capacity Market GPT Search API

## Public API Access for AI Systems

The UK Capacity Market database provides a public API endpoint for AI systems like ChatGPT to access capacity market data.

### Endpoint

```
POST https://capacitymarket.co.uk/api/gpt-search/
```

### Authentication

Use the public read-only API key in the `X-API-Key` header:

```
X-API-Key: cmr_public_readonly_ai_access_2024
```

### Request Format

```bash
curl -X POST https://capacitymarket.co.uk/api/gpt-search/ \
  -H "Content-Type: application/json" \
  -H "X-API-Key: cmr_public_readonly_ai_access_2024" \
  -d '{"query": "gas plants in London"}'
```

### Request Body

```json
{
  "query": "Natural language search query"
}
```

### Response Format

```json
{
  "query": "gas plants in London",
  "results_count": 15,
  "summary": "Found 15 gas plants in London area",
  "components": [
    {
      "cmu_id": "EXAMPLE123",
      "company_name": "Example Energy Ltd",
      "location": "London, E1 6AN",
      "description": "Gas fired power station",
      "technology": "CCGT",
      "derated_capacity_mw": 500.0,
      "delivery_year": "2025",
      "auction_name": "T-4 2021",
      "market_status": "Active"
    }
  ],
  "error": null
}
```

### Example Queries

- `"Show me all battery storage projects"`
- `"What nuclear plants are in the capacity market?"`
- `"Find DSR projects by EDF"`
- `"Gas plants over 100MW capacity"`
- `"Solar projects in Scotland"`

### Rate Limits

- Public API key is rate-limited for fair usage
- Designed for AI assistant queries, not bulk data extraction
- For higher volume access, contact the site administrators

### Error Responses

**401 Unauthorized**
```json
{
  "error": "Invalid API key. Use X-API-Key header with: cmr_public_readonly_ai_access_2024"
}
```

**400 Bad Request**
```json
{
  "error": "Query parameter is required"
}
```

### OpenAPI Documentation

Full API specification available at:
https://capacitymarket.co.uk/.well-known/openapi.json

### Support

For API support or higher access levels, contact: info@capacitymarket.co.uk

---

*This API provides access to UK government capacity market data licensed under Creative Commons Attribution 4.0 International License and Open Government Licence v3.0*