from langchain_core.tools import tool
from typing import List, Dict, Any

@tool
def plan_odoo_environment(business_need: str, required_modules: List[str]) -> Dict[str, Any]:
    """
    Takes a business need and a list of required modules and returns a structured deployment plan.
    This tool is called by the agent after it has analyzed the user's request and determined the necessary modules.
    This tool does NOT provision the environment. It returns a structured plan for review.
    
    Args:
        business_need (str): The user's description of their business requirements.
        required_modules (List[str]): A list of Odoo module names identified by the agent as necessary.
    """
    module_list_str = ", ".join(required_modules)
    summary = (f"The following modules have been selected to meet your business need: {module_list_str}.")
    
    print("--- ODOO PLANNING TOOL ---")
    print(f"Business Need: {business_need}")
    print(f"Modules planned: {required_modules}")
    print("--------------------------")
    
    # Return a structured dictionary which is easier for the backend to parse.
    return {
        "modules": required_modules,
        "summary": summary
    }