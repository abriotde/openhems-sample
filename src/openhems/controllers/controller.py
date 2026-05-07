
class Controller(ABC):
    """Un contrôleur exécute une logique à chaque tick."""
    
    def __init__(self, name: str, enabled: bool = True, priority: int = 100):
        self.name = name
        self.enabled = enabled
        self.priority = priority  # Plus petit = plus prioritaire
    
    @abstractmethod
    def run(self, context: 'ControllerContext'):
        """Exécute la logique et modifie le contexte (consignes)."""
        pass

