from . import employee_tools
from . import hr_tools
from . import it_tools
from . import calendar_tools
from . import communication_tools
from . import document_tools

def register_all_connectors():
    """Initializes and registers all enterprise connectors."""
    employee_tools.register()
    hr_tools.register()
    it_tools.register()
    calendar_tools.register()
    communication_tools.register()
    document_tools.register()
