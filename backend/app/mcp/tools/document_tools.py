from typing import Dict, Any, List
from ..registry import mcp_registry
from ...auth import IdentityContext
from ...knowledge import knowledge_base

def handle_search_enterprise_documents(identity: IdentityContext, params: Dict[str, Any]) -> Dict[str, Any]:
    query = params.get("query", "").strip()
    top_k = int(params.get("top_k", 3))

    if not query:
        return {"status": "error", "message": "Search query cannot be empty."}

    chunks, citations = knowledge_base.retrieve(query, top_k=top_k, user_role=identity.role)

    results = []
    for c in chunks:
        results.append({
            "source": c.source,
            "section": c.section,
            "content": c.content,
            "provider": "Azure AI Search (Hybrid)" if knowledge_base.is_azure_search_ready else "Local Enterprise RAG Index"
        })

    return {
        "status": "success",
        "query": query,
        "results_count": len(results),
        "documents": results,
        "engine": "REAL AZURE SERVICE (AI Search)" if knowledge_base.is_azure_search_ready else "LOCAL BM25 / COSINE ENGINE"
    }

def handle_list_sharepoint_libraries(identity: IdentityContext, params: Dict[str, Any]) -> Dict[str, Any]:
    libraries = [
        {"name": "NovaTech Corporate Policies", "type": "SharePoint Online", "access": "Granted (All Staff)", "site": "https://novatech.sharepoint.com/sites/policies"},
        {"name": "Engineering Architecture & Tech Specs", "type": "SharePoint Online", "access": "Granted" if identity.department == "Engineering" or identity.role in ["Admin", "IT"] else "Restricted", "site": "https://novatech.sharepoint.com/sites/engineering"},
        {"name": "Executive & HR Confidential Records", "type": "OneDrive for Business", "access": "Granted" if identity.role in ["HR", "Admin"] else "Restricted", "site": "https://novatech.sharepoint.com/sites/hr-confidential"},
        {"name": "IT Infrastructure Runbooks & Zero-Trust", "type": "SharePoint Online", "access": "Granted" if identity.department in ["IT Operations", "Information Security"] or identity.role == "Admin" else "Restricted", "site": "https://novatech.sharepoint.com/sites/it-sec"}
    ]
    return {
        "status": "success",
        "employee": identity.name,
        "role": identity.role,
        "libraries": libraries
    }

def register():
    mcp_registry.register(
        name="search_enterprise_documents",
        description="Search enterprise policies, manuals, SOPs, and company documentation. Backed by Azure AI Search / RAG index. [Real Azure Service]",
        category="Documents",
        required_permission="documents.read",
        parameters_schema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query or policy topic to retrieve"}
            },
            "required": ["query"]
        },
        handler=handle_search_enterprise_documents
    )

    mcp_registry.register(
        name="list_sharepoint_libraries",
        description="List enterprise SharePoint and OneDrive libraries accessible to the employee. [Mock Service]",
        category="Documents",
        required_permission="documents.read",
        parameters_schema={"type": "object", "properties": {}},
        handler=handle_list_sharepoint_libraries
    )
