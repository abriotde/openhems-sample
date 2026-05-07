
class Scheduler:
    def __init__(self):
        self.controllers = []
    
    def add_controller(self, ctrl: Controller):
        self.controllers.append(ctrl)
        self.controllers.sort(key=lambda c: c.priority)
    
    def tick(self, context: ControllerContext):
        for ctrl in self.controllers:
            if ctrl.enabled:
                ctrl.run(context)
        # Après tous les contrôleurs, appliquer les consignes
        self._apply_orders(context)

