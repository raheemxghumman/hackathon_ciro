def search_crisis_context(query: str) -> dict:
    query_lower = query.lower()
    
    context_db = {
        "flooding": {
            "historical_context": "Sector G-10 is prone to urban flooding during monsoon.",
            "infrastructure_status": "Drainage systems in Blue Area are currently under maintenance."
        },
        "accident": {
            "historical_context": "Kashmir Highway near G-10 has a high accident rate during rain.",
            "infrastructure_status": "Traffic cameras active. Emergency response time average is 8 mins."
        },
        "heatwave": {
            "historical_context": "Islamabad experiences severe heatwaves in June-July.",
            "infrastructure_status": "Hospitals equipped with heatstroke wards in F-8 and G-8."
        }
    }
    
    for key, data in context_db.items():
        if key in query_lower:
            return data
            
    return {
        "historical_context": "No specific historical data for this query.",
        "infrastructure_status": "Standard operational status."
    }
