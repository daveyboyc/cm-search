# UK Capacity Market GPT API Deployment Guide

This guide outlines the steps to deploy the GPT API integration that connects OpenAI's GPT to the UK Capacity Market search application.

## Overview

The integration consists of:

1. A Django API endpoint that accepts natural language queries from GPT
2. Query processing logic to extract search parameters
3. Connection to the existing search functionality
4. Response formatting for GPT consumption
5. API key authentication for security

## Deployment Steps

### 1. Update Database Configuration

Ensure the `settings.py` has the correct Supabase database connection:

```python
# Database connection
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'postgres',
        'USER': 'postgres',
        'PASSWORD': os.environ.get('DATABASE_PASSWORD', ''),
        'HOST': os.environ.get('DATABASE_HOST', 'aws-0-eu-west-2.pooler.supabase.com'),
        'PORT': os.environ.get('DATABASE_PORT', '5432'),
    }
}
```

### 2. Set Environment Variables

Set the following environment variables in your Heroku app:

```
API_KEY=your_custom_api_key_for_auth
OPENAI_API_KEY=your_openai_api_key
```

You can set these in Heroku with:

```bash
heroku config:set API_KEY=your_custom_api_key_for_auth -a neso-cmr-search
heroku config:set OPENAI_API_KEY=your_openai_api_key -a neso-cmr-search
```

### 3. Deploy to Heroku

Ensure you're on the main branch and deploy to Heroku:

```bash
git push heroku main
```

Or if deploying from a different branch:

```bash
git push heroku your-branch:main
```

### 4. Verify the API Endpoint

Test the API using the provided test script:

```bash
python test_gpt_api.py
```

Or using curl:

```bash
curl -X POST \
  https://neso-cmr-search-da0169863eae.herokuapp.com/api/gpt-search/ \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: your_custom_api_key_for_auth' \
  -d '{"query": "Find nuclear power stations in the UK"}'
```

### 5. Creating a Custom GPT

1. Go to OpenAI's GPT Builder: https://chat.openai.com/gpts/builder
2. Create a new GPT named "UK Capacity Market Search"
3. In the "Instructions" section, paste the contents of `gpt_instructions.md`
4. In the "Actions" section, add a new action:
   - Set Authentication to "API Key" in "Header"
   - Header name: "X-API-Key"
   - Value: Your API key
   - Set OpenAPI Schema by uploading `gpt_openapi_schema.json`
5. Test the GPT with sample queries

## Troubleshooting

### Template Rendering Issues

If you encounter a `KeyError: 'dict'` in `component_detail.html`, check:

1. Make sure the API endpoint returns raw data and doesn't attempt to render templates
2. Verify the `return_data_only=True` parameter works correctly in `search_components_service`

### HTTP 500 Errors

If the API returns 500 errors:

1. Check Heroku logs: `heroku logs --tail -a neso-cmr-search`
2. Ensure database credentials are correct
3. Verify API key authentication is working

### Empty Results

If the API returns no results:

1. Try simplifying your query
2. Check if the search parameters are being extracted correctly
3. Verify the search service is connecting to the database

## Maintenance

### Updating the API

1. Make changes to the relevant files:
   - `views.py` - API endpoint and query processing
   - `urls.py` - URL routing
   - `component_search.py` - Search functionality

2. Test locally before deploying:
   ```bash
   python manage.py runserver
   ```

3. Deploy changes to Heroku:
   ```bash
   git push heroku main
   ```

### Updating the OpenAPI Schema

If you change the API's request or response format, update:
1. `gpt_openapi_schema.json`
2. Reupload to your custom GPT in the Actions section 