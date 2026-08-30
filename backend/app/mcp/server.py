"""MCP server for AI Agent CRUD operations on Maggie business records."""
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("maggie")

from app.mcp.tools.projects import register_project_tools
from app.mcp.tools.pricing_sheets import register_pricing_sheet_tools
from app.mcp.tools.collections import register_collection_tools
from app.mcp.tools.invoices import register_invoice_tools
from app.mcp.tools.master_budget import register_master_budget_tools

register_project_tools(mcp)
register_pricing_sheet_tools(mcp)
register_collection_tools(mcp)
register_invoice_tools(mcp)
register_master_budget_tools(mcp)
