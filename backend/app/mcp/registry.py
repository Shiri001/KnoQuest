import logging
from typing import Dict, Any, List, Optional, Callable
from pydantic import BaseModel
from ..auth import IdentityContext, check_permission

logger = logging.getLogger("knoquest.mcp")

class MCPToolDefinition:
    def __init__(
        self,
        name: str,
        description: str,
        category: str,
        required_permission: Optional[str],
        parameters_schema: Dict[str, Any],
        handler: Callable[[IdentityContext, Dict[str, Any]], Dict[str, Any]]
    ):
        self.name = name
        self.description = description
        self.category = category
        self.required_permission = required_permission
        self.parameters_schema = parameters_schema
        self.handler = handler

    def to_openai_tool_schema(self) -> Dict[str, Any]:
        """Converts into OpenAI / Azure Foundry tool declaration."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters_schema
            }
        }

class MCPRegistry:
    """
    Central registry for KnoQuest Enterprise MCP Connectors & Tools.
    Enforces authorization check before every tool execution.
    """
    def __init__(self):
        self._tools: Dict[str, MCPToolDefinition] = {}

    def register(
        self,
        name: str,
        description: str,
        category: str,
        required_permission: Optional[str],
        parameters_schema: Dict[str, Any],
        handler: Callable[[IdentityContext, Dict[str, Any]], Dict[str, Any]]
    ):
        tool = MCPToolDefinition(
            name=name,
            description=description,
            category=category,
            required_permission=required_permission,
            parameters_schema=parameters_schema,
            handler=handler
        )
        self._tools[name] = tool
        logger.debug(f"Registered MCP tool '{name}' (Category: {category}, Permission: {required_permission})")

    def get_tool(self, name: str) -> Optional[MCPToolDefinition]:
        return self._tools.get(name)

    def list_all_tools(self) -> List[MCPToolDefinition]:
        return list(self._tools.values())

    def get_available_openai_tools(self, identity: Optional[IdentityContext] = None) -> List[Dict[str, Any]]:
        """
        Returns tool definitions formatted for Foundry / OpenAI function calling.
        Can optionally filter or expose all to let the authorization layer intercept unauthorized attempts.
        """
        return [tool.to_openai_tool_schema() for tool in self._tools.values()]

    def execute_tool(self, tool_name: str, params: Dict[str, Any], identity: IdentityContext) -> Dict[str, Any]:
        """
        Server-side authorization and dispatch gate.
        The LLM can NEVER bypass this check.
        """
        tool = self._tools.get(tool_name)
        if not tool:
            return {
                "status": "error",
                "error": f"Tool '{tool_name}' is not recognized in the enterprise registry."
            }

        # 1. Server-side permission check
        if tool.required_permission:
            has_perm = check_permission(identity, tool.required_permission)
            if not has_perm:
                logger.warning(
                    f"PERMISSION DENIED: {identity.name} ({identity.full_id}, Role: {identity.role}) "
                    f"attempted to call '{tool_name}' which requires '{tool.required_permission}'."
                )
                return {
                    "status": "permission_denied",
                    "tool": tool_name,
                    "required_permission": tool.required_permission,
                    "employee_id": identity.full_id,
                    "employee_name": identity.name,
                    "role": identity.role,
                    "department": identity.department,
                    "message": (
                        f"Access Denied: Your account ({identity.name} - {identity.role}) "
                        f"lacks the '{tool.required_permission}' permission required to access '{tool_name}'. "
                        f"Please contact your Top Team / Admin if you require this authorization."
                    )
                }

        # 2. Execute with authenticated identity context
        try:
            result = tool.handler(identity, params)
            return result
        except Exception as e:
            logger.error(f"Error executing MCP tool '{tool_name}': {e}", exc_info=True)
            return {
                "status": "error",
                "tool": tool_name,
                "error": str(e)
            }

# Global singleton
mcp_registry = MCPRegistry()
